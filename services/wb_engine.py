import functools
import numpy as np
import pandas as pd
import requests

INDICATOR_REGISTRY = {
    "NY.GDP.MKTP.KD.ZG": {"name": "GDP Growth (Annual %)", "type": "rate", "unit": "%"},
    "NY.GDP.PCAP.CD": {"name": "GDP per Capita (Current US$)", "type": "level", "unit": " USD"},
    "FP.CPI.TOTL.ZG": {"name": "Inflation, Consumer Prices (Annual %)", "type": "rate", "unit": "%"},
    "SL.UEM.TOTL.ZS": {"name": "Unemployment (% of Total Labor Force)", "type": "rate", "unit": "%"},
    "IT.NET.USER.ZS": {"name": "Internet Usage (% of Population)", "type": "rate", "unit": "%"},
    "BX.KLT.DINV.WD.GD.ZS": {"name": "Foreign Direct Investment (% of GDP)", "type": "rate", "unit": "%"},
    "SP.DYN.LE00.IN": {"name": "Life Expectancy at Birth (Years)", "type": "level", "unit": " yrs"},
}

COUNTRY_REGISTRY = {
    "NGA": "Nigeria",
    "GHA": "Ghana",
    "KEN": "Kenya",
    "ZAF": "South Africa",
    "EGY": "Egypt",
    "RWA": "Rwanda",
    "BRA": "Brazil",
    "IND": "India",
}


@functools.lru_cache(maxsize=128)
def fetch_wb_indicator(countries_tuple: tuple, indicator_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    """
    Fetches raw indicator observations for multiple countries in a single request.
    Catches connection failures, timeouts, and API unavailability explicitly.
    """
    country_query = ";".join(countries_tuple).lower()
    url = f"https://api.worldbank.org/v2/country/{country_query}/indicator/{indicator_code}"
    params = {
        "date": f"{start_year}:{end_year}",
        "format": "json",
        "per_page": 2000,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            "Unable to connect to the internet or reach the World Bank API server. "
            "Please check your network connection and try again."
        )
    except requests.exceptions.Timeout:
        raise TimeoutError(
            "The World Bank API took too long to respond (request timed out). "
            "The remote service may be experiencing high traffic or degraded performance."
        )
    except requests.exceptions.HTTPError as http_err:
        status = http_err.response.status_code if http_err.response is not None else "Unknown"
        raise RuntimeError(
            f"World Bank API responded with HTTP error {status}. "
            "The endpoint may be down or the indicator query was rejected."
        )
    except requests.exceptions.RequestException as req_err:
        raise RuntimeError(f"Network transport error encountered while querying World Bank API: {req_err}")
    except ValueError:
        raise RuntimeError("Received invalid or non-JSON data from the World Bank API service.")

    # World Bank API returns: [metadata_dict, records_list]
    if not payload or len(payload) < 2 or not payload[1]:
        indicator_name = INDICATOR_REGISTRY.get(indicator_code, {}).get("name", indicator_code)
        raise ValueError(
            f"The World Bank has no recorded data for '{indicator_name}' across the selected countries "
            f"between {start_year} and {end_year}."
        )

    records = payload[1]
    rows = []
    for rec in records:
        rows.append({
            "country_code": rec.get("countryiso3code") or rec.get("country", {}).get("id", ""),
            "country_name": rec.get("country", {}).get("value", ""),
            "year": int(rec.get("date")),
            "value": rec.get("value")
        })

    df = pd.DataFrame(rows)
    df.sort_values(by=["country_code", "year"], inplace=True)
    return df


def clean_and_impute_series(df: pd.DataFrame, strategy: str = "forward_fill") -> pd.DataFrame:
    pivoted = df.pivot(index="year", columns="country_code", values="value")

    if strategy == "forward_fill":
        pivoted = pivoted.ffill().bfill()
    elif strategy == "drop":
        pivoted = pivoted.dropna()

    return pivoted


def build_peer_benchmark(countries: list, indicator: str, start_year: int, end_year: int, strategy: str) -> dict:
    raw_df = fetch_wb_indicator(tuple(sorted(countries)), indicator, start_year, end_year)
    metric_meta = INDICATOR_REGISTRY.get(indicator, {"name": indicator, "type": "level", "unit": ""})

    pivoted = clean_and_impute_series(raw_df, strategy=strategy)
    years = [int(y) for y in pivoted.index.tolist()]

    series = []
    for code in pivoted.columns:
        series.append({
            "country_code": code,
            "country_name": COUNTRY_REGISTRY.get(code, code),
            "years": years,
            "values": [None if np.isnan(v) else round(float(v), 2) for v in pivoted[code].tolist()]
        })

    momentum_rankings = []
    summary_table = []

    for code in pivoted.columns:
        s = pivoted[code].dropna()
        if s.empty:
            continue

        c_name = COUNTRY_REGISTRY.get(code, code)
        base_val = float(s.iloc[0])
        latest_val = float(s.iloc[-1])
        period_delta = latest_val - base_val
        std_dev = float(s.std()) if len(s) > 1 else 0.0

        if metric_meta["type"] == "level" and base_val > 0 and latest_val > 0:
            n_periods = max(1, len(s) - 1)
            cagr = ((latest_val / base_val) ** (1 / n_periods) - 1) * 100.0
            velocity_val = cagr
            velocity_label = "CAGR"
            unit = "%"
        else:
            velocity_val = period_delta
            velocity_label = "Period Δ"
            unit = metric_meta["unit"]

        momentum_rankings.append({
            "country_code": code,
            "country_name": c_name,
            "velocity_value": round(velocity_val, 2),
            "metric_type": velocity_label,
            "unit": unit
        })

        summary_table.append({
            "country_code": code,
            "country_name": c_name,
            "base_val": round(base_val, 2),
            "latest_val": round(latest_val, 2),
            "delta": round(period_delta, 2),
            "std_dev": round(std_dev, 2)
        })

    momentum_rankings.sort(key=lambda x: x["velocity_value"], reverse=True)

    return {
        "chart_payload": {
            "metric_title": metric_meta["name"],
            "series": series
        },
        "momentum_rankings": momentum_rankings,
        "peer_summary_table": summary_table,
        "primary_metric_name": metric_meta["name"]
    }


def build_bivariate_correlation(country: str, ind_x: str, ind_y: str, start_year: int, end_year: int, strategy: str) -> dict:
    df_x = fetch_wb_indicator((country,), ind_x, start_year, end_year)
    df_y = fetch_wb_indicator((country,), ind_y, start_year, end_year)

    meta_x = INDICATOR_REGISTRY.get(ind_x, {"name": ind_x, "unit": ""})
    meta_y = INDICATOR_REGISTRY.get(ind_y, {"name": ind_y, "unit": ""})

    piv_x = clean_and_impute_series(df_x, strategy=strategy)[country].rename("x")
    piv_y = clean_and_impute_series(df_y, strategy=strategy)[country].rename("y")

    aligned = pd.concat([piv_x, piv_y], axis=1).dropna()
    if len(aligned) < 3:
        raise ValueError(
            f"Only {len(aligned)} intersecting data point(s) found between '{meta_x['name']}' "
            f"and '{meta_y['name']}' for {COUNTRY_REGISTRY.get(country, country)}. "
            "At least 3 complete annual pairs are required for correlation analysis."
        )

    x_vals = aligned["x"].to_numpy(dtype=float)
    y_vals = aligned["y"].to_numpy(dtype=float)
    years = [int(y) for y in aligned.index.tolist()]

    corr_matrix = np.corrcoef(x_vals, y_vals)
    r_value = float(corr_matrix[0, 1])

    slope, intercept = np.polyfit(x_vals, y_vals, deg=1)
    line_x = np.linspace(np.min(x_vals), np.max(x_vals), num=20)
    line_y = slope * line_x + intercept

    abs_r = abs(r_value)
    if abs_r >= 0.7:
        strength = "Strong"
    elif abs_r >= 0.4:
        strength = "Moderate"
    else:
        strength = "Weak / Decoupled"

    direction = "positive" if r_value > 0 else "inverse (negative)"
    interpretation = (
        f"A {strength.lower()} {direction} correlation (r = {r_value:.2f}). "
        f"Higher values of {meta_x['name']} generally track "
        f"{'elevated' if r_value > 0 else 'dampened'} levels of {meta_y['name']} over this timeframe."
    )

    return {
        "chart_payload": {
            "years": years,
            "primary_label": meta_x["name"],
            "secondary_label": meta_y["name"],
            "primary_series": [round(float(v), 2) for v in x_vals],
            "secondary_series": [round(float(v), 2) for v in y_vals],
            "trendline_x": [round(float(v), 2) for v in line_x],
            "trendline_y": [round(float(v), 2) for v in line_y],
        },
        "correlation_r": r_value,
        "correlation_strength": strength,
        "correlation_interpretation": interpretation,
        "country_name": COUNTRY_REGISTRY.get(country, country),
        "primary_metric_name": meta_x["name"],
        "secondary_metric_name": meta_y["name"],
        "primary_latest_val": f"{round(float(x_vals[-1]), 2)}{meta_x['unit']}",
        "secondary_latest_val": f"{round(float(y_vals[-1]), 2)}{meta_y['unit']}"
    }
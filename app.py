from flask import Flask, render_template, request, redirect, url_for, flash
from services import (
    build_peer_benchmark,
    build_bivariate_correlation,
)

app = Flask(__name__)
app.secret_key = "macropulse-dev-secret-key"


@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # 1. Parameter extraction
    selected_countries = request.form.getlist("countries")
    primary_metric = request.form.get("primary_metric")
    secondary_metric = request.form.get("secondary_metric")

    try:
        start_year = int(request.form.get("start_year", 2010))
        end_year = int(request.form.get("end_year", 2024))
    except ValueError:
        flash("Start Year and End Year must be valid integers.", "warning")
        return redirect(url_for("home"))

    interpolation = request.form.get("interpolation", "forward_fill")

    # 2. Input validation guards
    if not selected_countries:
        flash("Please select at least one country to analyze.", "warning")
        return redirect(url_for("home"))

    if start_year >= end_year:
        flash("Start Year must be strictly earlier than End Year.", "warning")
        return redirect(url_for("home"))

    # 3. Execution & Granular Exception Handling
    try:
        # Route 1: Single-Country Correlation Mode
        if len(selected_countries) == 1:
            country = selected_countries[0]
            if not secondary_metric:
                flash("Please select a secondary indicator for single-country correlation analysis.", "warning")
                return redirect(url_for("home"))

            context = build_bivariate_correlation(
                country=country,
                ind_x=primary_metric,
                ind_y=secondary_metric,
                start_year=start_year,
                end_year=end_year,
                strategy=interpolation
            )
            context.update({
                "is_single_country": True,
                "start_year": start_year,
                "end_year": end_year
            })
            return render_template("analysis.html", **context)

        # Route 2: Multi-Country Peer Benchmark Mode
        else:
            context = build_peer_benchmark(
                countries=selected_countries,
                indicator=primary_metric,
                start_year=start_year,
                end_year=end_year,
                strategy=interpolation
            )
            context.update({
                "is_single_country": False,
                "start_year": start_year,
                "end_year": end_year
            })
            return render_template("analysis.html", **context)

    except (ConnectionError, TimeoutError) as net_err:
        flash(f"Network Failure: {str(net_err)}", "danger")
        return redirect(url_for("home"))

    except ValueError as val_err:
        flash(f"Data Availability Issue: {str(val_err)}", "warning")
        return redirect(url_for("home"))

    except Exception as general_err:
        flash(f"Unexpected Processing Error: {str(general_err)}", "danger")
        return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
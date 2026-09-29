# MacroPulse | World Bank Economic Intelligence Platform

A decision-support web application that ingests, cleans, and computes comparative macroeconomic analytics directly from the World Bank API ecosystem.

Unlike static dashboards, MacroPulse serves as an end-to-end analytical pipeline: extracting multi-country indicator time series, standardizing mismatched reporting intervals, computing statistical momentum metrics (CAGR, point deltas, volatility), and executing bivariate OLS regression modeling on demand.

---

## Key Features

- **Multi-Peer Macro Benchmarking:** Select 2 to 5 economies (e.g., Nigeria, Ghana, Kenya, South Africa) to evaluate comparative multi-year trajectories across key economic development metrics.
- **Economic Velocity & Momentum Scoring:** Evaluates real growth momentum using Compound Annual Growth Rate (CAGR) for level indicators (such as GDP per capita) and absolute point delta ($\Delta$) for percentage rates (such as Inflation and Unemployment).
- **Single-Country Bivariate Correlation:** Run deep-dive empirical checks on single economies (e.g., *Nigeria: Inflation vs. GDP Growth*). Computes Pearson correlation coefficient ($r$) alongside an Ordinary Least Squares (OLS) regression line and diagnostic summary.
- **Resilient Pipeline & Edge Caching:** 
  - Batched API queries using semicolon-delimited ISO3 country queries to minimize network overhead.
  - In-memory LRU caching to eliminate repeated API roundtrips.
  - Forward-fill/backward-fill temporal imputation routines to handle missing survey years.
  - Granular fault tolerance isolating network drops, timeouts, and API schema errors with contextual alert banners.

---

## Tech Stack

- **Backend:** Python, Flask
- **Data Engineering & Math:** Pandas, NumPy, Requests
- **Visualization:** Plotly.js (Dual-axis time-series, OLS regression scatter plots)
- **Frontend / Styling:** Jinja2 templates, Bootstrap 5.3, Bootstrap Icons
- **Data Source:** [World Bank Indicators API v2](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation)

---

## Project Structure

```text
macropulse/
├── app.py                  # Application entry point & Flask route controllers
├── requirements.txt        # Pinned dependency manifest
├── README.md               # Documentation
├── services/
│   ├── __init__.py         # Package interface & explicit public exports
│   └── wb_engine.py        # API client, imputation layer, statistical computation
└── templates/
    ├── base.html           # Master layout with SVG favicon, styling & alerts
    ├── home.html           # Interactive parameter configuration & preset controls
    └── analysis.html       # Dual-view visualization & diagnostic reporting engine

## Installation & Local Setup Guide

Follow these steps sequentially to set up your virtual environment, install required dependencies, and launch the application locally.

---

### 1. Prerequisites

- **Python 3.10+** installed on your system.
- An active internet connection (required to pull indicator datasets from the World Bank API).

---

### 2. Create and Activate Virtual Environment

Open your terminal or PowerShell, navigate to the project root directory, and run:

```bash
# Create the virtual environment named 'venv'
python -m venv venv


### 3. Install Dependencies

You can install the packages directly from the command line or generate a `requirements.txt` file first.

Run the following pip command in your activated environment:

```bash
pip install Flask requests pandas numpy
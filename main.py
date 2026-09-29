import os

from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException
from flask_bootstrap import Bootstrap5
from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET-KEY", "GEID-dev-key")
Bootstrap5(app)


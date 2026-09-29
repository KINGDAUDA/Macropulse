"""Services package for World Bank data extraction, pipeline transformation, and analytics."""

from .wb_engine import (
    build_peer_benchmark,
    build_bivariate_correlation,
    INDICATOR_REGISTRY,
    COUNTRY_REGISTRY,
)

__all__ = [
    "build_peer_benchmark",
    "build_bivariate_correlation",
    "INDICATOR_REGISTRY",
    "COUNTRY_REGISTRY",
]
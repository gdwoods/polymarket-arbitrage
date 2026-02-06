"""Arbitrage detection and optimization."""

from .single_condition import detect_single_condition_arbitrage
from .bregman import bregman_projection_lmsr

__all__ = ["detect_single_condition_arbitrage", "bregman_projection_lmsr"]
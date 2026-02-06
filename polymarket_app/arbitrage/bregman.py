"""
Bregman projection for arbitrage-free pricing.

For LMSR (Logarithmic Market Scoring Rule), the Bregman divergence
is the Kullback-Leibler divergence. The projection mu* onto the
marginal polytope M gives the arbitrage-free price vector.
"""

import numpy as np
from scipy.optimize import minimize


def kl_divergence(mu: np.ndarray, theta: np.ndarray, eps: float = 1e-10) -> float:
    theta_safe = np.clip(theta, eps, 1 - eps)
    mu_safe = np.clip(mu, eps, 1 - eps)
    return np.sum(mu_safe * (np.log(mu_safe) - np.log(theta_safe)))


def bregman_projection_lmsr(
    theta: np.ndarray,
    equality_constraints: np.ndarray,
    equality_values: np.ndarray,
    bounds: tuple[float, float] = (1e-6, 1 - 1e-6),
    max_iter: int = 500,
) -> tuple[np.ndarray, bool]:
    n = len(theta)
    theta = np.asarray(theta, dtype=float)

    def objective(mu: np.ndarray) -> float:
        return kl_divergence(mu, theta)

    constraints = [{"type": "eq", "fun": lambda m: equality_constraints @ m - equality_values}]
    bnds = [(bounds[0], bounds[1]) for _ in range(n)]
    res = minimize(
        objective,
        x0=np.clip(theta, bounds[0], bounds[1]),
        method="SLSQP",
        bounds=bnds,
        constraints=constraints,
        options={"maxiter": max_iter, "ftol": 1e-9},
    )
    return res.x, res.success


def frank_wolfe_oracle(
    gradient: np.ndarray,
    constraint_matrix: np.ndarray,
    constraint_rhs: np.ndarray,
) -> np.ndarray:
    i = np.argmin(gradient)
    z = np.zeros_like(gradient)
    z[i] = 1.0
    return z
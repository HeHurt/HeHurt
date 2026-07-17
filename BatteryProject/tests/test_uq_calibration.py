"""Closed-loop validation for M1 uncertainty-quantified calibration.

Uses an analytic capacity-fade model (no PyBaMM) so the test is fast and
exercises only the UQ layer. Truth is recovered from noisy synthetic data and
we check that the 95% CI covers it, and that a near-degenerate parameter pair
shows up as strong posterior correlation.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.uq_calibration import run_emcee, run_ensemble_fit


# Truth: retention(n) = 1 - (a*sqrt(n) + b*n). Early cycles -> a,b hard to separate.
A_TRUE, B_TRUE = 0.010, 0.0008
N_CYCLES = 80
RNG = np.random.default_rng(42)


def _retention(a: float, b: float, n: np.ndarray) -> np.ndarray:
    return 1.0 - (a * np.sqrt(n) + b * n)


N_GRID = np.arange(1, N_CYCLES + 1, dtype=float)
Y_OBS = _retention(A_TRUE, B_TRUE, N_GRID) + 0.001 * RNG.standard_normal(N_GRID.size)

CHANGE_PARAMS = {
    "a": ["user", "line", 0.001, 0.05],
    "b": ["user", "line", 0.0001, 0.005],
}


def objective(search_params: dict[str, float]) -> float:
    """Same contract as build_aging_objective: returns fitness = 1/loss."""
    y = _retention(search_params["a"], search_params["b"], N_GRID)
    rmse = float(np.sqrt(np.mean((y - Y_OBS) ** 2)))
    return 1.0 / (rmse + 1e-6)


def test_emcee_recovers_truth_within_ci():
    res = run_emcee(
        objective,
        CHANGE_PARAMS,
        sigma=0.001,  # matches synthetic noise scale
        n_walkers=16,
        n_steps=600,
        n_burn=300,
        init={"a": A_TRUE, "b": B_TRUE},
        seed=1,
    )
    summ = res.summary(cred=0.95)
    # summ is a DataFrame (pandas available in this project)
    a_lo, a_hi = summ.loc["a", "p2.5"], summ.loc["a", "p97.5"]
    b_lo, b_hi = summ.loc["b", "p2.5"], summ.loc["b", "p97.5"]
    assert a_lo <= A_TRUE <= a_hi, f"a truth {A_TRUE} not in CI [{a_lo},{a_hi}]"
    assert b_lo <= B_TRUE <= b_hi, f"b truth {B_TRUE} not in CI [{b_lo},{b_hi}]"


def test_degeneracy_shows_as_correlation():
    res = run_emcee(
        objective, CHANGE_PARAMS, sigma=0.001,
        n_walkers=16, n_steps=600, n_burn=300,
        init={"a": A_TRUE, "b": B_TRUE}, seed=2,
    )
    corr, keys = res.correlation()
    i, j = keys.index("a"), keys.index("b")
    # sqrt vs linear fade are strongly (negatively) coupled -> degeneracy signal.
    assert abs(corr[i, j]) > 0.5, f"expected strong a-b correlation, got {corr[i, j]:.2f}"


def test_ensemble_baseline_runs():
    res = run_ensemble_fit(
        objective, CHANGE_PARAMS, n_starts=20, method="MO", seed=3, keep_quantile=0.5,
    )
    assert res.samples_search.shape[0] >= 5
    summ = res.summary()
    # Median should be in the right ballpark of truth.
    assert 0.001 <= summ.loc["a", "median"] <= 0.05

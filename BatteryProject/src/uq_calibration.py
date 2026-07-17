"""Uncertainty-quantified aging calibration (Milestone M1).

This module sits *on top of* :mod:`parameter_identification`. Instead of finding
a single best-fit point (``run_parameter_optimization``), it samples the
parameter posterior so the platform can report:

- parameter posterior + credible intervals (95% CI),
- parameter correlation matrix (the degeneracy / non-identifiability signal),
- posterior-predictive capacity bands.

Likelihood model
----------------
The existing ``build_aging_objective`` returns ``fitness = 1 / mean_loss`` where
``mean_loss`` is an RMSE-like residual statistic between simulated and measured
capacity-fade curves. We treat that residual scale ``r = mean_loss`` as the
input to a Gaussian likelihood::

    log L = -0.5 * (r / sigma) ** 2

with ``sigma`` the assumed measurement-noise scale on the loss metric. The prior
is uniform over the same search bounds used by the optimizer. This keeps the UQ
layer fully reusing the existing objective without touching it. ``sigma`` is the
one knob that sets posterior width; M3 will replace this aggregate likelihood
with a per-point residual likelihood.

Two engines are provided so they can be compared on synthetic data:

- :func:`run_emcee` — ensemble MCMC (rigorous main path).
- :func:`run_ensemble_fit` — many random-restart optimizations whose optima
  approximate the distribution (fast baseline, reuses existing optimizers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from .parameter_identification import (
    _parse_change_params,
    _to_search_space,
    _vector_to_param_dict,
    run_parameter_optimization,
)


@dataclass
class PosteriorResult:
    """Container for a posterior calibration run."""

    engine: str
    keys: list[str]
    scales: dict[str, str]
    samples_search: np.ndarray  # (n_samples, n_dim) in optimizer/search space
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def samples_physical(self) -> np.ndarray:
        """Samples mapped back to physical space (10**x for log params)."""
        out = np.array(self.samples_search, dtype=float, copy=True)
        for j, k in enumerate(self.keys):
            if self.scales[k] == "log":
                out[:, j] = np.power(10.0, out[:, j])
        return out

    def summary(self, cred: float = 0.95) -> "Any":
        """Return a per-parameter summary table (median + credible interval).

        Uses pandas if available, else a list of dicts.
        """
        lo_q = (1.0 - cred) / 2.0 * 100.0
        hi_q = (1.0 + cred) / 2.0 * 100.0
        phys = self.samples_physical
        rows = []
        for j, k in enumerate(self.keys):
            col = phys[:, j]
            rows.append(
                {
                    "parameter": k,
                    "scale": self.scales[k],
                    "median": float(np.median(col)),
                    f"p{lo_q:g}": float(np.percentile(col, lo_q)),
                    f"p{hi_q:g}": float(np.percentile(col, hi_q)),
                    "std": float(np.std(col)),
                }
            )
        try:
            import pandas as pd

            return pd.DataFrame(rows).set_index("parameter")
        except ImportError:
            return rows

    def correlation(self) -> tuple[np.ndarray, list[str]]:
        """Posterior correlation matrix in *search* space.

        High |corr| between two parameters is the non-identifiability / degenerate
        -solution signal: the data cannot separate them.
        """
        s = self.samples_search
        if s.shape[0] < 2:
            return np.eye(len(self.keys)), self.keys
        corr = np.corrcoef(s, rowvar=False)
        return np.atleast_2d(corr), self.keys


def _build_search_meta(change_params: dict[str, Any]):
    specs = _parse_change_params(change_params)
    bounds = _to_search_space(specs)  # search-space bounds (log10 for log params)
    keys = list(bounds.keys())
    lo = np.array([bounds[k][0] for k in keys], dtype=float)
    hi = np.array([bounds[k][1] for k in keys], dtype=float)
    scales = {k: specs[k].scale for k in keys}
    return keys, lo, hi, scales


def make_log_prob(
    objective: Callable[[dict[str, float]], float],
    change_params: dict[str, Any],
    sigma: float,
    fail_loss: float = 100.0,
):
    """Build ``log_prob(x_vec)`` for emcee plus the search-space metadata.

    Parameters
    ----------
    objective:
        The function returned by ``build_aging_objective`` (fitness = 1/loss).
    sigma:
        Assumed measurement-noise scale on the loss metric. Sets posterior width.
    """
    keys, lo, hi, scales = _build_search_meta(change_params)
    inv_two_sig2 = 0.5 / float(sigma) ** 2

    def log_prob(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        if np.any(x < lo) or np.any(x > hi):
            return -np.inf  # uniform prior support
        fitness = objective(_vector_to_param_dict(x, keys))
        if not np.isfinite(fitness) or fitness <= 0:
            return -np.inf
        loss = 1.0 / fitness
        if not np.isfinite(loss):
            return -np.inf
        return -inv_two_sig2 * loss * loss

    return log_prob, keys, lo, hi, scales


def run_emcee(
    objective: Callable[[dict[str, float]], float],
    change_params: dict[str, Any],
    sigma: float,
    n_walkers: int | None = None,
    n_steps: int = 400,
    n_burn: int | None = None,
    init: dict[str, float] | None = None,
    seed: int = 0,
    progress: bool = False,
) -> PosteriorResult:
    """Sample the parameter posterior with ensemble MCMC (emcee).

    Returns a :class:`PosteriorResult` with flattened post-burn-in samples.
    """
    import emcee

    log_prob, keys, lo, hi, scales = make_log_prob(objective, change_params, sigma)
    n_dim = len(keys)
    if n_walkers is None:
        n_walkers = max(2 * n_dim + 2, 8)
    if n_burn is None:
        n_burn = n_steps // 2

    rng = np.random.default_rng(seed)
    # Initialize walkers: a tight ball around `init` if given, else uniform in box.
    if init is not None:
        x0 = np.array(
            [float(init[k]) if k in init else 0.5 * (lo[i] + hi[i]) for i, k in enumerate(keys)]
        )
        span = 0.05 * (hi - lo)
        p0 = x0[None, :] + span[None, :] * rng.standard_normal((n_walkers, n_dim))
        p0 = np.clip(p0, lo, hi)
    else:
        p0 = lo[None, :] + rng.random((n_walkers, n_dim)) * (hi - lo)[None, :]

    sampler = emcee.EnsembleSampler(n_walkers, n_dim, log_prob)
    sampler.run_mcmc(p0, n_steps, progress=progress)

    samples = sampler.get_chain(discard=n_burn, flat=True)
    try:
        tau = sampler.get_autocorr_time(tol=0)
        acc = float(np.mean(sampler.acceptance_fraction))
    except Exception:
        tau, acc = None, float(np.mean(sampler.acceptance_fraction))

    return PosteriorResult(
        engine="emcee",
        keys=keys,
        scales=scales,
        samples_search=samples,
        extra={
            "sigma": sigma,
            "n_walkers": n_walkers,
            "n_steps": n_steps,
            "n_burn": n_burn,
            "acceptance_fraction": acc,
            "autocorr_time": None if tau is None else np.asarray(tau).tolist(),
            "sampler": sampler,
        },
    )


def run_ensemble_fit(
    objective: Callable[[dict[str, float]], float],
    change_params: dict[str, Any],
    n_starts: int = 50,
    method: str = "MO",
    method_params: dict[str, Any] | None = None,
    seed: int = 0,
    keep_quantile: float = 1.0,
) -> PosteriorResult:
    """Random-restart optimization baseline.

    Runs ``run_parameter_optimization`` from ``n_starts`` random initial points
    and collects the optima. The spread of optima is a cheap, statistically
    looser proxy for posterior uncertainty. Useful as a fast cross-check on the
    emcee result.

    ``keep_quantile`` (0-1): keep only the best fraction of fits by fitness, to
    drop runs stuck in poor local optima.
    """
    keys, lo, hi, scales = _build_search_meta(change_params)
    rng = np.random.default_rng(seed)

    opt_vecs: list[np.ndarray] = []
    fitnesses: list[float] = []
    for _ in range(int(n_starts)):
        x0 = lo + rng.random(len(keys)) * (hi - lo)
        init = _vector_to_param_dict(x0, keys)
        res = run_parameter_optimization(
            objective, change_params, method=method, method_params=method_params, init=init
        )
        best = res["best_params"]
        opt_vecs.append(np.array([best[k] for k in keys], dtype=float))
        fitnesses.append(float(res["best_fitness"]))

    opt = np.array(opt_vecs, dtype=float)
    fit = np.array(fitnesses, dtype=float)

    if keep_quantile < 1.0 and opt.shape[0] > 2:
        thresh = np.quantile(fit, 1.0 - keep_quantile)
        mask = fit >= thresh
        opt, fit = opt[mask], fit[mask]

    return PosteriorResult(
        engine="ensemble_fit",
        keys=keys,
        scales=scales,
        samples_search=opt,
        extra={"fitness": fit.tolist(), "method": method, "n_starts": n_starts},
    )


def plot_correlation(result: PosteriorResult, ax=None, threshold: float = 0.8):
    """Heatmap of the posterior correlation matrix.

    Cells with |corr| >= ``threshold`` are annotated as degeneracy warnings.
    """
    import matplotlib.pyplot as plt

    corr, keys = result.correlation()
    if ax is None:
        _, ax = plt.subplots(figsize=(1.2 * len(keys) + 2, 1.2 * len(keys) + 1))

    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(keys)))
    ax.set_yticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=45, ha="right")
    ax.set_yticklabels(keys)
    for i in range(len(keys)):
        for j in range(len(keys)):
            v = corr[i, j]
            flag = "!" if (i != j and abs(v) >= threshold) else ""
            ax.text(j, i, f"{v:.2f}{flag}", ha="center", va="center",
                    color="white" if abs(v) > 0.5 else "black", fontsize=8)
    ax.set_title("Posterior parameter correlation\n(|corr|>=%.2f marked ! = degeneracy)" % threshold)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return ax


def posterior_predictive(
    result: PosteriorResult,
    simulate_fn: Callable[[dict[str, dict[str, float]]], Any],
    change_params: dict[str, Any],
    extract_fn: Callable[[Any], np.ndarray],
    fixed_input_params: dict[str, dict[str, float]] | None = None,
    n_draws: int = 50,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Run the forward model over posterior draws to get a predictive band.

    ``extract_fn`` maps a simulation output to a 1-D curve (e.g. normalized
    capacity vs cycle). Returns dict with stacked curves and percentile bands.
    Curves are aligned by index; ragged lengths are truncated to the shortest.
    """
    from .parameter_identification import params_to_model_input

    rng = np.random.default_rng(seed)
    s = result.samples_search
    idx = rng.choice(s.shape[0], size=min(n_draws, s.shape[0]), replace=False)

    curves: list[np.ndarray] = []
    for i in idx:
        search = _vector_to_param_dict(s[i], result.keys)
        model_input = params_to_model_input(search, change_params, fixed_input_params)
        try:
            sim = simulate_fn(model_input)
            y = np.asarray(extract_fn(sim), dtype=float)
        except Exception:
            continue
        if y.size > 1:
            curves.append(y)

    if not curves:
        return {"curves": np.empty((0, 0)), "median": np.array([]),
                "lower": np.array([]), "upper": np.array([])}

    n_min = min(len(c) for c in curves)
    stack = np.array([c[:n_min] for c in curves], dtype=float)
    return {
        "curves": stack,
        "median": np.median(stack, axis=0),
        "lower": np.percentile(stack, 2.5, axis=0),
        "upper": np.percentile(stack, 97.5, axis=0),
    }

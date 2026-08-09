"""Growth formulas: the mathematics of beating a benchmark, from the fields
that solved the problem before finance did.

WHY THIS MODULE EXISTS
----------------------
The repo's own forensics (BACKTEST-REPORT.md "Weekly loss forensics",
"Are the gates the edge?") measured three things and they are all the same
thing said three ways:

  1. the composite ranking does not sort forward returns (decile 1 minus
     decile 10 = -0.26% at 42 td),
  2. the gates are a defensiveness overlay, not a return source
     (beta 0.77, CAGR -1.76pp vs the ungated control),
  3. concentrating the book destroyed 0.128%/wk of compounding through
     variance drag alone.

Point 3 is the tell. The engine's objective was P(touch +5% inside 42 td) --
a FIRST-PASSAGE statistic. First passage is driven by volatility, not by
drift. So the engine was, by construction, selecting for variance; and
variance is subtracted from long-run growth, not added to it:

    g = mu - sigma^2 / 2                            (`growth_rate`)

Every formula below exists to attack one term of that identity, or to
decide honestly whether an attack worked. None of them is a stock-picking
signal, because ten years of this repo's own data say the stock-picking
layer has no measurable spread. The lever is portfolio GEOMETRY, and the
size of that lever is set by one equation:

    at leverage L on an edge with Sharpe S,   g(L) = L*S*sigma - L^2*sigma^2/2
    maximised at  L* = mu/sigma^2  ->  g* = S^2 / 2   (`optimal_leverage`)

Growth is QUADRATIC in Sharpe. Doubling Sharpe quadruples achievable
growth. That is the only honest route to "beat the market by a landslide",
and it says the research target is Sharpe -- not hit rate, not average
return, not how often a pick touches +5%.

Sharpe, in turn, is bought with breadth rather than skill:

    IR = IC * sqrt(BR) * TC                         (`grinold_ir`)
    S_portfolio = w'S / sqrt(w'Cw)                  (`combine_sharpe`)

Two uncorrelated sleeves of Sharpe 0.6 combine to 0.85; four to 1.20. That
arithmetic, not a better ranking, is where a landslide can legitimately
come from.

CONVENTIONS
-----------
- All `mu`/`sigma`/`returns` arguments are EXCESS (over cash) and in the
  SAME period units unless a function's docstring says otherwise; helpers
  that annualise say so explicitly and take `periods_per_year`.
- Every estimator here is CAUSAL: a value at index t uses data through
  t-1 only, so a lab can shift a signal by one bar and be safe. The two
  exceptions are `ledoit_wolf_cov`, `hrp_weights` and `ou_half_life`,
  which are fitted on a window the caller supplies -- the caller is
  responsible for that window ending before the period being predicted.
- Pure numpy/pandas. No scipy: the normal CDF/quantile are implemented
  here so the module has no dependency the repo does not already carry.

Nothing in this module is fitted to this repo's data. Every constant is
either a definition, or a value frozen from the cited literature.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329
TD_YEAR = 252


# --------------------------------------------------------------------------
# 0. Normal distribution (no scipy dependency)
# --------------------------------------------------------------------------

def norm_cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Standard normal quantile (Acklam's rational approximation, then one
    Halley refinement -- accurate to ~1e-15, plenty for a ship gate)."""
    if not 0.0 < p < 1.0:
        raise ValueError("norm_ppf needs 0 < p < 1")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    else:
        q, r = p - 0.5, (p - 0.5) ** 2
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


# --------------------------------------------------------------------------
# 1. The growth identity  (information theory: Kelly 1956, Shannon)
# --------------------------------------------------------------------------

def growth_rate(mu: float, sigma: float) -> float:
    """Long-run compounded growth of a return stream: g = mu - sigma^2/2.

    The single most consequential formula in this file. `mu` is the
    ARITHMETIC mean excess return; `g` is what actually compounds. The gap
    between them is variance drag, and it is what the weekly forensics
    measured at 0.128%/wk for the top-1 book (~6.6%/yr of pure loss)."""
    return mu - 0.5 * sigma * sigma


def optimal_leverage(mu: float, sigma: float) -> float:
    """Full-Kelly leverage L* = mu / sigma^2. At L*, g = S^2/2 where
    S = mu/sigma. Growth is QUADRATIC in Sharpe -- the whole argument for
    targeting Sharpe rather than return."""
    if sigma <= 0:
        return 0.0
    return mu / (sigma * sigma)


def growth_at_leverage(mu: float, sigma: float, leverage: float) -> float:
    """g(L) = L*mu - L^2 sigma^2 / 2. Note g(2L*) = 0: twice Kelly earns
    NOTHING while carrying double the risk. That asymmetry is why every
    practitioner runs a fraction of Kelly."""
    return leverage * mu - 0.5 * leverage * leverage * sigma * sigma


def kelly_fraction_for_drawdown(max_dd: float, prob: float = 0.10) -> float:
    """Fraction of full Kelly whose probability of EVER falling to
    (1 - max_dd) times the STARTING stake equals `prob`.

    For a GBM at fraction f of full Kelly the log-drift is
    nu = (mu^2/sigma^2)(f - f^2/2) against variance f^2 mu^2/sigma^2, so
    2*nu/sigma_p^2 = 2/f - 1, and the running-minimum result gives

        P(ever down by q) = (1 - q)^(2/f - 1)
        =>  f = 2 ln(1-q) / ( ln(1-q) + ln P )

    Sanity: f = 1 gives exponent 1, i.e. full Kelly carries a 50% chance of
    halving the stake -- the classic result, which no human holds through.

    This is the bet-hedging constraint from evolutionary ecology written in
    finance notation: maximise geometric growth SUBJECT TO surviving the bad
    state. Note it bounds drawdown from the START, not from a running peak:
    over an infinite horizon a positive-drift process makes new highs
    forever, so it eventually gives back any fixed fraction of SOME peak
    with probability 1. Peak-to-trough risk is a horizon question and must
    be simulated, not solved."""
    if not 0 < max_dd < 1 or not 0 < prob < 1:
        raise ValueError("need 0<max_dd<1 and 0<prob<1")
    lq = math.log(1.0 - max_dd)
    return 2.0 * lq / (lq + math.log(prob))


def kelly_shrinkage(sharpe: float, n_assets: int, n_obs: int) -> float:
    """Fraction of Kelly that survives ESTIMATION error.

    With N assets estimated over T observations, the out-of-sample growth
    of the plug-in Kelly rule is maximised at roughly

        lambda* = S^2 / (S^2 + N/T)

    i.e. the more parameters and the shorter the sample, the smaller the
    bet. A 4-sleeve book with S=1.0 on 10 years of daily data
    (N/T = 4/2520) shrinks almost not at all; a 500-stock covariance on the
    same sample shrinks to nearly zero -- which is the formal statement of
    why per-stock Kelly on this repo's universe is not available."""
    if n_obs <= 0 or n_assets <= 0:
        return 0.0
    s2 = sharpe * sharpe
    return s2 / (s2 + n_assets / n_obs) if s2 > 0 else 0.0


def kelly_weights(mu: np.ndarray, cov: np.ndarray, fraction: float = 1.0,
                  max_gross: float | None = None,
                  long_only: bool = False) -> np.ndarray:
    """Growth-optimal weights f = fraction * Sigma^-1 mu, with optional
    gross-exposure cap and long-only projection.

    `mu` and `cov` must be in the same period units. Uses the pseudo-inverse
    because a shrunk covariance can still be near-singular; pair it with
    `ledoit_wolf_cov` in anything real -- raw Sigma^-1 on a noisy sample
    covariance is the canonical way to blow up a Kelly book."""
    mu = np.asarray(mu, float).reshape(-1)
    cov = np.asarray(cov, float)
    w = fraction * np.linalg.pinv(cov) @ mu
    if long_only:
        w = np.clip(w, 0.0, None)
    if max_gross is not None:
        gross = np.abs(w).sum()
        if gross > max_gross and gross > 0:
            w = w * (max_gross / gross)
    return w


# --------------------------------------------------------------------------
# 2. Breadth  (Grinold's fundamental law -- the "what should we even build"
#    formula, and the reason a 3-stock book cannot win)
# --------------------------------------------------------------------------

def grinold_ir(ic: float, breadth: float, transfer: float = 1.0) -> float:
    """IR = IC * sqrt(BR) * TC.

    IC = cross-sectional correlation between forecast and realised return.
    BR = number of INDEPENDENT bets per year. TC = transfer coefficient,
    the correlation between the ideal and the implemented portfolio
    (constraints, costs and long-only all cut it; long-only alone is
    typically TC ~ 0.5-0.6).

    Applied to this repo as it stands: a top-2 book rebalanced ~12x/yr is
    BR ~ 24 and long-only TC ~ 0.55, so even a genuinely good IC of 0.05
    yields IR = 0.05*sqrt(24)*0.55 = 0.13. The measured IC was ~0. The law
    says the deficiency is structural -- 2 names is not a strategy, it is a
    sample of size 2 -- and that breadth is cheaper to buy than skill."""
    return ic * math.sqrt(max(breadth, 0.0)) * transfer


def required_ic(target_ir: float, breadth: float, transfer: float = 1.0) -> float:
    """The IC you would need for a target IR at a given breadth. Run this
    BEFORE building a signal: if the answer is an IC nobody in the
    literature has ever achieved out of sample (> ~0.10), the project is
    dead on arrival and the honest move is to buy breadth instead."""
    if breadth <= 0 or transfer <= 0:
        return float("inf")
    return target_ir / (math.sqrt(breadth) * transfer)


def combine_sharpe(sharpes, corr, weights=None) -> float:
    """Sharpe of a weighted combination of sleeves: S_p = w'S / sqrt(w'Cw).

    The arithmetic of the landslide. Weights are risk weights (each sleeve
    already scaled to the same volatility), defaulting to equal."""
    s = np.asarray(sharpes, float).reshape(-1)
    c = np.asarray(corr, float)
    w = np.full(len(s), 1.0 / len(s)) if weights is None else \
        np.asarray(weights, float).reshape(-1)
    denom = math.sqrt(float(w @ c @ w))
    return float(w @ s) / denom if denom > 0 else 0.0


def best_long_only_sharpe(sharpes, corr, n_grid: int = 201) -> float:
    """Highest Sharpe reachable by a LONG-ONLY risk-weighted combination.

    The unconstrained maximum, sqrt(S' C^-1 S), is the wrong answer for this
    repo's purposes: as rho rises it starts SHORTING one sleeve against the
    other, so a candidate that merely resembles the existing book scores as
    if it were a statistical-arbitrage pair. You cannot short your own book,
    and a research agenda ranked on that arithmetic would put near-duplicates
    at the top. Restricting weights to the simplex removes the artifact.

    Two sleeves are grid-searched exactly; more are evaluated at equal risk
    weight, which is what a real risk-parity book actually holds."""
    s = np.asarray(sharpes, float).reshape(-1)
    c = np.asarray(corr, float)
    if len(s) == 1:
        return float(s[0])
    if len(s) == 2:
        best = 0.0
        for w in np.linspace(0.0, 1.0, n_grid):
            best = max(best, combine_sharpe(s, c, [1 - w, w]))
        return float(best)
    return combine_sharpe(s, c)


def equal_weight_sharpe(n: int, sharpe: float, rho: float) -> float:
    """Closed form of `combine_sharpe` for n identical sleeves with a common
    pairwise correlation rho:  S_p = S * sqrt(n) / sqrt(1 + (n-1) rho).

    rho=0:  four Sharpe-0.6 sleeves -> 1.20.
    rho=0.3: the same four -> 0.87.
    rho=1:  -> 0.60, no matter how many you add.
    Correlation, not count, is the binding constraint on diversification --
    which is why the next sleeve should be chosen for LOW CORRELATION to
    what you already hold, not for its standalone Sharpe."""
    if n <= 0:
        return 0.0
    denom = math.sqrt(1.0 + (n - 1) * rho)
    return sharpe * math.sqrt(n) / denom if denom > 0 else 0.0


# --------------------------------------------------------------------------
# 3. Variance control  (control theory: measure the disturbance, scale the
#    input. The -sigma^2/2 term is the one the repo already proved is real.)
# --------------------------------------------------------------------------

def ewma_vol(returns: pd.Series, lam: float = 0.94,
             periods_per_year: int = TD_YEAR) -> pd.Series:
    """RiskMetrics EWMA volatility, ANNUALISED and CAUSAL.

    sigma^2_t = lam*sigma^2_{t-1} + (1-lam)*r^2_{t-1}: the value at t uses
    returns strictly before t, so it may be used as a weight for the return
    at t without lookahead. lam=0.94 is the frozen RiskMetrics daily value
    (~half-life 11 days), not a fitted parameter."""
    r = pd.Series(returns, dtype=float).fillna(0.0)
    var = np.empty(len(r))
    var[:] = np.nan
    seed_n = min(20, len(r))
    if seed_n < 2:
        return pd.Series(var, index=r.index)
    run = float(np.nanvar(r.iloc[:seed_n].to_numpy(), ddof=1))
    for i in range(seed_n, len(r)):
        var[i] = run                                  # forecast for bar i
        run = lam * run + (1 - lam) * float(r.iloc[i]) ** 2
    return pd.Series(np.sqrt(var * periods_per_year), index=r.index)


def blended_vol(returns: pd.Series, lam: float = 0.94, window: int = 63,
                periods_per_year: int = TD_YEAR) -> pd.Series:
    """Average of the EWMA forecast and a slower rolling estimate.

    Two estimators of the same quantity with different error structures;
    averaging them is the cheapest variance reduction available and is
    standard practice in managed-futures risk systems. Both legs are
    causal (the rolling leg is shifted)."""
    fast = ewma_vol(returns, lam, periods_per_year)
    r = pd.Series(returns, dtype=float)
    slow = (r.rolling(window, min_periods=window // 2).std().shift(1)
            * math.sqrt(periods_per_year))
    return pd.concat([fast, slow], axis=1).mean(axis=1, skipna=False)


def vol_target_scalar(vol_forecast, target_vol: float = 0.10,
                      max_leverage: float = 2.0, min_leverage: float = 0.0):
    """Position scalar sigma_target / sigma_forecast, clipped.

    Volatility is the one property of returns that is genuinely forecastable
    (clustering is the most replicated fact in empirical finance), which is
    exactly why targeting it works while targeting return does not. It does
    not raise mu; it stabilises sigma, and by the growth identity a stable
    sigma compounds better than a spiky one with the same mean.

    NOTE this repo already tested a LONG-ONLY, CAP-AT-1x version of this on
    single-stock picks (H5g) and rejected it: capped at 1x it can only ever
    de-lever, which in a rising high-vol tape is pure cost. The formula only
    pays when it is allowed to lever UP in calm periods -- hence the default
    max_leverage of 2.0 here and the explicit cap argument."""
    v = pd.Series(vol_forecast, dtype=float) if not np.isscalar(vol_forecast) \
        else float(vol_forecast)
    if np.isscalar(v):
        if not np.isfinite(v) or v <= 0:
            return 0.0
        return float(min(max(target_vol / v, min_leverage), max_leverage))
    out = target_vol / v.replace(0.0, np.nan)
    return out.clip(lower=min_leverage, upper=max_leverage)


# --------------------------------------------------------------------------
# 4. Stochastic portfolio theory  (Fernholz: the one PROVABLE edge here --
#    a theorem, not a backtest)
# --------------------------------------------------------------------------

def excess_growth_rate(weights, cov) -> float:
    """Fernholz's excess growth rate

        gamma* = 0.5 * ( sum_i w_i sigma_ii  -  w' Sigma w )

    For any long-only weights on the simplex this is NON-NEGATIVE by
    Jensen -- it is the rebalancing premium ("Shannon's demon"), and it is
    the amount by which a continuously rebalanced portfolio out-grows the
    weighted average growth of its own constituents. It is a mathematical
    identity, not an empirical regularity: it cannot be arbitraged away.

    It is also the exact quantity the repo's concentrated book threw away.
    gamma* is 0 for a single position and grows with the dispersion of the
    holdings, so 'concentration buys dispersion, not return' (H8) is this
    formula with a minus sign."""
    w = np.asarray(weights, float).reshape(-1)
    c = np.asarray(cov, float)
    return 0.5 * float(w @ np.diag(c) - w @ c @ w)


def diversity_weights(caps, p: float = 0.76) -> np.ndarray:
    """Fernholz diversity-weighted portfolio: w_i proportional to cap_i^p,
    0 < p < 1.

    Fernholz's theorem: over any period in which market DIVERSITY does not
    fall, this portfolio beats the cap-weighted index, with the outperformance
    equal to the integrated excess growth rate. p=0.76 is the value Fernholz
    used on the US market; p->1 is the index itself, p->0 is equal weight.

    The honest caveat, and this repo has already measured its shadow: the
    theorem's condition FAILED in 2017-2026, the most concentration-driven
    decade on record -- which is precisely why gates_lab found cap-weighted
    SPY beating every equal-weighted book. Diversity weighting is a bet that
    concentration mean-reverts, and it must be sized as one."""
    c = np.asarray(caps, float).reshape(-1)
    c = np.where(np.isfinite(c) & (c > 0), c, np.nan)
    x = np.power(c, p)
    tot = np.nansum(x)
    return np.zeros_like(c) if tot <= 0 else np.nan_to_num(x / tot)


# --------------------------------------------------------------------------
# 5. Covariance you can actually invert  (shrinkage + a clustering allocator)
# --------------------------------------------------------------------------

def ledoit_wolf_cov(returns: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf (2004) shrinkage toward a scaled identity.

    Returns (Sigma_hat, delta). The sample covariance of N assets on T
    observations has ~N^2/2 free parameters and its smallest eigenvalues are
    biased toward zero; inverting it -- which Kelly and mean-variance both
    do -- amplifies exactly that error. Shrinkage is the minimum viable fix
    and its intensity delta is derived, not chosen."""
    x = np.asarray(returns, float)
    if x.ndim != 2:
        raise ValueError("returns must be T x N")
    t, n = x.shape
    if t < 2:
        raise ValueError("need at least 2 observations")
    xc = x - x.mean(axis=0, keepdims=True)
    s = (xc.T @ xc) / t
    mu = float(np.trace(s) / n)
    f = mu * np.eye(n)
    d2 = float(((s - f) ** 2).sum() / n)
    b2_bar = 0.0
    for i in range(t):
        yi = np.outer(xc[i], xc[i])
        b2_bar += float(((yi - s) ** 2).sum())
    b2_bar /= (t * t * n)
    b2 = min(b2_bar, d2)
    delta = 0.0 if d2 <= 0 else b2 / d2
    return delta * f + (1 - delta) * s, delta


def _corr_from_cov(cov: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.clip(np.diag(cov), 1e-300, None))
    c = cov / np.outer(d, d)
    return np.clip(c, -1.0, 1.0)


def _single_linkage_order(dist: np.ndarray) -> list[int]:
    """Quasi-diagonalisation ordering by single-linkage agglomeration.

    Written out rather than pulled from scipy so the repo keeps its current
    dependency set. Clusters merge on the smallest inter-cluster distance;
    the returned order is the concatenation of the merged leaf lists, which
    places correlated assets adjacent -- the ordering HRP needs."""
    n = dist.shape[0]
    clusters = {i: [i] for i in range(n)}
    while len(clusters) > 1:
        keys = list(clusters)
        best, bi, bj = math.inf, keys[0], keys[1]
        for a in range(len(keys)):
            for b in range(a + 1, len(keys)):
                ka, kb = keys[a], keys[b]
                d = min(dist[i, j] for i in clusters[ka] for j in clusters[kb])
                if d < best:
                    best, bi, bj = d, ka, kb
        clusters[bi] = clusters[bi] + clusters[bj]
        del clusters[bj]
    return list(clusters.values())[0]


def _inv_var_weights(cov: np.ndarray, idx) -> np.ndarray:
    ivp = 1.0 / np.clip(np.diag(cov)[idx], 1e-300, None)
    return ivp / ivp.sum()


def _cluster_var(cov: np.ndarray, idx) -> float:
    w = _inv_var_weights(cov, idx)
    sub = cov[np.ix_(idx, idx)]
    return float(w @ sub @ w)


def hrp_weights(cov: np.ndarray) -> np.ndarray:
    """Hierarchical Risk Parity (Lopez de Prado 2016).

    Allocates by recursive bisection of a correlation-clustered ordering,
    splitting risk between the two halves in inverse proportion to their
    cluster variance. It never inverts the covariance matrix, so it does not
    inherit the instability that makes mean-variance and Kelly weights
    thrash out of sample; published out-of-sample variance is materially
    below both min-variance and inverse-variance.

    Distance metric d_ij = sqrt((1 - rho_ij)/2) -- a proper metric, which is
    what makes the clustering meaningful rather than decorative."""
    cov = np.asarray(cov, float)
    n = cov.shape[0]
    if n == 1:
        return np.ones(1)
    corr = _corr_from_cov(cov)
    dist = np.sqrt(np.clip((1.0 - corr) / 2.0, 0.0, None))
    order = _single_linkage_order(dist)
    w = np.ones(n)
    groups = [order]
    while groups:
        nxt = []
        for g in groups:
            if len(g) <= 1:
                continue
            half = len(g) // 2
            left, right = g[:half], g[half:]
            vl, vr = _cluster_var(cov, left), _cluster_var(cov, right)
            alpha = 1.0 - vl / (vl + vr) if (vl + vr) > 0 else 0.5
            for i in left:
                w[i] *= alpha
            for i in right:
                w[i] *= (1 - alpha)
            nxt.extend([left, right])
        groups = nxt
    return w / w.sum()


def effective_bets(weights, cov) -> float:
    """Meucci's effective number of bets: exp(entropy of the portfolio's
    risk distribution across principal components).

    p_i = (v_i'w)^2 lambda_i / sum_j (...);  N_ent = exp(-sum p_i ln p_i).

    Borrowed wholesale from information theory: a book holding 30 names that
    all load on one factor has N_ent near 1 and is a single bet in costume.
    This is the right diagnostic for 'am I actually diversified', because
    counting positions answers a question nobody asked."""
    w = np.asarray(weights, float).reshape(-1)
    c = np.asarray(cov, float)
    vals, vecs = np.linalg.eigh(c)
    vals = np.clip(vals, 0.0, None)
    contrib = (vecs.T @ w) ** 2 * vals
    tot = contrib.sum()
    if tot <= 0:
        return 0.0
    p = contrib / tot
    p = p[p > 0]
    return float(np.exp(-(p * np.log(p)).sum()))


# --------------------------------------------------------------------------
# 6. Signal shaping  (signal processing: the matched filter and the Kalman
#    filter, which is what a trend rule actually is)
# --------------------------------------------------------------------------

def ewmac_forecast(close: pd.Series, fast: int, slow: int,
                   vol_window: int = 63, cap: float = 2.0) -> pd.Series:
    """One exponential moving-average crossover, volatility-normalised.

        raw_t = EMA_fast(P)_t - EMA_slow(P)_t
        f_t   = raw_t / (P_t * sigma_daily_t)

    An EMA crossover is the discrete matched filter for a drift embedded in
    noise: it is the optimal linear detector when the signal is a ramp and
    the noise is (approximately) white. Dividing by price volatility makes
    forecasts comparable ACROSS assets and across time, which is the step
    that lets a bond future and a copper future sit in the same book.

    Causal: the value at t uses closes through t, so a lab must shift by one
    bar before using it as a weight for t+1's return."""
    p = pd.Series(close, dtype=float)
    raw = p.ewm(span=fast, adjust=False).mean() - p.ewm(span=slow, adjust=False).mean()
    daily_vol = p.pct_change().rolling(vol_window, min_periods=vol_window // 2).std()
    f = raw / (p * daily_vol.replace(0.0, np.nan))
    return f.clip(-cap, cap)


def trend_forecast(close: pd.Series, spans=((8, 32), (16, 64), (32, 128), (64, 256)),
                   cap: float = 2.0, scale: float = 1.0) -> pd.Series:
    """Blend of EWMAC filters at several speeds, squashed to (-1, 1) by tanh.

    Mechanism (not a pattern): time-series momentum is the most robustly
    documented return source outside the equity premium itself -- Moskowitz-
    Ooi-Pedersen (2012) across 58 instruments, Hurst-Ooi-Pedersen (2017)
    across 100+ years and four asset classes -- and its accepted cause is
    slow diffusion of macro information plus flow effects (rebalancing,
    hedging, risk limits), not a statistical accident.

    Why a BLEND: no one speed is right, the speeds disagree at turning
    points, and averaging noisy detectors of the same signal is the same
    variance reduction `blended_vol` uses. Why tanh: it caps a runaway
    forecast without a discontinuity, so position size responds smoothly
    instead of flipping."""
    parts = [ewmac_forecast(close, f, s, cap=cap) for f, s in spans]
    avg = pd.concat(parts, axis=1).mean(axis=1, skipna=False)
    return np.tanh(scale * avg)


def kalman_beta(y: pd.Series, x: pd.Series, q: float = 1e-5,
                r: float | None = None) -> pd.Series:
    """Time-varying beta of y on x via a scalar random-walk Kalman filter.

        state:       beta_t = beta_{t-1} + w,   w ~ N(0, q)
        observation: y_t    = beta_t x_t + v,   v ~ N(0, r)

    A rolling-window beta is a rectangular filter: it forgets everything at
    once when the window rolls off, and it lags by half the window. The
    Kalman filter is the minimum-variance estimator for the same quantity
    and adapts immediately to a regime change. `q/r` is the only knob (how
    fast beta is allowed to move); r defaults to the sample variance of y.

    Causal: the value at t is the POSTERIOR after seeing t, so hedging the
    t+1 return requires a shift(1)."""
    ys = pd.Series(y, dtype=float)
    xs = pd.Series(x, dtype=float).reindex(ys.index)
    if r is None:
        r = float(np.nanvar(ys.to_numpy())) or 1.0
    beta, p = 0.0, 1.0
    out = np.full(len(ys), np.nan)
    for i in range(len(ys)):
        yi, xi = ys.iloc[i], xs.iloc[i]
        if not (np.isfinite(yi) and np.isfinite(xi)):
            out[i] = beta
            continue
        p += q                                          # predict
        denom = xi * xi * p + r
        k = (p * xi) / denom if denom > 0 else 0.0      # Kalman gain
        beta = beta + k * (yi - beta * xi)              # update
        p = (1 - k * xi) * p
        out[i] = beta
    return pd.Series(out, index=ys.index)


def ou_half_life(series: pd.Series) -> float:
    """Half-life of mean reversion under an Ornstein-Uhlenbeck fit:

        dY = lambda (mu - Y) dt + sigma dW      ->   h = ln(2) / lambda

    estimated by regressing dY_t on Y_{t-1}. Straight out of statistical
    physics (the Langevin equation for a damped particle). Its use here is
    as a SIZING and HORIZON input, not a signal: a spread with a 90-day
    half-life must not be traded on a 5-day clock, which is the mistake the
    weekly lab made in a different costume. Returns inf when the series
    shows no reversion."""
    s = pd.Series(series, dtype=float).dropna()
    if len(s) < 30:
        return float("inf")
    y = s.shift(1).dropna()
    dy = s.diff().dropna()
    idx = y.index.intersection(dy.index)
    y, dy = y.loc[idx].to_numpy(), dy.loc[idx].to_numpy()
    a = np.vstack([np.ones_like(y), y]).T
    coef, *_ = np.linalg.lstsq(a, dy, rcond=None)
    lam = -coef[1]
    return float(math.log(2) / lam) if lam > 0 else float("inf")


# --------------------------------------------------------------------------
# 7. Ship gates  (clinical trials: pre-registration is only half of it --
#    you also need a stopping rule and a multiplicity correction)
# --------------------------------------------------------------------------

def deflated_sharpe(sr: float, n_trials: int, n_obs: int,
                    skew: float = 0.0, kurtosis: float = 3.0,
                    sr_benchmark: float | None = None,
                    trial_sr_std: float | None = None) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014): the probability
    that an observed Sharpe is real, given how many strategies were tried and
    how non-normal the returns are.

    `sr` and `sr_benchmark` are in the SAME period units as `n_obs`
    (e.g. both per-day if n_obs counts days).

    The expected maximum Sharpe from N independent lucky draws is

        SR_0 = sigma_SR * [ (1-g) Z^-1(1 - 1/N) + g Z^-1(1 - 1/(N e)) ]

    with g the Euler-Mascheroni constant; DSR then asks whether the observed
    SR clears that bar:

        DSR = Phi( (SR - SR_0) sqrt(T-1) / sqrt(1 - skew*SR + (kurt-1)/4 SR^2) )

    Note the penalty terms: NEGATIVE skew and FAT tails both inflate the
    denominator and cut DSR. A strategy that earns a premium for taking tail
    risk -- selling variance, carry, short-vol in any form -- is penalised
    here by construction, which is the correct treatment and the reason this
    gate is worth having. RESEARCH-AGENDA's registry supplies N honestly;
    `scout/hypotheses.md` is the count."""
    if n_obs < 2 or n_trials < 1:
        return 0.0
    if trial_sr_std is None:
        # Dispersion of Sharpe estimates ACROSS trials. When the trial set
        # is not available, the sampling standard error of a single Sharpe,
        # sqrt((1 + SR^2/2)/T), is the honest floor: it assumes the trials
        # differ only by luck. A real trial set is usually MORE dispersed
        # than that, so passing the measured value makes the gate stricter,
        # never looser. Supply it whenever the registry has the numbers.
        trial_sr_std = math.sqrt((1.0 + 0.5 * sr * sr) / n_obs)
    if sr_benchmark is None:
        if n_trials == 1:
            sr_benchmark = 0.0
        else:
            z1 = norm_ppf(1 - 1.0 / n_trials)
            z2 = norm_ppf(1 - 1.0 / (n_trials * math.e))
            sr_benchmark = trial_sr_std * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)
    denom = 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        return 0.0
    z = (sr - sr_benchmark) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return norm_cdf(z)


def min_track_record_length(sr: float, sr_target: float = 0.0,
                            skew: float = 0.0, kurtosis: float = 3.0,
                            confidence: float = 0.95) -> float:
    """Observations needed before an observed Sharpe is distinguishable from
    `sr_target` at `confidence`:

        MinTRL = 1 + (1 - skew*SR + (kurt-1)/4 SR^2) * (Z_conf / (SR - SR*))^2

    Same period units throughout. Run this BEFORE a live experiment: it
    answers 'how long until I could possibly know', and the answer is
    routinely years. It is the honest reply to 'the strategy is down three
    months, is it broken'."""
    if sr <= sr_target:
        return float("inf")
    z = norm_ppf(confidence)
    var_term = 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr * sr
    return 1.0 + var_term * (z / (sr - sr_target)) ** 2


def sprt_decision(returns, mu1: float, sigma: float | None = None,
                  alpha: float = 0.05, beta: float = 0.20) -> dict:
    """Wald's Sequential Probability Ratio Test as a strategy KILL SWITCH.

    H0: per-period mean = 0 (the edge is gone).  H1: mean = mu1 (the edge is
    what the backtest claimed). Under a normal likelihood the log-ratio
    accumulates as

        L_n = sum_i [ mu1*r_i/sigma^2 - mu1^2/(2 sigma^2) ]

    and the test stops when L_n leaves ( ln(beta/(1-alpha)), ln((1-beta)/alpha) ).

    Why this and not 'give it another quarter': the SPRT reaches a decision
    with a STATED error rate in the smallest expected number of observations
    of any test (Wald-Wolfowitz optimality). Medicine adopted it so trials
    stop as soon as the answer is known; a live strategy deserves the same
    courtesy, in both directions."""
    r = np.asarray(pd.Series(returns, dtype=float).dropna(), float)
    if len(r) == 0:
        return {"decision": "continue", "llr": 0.0, "n": 0,
                "upper": float("nan"), "lower": float("nan")}
    if sigma is None:
        sigma = float(r.std(ddof=1)) or 1e-9
    upper = math.log((1 - beta) / alpha)
    lower = math.log(beta / (1 - alpha))
    inc = mu1 * r / (sigma ** 2) - mu1 ** 2 / (2 * sigma ** 2)
    llr = np.cumsum(inc)
    decision, n = "continue", len(r)
    for i, v in enumerate(llr):
        if v >= upper:
            decision, n = "keep", i + 1
            break
        if v <= lower:
            decision, n = "kill", i + 1
            break
    return {"decision": decision, "llr": float(llr[n - 1]), "n": int(n),
            "upper": upper, "lower": lower}


# --------------------------------------------------------------------------
# 8. Small helpers the labs share
# --------------------------------------------------------------------------

def sharpe(returns, periods_per_year: int = TD_YEAR) -> float:
    """Annualised Sharpe of a period-return series (excess assumed)."""
    r = pd.Series(returns, dtype=float).dropna()
    if len(r) < 2:
        return 0.0
    sd = float(r.std(ddof=1))
    return float(r.mean()) / sd * math.sqrt(periods_per_year) if sd > 0 else 0.0


def max_drawdown(returns) -> float:
    """Worst peak-to-trough of the compounded curve, as a negative fraction."""
    r = pd.Series(returns, dtype=float).fillna(0.0)
    curve = (1 + r).cumprod()
    return float((curve / curve.cummax() - 1).min()) if len(curve) else 0.0


def turnover_cost(w_prev: pd.Series, w_target: pd.Series,
                  cost_bps: float) -> float:
    """Two-way turnover charge 0.5*sum|w_target - w_prev| * cost.

    Same definition gates_lab.rebalance_turnover uses, kept identical on
    purpose: a lab that measures turnover differently from its neighbour
    produces numbers that cannot be compared."""
    names = w_prev.index.union(w_target.index)
    a = w_prev.reindex(names).fillna(0.0)
    b = w_target.reindex(names).fillna(0.0)
    return 0.5 * float((b - a).abs().sum()) * cost_bps / 10_000.0

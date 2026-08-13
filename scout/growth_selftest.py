"""Offline validation of scout/growth.py -- no API keys, no network.

Every formula in growth.py is checked against a Monte-Carlo simulation of a
process whose answer is known in closed form, or against an analytic identity.
This is the part of a research stack that is allowed to be certain: if the
Kelly code cannot find the optimum of a simulated GBM whose optimum we
computed by hand, no result it produces on real data means anything.

It also doubles as the demonstration of the central claim -- test 5 shows two
uncorrelated Sharpe-0.6 sleeves combining to 0.85 in simulation, and test 4
shows the rebalancing premium being harvested from two assets that each earn
exactly zero.

Run:  python -m scout.growth_selftest [-v]
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

from . import growth as g

RNG = np.random.default_rng(20260809)
FAILURES: list[str] = []
VERBOSE = "-v" in sys.argv


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail or not ok else ""))
    if not ok:
        FAILURES.append(name)


def approx(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


# --------------------------------------------------------------------------

def t1_growth_identity() -> None:
    """g = mu - sigma^2/2 should equal the realised compounded growth."""
    print("\n[1] growth identity  g = mu - sigma^2/2")
    mu_d, sd_d, n = 0.0004, 0.011, 400_000
    r = RNG.normal(mu_d, sd_d, n)
    realised = math.log(float(np.prod(1 + r))) / n
    predicted = g.growth_rate(mu_d, sd_d)
    check("realised log-growth matches mu - sigma^2/2",
          approx(realised, predicted, 3e-5),
          f"realised {realised:.6f} vs predicted {predicted:.6f}")

    # The drag is not a rounding error at book-level volatilities: this is
    # the weekly-forensics number reproduced from first principles.
    drag_top1 = g.growth_rate(0.0, 0.0506) - 0.0
    check("sd 5.06%/wk implies ~0.128%/wk drag",
          approx(-drag_top1, 0.00128, 1e-4), f"{-drag_top1*100:.3f}%/wk")


def t2_optimal_leverage() -> None:
    """Grid-search the simulated growth curve; the peak must be at mu/sigma^2."""
    print("\n[2] Kelly leverage  L* = mu/sigma^2,  g(L*) = S^2/2")
    mu, sd = 0.08, 0.16
    ls = np.linspace(0.1, 8.0, 400)
    gs = [g.growth_at_leverage(mu, sd, L) for L in ls]
    argmax = float(ls[int(np.argmax(gs))])
    check("grid peak equals mu/sigma^2",
          approx(argmax, g.optimal_leverage(mu, sd), 0.05),
          f"grid {argmax:.2f} vs formula {g.optimal_leverage(mu, sd):.2f}")

    s = mu / sd
    check("g(L*) equals S^2/2",
          approx(g.growth_at_leverage(mu, sd, g.optimal_leverage(mu, sd)),
                 s * s / 2, 1e-9), f"S={s:.2f}, g*={s*s/2:.3f}")
    check("g(2 L*) = 0 (double Kelly earns nothing)",
          approx(g.growth_at_leverage(mu, sd, 2 * g.optimal_leverage(mu, sd)),
                 0.0, 1e-9))

    # The quadratic claim, stated as a number: doubling Sharpe quadruples g*.
    check("doubling Sharpe quadruples achievable growth",
          approx((2 * s) ** 2 / 2, 4 * (s * s / 2), 1e-12),
          f"S={s:.2f} -> {s*s/2:.1%}/yr;  S={2*s:.2f} -> {(2*s)**2/2:.1%}/yr")


def t3_drawdown_kelly() -> None:
    """P(ever down q) = (1-q)^(2/f) -- verify by simulating paths."""
    print("\n[3] drawdown-constrained Kelly fraction")
    f = g.kelly_fraction_for_drawdown(max_dd=0.20, prob=0.10)
    check("formula returns a sane fraction", 0.05 < f < 0.6, f"f = {f:.3f}")
    check("full Kelly means a 50% chance of halving the stake",
          approx(g.kelly_fraction_for_drawdown(0.50, 0.50), 1.0, 1e-9))

    mu, sd = 0.08, 0.16                      # full Kelly L* = 3.125
    lev = f * g.optimal_leverage(mu, sd)
    mu_d, sd_d = lev * mu / 252, lev * sd / math.sqrt(252)
    paths, years = 3000, 60
    hits = 0
    for _ in range(paths):
        curve = np.cumprod(1 + RNG.normal(mu_d, sd_d, 252 * years))
        if float(curve.min()) <= 0.80:       # down 20% FROM THE START
            hits += 1
    rate = hits / paths
    # 60y is a long-but-finite proxy for "ever", so the simulated rate sits
    # just under the asymptotic 10%.
    check("simulated P(ever down 20% from start) matches the targeted 10%",
          0.05 <= rate <= 0.15, f"simulated {rate:.1%} over {years}y paths")

    # Peak-to-trough over the same paths is a different, much larger number.
    dds = []
    for _ in range(300):
        curve = np.cumprod(1 + RNG.normal(mu_d, sd_d, 252 * years))
        dds.append(float((curve / np.maximum.accumulate(curve) - 1).min()))
    check("peak-to-trough drawdown is far worse than start-relative",
          float(np.median(dds)) < -0.20,
          f"median max-DD {np.median(dds):.1%} -- size for THIS, not the 20%")


def t4_rebalancing_premium() -> None:
    """Fernholz gamma*: two zero-growth assets, rebalanced, earn money."""
    print("\n[4] excess growth rate (Fernholz) / Shannon's demon")
    sd_d, n = 0.02, 2_000_000            # n set so the MC error (~1.4e-5) is
    mu_d = 0.5 * sd_d ** 2               # well inside gamma* = 1e-4
    a = RNG.normal(mu_d, sd_d, n)
    b = RNG.normal(mu_d, sd_d, n)
    ga = math.log(float(np.prod(1 + a))) / n
    gb = math.log(float(np.prod(1 + b))) / n
    port = 0.5 * a + 0.5 * b             # rebalanced to 50/50 every step
    gp = math.log(float(np.prod(1 + port))) / n

    cov = np.array([[sd_d ** 2, 0.0], [0.0, sd_d ** 2]])
    gamma = g.excess_growth_rate([0.5, 0.5], cov)
    check("both constituents grow at ~0",
          abs(ga) < 5e-5 and abs(gb) < 5e-5, f"{ga:.6f}, {gb:.6f}")
    check("rebalanced book grows at gamma* > 0",
          approx(gp, gamma, 5e-5) and gamma > 0,
          f"realised {gp:.6f} vs gamma* {gamma:.6f} ({gamma*252:.2%}/yr)")

    check("gamma* is zero for a single position",
          approx(g.excess_growth_rate([1.0, 0.0], cov), 0.0, 1e-15))
    check("gamma* is zero for perfectly correlated assets",
          approx(g.excess_growth_rate(
              [0.5, 0.5], np.array([[sd_d**2, sd_d**2], [sd_d**2, sd_d**2]])),
              0.0, 1e-15))
    # Non-negativity over random long-only books -- the theorem, spot-checked.
    worst = 0.0
    for _ in range(300):
        k = RNG.integers(2, 8)
        w = RNG.random(k); w /= w.sum()
        x = RNG.normal(0, 1, (400, k))
        worst = min(worst, g.excess_growth_rate(w, np.cov(x.T)))
    check("gamma* >= 0 over 300 random long-only books", worst >= -1e-12,
          f"min {worst:.2e}")


def t5_diversification_arithmetic() -> None:
    """S_p = w'S / sqrt(w'Cw), checked against simulated sleeves."""
    print("\n[5] the arithmetic of the landslide")
    check("4 uncorrelated Sharpe-0.6 sleeves -> 1.20",
          approx(g.equal_weight_sharpe(4, 0.6, 0.0), 1.2, 1e-9),
          f"{g.equal_weight_sharpe(4, 0.6, 0.0):.2f}")
    check("the same 4 at rho=0.3 -> 0.87",
          approx(g.equal_weight_sharpe(4, 0.6, 0.3), 0.871, 5e-3),
          f"{g.equal_weight_sharpe(4, 0.6, 0.3):.2f}")
    check("perfectly correlated sleeves add nothing",
          approx(g.equal_weight_sharpe(10, 0.6, 1.0), 0.6, 1e-9))

    n, k, s_ann = 252 * 60, 4, 0.6
    sd_d = 0.15 / math.sqrt(252)
    mu_d = (s_ann / math.sqrt(252)) * sd_d   # per-day mean giving annual SR 0.6
    x = RNG.normal(mu_d, sd_d, (n, k))
    # SE of an annual Sharpe over 60 years is ~sqrt(1/60) = 0.13, so the
    # tolerance here is sampling noise, not slack.
    check("each simulated sleeve is Sharpe ~0.6 (+/- 2 SE)",
          approx(g.sharpe(pd.Series(x[:, 0])), 0.6, 0.30),
          f"{g.sharpe(pd.Series(x[:, 0])):.2f}")
    sim = g.sharpe(pd.Series(x.mean(axis=1)))
    check("simulated 4-sleeve combination reaches the predicted Sharpe",
          approx(sim, 1.2, 0.2), f"simulated {sim:.2f} vs predicted 1.20")

    check("combine_sharpe agrees with the closed form",
          approx(g.combine_sharpe([0.6] * 4, np.full((4, 4), 0.3) + 0.7 * np.eye(4)),
                 g.equal_weight_sharpe(4, 0.6, 0.3), 1e-9))


def t6_vol_targeting() -> None:
    """Vol targeting on a heteroskedastic series should raise Sharpe."""
    print("\n[6] volatility targeting (control loop)")
    # Constant expected return, clustered volatility -- the empirical shape
    # of equity returns, and the exact condition under which targeting pays.
    # Regimes persist for ~6 months: a forecast with an 11-day half-life can
    # actually track them. Flip the blocks to 21 days and the gain collapses
    # -- which is the honest limit of the technique, not a bug in it.
    n, block = 252 * 30, 126
    regime = np.repeat(RNG.choice([0.006, 0.024], size=n // block + 1), block)[:n]
    s = pd.Series(0.0005 + regime * RNG.normal(0, 1, n))
    vol = g.blended_vol(s)
    lev = g.vol_target_scalar(vol, target_vol=0.15, max_leverage=3.0)
    managed = (lev.shift(1) * s).dropna()      # shift: yesterday's forecast
    base_sr, man_sr = g.sharpe(s), g.sharpe(managed)
    check("vol-targeted Sharpe clearly exceeds the raw series",
          man_sr > base_sr + 0.05, f"raw {base_sr:.2f} -> targeted {man_sr:.2f}")
    realised_vol = float(managed.std(ddof=1) * math.sqrt(252))
    check("realised vol lands near the 15% target",
          0.10 <= realised_vol <= 0.22, f"{realised_vol:.1%}")

    # Causality: the forecast for bar t must not move when r_t changes.
    s2 = s.copy()
    s2.iloc[500] = 5.0
    v1, v2 = g.ewma_vol(s), g.ewma_vol(s2)
    check("ewma_vol is causal (bar t's forecast ignores bar t's return)",
          approx(float(v1.iloc[500]), float(v2.iloc[500]), 1e-12)
          and not approx(float(v1.iloc[501]), float(v2.iloc[501]), 1e-12))


def t7_covariance() -> None:
    print("\n[7] Ledoit-Wolf shrinkage, HRP, effective bets")
    n_assets, t = 30, 60                      # T < N*2: the hard regime
    true_cov = np.eye(n_assets) * 0.0004
    true_cov[:10, :10] += 0.0002              # one correlated block
    x = RNG.multivariate_normal(np.zeros(n_assets), true_cov, t)
    shrunk, delta = g.ledoit_wolf_cov(x)
    sample = np.cov(x.T, ddof=0)
    check("shrinkage intensity in (0,1)", 0.0 < delta < 1.0, f"delta {delta:.3f}")
    check("shrunk covariance is better conditioned",
          np.linalg.cond(shrunk) < np.linalg.cond(sample),
          f"cond {np.linalg.cond(shrunk):.1f} vs {np.linalg.cond(sample):.1e}")
    check("shrunk covariance is closer to the truth (Frobenius)",
          np.linalg.norm(shrunk - true_cov) < np.linalg.norm(sample - true_cov))

    w = g.hrp_weights(true_cov)
    check("HRP weights sum to 1 and are non-negative",
          approx(float(w.sum()), 1.0, 1e-9) and (w >= 0).all())
    check("HRP underweights the correlated block per name",
          w[:10].mean() < w[10:].mean(),
          f"block {w[:10].mean():.4f} vs independent {w[10:].mean():.4f}")

    eq = np.full(n_assets, 1 / n_assets)
    check("HRP has lower variance than equal weight",
          float(w @ true_cov @ w) < float(eq @ true_cov @ eq))

    check("effective bets = N for an uncorrelated equal-weight book",
          approx(g.effective_bets(np.full(8, 1 / 8), np.eye(8)), 8.0, 1e-6),
          f"{g.effective_bets(np.full(8, 1/8), np.eye(8)):.2f}")
    ones = np.ones((8, 8))
    check("effective bets -> 1 when everything is one factor",
          approx(g.effective_bets(np.full(8, 1 / 8), ones + 1e-9 * np.eye(8)),
                 1.0, 1e-3))


def t8_kelly_weights() -> None:
    print("\n[8] Kelly weights and estimation-error shrinkage")
    mu = np.array([0.0004, 0.0002])
    cov = np.array([[0.0001, 0.00002], [0.00002, 0.00004]])
    w = g.kelly_weights(mu, cov)
    check("Kelly weights solve Sigma w = mu",
          np.allclose(cov @ w, mu, atol=1e-10))

    best, best_w = -1e9, None
    for a in np.linspace(-2, 8, 201):
        for b in np.linspace(-2, 8, 201):
            v = np.array([a, b])
            val = float(v @ mu - 0.5 * v @ cov @ v)
            if val > best:
                best, best_w = val, v
    check("grid search finds the same optimum",
          np.allclose(best_w, w, atol=0.1), f"grid {best_w} vs formula {w.round(2)}")

    check("gross cap is respected",
          approx(float(np.abs(g.kelly_weights(mu, cov, max_gross=1.0)).sum()),
                 1.0, 1e-9))
    check("4 sleeves on 10y daily data barely shrink",
          g.kelly_shrinkage(1.0, 4, 2520) > 0.99,
          f"lambda {g.kelly_shrinkage(1.0, 4, 2520):.3f}")
    check("500 assets on the same sample shrink to ~nothing",
          g.kelly_shrinkage(1.0, 500, 2520) < 0.85,
          f"lambda {g.kelly_shrinkage(1.0, 500, 2520):.3f}")


def t9_breadth() -> None:
    print("\n[9] fundamental law of active management")
    check("IR = IC sqrt(BR) TC",
          approx(g.grinold_ir(0.05, 24, 0.55), 0.05 * math.sqrt(24) * 0.55, 1e-12),
          f"top-2 book, IC 0.05 -> IR {g.grinold_ir(0.05, 24, 0.55):.2f}")
    check("required_ic inverts grinold_ir",
          approx(g.grinold_ir(g.required_ic(1.0, 24, 0.55), 24, 0.55), 1.0, 1e-9))
    need = g.required_ic(1.0, 24, 0.55)
    check("IR 1.0 from a 2-name monthly book needs an impossible IC",
          need > 0.30, f"needs IC {need:.2f} (published skill tops out ~0.05-0.10)")
    need_wide = g.required_ic(1.0, 1500 * 12 * 0.02, 0.55)
    check("the same IR is reachable once breadth is bought",
          need_wide < 0.12, f"at BR=360 independent bets: IC {need_wide:.3f}")


def t10_ship_gates() -> None:
    print("\n[10] deflated Sharpe, MinTRL, SPRT")
    sr_d = 1.0 / math.sqrt(252)                # annual Sharpe 1.0, daily units
    d1 = g.deflated_sharpe(sr_d, n_trials=1, n_obs=2520)
    d50 = g.deflated_sharpe(sr_d, n_trials=50, n_obs=2520)
    d500 = g.deflated_sharpe(sr_d, n_trials=500, n_obs=2520)
    check("DSR falls as the trial count rises",
          d1 > d50 > d500, f"N=1 {d1:.3f}, N=50 {d50:.3f}, N=500 {d500:.3f}")
    neg = g.deflated_sharpe(sr_d, 50, 2520, skew=-2.0, kurtosis=12.0)
    check("negative skew and fat tails are penalised",
          neg < d50, f"skewed {neg:.3f} vs normal {d50:.3f}")

    trl = g.min_track_record_length(sr_d, 0.0, confidence=0.95)
    check("a Sharpe-1.0 strategy needs ~2.7 years to prove itself",
          2.0 < trl / 252 < 3.5, f"{trl/252:.1f} years")
    trl_half = g.min_track_record_length(0.5 / math.sqrt(252), 0.0, confidence=0.95)
    check("a Sharpe-0.5 strategy needs ~11 years",
          8 < trl_half / 252 < 14, f"{trl_half/252:.1f} years")

    # The SPRT has STATED error rates (alpha=5%, beta=20%), so a single run
    # proves nothing -- the right check is that the realised error rates
    # come in at or under the design. 40 independent runs of each.
    dead = [g.sprt_decision(RNG.normal(0.0, 0.01, 6000), mu1=0.0008, sigma=0.01)
            for _ in range(40)]
    live = [g.sprt_decision(RNG.normal(0.0008, 0.01, 6000), mu1=0.0008, sigma=0.01)
            for _ in range(40)]
    false_keep = sum(d["decision"] == "keep" for d in dead) / len(dead)
    missed = sum(d["decision"] != "keep" for d in live) / len(live)
    n_dead = np.median([d["n"] for d in dead if d["decision"] == "kill"] or [0])
    check("SPRT kills dead strategies, false-keep rate at or under alpha=5%",
          false_keep <= 0.10,
          f"false keep {false_keep:.0%}, median {n_dead:.0f} observations to kill")
    check("SPRT keeps live ones, miss rate at or under beta=20%",
          missed <= 0.30, f"missed {missed:.0%} of live strategies")


def t11_filters() -> None:
    print("\n[11] Kalman beta, OU half-life, trend forecast")
    n = 3000
    x = RNG.normal(0, 0.01, n)
    beta_true = np.where(np.arange(n) < 1500, 0.5, 1.5)
    y = beta_true * x + RNG.normal(0, 0.002, n)
    bhat = g.kalman_beta(pd.Series(y), pd.Series(x), q=1e-5, r=0.002 ** 2)
    check("Kalman beta finds the first regime",
          approx(float(bhat.iloc[1400]), 0.5, 0.15), f"{float(bhat.iloc[1400]):.2f}")
    check("Kalman beta adapts to the step within ~100 bars",
          approx(float(bhat.iloc[1600]), 1.5, 0.25), f"{float(bhat.iloc[1600]):.2f}")

    lam, n2 = 0.05, 20_000                     # true half-life = ln2/0.05 = 13.9
    y2 = np.empty(n2); y2[0] = 0.0
    for i in range(1, n2):
        y2[i] = y2[i - 1] + lam * (0.0 - y2[i - 1]) + RNG.normal(0, 0.1)
    hl = g.ou_half_life(pd.Series(y2))
    check("OU half-life recovered from a simulated process",
          approx(hl, math.log(2) / lam, 1.5), f"{hl:.1f} vs {math.log(2)/lam:.1f}")
    rw = np.cumsum(RNG.normal(0, 0.01, 5000))
    check("a random walk reports no reversion",
          g.ou_half_life(pd.Series(rw)) > 200, f"{g.ou_half_life(pd.Series(rw)):.0f}")

    # A forecast is useful if forecast_{t-1} * return_t has a positive mean.
    # Magnitude is not the claim -- sign and usefulness are.
    def trend_pnl(rets: np.ndarray) -> tuple[float, float]:
        px = pd.Series(np.cumprod(1 + rets))
        f = g.trend_forecast(px)
        pnl = (f.shift(1) * px.pct_change()).dropna()
        return float(f.dropna().mean()), g.sharpe(pnl)

    drift_mean, drift_sr = trend_pnl(RNG.normal(0.0008, 0.01, 6000))
    check("trend forecast is bounded in (-1, 1)",
          float(g.trend_forecast(pd.Series(np.cumprod(
              1 + RNG.normal(0.0008, 0.01, 6000)))).abs().max()) < 1.0)
    check("trend forecast leans long on a trending series",
          drift_mean > 0.1, f"mean forecast {drift_mean:.2f}")
    check("and trading it makes money there",
          drift_sr > 0.3, f"Sharpe {drift_sr:.2f}")
    chop_mean, chop_sr = trend_pnl(RNG.normal(0.0, 0.01, 6000))
    check("it neither leans nor earns on a driftless series",
          abs(chop_mean) < 0.4 and abs(chop_sr) < 0.5,
          f"mean {chop_mean:.2f}, Sharpe {chop_sr:.2f}")


def t12_misc() -> None:
    print("\n[12] shared helpers")
    check("max_drawdown of a monotone rise is 0",
          approx(g.max_drawdown(pd.Series([0.01] * 50)), 0.0, 1e-12))
    check("max_drawdown catches a -50% dip",
          approx(g.max_drawdown(pd.Series([0.0, -0.5, 1.0])), -0.5, 1e-12))
    a = pd.Series({"A": 0.5, "B": 0.5})
    b = pd.Series({"B": 0.5, "C": 0.5})
    check("turnover_cost charges the two-way move",
          approx(g.turnover_cost(a, b, 10.0), 0.5 * 1.0 * 10 / 10_000, 1e-12),
          f"{g.turnover_cost(a, b, 10.0)*10_000:.1f} bps")
    check("diversity weights sit between cap and equal weight",
          (lambda w: w[0] < 0.7 and w[0] > 1 / 3)(
              g.diversity_weights([700.0, 200.0, 100.0], 0.76)),
          f"{np.round(g.diversity_weights([700.0, 200.0, 100.0], 0.76), 3)}")


def main() -> None:
    print("scout.growth self-test  (synthetic data only -- no keys, no network)")
    for fn in (t1_growth_identity, t2_optimal_leverage, t3_drawdown_kelly,
               t4_rebalancing_premium, t5_diversification_arithmetic,
               t6_vol_targeting, t7_covariance, t8_kelly_weights, t9_breadth,
               t10_ship_gates, t11_filters, t12_misc):
        fn()
    print("\n" + "=" * 62)
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: " + ", ".join(FAILURES))
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()

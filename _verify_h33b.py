"""Part 2: Round-4 metric (Sharpe), deflated Sharpe at the repo's running N, regime."""
import numpy as np, math
from scout import coverage_lab as L

raw = L.load_raw(); panel = L.build_panel(raw, guard=True); lag = panel["lag"]
bench = panel["BENCH"]
bs_ew = L.bucket_series(panel, "RESID", 3, "ew")
bs_dv = L.bucket_series(panel, "RESID", 3, "dv")
ew, dv, sel = bs_ew["pool"], bs_dv["pool"], bs_ew["spread"]
low_ew = bs_ew["buckets"][:, 0]
dates = panel["dates"]
ANN = math.sqrt(252.0 / 42.0)

def _norm_ppf(p):
    # Acklam inverse normal CDF
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,-2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,3.754408661907416e+00]
    pl,ph=0.02425,1-0.02425
    if p<pl:
        q=math.sqrt(-2*math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p>ph:
        q=math.sqrt(-2*math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q=p-0.5; r=q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

def _norm_cdf(x):
    return 0.5*(1+math.erf(x/math.sqrt(2)))

def _skew(x):
    x=np.asarray(x,float); m=x.mean(); s=x.std(ddof=0)
    return float(((x-m)**3).mean()/s**3)

def _kurt(x):
    x=np.asarray(x,float); m=x.mean(); s=x.std(ddof=0)
    return float(((x-m)**4).mean()/s**4)


def sh(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return x.mean() / x.std(ddof=1) * ANN

print("=== ROUND 4's OWN METRIC (Sharpe), on this panel ===")
for n, x in [("SPY", bench), ("EW pool", ew), ("DV pool", dv),
             ("LOW leg EW (selection)", low_ew)]:
    print(f"  {n:24s} ann.Sharpe {sh(x):6.3f}")
print(f"  CONSTRUCTION gap in Sharpe (DV-EW)  {sh(dv)-sh(ew):+.3f}   "
      f"[Round 4 quoted 0.216 for cap-vs-equal]")
print(f"  SELECTION  gap in Sharpe (LOW-EWpool) {sh(low_ew)-sh(ew):+.3f}  "
      f"[Round 4 quoted +0.030]")
print(f"  Sharpe ratio construction:selection = "
      f"{abs((sh(dv)-sh(ew))/(sh(low_ew)-sh(ew))):.2f} : 1  (headline says 3.6:1)")
print(f"  DV pool vs SPY on Sharpe: {sh(dv)-sh(bench):+.3f}")

# deflated Sharpe at the repo's real running trial count
def dsr(x, N, lag=lag):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    n = len(x)
    # effective independent obs for 42-session overlap at step 1
    n_eff = max(n / (lag + 1), 5)
    s = x.mean() / x.std(ddof=1)
    g3 = _skew(x); g4 = _kurt(x)
    emc = 0.5772156649
    s0 = math.sqrt(1.0 / n_eff) * ((1 - emc) * _norm_ppf(1 - 1.0 / N)
                                   + emc * _norm_ppf(1 - 1.0 / (N * math.e)))
    num = (s - s0) * math.sqrt(n_eff - 1)
    den = math.sqrt(1 - g3 * s + (g4 - 1) / 4.0 * s * s)
    return _norm_cdf(num / den), s * ANN, n_eff

print("\n=== DEFLATED SHARPE at the repo's real running N (not the lab's 51) ===")
for name, x in [("construction gap DV-EW", dv - ew),
                ("DV pool minus SPY", dv - bench),
                ("selection spread LOW-HIGH", sel),
                ("LOW leg minus SPY", low_ew - bench)]:
    for N in (51, 740):
        p, s, ne = dsr(x, N)
        print(f"  {name:26s} N={N:4d}  DSR {p:5.3f}  ann.Sharpe {s:6.3f}  n_eff {ne:.0f}")

print("\n=== REGIME: construction gap by year ===")
yrs = np.array([d.year for d in dates])
g = dv - ew
for y in sorted(set(yrs)):
    m = (yrs == y) & np.isfinite(g)
    print(f"  {y}: gap {1e4*g[m].mean():8.1f} bps   DV {1e4*dv[m].mean():8.1f}   "
          f"EW {1e4*ew[m].mean():8.1f}   SPY {1e4*bench[m].mean():8.1f}   n={m.sum()}")

print("\n=== does the gap survive dropping the single best year? ===")
for y in sorted(set(yrs)):
    m = np.isfinite(g) & (yrs != y)
    s = L.stats(g[m], lag)
    print(f"  ex-{y}: {s['mean_bps']:7.1f} bps  nw_t {s['nw_t']:5.2f}")

print("\n=== drawdown / tail: worst 42-session window, each book ===")
for n, x in [("SPY", bench), ("EW pool", ew), ("DV pool", dv)]:
    x2 = x[np.isfinite(x)]
    print(f"  {n:10s} worst {1e4*x2.min():9.1f}  p05 {1e4*np.percentile(x2,5):9.1f}  "
          f"sd {1e4*x2.std(ddof=1):8.1f}")

print("\n=== was NVDA driving it?  DV pool with the single largest weight capped ===")
for cap in (1.0, 0.05, 0.03):
    out = np.full(len(dates), np.nan)
    for i in range(len(dates)):
        m = panel["OPEN"][i]
        if m.sum() < 30: continue
        w = L._weights("dv", panel["SIZE"][i][m]); w = w / w.sum()
        if cap < 1.0:
            for _ in range(50):
                over = w > cap
                if not over.any(): break
                ex = (w[over] - cap).sum(); w[over] = cap
                free = ~over
                if not free.any(): break
                w[free] += ex * w[free] / w[free].sum()
        out[i] = panel["FWD"][i][m] @ w / w.sum()
    s = L.stats(out[np.isfinite(out)], lag)
    ba, _ = L.beta_alpha(out, bench, lag)
    gap = out - ew
    sg = L.stats(gap[np.isfinite(gap)], lag)
    print(f"  cap {cap:>4}: DV pool {s['mean_bps']:7.1f}  beta {ba['beta']:.3f} "
          f"alpha {ba['alpha_bps']:6.1f} (t {ba['alpha_t']})  | gap vs EW "
          f"{sg['mean_bps']:7.1f} (t {sg['nw_t']:.2f})")

"""Part 3: is 'construction' a law, or a momentum/one-name tilt?"""
import numpy as np, math
from scout import coverage_lab as L

raw = L.load_raw(); panel = L.build_panel(raw, guard=True); lag = panel["lag"]
bench = panel["BENCH"]; dates = panel["dates"]
bs_ew = L.bucket_series(panel, "RESID", 3, "ew"); ew = bs_ew["pool"]

def pool_with(wfun):
    out = np.full(len(dates), np.nan)
    for i in range(len(dates)):
        m = panel["OPEN"][i]
        if m.sum() < 30: continue
        w = wfun(panel["SIZE"][i][m], i, m)
        w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
        if w.sum() <= 0: continue
        out[i] = panel["FWD"][i][m] @ w / w.sum()
    return out

print("=== H31c-style monotonicity: pool return vs weight exponent p on ADV$ ===")
print("   (a real construction law should be monotone in p)")
for p in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25):
    x = pool_with(lambda s, i, m, p=p: np.exp(p * s))
    st = L.stats(x[np.isfinite(x)], lag); ba, _ = L.beta_alpha(x, bench, lag)
    g = x - ew; sg = L.stats(g[np.isfinite(g)], lag)
    print(f"  p={p:4.2f}: {st['mean_bps']:7.1f} bps  beta {ba['beta']:.3f}  "
          f"alpha {ba['alpha_bps']:6.1f} (t {ba['alpha_t']})  gap vs EW "
          f"{sg['mean_bps']:7.1f} (t {sg['nw_t']:5.2f})  halves "
          f"{sg['h1_bps']:7.1f}/{sg['h2_bps']:7.1f}  thirds {sg['thirds_bps']}")

print("\n=== is DV weight a MOMENTUM tilt?  xs rank corr(log ADV$, 12-1 mom) ===")
cs = []
for i in range(len(dates)):
    m = panel["OPEN"][i] & np.isfinite(panel["MOM"][i])
    if m.sum() < 30: continue
    a = L._rank_pct(panel["SIZE"][i][m]); b = L._rank_pct(panel["MOM"][i][m])
    cs.append(np.corrcoef(a, b)[0, 1])
print(f"  median {np.median(cs):+.3f}  mean {np.mean(cs):+.3f}  "
      f"frac>0 {np.mean(np.array(cs) > 0):.1%}")

print("\n=== the retail alternative: hold 1.186x SPY instead ===")
lev = 1.186 * bench
st = L.stats(lev[np.isfinite(lev)], lag)
bs_dv = L.bucket_series(panel, "RESID", 3, "dv"); dv = bs_dv["pool"]
d = dv - lev; sd_ = L.stats(d[np.isfinite(d)], lag)
print(f"  1.186x SPY  {st['mean_bps']:7.1f} bps/window   DV pool 352.4")
print(f"  DV pool minus levered SPY: {sd_['mean_bps']:7.1f} bps  nw_t {sd_['nw_t']:5.2f}  "
      f"halves {sd_['h1_bps']:7.1f}/{sd_['h2_bps']:7.1f}  thirds {sd_['thirds_bps']}")

print("\n=== drop the single largest DV name each date (is it one stock?) ===")
def pool_drop_top(k):
    out = np.full(len(dates), np.nan)
    for i in range(len(dates)):
        m = panel["OPEN"][i]
        if m.sum() < 30: continue
        w = L._weights("dv", panel["SIZE"][i][m]); idx = np.argsort(w)[::-1]
        w = w.copy(); w[idx[:k]] = 0.0
        out[i] = panel["FWD"][i][m] @ w / w.sum()
    return out
for k in (0, 1, 2, 3):
    x = pool_drop_top(k); g = x - ew; sg = L.stats(g[np.isfinite(g)], lag)
    ba, _ = L.beta_alpha(g, bench, lag)
    print(f"  drop top-{k}: gap vs EW {sg['mean_bps']:7.1f} (t {sg['nw_t']:5.2f})  "
          f"Rule13 beta {ba['beta']:+.3f} alpha {ba['alpha_bps']:6.1f} (t {ba['alpha_t']})")

print("\n=== how often does the top DV name change, and who is it? ===")
from collections import Counter
c = Counter()
for i in range(len(dates)):
    m = panel["OPEN"][i]
    if m.sum() < 30: continue
    w = L._weights("dv", panel["SIZE"][i][m])
    c[np.array(panel["cols"])[m][int(np.argmax(w))]] += 1
print("  top-DV-name occupancy:", c.most_common(8))

"""Adversarial recomputation of H33's 'construction beats selection 3.6:1' bonus."""
import numpy as np, math, json
from scout import coverage_lab as L

raw = L.load_raw()
panel = L.build_panel(raw, guard=True)
lag = panel["lag"]
print("dates", len(panel["dates"]), panel["dates"][0].date(), panel["dates"][-1].date(), "lag", lag)

bs_ew = L.bucket_series(panel, "RESID", 3, "ew")
bs_dv = L.bucket_series(panel, "RESID", 3, "dv")
bench = panel["BENCH"]

ew = bs_ew["pool"]; dv = bs_dv["pool"]; sel = bs_ew["spread"]
ok = np.isfinite(ew) & np.isfinite(dv) & np.isfinite(bench) & np.isfinite(sel)
print("n usable", ok.sum())

def rep(name, x, b=bench):
    x = np.asarray(x, float)
    m = np.isfinite(x) & np.isfinite(b)
    s = L.stats(x[m], lag)
    ba, adj = L.beta_alpha(x, b, lag)
    print(f"{name:34s} mean {s['mean_bps']:8.1f}  nw_t {s['nw_t']:5.2f} | "
          f"beta {ba['beta']:6.3f} alpha {ba['alpha_bps']:8.1f} (t {ba['alpha_t']:5.2f}) "
          f"| halves {s['h1_bps']:7.1f}/{s['h2_bps']:7.1f} "
          f"| alpha halves {ba['alpha_h1_bps']:7.1f}/{ba['alpha_h2_bps']:7.1f} "
          f"| alpha thirds {ba['alpha_thirds_bps']}")
    return s, ba

print("\n=== the three legs the bonus compares ===")
rep("EW pool", ew)
rep("DV pool", dv)
rep("SPY", bench)
print()
rep("SELECTION spread (LOW-HIGH, EW)", sel)
con = dv - ew
rep("CONSTRUCTION diff (DV - EW pool)", con)

# same, restricted to the identical usable subset for an apples-to-apples ratio
print("\n=== Rule 13 arithmetic decomposition of the +91.8 ===")
s_ew = L.stats(ew[ok], lag); s_dv = L.stats(dv[ok], lag); s_b = L.stats(bench[ok], lag)
ba_ew, _ = L.beta_alpha(ew, bench, lag); ba_dv, _ = L.beta_alpha(dv, bench, lag)
dbeta = ba_dv["beta"] - ba_ew["beta"]
print(f"  raw gap                {s_dv['mean_bps'] - s_ew['mean_bps']:.1f} bps")
print(f"  beta gap               {dbeta:.3f}  x SPY {s_b['mean_bps']:.1f} bps = "
      f"{dbeta * s_b['mean_bps']:.1f} bps of PURE BETA")
print(f"  alpha gap              {ba_dv['alpha_bps'] - ba_ew['alpha_bps']:.1f} bps")
print(f"  beta share of the gap  {dbeta * s_b['mean_bps'] / (s_dv['mean_bps'] - s_ew['mean_bps']):.1%}")

ba_con, _ = L.beta_alpha(con, bench, lag)
print(f"\n  DIRECT Rule 13 on the construction DIFFERENCE series: "
      f"beta {ba_con['beta']:.3f}  alpha {ba_con['alpha_bps']:.1f}  t {ba_con['alpha_t']}")
ba_sel, _ = L.beta_alpha(sel, bench, lag)
print(f"  Rule 13 on the SELECTION spread:                       "
      f"beta {ba_sel['beta']:.3f}  alpha {ba_sel['alpha_bps']:.1f}  t {ba_sel['alpha_t']}")
print(f"\n  HEADLINE ratio (raw)          {abs((s_dv['mean_bps']-s_ew['mean_bps'])/25.5):.2f} : 1")
print(f"  RISK-ADJUSTED ratio (alpha)   "
      f"{abs(ba_con['alpha_bps'] / ba_sel['alpha_bps']):.2f} : 1")

# equal-beta comparison: lever the EW pool to the DV pool's beta
print("\n=== beta-matched construction gap (lever EW pool to DV's beta) ===")
k = ba_dv["beta"] / ba_ew["beta"]
ew_lev = k * ew
rep(f"EW pool levered x{k:.3f}", ew_lev)
rep("DV - levered EW", dv - ew_lev)

# concentration / capacity of the DV pool
print("\n=== capacity: DV weight concentration ===")
effn, top1, top5, top10 = [], [], [], []
for i in range(len(panel["dates"])):
    m = panel["OPEN"][i]
    if m.sum() < 30:
        continue
    w = L._weights("dv", panel["SIZE"][i][m])
    w = w / w.sum()
    ws = np.sort(w)[::-1]
    effn.append(1.0 / (w ** 2).sum()); top1.append(ws[0]); top5.append(ws[:5].sum())
    top10.append(ws[:10].sum())
print(f"  median effective N {np.median(effn):.1f} of {int(np.median(bs_dv['size'])) } names; "
      f"top-1 weight {np.median(top1):.1%}, top-5 {np.median(top5):.1%}, top-10 {np.median(top10):.1%}")

# name-level: who carries the DV pool at the end of the sample
i = len(panel["dates"]) - 1
m = panel["OPEN"][i]
w = L._weights("dv", panel["SIZE"][i][m]); w = w / w.sum()
names = np.array(panel["cols"])[m]
o = np.argsort(w)[::-1][:10]
print("  last formation top-10 DV weights:",
      ", ".join(f"{names[j]} {w[j]:.1%}" for j in o))

# turnover of the DV pool weights (dollar turnover, not name turnover)
print("\n=== DV-pool weight turnover per 42-session rebalance (one-way) ===")
lagn = 42
tw = []
for i in range(lagn, len(panel["dates"])):
    m0, m1 = panel["OPEN"][i - lagn], panel["OPEN"][i]
    if m0.sum() < 30 or m1.sum() < 30:
        continue
    w0 = np.zeros(len(panel["cols"])); w1 = np.zeros(len(panel["cols"]))
    a = L._weights("dv", panel["SIZE"][i - lagn][m0]); w0[m0] = a / a.sum()
    b = L._weights("dv", panel["SIZE"][i][m1]); w1[m1] = b / b.sum()
    tw.append(0.5 * np.abs(w1 - w0).sum())
print(f"  median one-way weight turnover {np.median(tw):.3f}  mean {np.mean(tw):.3f}")

json.dump({"ok": True}, open("/dev/null", "w"))

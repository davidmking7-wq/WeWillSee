"""Which project should we actually build? -- the selection formula.

RESEARCH-AGENDA.md ranks candidate edges by prose judgement. This makes the
ranking arithmetic, because the arithmetic disagrees with intuition in a
specific and repeatable way: intuition ranks ideas by how much return they
promise, and the growth identity ranks them by how much SHARPE they add to
the book you already hold -- which depends on their CORRELATION to it far
more than on their standalone quality.

    Delta g  =  (S_after^2 - S_before^2) / 2 * f          [growth.py]
    S_after  =  sqrt( S_before^2 + S_new^2 )   when rho = 0
                (w'S / sqrt(w'Cw) in general)

A sleeve with Sharpe 0.4 and zero correlation to your book beats a sleeve
with Sharpe 0.8 correlated 0.8 to it. That single fact reorders the agenda.

THE SCORE
---------
For each candidate:

    S_eff    = S_lit * decay * transfer          expected LIVE Sharpe
    S_after  = combine_sharpe([S_book, S_eff], [[1, rho], [rho, 1]])
    Delta g  = ( S_after^2 - S_book^2 ) / 2 * f_kelly
    P_ship   = prior * P(clears the deflated-Sharpe gate at this data size)
    Priority = Delta g * P_ship / effort_days

`decay` applies McLean-Pontiff (2016) directly: an anomaly loses ~26% of
its published size out of sample and ~58% after publication. `transfer` is
Grinold's TC -- what survives long-only constraints, retail execution and
free-data approximations of the real signal. Both are haircuts applied
BEFORE the idea competes, so an effect that is only impressive in a paper
does not out-rank one that is modest but implementable.

The numbers below are frozen from the cited literature and from this repo's
own measured results. They are estimates and they are stated as estimates:
the output is a RANKING to spend research time against, not a forecast.

Run:  python -m scout.agenda_rank [--book-sharpe 0.5] [--max-dd 0.30]
"""
from __future__ import annotations

import argparse
import math

import numpy as np

from . import growth as g


# effort_days is calendar days of work for one researcher with this repo's
# existing harness. data_free=False means the idea needs a paid or
# unavailable feed, which is a hard blocker here, not a cost.
CANDIDATES = [
    dict(
        name="multi-asset trend", field="signal processing / macro flows",
        mechanism="Macro information diffuses slowly and institutional flows "
                  "(rebalancing, hedging, risk limits) push with recent moves; "
                  "an EWMA crossover is the matched filter for that drift.",
        s_lit=0.75, decay=0.60, transfer=0.75, rho_book=0.05,
        prior=0.75, effort_days=6, data_free=True,
        evidence="Moskowitz-Ooi-Pedersen 2012 (58 instruments); "
                 "Hurst-Ooi-Pedersen 2017 (100+ years, 4 asset classes)",
    ),
    dict(
        name="cross-asset carry", field="economics / term structure",
        mechanism="Holders of assets in backwardation or with positive roll "
                  "are paid a risk premium for warehousing a risk somebody "
                  "else wants to shed; the premium is observable ex ante.",
        s_lit=0.70, decay=0.55, transfer=0.55, rho_book=0.25,
        prior=0.60, effort_days=12, data_free=False,
        evidence="Koijen-Moskowitz-Pedersen-Vrugt 2018. ETF proxies capture "
                 "only a fraction; the real signal needs futures curves.",
    ),
    dict(
        name="volatility targeting", field="control theory",
        mechanism="Volatility is forecastable (clustering) while return is "
                  "not; holding risk constant raises the geometric mean "
                  "without touching the arithmetic one.",
        s_lit=0.15, decay=0.90, transfer=0.85, rho_book=0.95,
        prior=0.85, effort_days=2, data_free=True,
        evidence="Moreira-Muir 2017; Harvey et al. 2018. Applies TO the book "
                 "rather than beside it -- rho ~1 by construction, so its "
                 "value shows up as a Sharpe uplift, not a new bet.",
    ),
    dict(
        name="fractional Kelly sizing", field="information theory",
        mechanism="Growth is maximised at L*=mu/sigma^2 and is quadratic "
                  "around it; most books are sized by feel, which is a "
                  "point estimate of a quantity nobody measured.",
        s_lit=0.10, decay=1.00, transfer=0.90, rho_book=0.98,
        prior=0.90, effort_days=2, data_free=True,
        evidence="Kelly 1956; MacLean-Thorp-Ziemba. Converts an existing "
                 "Sharpe into return; adds no new Sharpe on its own.",
    ),
    dict(
        name="rebalancing premium / diversity weights",
        field="stochastic portfolio theory",
        mechanism="gamma* = 0.5(sum w_i sigma_ii - w'Sigma w) >= 0 is an "
                  "identity, not an anomaly: a rebalanced diversified book "
                  "out-grows the weighted average of its constituents.",
        s_lit=0.25, decay=1.00, transfer=0.70, rho_book=0.85,
        prior=0.70, effort_days=4, data_free=True,
        evidence="Fernholz 2002. The theorem's condition (diversity does not "
                 "fall) FAILED in 2017-2026 -- this repo's gates lab measured "
                 "cap-weight beating every equal-weight book. It is a bet on "
                 "concentration mean-reverting.",
    ),
    dict(
        name="merger arbitrage", field="event-driven / insurance",
        mechanism="The spread between the deal price and the market price "
                  "pays for bearing deal-break risk, which is nearly "
                  "uncorrelated with the market except in credit crises.",
        s_lit=0.80, decay=0.60, transfer=0.45, rho_book=0.20,
        prior=0.55, effort_days=20, data_free=True,
        evidence="Mitchell-Pulvino 2001. Free deal terms via SEC 8-K/DEFM14A. "
                 "Negative skew: it sells insurance, and the deflated-Sharpe "
                 "gate penalises that correctly.",
    ),
    dict(
        name="variance risk premium", field="actuarial / insurance",
        mechanism="Implied variance exceeds realised variance by 2-4 vol "
                  "points on average because buyers of protection pay for "
                  "certainty; the seller collects that premium.",
        s_lit=1.00, decay=0.55, transfer=0.40, rho_book=0.55,
        prior=0.50, effort_days=25, data_free=False,
        evidence="Carr-Wu 2009; Bollerslev-Tauchen-Zhou 2009. Needs options "
                 "data. Left tail is severe (Feb 2018 wiped out several "
                 "levered sellers) -- Kelly sizing on a fat-tailed "
                 "distribution is not the Gaussian formula.",
    ),
    dict(
        name="betting against beta", field="behavioural / leverage limits",
        mechanism="Investors who want more return but cannot use leverage "
                  "buy high beta instead, overpricing it; the fix is to hold "
                  "low beta AND lever it.",
        s_lit=0.55, decay=0.45, transfer=0.60, rho_book=0.60,
        prior=0.55, effort_days=5, data_free=True,
        evidence="Frazzini-Pedersen 2014; Black 1972. Heavily published and "
                 "heavily traded since -- the decay haircut is doing real "
                 "work here.",
    ),
    dict(
        name="net share issuance", field="corporate finance / accounting",
        mechanism="Managers issue stock when they believe it is overvalued "
                  "and buy it back when undervalued; shares outstanding is "
                  "an insider forecast disclosed quarterly for free.",
        s_lit=0.45, decay=0.45, transfer=0.60, rho_book=0.30,
        prior=0.65, effort_days=10, data_free=True,
        evidence="Pontiff-Woodgate 2008; Daniel-Titman 2006. Among the most "
                 "robust cross-sectional anomalies in replication studies. "
                 "Free via SEC XBRL companyconcept (reachable from here).",
    ),
    dict(
        name="gross profitability / quality", field="accounting",
        mechanism="Gross profit / assets measures productive capacity before "
                  "accounting discretion can distort it; profitable firms "
                  "trade at a discount to their fundamentals.",
        s_lit=0.40, decay=0.45, transfer=0.60, rho_book=0.35,
        prior=0.60, effort_days=10, data_free=True,
        evidence="Novy-Marx 2013. Same free XBRL pipeline as net issuance -- "
                 "build once, get both.",
    ),
    dict(
        name="economic-link lead-lag", field="network science",
        mechanism="Investors have limited attention and do not update a "
                  "supplier's price when its major customer moves; the link "
                  "is disclosed in 10-K customer concentration notes.",
        s_lit=0.60, decay=0.45, transfer=0.45, rho_book=0.35,
        prior=0.40, effort_days=25, data_free=True,
        evidence="Cohen-Frazzini 2008; Menzly-Ozbas 2010. Free but expensive "
                 "to build: the link graph must be parsed from filing text, "
                 "and it must be point-in-time or the result is fiction.",
    ),
    dict(
        name="residual momentum", field="factor econometrics",
        mechanism="Rank on the momentum of returns AFTER removing factor "
                  "exposure, so the signal is firm-specific drift rather "
                  "than a bet on whatever factor recently ran.",
        s_lit=0.50, decay=0.50, transfer=0.55, rho_book=0.70,
        prior=0.55, effort_days=7, data_free=True,
        evidence="Blitz-Huij-Martens 2011. Correlated to what this repo "
                 "already does -- which is exactly why its marginal value "
                 "is smaller than its standalone Sharpe suggests.",
    ),
    dict(
        name="short interest / lending fees", field="supply and demand",
        mechanism="Expensive-to-borrow names are ones informed short sellers "
                  "want and cannot get enough of; the fee is a price signal.",
        s_lit=0.55, decay=0.50, transfer=0.35, rho_book=0.30,
        prior=0.45, effort_days=12, data_free=True,
        evidence="Boehmer-Jones-Zhang; Drechsler-Drechsler. FINRA short "
                 "interest is free and biweekly; actual borrow fees are not, "
                 "and the fee is where most of the signal lives.",
    ),
    dict(
        name="calendar-month seasonality", field="behavioural",
        mechanism="Same-calendar-month return persists across years through "
                  "recurring institutional flows (tax, fiscal-year, "
                  "index-cycle dates).",
        s_lit=0.35, decay=0.40, transfer=0.50, rho_book=0.15,
        prior=0.30, effort_days=5, data_free=True,
        evidence="Heston-Sadka 2008. Weak prior: this is the candidate in "
                 "the list closest to pattern-mining, and RESEARCH-AGENDA "
                 "rule 1 says mechanism first.",
    ),
    dict(
        name="stock selection inside the S&P 1500",
        field="the current engine",
        mechanism="Rank stocks by a momentum composite and hold the top few.",
        s_lit=0.0, decay=1.0, transfer=1.0, rho_book=1.0,
        prior=0.05, effort_days=30, data_free=True,
        evidence="MEASURED AT ZERO IN THIS REPO. Decile 1 minus decile 10 = "
                 "-0.26% at 42 td over ten years; gated book alpha -1.08%/yr "
                 "on point-in-time data. Listed so the ranking includes the "
                 "thing we have already spent the most time on.",
    ),
]


OVERLAY_RHO = 0.90     # above this a candidate is an overlay, not a sleeve


def score(c: dict, book_sharpe: float, f_kelly: float) -> dict:
    s_eff = c["s_lit"] * c["decay"] * c["transfer"]
    rho = c["rho_book"]
    if rho > OVERLAY_RHO:
        # An OVERLAY acts on the book you already have (vol targeting, Kelly
        # sizing, rebalancing discipline). Treating it as a second sleeve is
        # wrong twice over: at equal risk weight it looks dilutive, and at the
        # optimal weight the two-asset formula explodes as rho -> 1 because it
        # starts arbitraging one against the other. Its effect is additive on
        # the book's own Sharpe, which is what the literature measures.
        s_after = book_sharpe + s_eff
    else:
        # Best LONG-ONLY mix of the existing book and the new sleeve. Equal
        # weighting would score a weak-but-uncorrelated sleeve as harmful
        # (the right answer is "hold less of it"); the unconstrained optimum
        # would score a near-duplicate as a stat-arb pair. The simplex is
        # the honest middle.
        corr = np.array([[1.0, rho], [rho, 1.0]])
        s_after = g.best_long_only_sharpe([book_sharpe, s_eff], corr)
    s_after = max(s_after, book_sharpe)
    d_growth = (s_after ** 2 - book_sharpe ** 2) / 2.0 * f_kelly

    # PROVABILITY, reported separately from value. Years of our OWN daily
    # data needed before this Sharpe is distinguishable from zero at 95%.
    # Meaningless for overlays: those are tested PAIRED (same book with and
    # without), and the difference has far lower variance than either leg.
    sr_d = s_eff / math.sqrt(252)
    years_to_prove = (float("nan") if rho > OVERLAY_RHO else
                      (g.min_track_record_length(sr_d, 0.0, confidence=0.95) / 252
                       if sr_d > 0 else float("inf")))
    # And whether it could clear a deflated-Sharpe gate on 10 years, given
    # the repo's running trial count. Mostly it cannot -- see the note below.
    p_gate = g.deflated_sharpe(sr_d, n_trials=120, n_obs=2520)

    p_ship = c["prior"] * (1.0 if c["data_free"] else 0.25)
    return {**c, "s_eff": s_eff, "s_after": s_after, "d_growth": d_growth,
            "p_gate": p_gate, "p_ship": p_ship,
            "years_to_prove": years_to_prove,
            "priority": d_growth * p_ship / c["effort_days"] * 100}


def main() -> None:
    ap = argparse.ArgumentParser(prog="scout.agenda_rank")
    ap.add_argument("--book-sharpe", type=float, default=0.50,
                    help="Sharpe of what you hold today (SPY long-run ~0.4-0.5; "
                         "this repo's gated equity book measured 0.81 over the "
                         "2017-2026 bull decade, which is not a long-run number)")
    ap.add_argument("--max-dd", type=float, default=0.30)
    ap.add_argument("--dd-prob", type=float, default=0.10)
    ap.add_argument("--n-sleeves", type=int, default=3,
                    help="how many diversifying sleeves to stack")
    ap.add_argument("--sleeve-corr", type=float, default=0.25,
                    help="assumed correlation BETWEEN sleeves; zero is the "
                         "classic way to overstate a multi-strategy book")
    args = ap.parse_args()

    f = g.kelly_fraction_for_drawdown(args.max_dd, args.dd_prob)
    print(f"Book Sharpe today: {args.book_sharpe:.2f}  ->  achievable growth at "
          f"full Kelly {args.book_sharpe**2/2:.1%}/yr, at the "
          f"{args.max_dd:.0%}-drawdown fraction f={f:.2f}: "
          f"{args.book_sharpe**2/2*f:.1%}/yr\n")

    rows = sorted((score(c, args.book_sharpe, f) for c in CANDIDATES),
                  key=lambda r: -r["priority"])
    hdr = (f"{'#':<3}{'candidate':<38}{'S_lit':>7}{'S_eff':>7}{'rho':>6}"
           f"{'S_book+':>9}{'dGrowth':>9}{'prove_y':>9}{'days':>6}{'score':>8}")
    print(hdr); print("-" * len(hdr))
    for i, r in enumerate(rows, 1):
        free = "" if r["data_free"] else "  [PAID DATA]"
        y = r["years_to_prove"]
        yrs = ("paired" if math.isnan(y) else
               "inf" if math.isinf(y) else f"{y:.0f}")
        print(f"{i:<3}{r['name'][:36]:<38}{r['s_lit']:>7.2f}{r['s_eff']:>7.2f}"
              f"{r['rho_book']:>6.2f}{r['s_after']:>9.2f}"
              f"{100*r['d_growth']:>8.1f}%{yrs:>9}"
              f"{r['effort_days']:>6}{r['priority']:>8.2f}{free}")

    print("\nHow to read this")
    print("  S_eff    = S_lit after the McLean-Pontiff decay haircut and the "
          "transfer\n             coefficient (long-only, retail execution, "
          "free-data proxy).")
    print("  S_book+  = the book's Sharpe AFTER adding this, at the optimal "
          "weight.")
    print("  dGrowth  = extra annual COMPOUNDED return for the WHOLE book at "
          f"the\n             {args.max_dd:.0%}-drawdown Kelly fraction "
          f"(f={f:.2f}) -- not the candidate's own return.")
    print("  prove_y  = years of OUR OWN daily data needed before that Sharpe "
          "is\n             distinguishable from zero at 95% "
          "(min_track_record_length).")
    print("  score    = dGrowth x prior x data-availability / effort_days. "
          "Rank, not forecast.")

    # The headline the whole exercise is for. Sleeves are ranked by the
    # growth they ADD, not by the score (which divides by effort and would
    # let a cheap overlay crowd out the sleeve that actually diversifies).
    sleeves = sorted((r for r in rows
                      if r["data_free"] and r["rho_book"] <= OVERLAY_RHO
                      and r["d_growth"] > 0),
                     key=lambda r: -r["d_growth"])[:args.n_sleeves]
    overlays = [r for r in rows
                if r["rho_book"] > OVERLAY_RHO and r["data_free"]
                and r["s_eff"] > 0]

    # Correlation structure: each sleeve's stated rho to the book, and a
    # common rho between sleeves (different mechanisms, but they all live in
    # the same markets -- assuming zero here is the classic way to overstate
    # a multi-strategy book).
    inter = args.sleeve_corr
    sharpes = [args.book_sharpe] + [r["s_eff"] for r in sleeves]
    n = len(sharpes)
    c_mat = np.full((n, n), inter)
    for i, r in enumerate(sleeves, start=1):
        c_mat[0, i] = c_mat[i, 0] = r["rho_book"]
    np.fill_diagonal(c_mat, 1.0)
    s_sleeves = g.combine_sharpe(sharpes, c_mat)          # equal risk weight
    overlay_add = sum(r["s_eff"] for r in overlays)
    s_stack = s_sleeves + overlay_add

    print("\n" + "=" * 79)
    print("WHAT THE WHOLE STACK IS WORTH -- 'beat the market by a landslide', "
          "costed")
    print("=" * 79)
    print(f"  current book                       Sharpe {args.book_sharpe:.2f}")
    for r in sleeves:
        print(f"  + {r['name']:<32} S_eff {r['s_eff']:.2f}  "
              f"rho to book {r['rho_book']:.2f}  ({r['effort_days']}d)")
    print(f"  = equal-risk combination           Sharpe {s_sleeves:.2f}   "
          f"(rho={inter} assumed BETWEEN sleeves)")
    for r in overlays:
        print(f"  + {r['name']:<32} +{r['s_eff']:.2f} (overlay, {r['effort_days']}d)")
    print(f"  = stacked                          Sharpe {s_stack:.2f}")

    mult = s_stack / args.book_sharpe if args.book_sharpe > 0 else float("inf")
    print("\n  At the market's own volatility (15%), excess return:")
    print(f"     today    {args.book_sharpe * 0.15:>6.1%}/yr")
    print(f"     stacked  {s_stack * 0.15:>6.1%}/yr    -> {mult:.1f}x the "
          f"market's excess return at the SAME risk")
    print(f"\n  Compounded growth at the {args.max_dd:.0%}-drawdown Kelly "
          f"fraction (f={f:.2f}):")
    print(f"     today    {args.book_sharpe**2/2*f:>6.1%}/yr")
    print(f"     stacked  {s_stack**2/2*f:>6.1%}/yr    -> "
          f"{(s_stack**2)/(args.book_sharpe**2):.1f}x, because growth is "
          f"QUADRATIC in Sharpe")
    print(f"\n  {mult:.1f}x the market's excess return at unchanged risk is "
          f"what a landslide\n  honestly looks like from free data. It is not "
          f"10x. It is also not free:\n  {len(sleeves)} sleeves plus "
          f"{len(overlays)} overlays, "
          f"{sum(r['effort_days'] for r in sleeves + overlays)} days of work, "
          f"each piece able to\n  fail its own test -- and the whole thing "
          f"rests on the rho={inter} assumption\n  above. Re-run with "
          f"--sleeve-corr 0.5 to see how fast it degrades.")

    print("\nTHE PROVABILITY PROBLEM, stated plainly:")
    n_provable = sum(1 for r in rows if r["years_to_prove"] <= 10)
    print(f"  {n_provable} of {len(rows)} candidates could be proven on ten "
          f"years of our own data.\n  Deflated-Sharpe probabilities at the "
          f"repo's ~120-trial count are near zero\n  for almost every row. "
          f"This is not a reason to give up; it is the reason the\n  "
          f"EXTERNAL evidence base has to do the work -- a 100-year, "
          f"58-instrument study\n  is worth more than anything this repo can "
          f"establish on 2016-2026, and\n  candidates should be chosen for "
          f"the strength of that outside record.")

    print("\nThe correlation column is the point. Ranking by S_lit instead of "
          "dGrowth\nreorders this table: high-Sharpe candidates that overlap "
          "what you already own\nadd far less than their headline, and the "
          "overlays score well despite tiny\nS_lit because they multiply the "
          "entire book for two days of work.")

    print("\nMechanisms for the stacked sleeves:")
    for r in sleeves:
        print(f"\n  {r['name']}  [{r['field']}]")
        print(f"    mechanism: {r['mechanism']}")
        print(f"    evidence:  {r['evidence']}")


if __name__ == "__main__":
    main()

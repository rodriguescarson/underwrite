"""Turns the ledger into the three numbers that decide position size.

  claim accuracy   — of orders the executor said were placed/filled, how many did the CLI confirm
  silent failures  — claimed filled, CLI says otherwise (the dangerous quadrant)
  Brier / ECE      — stated p_profit vs realised outcome, over resolved structures

The metric arithmetic is `calibration_metrics.py`, reused from Attest (Brier, ECE,
risk-coverage — standard definitions, no LLM anywhere).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from . import ledger
from .calibration_metrics import Sample, brier, ece, risk_coverage
from .config import RISK


@dataclass
class CalibrationState:
    n_claims: int
    n_audited: int
    claim_accuracy: Optional[float]
    silent_failures: int
    n_resolved: int
    wins: int
    brier: Optional[float]
    ece: Optional[float]
    earned: bool
    risk_frac: float
    reasons: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def compute() -> CalibrationState:
    claims = ledger.read("orders")
    audits = ledger.latest_by("audits", "claim_id")
    outcomes = ledger.read("outcomes")

    n_claims = len(claims)
    audited = [(c, audits.get(c.get("claim_id"))) for c in claims if audits.get(c.get("claim_id"))]
    n_audited = len(audited)
    matches = sum(1 for _, a in audited if a.get("matches_claim"))
    silent = sum(1 for c, a in audited if c.get("claimed_status") in ("filled", "partially_filled") and a.get("observed_status") not in ("filled", "partially_filled"))
    claim_accuracy = round(matches / n_audited, 4) if n_audited else None

    resolved = [o for o in outcomes if o.get("resolved")]
    samples = [Sample(claimed_done=True, confidence=float(o["p_profit"]), verified=bool(o["win"])) for o in resolved]
    b = brier(samples) if samples else None
    e = ece(samples, bins=5) if samples else None
    wins = sum(1 for o in resolved if o.get("win"))

    reasons = []
    ok = True
    if len(resolved) < RISK.calib_min_resolved:
        ok = False
        reasons.append(f"only {len(resolved)}/{RISK.calib_min_resolved} structures resolved")
    if e is None or e > RISK.calib_max_ece:
        ok = False
        reasons.append(f"ECE {e} > {RISK.calib_max_ece}" if e is not None else "ECE undefined")
    if b is None or b > RISK.calib_max_brier:
        ok = False
        reasons.append(f"Brier {b} > {RISK.calib_max_brier}" if b is not None else "Brier undefined")
    if claim_accuracy is None or claim_accuracy < RISK.calib_min_claim_accuracy:
        ok = False
        reasons.append(f"claim accuracy {claim_accuracy} < {RISK.calib_min_claim_accuracy}")
    if silent:
        ok = False
        reasons.append(f"{silent} silent failure(s) on record")
    if ok:
        reasons.append("calibration earned: full risk budget unlocked")
    return CalibrationState(n_claims, n_audited, claim_accuracy, silent, len(resolved), wins, b, e, ok, RISK.earned_risk_frac if ok else RISK.floor_risk_frac, reasons)


def coverage_curve() -> list[dict]:
    resolved = [o for o in ledger.read("outcomes") if o.get("resolved")]
    return risk_coverage([Sample(True, float(o["p_profit"]), bool(o["win"])) for o in resolved])

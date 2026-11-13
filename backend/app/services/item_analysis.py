"""Classical Test Theory item analysis (madde analizi) — pure functions.

Outputs are *observed* statistics of one exam administration. They are not mastery
estimates (Phase 4 / BKT) and must be labelled as such in the UI and reports.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, pstdev

SMALL_SAMPLE = 30


@dataclass
class ItemStats:
    item_id: str
    position: int
    n: int
    difficulty_p: float | None  # mean proportion of max points (higher = easier)
    discrimination_rpbis: float | None  # corrected item-total correlation
    discrimination_d: float | None  # upper 27% - lower 27%
    flags: list[str] = field(default_factory=list)
    distractors: dict[str, dict[str, int]] | None = None  # option -> {"upper": n, "lower": n, "total": n}


@dataclass
class TestStats:
    n_students: int
    n_items: int
    mean_pct: float | None
    sd_pct: float | None
    reliability: float | None
    reliability_method: str
    sem_pct: float | None
    warnings: list[str] = field(default_factory=list)


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    mx, my = mean(x), mean(y)
    sx, sy = pstdev(x), pstdev(y)
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True)) / (len(x) * sx * sy)


def analyze_items(
    items: list[tuple[str, int, float]],  # (item_id, position, max_points)
    scores: dict[str, dict[str, float | None]],  # student_id -> item_id -> points (None=missing)
    choices: dict[str, dict[str, str | None]] | None = None,  # student_id -> item_id -> option
    correct_options: dict[str, str] | None = None,
) -> tuple[list[ItemStats], TestStats]:
    students = list(scores.keys())
    n = len(students)
    warnings: list[str] = []
    if n < SMALL_SAMPLE:
        warnings.append(f"Öğrenci sayısı ({n}) {SMALL_SAMPLE}'un altında; madde istatistikleri kararsız olabilir.")

    # proportion matrix, missing = 0 (not answered)
    prop = {s: {iid: (scores[s].get(iid) or 0.0) / mp if mp else 0.0 for iid, _, mp in items} for s in students}
    totals = {s: sum(prop[s].values()) for s in students}
    k = len(items)

    order = sorted(students, key=lambda s: totals[s], reverse=True)
    g = max(1, round(n * 0.27)) if n >= 4 else 0
    upper, lower = set(order[:g]), set(order[-g:]) if g else set()

    item_stats: list[ItemStats] = []
    for iid, pos, _mp in items:
        col = [prop[s][iid] for s in students]
        p = round(mean(col), 3) if col else None
        rest = [totals[s] - prop[s][iid] for s in students]
        r = _pearson(col, rest)
        d = None
        if g:
            d = round(mean(prop[s][iid] for s in upper) - mean(prop[s][iid] for s in lower), 3)
        flags: list[str] = []
        if p is not None and p < 0.20:
            flags.append("cok_zor")
        if p is not None and p > 0.90:
            flags.append("cok_kolay")
        if r is not None and r < 0:
            flags.append("negatif_ayirt_edicilik")  # check answer key!
        elif r is not None and r < 0.20:
            flags.append("dusuk_ayirt_edicilik")
        dist = None
        if choices is not None and correct_options and iid in correct_options:
            dist = {}
            for s in students:
                opt = (choices.get(s, {}).get(iid) or "BOŞ").upper()[:4]
                row = dist.setdefault(opt, {"upper": 0, "lower": 0, "total": 0})
                row["total"] += 1
                if s in upper:
                    row["upper"] += 1
                if s in lower:
                    row["lower"] += 1
            for opt, row in dist.items():
                if opt != correct_options[iid].upper() and opt != "BOŞ" and row["upper"] > row["lower"]:
                    flags.append(f"celdirici_{opt}_ust_grubu_cekiyor")
        item_stats.append(ItemStats(iid, pos, n, p, None if r is None else round(r, 3), d, flags, dist))

    # reliability: KR-20 if all items dichotomous, else Cronbach's alpha (same formula on proportions)
    dichotomous = all(v in (0.0, 1.0) for s in students for v in prop[s].values())
    method = "KR-20" if dichotomous else "Cronbach alfa"
    rel = sem = None
    if n >= 2 and k >= 2:
        total_var = pstdev(list(totals.values())) ** 2
        item_var_sum = sum(pstdev([prop[s][iid] for s in students]) ** 2 for iid, _, _ in items)
        if total_var > 0:
            rel = round((k / (k - 1)) * (1 - item_var_sum / total_var), 3)
    pct = [100 * totals[s] / k for s in students] if k else []
    m = round(mean(pct), 2) if pct else None
    sd = round(pstdev(pct), 2) if len(pct) > 1 else None
    if rel is not None and sd is not None:
        sem = round(sd * math.sqrt(max(0.0, 1 - rel)), 2)
    if rel is not None and rel < 0.6:
        warnings.append("Güvenirlik katsayısı düşük; puanları yorumlarken dikkatli olun.")
    return item_stats, TestStats(n, k, m, sd, rel, method, sem, warnings)


def outcome_achievement(
    mapping: dict[str, list[tuple[str, float]]],  # item_id -> [(outcome_id, weight)]
    max_points: dict[str, float],
    student_scores: dict[str, float | None],
) -> dict[str, dict]:
    """Observed per-outcome percentage for ONE student in ONE exam (not a mastery estimate)."""
    acc: dict[str, list[float]] = {}
    for iid, outs in mapping.items():
        mp = max_points.get(iid) or 0
        sc = student_scores.get(iid)
        if not mp:
            continue
        for oid, w in outs:
            a = acc.setdefault(oid, [0.0, 0.0, 0])
            a[0] += w * (sc or 0.0)
            a[1] += w * mp
            a[2] += 1
    return {oid: {"observed_pct": round(100 * a[0] / a[1], 1) if a[1] else None, "n_items": a[2],
                  "kind": "observed_exam_percentage"} for oid, a in acc.items()}

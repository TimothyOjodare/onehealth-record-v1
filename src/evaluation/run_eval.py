"""
Evaluation runner.

For each gold-standard dictation, run the extractor, align predicted spans
against gold spans, and compute:
  - per-entity-kind precision / recall / F1
  - confidence calibration bins
  - runtime per pipeline stage (parse, NER, FHIR build)
  - top false-positive and false-negative patterns

Output: data/synthetic/evaluation.json
"""
from __future__ import annotations

import json
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"

import sys
sys.path.insert(0, str(PROJECT_ROOT))

from src.nlp.dictation_parser import parse as parse_dictation  # noqa: E402
from src.nlp.entity_extractor import extract_entities  # noqa: E402
from src.nlp.fhir_builder import build_bundle  # noqa: E402


# ---------------------------------------------------------------------------
# Coarsen entity kinds so gold and predicted live in the same label space.
# ---------------------------------------------------------------------------
def _coarsen_pred_kind(k: str) -> str:
    k = k.lower()
    if k.startswith("vital_"):     return "vital"
    if k == "condition":           return "condition"
    if k == "symptom":             return "symptom"
    if k == "medication":          return "medication"
    if k == "demographic":         return "demographic"
    if k == "duration":            return "duration"
    if k == "exposure":            return "exposure"
    return k


def _coarsen_gold_kind(k: str) -> str:
    k = k.lower()
    if k in ("condition_human", "condition_animal"): return "condition"
    if k.startswith("vital_"):                       return "vital"
    return k


def _spans_align(a: tuple, b: tuple, tol: int = 2) -> bool:
    """Soft span match: starts within tol chars and ends within tol chars."""
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


# ---------------------------------------------------------------------------
def evaluate_one(gold: dict) -> dict:
    """Run pipeline against one gold dictation; return alignment record."""
    text = gold["text"]
    t0 = time.perf_counter()
    parsed = parse_dictation(text)
    t1 = time.perf_counter()
    parsed, ents = extract_entities(parsed)
    t2 = time.perf_counter()
    bundle = build_bundle(ents, text)
    t3 = time.perf_counter()

    pred = [{
        "char_start": e.char_start,
        "char_end": e.char_end,
        "kind": _coarsen_pred_kind(e.kind),
        "text": e.text,
        "negated": e.negated,
        "uncertain": e.uncertain,
        "confidence": e.confidence,
    } for e in ents if e.kind.lower() not in ("demographic", "duration", "exposure")]

    gold_ents = [{
        "char_start": g["char_start"],
        "char_end": g["char_end"],
        "kind": _coarsen_gold_kind(g["kind"]),
        "text": g["text"],
        "negated": g["negated"],
        "uncertain": g["uncertain"],
    } for g in gold["entities"] if _coarsen_gold_kind(g["kind"]) in ("condition", "symptom", "medication", "vital")]

    # Greedy alignment: walk gold; pick best matching prediction
    used_pred = set()
    matches = []  # (gold_idx, pred_idx)
    for gi, g in enumerate(gold_ents):
        # candidates: same kind, near same span
        for pi, p in enumerate(pred):
            if pi in used_pred: continue
            if p["kind"] != g["kind"]: continue
            if _spans_align((g["char_start"], g["char_end"]), (p["char_start"], p["char_end"]), tol=3):
                used_pred.add(pi)
                matches.append((gi, pi))
                break

    return {
        "id": gold["id"],
        "text": text,
        "gold": gold_ents,
        "pred": pred,
        "matches": matches,
        "runtimes": {
            "parse_ms": (t1 - t0) * 1000,
            "extract_ms": (t2 - t1) * 1000,
            "fhir_ms": (t3 - t2) * 1000,
            "total_ms": (t3 - t0) * 1000,
        },
    }


# ---------------------------------------------------------------------------
def aggregate(results: list[dict]) -> dict:
    """Compute precision/recall/F1, calibration, runtime, errors."""

    # Per-kind tallies
    KINDS = ("condition", "symptom", "medication", "vital")
    tallies = {k: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for k in KINDS}

    # Calibration: bin predictions by confidence; track whether matched
    bin_edges = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    bins = [{"bin_lo": bin_edges[i], "bin_hi": bin_edges[i+1],
             "bin_mid": (bin_edges[i] + bin_edges[i+1]) / 2,
             "n": 0, "n_correct": 0, "observed_accuracy": 0.0}
            for i in range(len(bin_edges) - 1)]

    # Error patterns
    fp_counter: Counter = Counter()
    fn_counter: Counter = Counter()

    runtime_by_stage = defaultdict(list)

    for r in results:
        for st, ms in r["runtimes"].items():
            runtime_by_stage[st].append(ms)

        gold = r["gold"]
        pred = r["pred"]
        matched_pred = {pi for (_gi, pi) in r["matches"]}
        matched_gold = {gi for (gi, _pi) in r["matches"]}

        # TP / FN by gold
        for gi, g in enumerate(gold):
            tallies[g["kind"]]["support"] += 1
            if gi in matched_gold:
                tallies[g["kind"]]["tp"] += 1
            else:
                tallies[g["kind"]]["fn"] += 1
                fn_counter[(g["kind"], g["text"].lower())] += 1

        # FP by pred
        for pi, p in enumerate(pred):
            if p["kind"] not in tallies:
                continue
            if pi not in matched_pred:
                tallies[p["kind"]]["fp"] += 1
                fp_counter[(p["kind"], p["text"].lower())] += 1

        # Calibration: every prediction (regardless of kind) — was it matched?
        for pi, p in enumerate(pred):
            for b in bins:
                if b["bin_lo"] <= p["confidence"] < b["bin_hi"]:
                    b["n"] += 1
                    if pi in matched_pred:
                        b["n_correct"] += 1
                    break

    for b in bins:
        b["observed_accuracy"] = (b["n_correct"] / b["n"]) if b["n"] > 0 else 0.0

    # Per-kind metrics
    per_kind = []
    overall_tp = overall_fp = overall_fn = overall_support = 0
    for kind, t in tallies.items():
        precision = (t["tp"] / (t["tp"] + t["fp"])) if (t["tp"] + t["fp"]) > 0 else 0.0
        recall    = (t["tp"] / (t["tp"] + t["fn"])) if (t["tp"] + t["fn"]) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        per_kind.append({
            "kind": kind, "support": t["support"],
            "tp": t["tp"], "fp": t["fp"], "fn": t["fn"],
            "precision": precision, "recall": recall, "f1": f1,
        })
        overall_tp += t["tp"]; overall_fp += t["fp"]; overall_fn += t["fn"]
        overall_support += t["support"]

    overall_p = (overall_tp / (overall_tp + overall_fp)) if (overall_tp + overall_fp) > 0 else 0.0
    overall_r = (overall_tp / (overall_tp + overall_fn)) if (overall_tp + overall_fn) > 0 else 0.0
    overall_f1 = (2 * overall_p * overall_r / (overall_p + overall_r)) if (overall_p + overall_r) > 0 else 0.0

    # Runtime
    runtime = []
    for stage in ["parse_ms", "extract_ms", "fhir_ms", "total_ms"]:
        vals = runtime_by_stage[stage]
        if not vals: continue
        runtime.append({
            "stage": stage.replace("_ms", "").replace("_", " "),
            "median_ms": statistics.median(vals),
            "p95_ms": sorted(vals)[int(0.95 * (len(vals) - 1))],
            "n": len(vals),
        })

    # Top FP / FN
    top_fp = [{"kind": k, "text": t, "n": n}
              for ((k, t), n) in fp_counter.most_common(8)]
    top_fn = [{"kind": k, "text": t, "n": n}
              for ((k, t), n) in fn_counter.most_common(8)]

    return {
        "overall": {
            "precision": overall_p, "recall": overall_r, "f1": overall_f1,
            "n_gold": overall_support,
            "n_predicted": overall_tp + overall_fp,
            "tp": overall_tp, "fp": overall_fp, "fn": overall_fn,
        },
        "per_kind": per_kind,
        "calibration": bins,
        "runtime": runtime,
        "errors": {"top_fp": top_fp, "top_fn": top_fn},
    }


# ---------------------------------------------------------------------------
def main():
    gold = json.loads((SYNTH_DIR / "gold_standard.json").read_text())
    results = [evaluate_one(g) for g in gold["dictations"]]
    metrics = aggregate(results)
    out = {
        "_metadata": {
            "n_dictations": len(results),
            "engine": "rule-based-v0.1",
            "schema_version": "0.1.0",
        },
        "results": metrics,
    }
    (SYNTH_DIR / "evaluation.json").write_text(json.dumps(out, indent=2))
    return metrics


if __name__ == "__main__":
    m = main()
    o = m["overall"]
    print(f"Overall: P={o['precision']:.3f}  R={o['recall']:.3f}  F1={o['f1']:.3f}")
    print(f"  Gold entities: {o['n_gold']}  TP={o['tp']}  FP={o['fp']}  FN={o['fn']}")
    print()
    print(f"{'kind':<14} {'support':>7} {'TP':>4} {'FP':>4} {'FN':>4}  {'P':>6} {'R':>6} {'F1':>6}")
    for k in m["per_kind"]:
        print(f"{k['kind']:<14} {k['support']:>7} {k['tp']:>4} {k['fp']:>4} {k['fn']:>4}  "
              f"{k['precision']:>6.3f} {k['recall']:>6.3f} {k['f1']:>6.3f}")
    print()
    print("Calibration bins:")
    for b in m["calibration"]:
        print(f"  [{b['bin_lo']:.2f}-{b['bin_hi']:.2f})  n={b['n']:>3}  obs_acc={b['observed_accuracy']:.3f}")
    print()
    print("Runtime:")
    for r in m["runtime"]:
        print(f"  {r['stage']:<12} median={r['median_ms']:>6.2f} ms  p95={r['p95_ms']:>6.2f} ms (n={r['n']})")

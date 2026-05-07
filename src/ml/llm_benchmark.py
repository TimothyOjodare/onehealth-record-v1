"""
LLM-vs-rules NER head-to-head.

Runs the same 25 gold-standard dictations through:
- The deterministic rule-based extractor (already evaluated in run_eval.py)
- Claude Haiku via the Anthropic API

Produces:
- data/synthetic/llm_benchmark.json — for the demo + report

The point is NOT that one system is better. The point is to measure the
deterministic-vs-statistical tradeoff with real numbers:
- Rule-based: deterministic, free, ~1 ms/encounter, brittle to novel surface forms
- LLM: probabilistic, $-per-call, ~1 s/encounter, robust to phrasing
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import anthropic

# Adjust path so we can import the rule-based extractor
BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "src" / "nlp"))

# Use Haiku 4.5 for cost-efficient, high-quality extraction
MODEL = "claude-haiku-4-5-20251001"

EXTRACTION_PROMPT = """\
You are a clinical NER engine. Extract entities from the dictation below as JSON.

Entity kinds: condition, symptom, medication, vital_sign

For each entity, output:
- text: exact span as it appears in the source
- start: character offset (0-indexed)
- end: character offset (exclusive)
- kind: one of the four kinds above
- negated: true if negated in context (e.g. "no fever", "denies cough"), else false
- confidence: float 0.0-1.0

Output ONLY a JSON array of entity objects. No commentary, no markdown fences, no preamble.

Dictation:
\"\"\"
{text}
\"\"\""""


def extract_with_llm(client: anthropic.Anthropic, text: str) -> Tuple[List[dict], float, int]:
    """Returns (entities, latency_seconds, tokens_used)."""
    t0 = time.perf_counter()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}],
    )
    latency = time.perf_counter() - t0

    raw = response.content[0].text.strip()
    # Strip code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        raw = raw.rsplit("```", 1)[0] if raw.endswith("```") or "```" in raw else raw
    raw = raw.strip()
    # Find first [ and last ]
    start_i = raw.find("[")
    end_i = raw.rfind("]")
    if start_i == -1 or end_i == -1:
        return [], latency, response.usage.input_tokens + response.usage.output_tokens

    json_str = raw[start_i:end_i + 1]
    try:
        entities = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  JSON decode error: {e}", file=sys.stderr)
        print(f"  raw: {raw[:200]}", file=sys.stderr)
        entities = []

    tokens = response.usage.input_tokens + response.usage.output_tokens
    return entities, latency, tokens


def normalize_kind(k: str) -> str:
    k = (k or "").lower().strip()
    if k.startswith("vital") or k in ("vital_sign", "vitalsign", "vitals"):
        return "vital_sign"
    if k.startswith("cond"):
        return "condition"
    if k.startswith("symp"):
        return "symptom"
    if k.startswith("med"):
        return "medication"
    return k


def score_entities(predicted: List[dict], gold: List[dict]) -> Dict:
    """Compute per-kind P/R/F1 using overlapping span match (lenient)."""
    # Group by kind
    g_by_kind: Dict[str, List[dict]] = {}
    for g in gold:
        g_by_kind.setdefault(normalize_kind(g["kind"]), []).append(g)

    p_by_kind: Dict[str, List[dict]] = {}
    for p in predicted:
        p_by_kind.setdefault(normalize_kind(p.get("kind", "")), []).append(p)

    all_kinds = set(g_by_kind) | set(p_by_kind)
    per_kind = {}
    total_tp = total_fp = total_fn = 0

    for kind in all_kinds:
        gs = g_by_kind.get(kind, [])
        ps = p_by_kind.get(kind, [])

        matched_g = set()
        tp = 0
        for p_i, p in enumerate(ps):
            for g_j, g in enumerate(gs):
                if g_j in matched_g:
                    continue
                # Check span overlap
                p_s, p_e = int(p.get("start", -1)), int(p.get("end", -1))
                g_s, g_e = int(g.get("start", -1)), int(g.get("end", -1))
                if p_s < 0 or g_s < 0:
                    # Fall back to text match
                    if (p.get("text") or "").lower().strip() == (g.get("text") or "").lower().strip():
                        matched_g.add(g_j)
                        tp += 1
                        break
                    continue
                # Lenient overlap: any character intersection
                if p_s < g_e and g_s < p_e:
                    matched_g.add(g_j)
                    tp += 1
                    break

        fp = len(ps) - tp
        fn = len(gs) - len(matched_g)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        per_kind[kind] = {"support": len(gs), "tp": tp, "fp": fp, "fn": fn,
                          "precision": prec, "recall": rec, "f1": f1}
        total_tp += tp
        total_fp += fp
        total_fn += fn

    overall = {
        "support":   total_tp + total_fn,
        "tp":        total_tp,
        "fp":        total_fp,
        "fn":        total_fn,
        "precision": total_tp / max(total_tp + total_fp, 1),
        "recall":    total_tp / max(total_tp + total_fn, 1),
        "f1":        0.0,
    }
    if overall["precision"] + overall["recall"] > 0:
        overall["f1"] = 2 * overall["precision"] * overall["recall"] / (overall["precision"] + overall["recall"])

    return {"overall": overall, "per_kind": per_kind}


def normalize_gold_entity(g: dict) -> dict:
    """Map gold-standard kind names (Demographic / Vital_HR / etc) to our 4 kinds."""
    k = g.get("kind", "")
    nk = normalize_kind(k)
    if nk.startswith("vital_") or nk == "vital_sign":
        nk = "vital_sign"
    elif "demographic" in k.lower():
        nk = "demographic"
    elif "duration" in k.lower():
        nk = "duration"
    elif "exposure" in k.lower():
        nk = "exposure"
    return {**g, "kind": nk}


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    base = Path(__file__).resolve().parents[2]
    gold = json.load(open(base / "data/synthetic/gold_standard.json"))
    items = gold.get("dictations", []) or gold.get("items", []) or gold

    print(f"running LLM benchmark on {len(items)} dictations using {MODEL}")
    print()

    per_dictation = []
    all_predicted = []
    all_gold = []
    total_latency = 0.0
    total_tokens = 0

    for i, item in enumerate(items):
        text = item.get("text") or item.get("dictation") or item.get("source_text") or ""
        # Filter to just the 4 entity kinds we're benchmarking
        gold_entities = [normalize_gold_entity(e) for e in item.get("entities", [])
                         if normalize_kind(e.get("kind", "")).split("_")[0] in {"vital", "condition", "symptom", "medication"}
                         or normalize_kind(e.get("kind", "")) == "vital_sign"]
        gold_entities = [e for e in gold_entities if e["kind"] in {"vital_sign", "condition", "symptom", "medication"}]

        try:
            preds, lat, tok = extract_with_llm(client, text)
        except Exception as e:
            print(f"  [{i+1}/{len(items)}] ERROR: {e}", file=sys.stderr)
            preds, lat, tok = [], 0.0, 0

        scored = score_entities(preds, gold_entities)
        per_dictation.append({
            "scenario_id":      item.get("scenario_id", item.get("id", f"scn-{i}")),
            "text_preview":     text[:80] + "..." if len(text) > 80 else text,
            "n_predicted":      len(preds),
            "n_gold":           len(gold_entities),
            "overall":          scored["overall"],
            "per_kind":         scored["per_kind"],
            "latency_seconds":  lat,
            "tokens_used":      tok,
        })
        all_predicted.append(preds)
        all_gold.append(gold_entities)
        total_latency += lat
        total_tokens += tok

        print(f"  [{i+1:2d}/{len(items)}]  preds={len(preds):2d}  gold={len(gold_entities):2d}  "
              f"P={scored['overall']['precision']:.3f}  R={scored['overall']['recall']:.3f}  "
              f"F1={scored['overall']['f1']:.3f}  lat={lat:.2f}s  tok={tok}")

    # Aggregate
    flat_pred = [p for lst in all_predicted for p in lst]
    flat_gold = [g for lst in all_gold for g in lst]
    overall = score_entities(flat_pred, flat_gold)

    # Pull rule-based numbers from the existing eval
    try:
        rb = json.load(open(base / "data/synthetic/evaluation.json"))
        rb_overall = {
            "precision": rb.get("overall", {}).get("precision"),
            "recall":    rb.get("overall", {}).get("recall"),
            "f1":        rb.get("overall", {}).get("f1"),
        }
    except Exception:
        rb_overall = {}

    avg_latency_ms = (total_latency / max(len(items), 1)) * 1000
    avg_tokens = total_tokens / max(len(items), 1)
    cost_per_1m_input = 1.00      # Haiku 4.5 pricing in USD
    cost_per_1m_output = 5.00
    estimated_cost = (total_tokens / 1_000_000) * 3.0  # rough blended

    payload = {
        "_metadata": {
            "model":                  MODEL,
            "n_dictations":           len(items),
            "total_tokens":           total_tokens,
            "total_latency_seconds":  total_latency,
            "avg_latency_ms":         avg_latency_ms,
            "avg_tokens_per_dictation": avg_tokens,
            "estimated_cost_usd":     estimated_cost,
        },
        "llm_overall":         overall["overall"],
        "llm_per_kind":        overall["per_kind"],
        "rule_based_overall":  rb_overall,
        "head_to_head": {
            "rule_based":   {
                "precision":      rb_overall.get("precision"),
                "recall":         rb_overall.get("recall"),
                "f1":             rb_overall.get("f1"),
                "latency_ms":     1.2,           # from existing evaluation.json
                "cost_per_dictation_usd": 0.0,
                "deterministic":  True,
            },
            "llm_haiku":    {
                "precision":      overall["overall"]["precision"],
                "recall":         overall["overall"]["recall"],
                "f1":             overall["overall"]["f1"],
                "latency_ms":     avg_latency_ms,
                "cost_per_dictation_usd": estimated_cost / max(len(items), 1),
                "deterministic":  False,
            },
        },
        "per_dictation": per_dictation,
    }

    out = base / "data/synthetic/llm_benchmark.json"
    json.dump(payload, open(out, "w"), indent=2)
    print(f"\nwrote {out}")
    print()
    print(f"=== HEAD-TO-HEAD ===")
    print(f"  Rule-based:  P={rb_overall.get('precision', 0):.3f}  R={rb_overall.get('recall', 0):.3f}  F1={rb_overall.get('f1', 0):.3f}  ~1.2 ms/dictation  $0/dictation")
    print(f"  Claude Haiku: P={overall['overall']['precision']:.3f}  R={overall['overall']['recall']:.3f}  F1={overall['overall']['f1']:.3f}  ~{avg_latency_ms:.0f} ms/dictation  ~${estimated_cost / max(len(items), 1):.4f}/dictation")


if __name__ == "__main__":
    main()

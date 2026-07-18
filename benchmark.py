"""
Real-data benchmark: measures this repo's identity-matching approach against
the Febrl record-linkage benchmark (Christen, ANU) - a well-known academic
gold-standard dataset with real injected corruption and known true-match
ground truth, via the actively-maintained `recordlinkage` Python package.

This is a SEPARATE scenario from pipeline.py's CRM contact-dedup demo above.
Febrl is person-identity data (name/address/date-of-birth) - it has no
company/title/status fields, so it is not used to replace or reframe the
CRM demo, only to prove the same underlying approach (deterministic
blocking + Claude arbitration on the genuinely ambiguous residue) against
real ground truth, with an actual measured precision/recall/F1 - not an
eyeballed "looks right."

Methodology (standard record-linkage evaluation practice):
1. Sample N true-duplicate pairs from Febrl 1 (500 available).
2. Deterministic blocking in plain code generates candidate pairs - this
   necessarily has a recall ceiling (a true pair whose blocking key was
   itself corrupted won't become a candidate at all - that's real and
   reported, not hidden).
3. Claude classifies each candidate pair as same-person or not.
4. Score in code, not by Claude: precision/recall/F1 against real ground
   truth, plus the blocking-stage recall ceiling reported separately.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python benchmark.py
"""
from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

import pandas as pd
from recordlinkage.datasets import load_febrl1

from llm_client import AnthropicClient

ROOT = Path(__file__).parent
CODE_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)
SAMPLE_TRUE_PAIRS = 30
RANDOM_SEED = 42


def extract_json(text: str) -> list:
    return json.loads(CODE_FENCE_RE.sub("", text.strip()).strip())


def blocking_key(row: pd.Series) -> str | None:
    """Deterministic blocking - transparent and auditable, not a black box.
    Falls back through surname -> given_name -> postcode so a record with a
    corrupted/missing surname still lands in *some* block."""
    for field in ("surname", "given_name", "postcode"):
        val = row.get(field)
        if isinstance(val, str) and val.strip():
            return f"{field}:{val.strip().lower()[:4]}"
    return None


def main() -> None:
    client = AnthropicClient()

    df, true_links = load_febrl1(return_links=True)
    true_pairs = list(true_links)

    sample_pairs = pd.Series(true_pairs).sample(n=SAMPLE_TRUE_PAIRS, random_state=RANDOM_SEED).tolist()
    sample_ids = sorted({rec_id for pair in sample_pairs for rec_id in pair})
    sample_df = df.loc[sample_ids]
    true_pair_set = {frozenset(p) for p in sample_pairs}

    print(f"Sampled {len(sample_pairs)} true pairs -> {len(sample_ids)} records from Febrl 1.\n")

    blocks: dict[str, list[str]] = {}
    for rec_id, row in sample_df.iterrows():
        key = blocking_key(row)
        if key:
            blocks.setdefault(key, []).append(rec_id)

    candidate_pairs = set()
    for members in blocks.values():
        for a, b in combinations(sorted(members), 2):
            candidate_pairs.add(frozenset((a, b)))

    reachable_true_pairs = candidate_pairs & true_pair_set
    print(f"Blocking generated {len(candidate_pairs)} candidate pairs.")
    print(f"Blocking-stage recall ceiling: {len(reachable_true_pairs)}/{len(true_pair_set)} "
          f"true pairs were even reachable as candidates.\n")

    indexed_candidates = list(candidate_pairs)
    payload = []
    for i, pair in enumerate(indexed_candidates):
        a, b = sorted(pair)
        payload.append({
            "pair_index": i,
            "record_a": {"id": a, **sample_df.loc[a][["given_name", "surname", "postcode", "date_of_birth", "address_1"]].to_dict()},
            "record_b": {"id": b, **sample_df.loc[b][["given_name", "surname", "postcode", "date_of_birth", "address_1"]].to_dict()},
        })

    system_prompt = (
        "You are a record-linkage analyst. For each candidate pair of person "
        "records (which may have typos, transpositions, or missing fields), "
        "decide whether they represent the same real person. Reply with ONLY "
        "a JSON array (no markdown fences), one object per pair in the same "
        "order given: "
        '{"pair_index": <int>, "same_person": true|false, "reasoning": "..."}'
    )
    response = client.create(
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(payload, indent=2, default=str)}],
        max_tokens=4096,
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        decisions = extract_json(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Claude's classification response wasn't valid JSON: {exc}\nRaw response:\n{text}") from exc

    tp = fp = fn = 0
    for d in decisions:
        pair = indexed_candidates[d["pair_index"]]
        is_true_pair = pair in true_pair_set
        if d["same_person"] and is_true_pair:
            tp += 1
        elif d["same_person"] and not is_true_pair:
            fp += 1
        elif not d["same_person"] and is_true_pair:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall_of_reachable = tp / len(reachable_true_pairs) if reachable_true_pairs else float("nan")
    recall_overall = tp / len(true_pair_set)
    f1 = (2 * precision * recall_of_reachable / (precision + recall_of_reachable)
          if (precision + recall_of_reachable) else float("nan"))

    report = [
        "# Febrl Real-Data Benchmark Report (llm-crm-data-pipeline)",
        "",
        f"- Sampled true pairs: {len(true_pair_set)}",
        f"- Candidate pairs after deterministic blocking: {len(candidate_pairs)}",
        f"- Blocking-stage recall ceiling: {len(reachable_true_pairs)}/{len(true_pair_set)} "
        f"({100*len(reachable_true_pairs)/len(true_pair_set):.0f}%)",
        f"- Claude true positives: {tp}, false positives: {fp}, false negatives: {fn}",
        f"- Precision (of Claude's positive calls): {precision:.2%}",
        f"- Recall (of blocking-reachable true pairs): {recall_of_reachable:.2%}",
        f"- Recall (of all sampled true pairs, incl. blocking misses): {recall_overall:.2%}",
        f"- F1 (on reachable candidates): {f1:.2%}",
        "",
        "Blocking-stage misses are a real, expected limitation (a true pair whose "
        "blocking key field was itself corrupted by Febrl's noise generator won't "
        "become a candidate at all) - reported separately from Claude's "
        "classification accuracy on the candidates it was actually given, per "
        "standard record-linkage evaluation practice.",
    ]
    (ROOT / "benchmark_report.md").write_text("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nWrote benchmark_report.md")


if __name__ == "__main__":
    main()

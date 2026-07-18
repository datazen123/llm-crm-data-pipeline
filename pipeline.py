"""
CRM contact data-quality pipeline: deterministic cleaning + normalization in
plain Python, then Claude arbitrates ambiguous duplicate clusters (which
raw row is most correct/complete) and writes a short data-quality report.

Claude is deliberately NOT used to invent missing business facts (e.g. it
never guesses a missing job title) - only to normalize/arbitrate between
conflicting values that already exist in the raw data, and to summarize.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python pipeline.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from llm_client import AnthropicClient

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"

COMPANY_SUFFIXES = re.compile(r"\b(inc|llc|co|corp|company)\b\.?", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> dict:
    """Claude sometimes wraps JSON in ```json fences even when told not to - strip them."""
    return json.loads(CODE_FENCE_RE.sub("", text.strip()).strip())


def normalize_company(name: str) -> str:
    name = COMPANY_SUFFIXES.sub("", name or "")
    return re.sub(r"\s+", " ", name).strip().lower()


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return phone or ""


def cluster_key(row: pd.Series) -> tuple[str, str]:
    return (str(row["last_name"]).strip().lower(), normalize_company(row["company"]))


def arbitrate_cluster(client: AnthropicClient, rows: list[dict]) -> dict:
    """Ask Claude to pick/merge the most correct canonical record from conflicting rows."""
    prompt = (
        "These CRM rows look like the same contact recorded inconsistently. "
        "Pick the most correct value for each field (prefer complete, "
        "consistently-cased, more specific values) and return ONLY JSON:\n"
        '{"first_name": "...", "last_name": "...", "email": "...", '
        '"phone": "...", "company": "...", "title": "...", '
        '"merge_note": "one short sentence on what you merged and why"}\n\n'
        "Do not invent any value that isn't present in at least one of the rows below "
        "(except normalizing casing/formatting).\n\n"
        f"Rows:\n{json.dumps(rows, indent=2)}"
    )
    response = client.create(
        system="You are a CRM data-quality assistant. Reply with strict JSON only, no prose.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        return extract_json(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Claude's response for this cluster wasn't valid JSON after fence-stripping: {exc}\n"
            f"Raw response:\n{text}"
        ) from exc


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    client = AnthropicClient()

    df = pd.read_csv(DATA_DIR / "raw_contacts.csv", dtype=str).fillna("")
    df["phone"] = df["phone"].apply(normalize_phone)

    clusters: dict[tuple[str, str], list[dict]] = {}
    for _, row in df.iterrows():
        clusters.setdefault(cluster_key(row), []).append(row.to_dict())

    canonical_rows = []
    merge_notes = []
    duplicate_clusters = 0

    for key, rows in clusters.items():
        if len(rows) > 1:
            duplicate_clusters += 1
            merged = arbitrate_cluster(client, rows)
            merge_notes.append(f"{merged['first_name']} {merged['last_name']}: {merged['merge_note']}")
            canonical_rows.append({k: merged[k] for k in
                                    ["first_name", "last_name", "email", "phone", "company", "title"]})
        else:
            canonical_rows.append(rows[0])

    cleaned = pd.DataFrame(canonical_rows)
    cleaned.to_csv(OUTPUT_DIR / "cleaned_contacts.csv", index=False)

    missing_phone = (cleaned["phone"] == "").sum()
    missing_title = (cleaned["title"] == "").sum()

    report_lines = [
        "# Data Quality Report",
        "",
        f"- Raw rows: {len(df)}",
        f"- Canonical contacts after merge: {len(cleaned)}",
        f"- Duplicate clusters merged: {duplicate_clusters}",
        f"- Contacts missing phone: {missing_phone}",
        f"- Contacts missing title: {missing_title}",
        "",
        "## Merge decisions",
    ] + [f"- {note}" for note in merge_notes]

    (OUTPUT_DIR / "data_quality_report.md").write_text("\n".join(report_lines) + "\n")

    print("\n".join(report_lines))
    print(f"\nCleaned data written to {OUTPUT_DIR / 'cleaned_contacts.csv'}")


if __name__ == "__main__":
    main()

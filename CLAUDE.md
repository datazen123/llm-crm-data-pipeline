# Context for Claude Code working in this repo

This repo is one of a **10-repo public portfolio** (github.com/datazen123)
demonstrating real, live-verified agentic AI engineering for a specific
DoD-contractor job pursuit. Full README below covers this repo in detail;
this file covers conventions and status a coding agent needs before making
changes.

## This repo's role

CRM contact data-quality pipeline: deterministic normalization (phone
formatting, company-name cleanup) plus Claude-arbitrated judgment calls on
duplicate/conflicting records. **Weakest fit for this specific pursuit** -
CRM/Salesforce is not in SecureBine's stated service lines (confirmed by
checking their site directly - see the private context repo's research);
kept published and framed honestly as a "general skills demo," not
positioned as USFK-specific.

**Status**: 14/14 tests passing. Real benchmark against the Febrl
record-linkage academic benchmark: 100% precision, 84% recall-on-
reachable, 53% overall recall (bottlenecked by the blocking stage,
reported honestly).

**Not yet given the "deep pass"** applied to the more recently-worked
repos - lowest priority on the punch list given the weak fit.

## Non-negotiable discipline this whole portfolio follows

1. Never fabricate a source - every real-data claim is independently
   fetched/verified.
2. Deterministic code owns any mechanical computation; Claude only
   handles the genuinely ambiguous/language part - never asked to invent
   a missing fact.
3. Live-verify against the real Anthropic API before claiming a result.
4. Synthetic demo data is always labeled as synthetic; real external data
   is cited with exact source.
5. Pytest suite, GitHub Actions CI, "Security notes" README section,
   pinned dependencies.
6. No real client, unit, or classified-sounding content ever.
7. Ask Sage (not Claude directly) is named as the realistic DoD/DIB
   production deployment path.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # fill in your own ANTHROPIC_API_KEY, never commit it
pytest -q
```

Full cross-repo strategy, founder research, and environment notes live in
the private `datazen123/securebine-portfolio-context` repo - not
duplicated here since this repo is public.

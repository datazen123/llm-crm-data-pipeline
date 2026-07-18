# llm-crm-data-pipeline

A CRM contact data-quality pipeline: deterministic normalization in plain
Python (phone formatting, company-name cleanup), with Claude arbitrating the
judgment calls that don't have a clean rule - deciding which of several
conflicting rows for the same person is most correct, and writing a short
data-quality report.

`data/raw_contacts.csv` is synthetic sample data written for this demo - not
from any real company or client.

## Why this exists

Every CRM accumulates duplicate/inconsistent contact records over time
(same person entered twice with different casing, an old phone number,
a company name typed two different ways). This shows that cleanup handled
as an automated pipeline: cheap deterministic rules where possible, an LLM
call only where real judgment is needed.

**Guardrail:** Claude is never asked to invent a missing fact (like guessing
a blank job title). Its role is limited to picking/merging between values
that already exist in the raw data, plus summarizing.

## Architecture

```
data/raw_contacts.csv
        |
        v
  deterministic cleanup (phone format, company-name normalization)
        |
        v
  cluster candidate duplicates (last name + normalized company)
        |
        v
  Claude arbitrates each cluster  --> output/cleaned_contacts.csv
        |                              output/data_quality_report.md
        v
  printed report
```

- `llm_client.py` - thin provider adapter. Anthropic is the tested backend
  used throughout this repo. OpenAI and Ask Sage adapters are included for
  the same interface, but have **not** been run against live credentials in
  this repo - treat them as reference code until verified.
- `pipeline.py` - the full pipeline described above.

## Real-data benchmark

`pipeline.py` above is an illustrative demo over 10 hand-written CRM rows -
useful for showing the architecture, but "looks right" isn't a measurement.
`benchmark.py` is a separate, additive scenario that measures the same
underlying approach (deterministic blocking + Claude arbitration on the
genuinely ambiguous residue) against the **Febrl record-linkage benchmark**
(Christen, ANU) - a well-known academic dataset with real injected
corruption and known ground truth, loaded via the actively-maintained
[`recordlinkage`](https://recordlinkage.readthedocs.io/) Python package.

Febrl is person-identity data (name/address/date-of-birth), not CRM
business fields - it's not a replacement for the demo above, it's proof the
matching *architecture* holds up against a real, external gold standard.

**Actual measured result** (30 sampled true pairs, seed=42, full run in
`benchmark_report.md`):

| Metric | Result |
|---|---|
| Blocking-stage recall ceiling | 19/30 (63%) |
| Claude precision on reachable candidates | 100.00% (0 false positives) |
| Claude recall on reachable candidates | 84.21% |
| Overall recall (incl. blocking misses) | 53.33% |

The bottleneck is the deterministic blocking stage, not Claude's judgment -
a true pair whose blocking key field was itself corrupted by Febrl's noise
generator never becomes a candidate at all. That's a real, honestly-reported
limitation of this blocking strategy, not hidden behind an aggregate number.

```bash
python benchmark.py
```

## Deployment path

This demo calls the Anthropic API directly. A production version for a
DoD-adjacent client would more likely run through
**[Ask Sage](https://www.asksage.ai/)** - the IL5/IL6-authorized multi-model
gateway built for Defense Industrial Base contractors (`llm_client.py`
includes an `AskSageClient` built from Ask Sage's
[public API docs](https://github.com/Ask-Sage/AskSage-Open-Source-Community),
untested pending an account) - or through a CRM platform's own embedded
agentic layer.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your own ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
python pipeline.py
```

Built with [Claude Code](https://claude.com/claude-code).

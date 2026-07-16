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
  used throughout this repo. An OpenAI-compatible adapter is included for
  the same interface, but has **not** been run against a live OpenAI/Codex
  key in this repo - treat it as reference code until verified.
- `pipeline.py` - the full pipeline described above.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your own ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
python pipeline.py
```

Built with [Claude Code](https://claude.com/claude-code).

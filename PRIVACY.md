# Data & Privacy

This repository was built against a live DokuWiki (HTL Leonding). To publish
it responsibly:

- **Secrets** (API tokens, SSL certificate) live only in `config/secrets/`,
  are gitignored, and were never committed (verified with `gitleaks` across
  the full history).
- **Personal data** in the source wiki (staff/contact email addresses) is
  **not** published. The full fetched corpus and embeddings stay local.
- **Samples** under `data/<stage>/samples/` are institutional/procedural
  pages only, with all email addresses redacted via `scripts/redact_sample.py`.
- A `pre-commit` hook (gitleaks + an email guard) protects future commits.

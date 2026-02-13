# Wiki Fetcher Pipeline - Improvement Plan

## Regression Analysis Summary

| Metric            | Research Prototype  | Pipeline Version     | Delta          |
|-------------------|---------------------|----------------------|----------------|
| Page success rate | 207/207 (100%)      | 49/210 (23.3%)       | **-76.7 pp**   |
| Media success     | 330/335 (98.5%)     | 267/336 (79.5%)      | -19.0 pp       |
| Duration          | 623s (10.4 min)     | 2073s (34.5 min)     | +232%          |
| Error count       | ~5                  | 230                  | +4,500%        |

---

## PHASE 1: Critical Fixes (Restore Baseline)

### 1.1 Fix `_failed_methods` Cascade Bug

**File:** `api_client.py`
**Severity:** CRITICAL
**Impact:** Restores ~160 pages (76.7% success rate recovery)

**Problem:**
`_failed_methods` tracks **method names** (e.g., `"core.getPage"`), not method+params.
When ONE page returns HTTP 400, the method name is blocklisted, causing ALL
subsequent calls to `core.getPage` for ANY page to be immediately skipped.

**Evidence:**
- First error: `competitions:2122` returns 400 Bad Request
- All 160 subsequent errors: `"Method 'core.getPage' previously failed, skipping"`
- `api_client.py:221` adds method to `_failed_methods` on permanent error
- `api_client.py:164-165` skips if method is in `_failed_methods`

**Fix approach:**
Only blocklist methods that are genuinely unsupported by the wiki (e.g., `wiki.getAllPages`
returning 400 means the API does not support that method at all). Page-specific methods
where the params determine success/failure (e.g., `core.getPage` with page param) must
NOT be blocklisted globally.

```python
# Define methods where failure is page-specific, not method-wide
_PAGE_SPECIFIC_METHODS = {
    "core.getPage", "core.getPageHTML", "core.getPageInfo",
    "core.getPageHistory", "core.getPageLinks", "core.getPageBackLinks",
    "core.aclCheck", "core.getMediaInfo", "core.getMediaUsage",
    "core.getMediaHistory",
}

# In _handle_permanent_error / the 4xx handler:
# ONLY add to _failed_methods for non-page-specific methods
if method not in _PAGE_SPECIFIC_METHODS:
    self._failed_methods.add(method)
```

**Files to change:**
- `pipeline/01_wiki_fetcher/api_client.py`

---

### 1.2 Restore Timeout to 30 Seconds

**File:** `config/env.yaml` (central)
**Severity:** HIGH
**Impact:** Fixes 64+ media download failures, reduces timeout-related errors

**Problem:**
Central `config/env.yaml` line 84 has `timeout: 2` (seconds).
Research prototype used `timeout: 30`.
The local `pipeline/01_wiki_fetcher/config/env.yaml` also has `timeout: 2`.

With 2s timeout:
- Large media files (up to 20 MB) cannot download
- Slow server responses trigger unnecessary failures
- Docker bridge networking adds latency

**Fix:**

```yaml
# config/env.yaml (central) - line 84
timeout: 30                    # Request timeout in seconds (was: 2)

# pipeline/01_wiki_fetcher/config/env.yaml - line 43
timeout: 30                    # Request timeout in Sekunden (was: 2)
```

---

### 1.3 Add Namespace Exclusions

**File:** `config/env.yaml` (central)
**Severity:** MEDIUM
**Impact:** Reduces error surface, matches proven prototype config

**Problem:**
Pipeline has `exclude_namespaces: []` (fetches everything).
Prototype excluded `playground` and `wiki` (DokuWiki system pages).

**Fix:**

```yaml
# config/env.yaml (central)
filter:
  exclude_namespaces:
    - playground               # Test namespace
    - wiki                     # DokuWiki system pages
```

---

## PHASE 2: Performance Investigation

### 2.1 Why the Pipeline Takes 3.3x Longer

**Measured: 2073s (pipeline) vs 623s (prototype) = +1450s (+232%)**

**Root causes identified:**

#### A. Additional Page Discovery Methods (+~120s)
The pipeline runs 4 page discovery methods vs 1 in the prototype:
1. `core.listPages` (both have this)
2. `wiki.getAllPages` (pipeline only) - extra API call
3. `wiki.getPagelist` recursive for each namespace (pipeline only) - many API calls
4. `core.search` / `wiki.search` for 10 search terms (pipeline only) - 20 extra API calls

Each fails and triggers error prompts or skip delays.

**Fix:** These are useful for coverage but add overhead. Since `core.listPages` already
finds ~207 pages (matching the prototype), Methods 2-4 only add ~3 pages. Consider
making them configurable and off-by-default:

```yaml
# config/env.yaml
use_recursive_listing: false   # Only enable if pages are missing
use_search_discovery: false    # Only enable if pages are missing
```

#### B. Cascade Error Processing (~200s wasted)
161 failed pages still go through the error handling pipeline:
each triggers `PermanentError` creation, stats update, timestamp generation, etc.
With the cascade fix (1.1), this overhead disappears entirely.

#### C. More API Calls per Page (+~400s)
The pipeline fetches 7 items per page vs 3 in the prototype:

| Per-page API call      | Prototype | Pipeline |
|------------------------|-----------|----------|
| core.getPageInfo       | Yes       | Yes      |
| core.getPage           | Yes       | Yes      |
| core.getPageHTML       | Yes       | Yes      |
| core.aclCheck          | No        | Yes (+)  |
| core.getPageHistory    | No        | Yes (+)  |
| core.getPageBackLinks  | No        | Yes (+)  |
| core.getPageLinks      | No        | Yes (+)  |

That is 4 extra API calls per page. With 210 pages at ~0.5-2s each = 420-1680s additional.

**Fix:** These are valuable data. No change needed, but document the expected
duration increase. Consider:
- Making each optional (already configurable via `content.fetch_*`)
- Using `requests.Session()` for connection reuse (see 2.2)

#### D. Media Namespace Scanning Overhead (+~100s)
Pipeline scans 35 namespace prefixes for media (depth=5) vs the prototype which
used a simpler approach. Each namespace scan is a separate API call.

#### E. No Connection Pooling
Both implementations create a new TCP connection + TLS handshake for each request.
With ~800+ API calls, this adds significant overhead.

**Fix:** See 3.1 below.

---

## PHASE 3: Code Quality & Design Issues

### 3.1 No `requests.Session` (Connection Pooling)

**Files:** `api_client.py`

**Problem:** Every API call in `api_client.py:196` uses bare `requests.post()`,
which creates a new TCP connection + TLS handshake per request.
Media downloads in `fetch_full_wiki_extended.py:896` and
`incremental_fetcher.py:352` also use bare `requests.get()`.

**Fix:** Use `requests.Session()` for connection reuse:

```python
class WikiAPIClient:
    def __init__(self, ...):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.verify = ...  # cert path or True

    def call(self, method, params):
        response = self.session.post(self.api_url, json=payload, timeout=current_timeout)
```

**Expected impact:** 30-50% reduction in total fetch time due to TCP/TLS reuse.

---

### 3.2 `format_bytes()` Duplicated 3 Times

**Files:**
- `fetch_full_wiki_extended.py:74`
- `media_cache.py:249`
- `resume_fetch.py:29`

**Fix:** Move to a shared `utils.py` module, import from there.

---

### 3.3 `sanitize_filename()` Duplicated 2 Times

**Files:**
- `fetch_full_wiki_extended.py:62`
- `resume_fetch.py:39`

**Fix:** Move to `utils.py`.

---

### 3.4 Inconsistent SSL Cert Handling

**Problem:** Three different SSL verification approaches are used:

1. `api_client.py:50-52` - Always sets `self.ca_cert = True` (ignores configured cert)
2. `fetch_full_wiki_extended.py:899` - Uses `verify=CA_CERT_PATH` (string from config)
3. `incremental_fetcher.py:355` - Uses `verify=CA_CERT_PATH` (string from config)
4. `resume_fetch.py:211` - Uses `verify=CA_CERT_PATH` (string from config)

The `api_client.py` **silently ignores** the configured cert path and always uses
the system CA bundle. The other files use `CA_CERT_PATH` directly.

**Fix:** Centralize SSL handling. All HTTP requests should go through `api_client.py`'s
session, which should use the configured cert path:

```python
# api_client.py - respect the configured cert
if CA_CERT_PATH and Path(CA_CERT_PATH).exists():
    self.session.verify = CA_CERT_PATH
else:
    self.session.verify = True  # System CA bundle
```

---

### 3.5 Media Downloads Bypass `api_client.py`

**Problem:** Media files are downloaded with raw `requests.get()` calls in:
- `fetch_full_wiki_extended.py:894-903`
- `incremental_fetcher.py:350-358`
- `resume_fetch.py:205-213`

These bypass the api_client's retry logic, error handling, session, and
connection pooling. Each duplicates URL construction, headers, verify, timeout.

**Fix:** Add a `download_file(url, target_path)` method to `WikiAPIClient` that
reuses the session and has proper retry logic for binary downloads.

---

## PHASE 4: Config Sprawl (Single Source of Truth)

### 4.1 Problem: Three Config Locations

Currently configuration is spread across:

1. **`config/env.yaml`** (repo root, central) - The intended single source
2. **`pipeline/01_wiki_fetcher/config/env.yaml`** (local) - A stale copy with
   PATHS pointing to the research directory (!), timeout: 2
3. **`pipeline/01_wiki_fetcher/config/settings.json`** (auto-generated) - Redundant

Additionally, `config.py` has:
- 132 lines of `DEFAULT_FETCH_CONFIG` hardcoded defaults (lines 71-132)
- Module-level global variables: `API_URL`, `HEADERS`, `CA_CERT_PATH`, `TIMEOUT`,
  `MAX_RETRIES`, `RETRY_DELAY`, `API_BASE_URL`, `API_FETCH_URL`, etc.
- These globals are imported by 4 different files

**Issues:**
- Local `config/env.yaml` has PATHS pointing to research repo, not dev_dito
- `timeout: 2` exists in both local AND central config
- Changing timeout requires updating TWO files (or knowing which one is used)
- `settings.json` is auto-generated but also gitignored - confusing
- Token and cert paths are duplicated across configs

### 4.2 Fix: Single Config Authority

**Step 1: Delete the local config**
```
DELETE: pipeline/01_wiki_fetcher/config/env.yaml
DELETE: pipeline/01_wiki_fetcher/config/settings.json
```
Keep only:
- `pipeline/01_wiki_fetcher/config/.gitignore`
- `pipeline/01_wiki_fetcher/config/PLACEHOLDER_env.yaml` (for documentation)
- Symlinks or copies of token/cert from central `config/secrets/`

**Step 2: Remove fallback logic from `config.py`**
Remove the `USE_CENTRAL_CONFIG` toggle and local config fallback (lines 49-61).
Always load from central `config/env.yaml`. If it's missing, fail with clear error.

**Step 3: Reduce module-level globals**
Instead of 15+ module-level variables, export only `FETCH_CONFIG` (the dataclass)
and `settings` (the raw dict). Consumers should use:
```python
from config import FETCH_CONFIG, settings
# Instead of: from config import API_URL, HEADERS, CA_CERT_PATH, TIMEOUT, ...
```

**Step 4: Token and cert should live in one place**
Currently referenced as:
- Central: `config/secrets/json_rpc_api.token` and `config/secrets/ssl.cert`
- Local: `pipeline/01_wiki_fetcher/config/json_rpc_api.token` (copy!)

Delete the local copies. All modules should use the path from the central config.

---

## PHASE 5: Unused / Redundant Code

### 5.1 `fetch_full_wiki.py` (research prototype copy)

The original simple fetcher `fetch_full_wiki.py` does NOT exist in the pipeline
(confirmed by glob). The pipeline only has `fetch_full_wiki_extended.py`. Good.

### 5.2 `change_report.py` vs `change_detector.py` Overlap

- `change_detector.py` - Detects changes between manifests
- `change_report.py` - Generates reports about changes

Both define similar dataclasses (`PageChange` vs `PageDiff`, `MediaChange` vs
`MediaDiff`). Consider merging or clarifying the boundary.

### 5.3 `carry_forward_unchanged` Logic Bug

`incremental_fetcher.py:400-427` has dead code at line 414-418:

```python
# Copy unchanged pages
for change in self.changes.page_changes:
    if change.change_type == ChangeType.UNCHANGED:  # Never true
        entry = self.previous_manifest.get_page(change.page_id)
        ...
```

The comment at line 420 acknowledges this:
`# Actually, unchanged items are NOT in page_changes`

The loop at 414-418 does nothing because `page_changes` only contains changes.
Lines 422-426 then do the correct thing. The dead code should be removed.

### 5.4 Stats Dictionary is 80+ Lines of Inline Init

`fetch_full_wiki_extended.py:139-233` initializes a massive stats dictionary inline
in `__init__`. This should be extracted to a dataclass or factory function for
type safety and readability.

---

## PHASE 6: Naming Issues

### 6.1 `fetch_full_wiki_extended.py` - Misleading Name

The name suggests this is an "extended" variant of `fetch_full_wiki.py`, but that
file doesn't exist in the pipeline. Rename to `fetcher.py` or `wiki_fetcher.py`.

### 6.2 `_PAGE_SPECIFIC_METHODS` vs `_failed_methods`

After fixing 1.1, rename `_failed_methods` to `_unsupported_methods` to clarify
that it tracks methods the API doesn't support at all, not per-page failures.

### 6.3 Config Key Inconsistency

Central config uses `SOURCE_WIKI` but the code normalizes it to `JSONRPC`.
Local config uses `JSONRPC` directly. The normalization layer in `config.py:408-418`
is confusing. Pick one name and use it everywhere.

### 6.4 `content_output` vs `data/fetched`

Research prototype outputs to `content_output/`. Pipeline outputs to `data/fetched/`.
But the local `config/env.yaml` still points to the research path. This is part of
the config sprawl issue (Phase 4).

---

## Implementation Order

| Priority | Task                                    | Phase | Est. Effort | Impact     |
|----------|-----------------------------------------|-------|-------------|------------|
| 1        | Fix `_failed_methods` cascade           | 1.1   | 30 min      | CRITICAL   |
| 2        | Restore timeout to 30s                  | 1.2   | 5 min       | HIGH       |
| 3        | Add namespace exclusions                | 1.3   | 5 min       | MEDIUM     |
| 4        | Add `requests.Session` pooling          | 3.1   | 30 min      | HIGH       |
| 5        | Centralize SSL cert handling            | 3.4   | 20 min      | MEDIUM     |
| 6        | Extract `utils.py` (dedup functions)    | 3.2-3 | 15 min      | LOW        |
| 7        | Delete stale local config               | 4.1-2 | 30 min      | HIGH       |
| 8        | Move media downloads into api_client    | 3.5   | 45 min      | MEDIUM     |
| 9        | Remove dead code in incremental_fetcher | 5.3   | 5 min       | LOW        |
| 10       | Rename files/variables                  | 6.x   | 15 min      | LOW        |
| 11       | Disable recursive/search discovery      | 2.1.A | 5 min       | LOW        |

**Total estimated effort:** ~3.5 hours

**Expected outcome after all fixes:**
- Page success rate: ~100% (matching prototype)
- Media success rate: ~98.5% (matching prototype)
- Duration: ~400-500s (faster than prototype due to connection pooling)
- Config: Single `config/env.yaml` as sole source of truth
- Code: No duplicated utilities, consistent error handling

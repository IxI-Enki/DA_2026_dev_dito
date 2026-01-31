# Feature 003: Task Breakdown

## Overview

| Metric | Value |
|--------|-------|
| **Total Tasks** | 42 |
| **Phases** | 6 |
| **Estimated Hours** | 60-80 |

---

## Phase 1: Fetch Manifest System

### T-1.1: Design FetchManifest Class
- [ ] **T-1.1.1**: Create `pipeline/01_wiki_fetcher/manifest.py`
- [ ] **T-1.1.2**: Define `PageEntry` dataclass (id, revision, hash, size, timestamp, status)
- [ ] **T-1.1.3**: Define `MediaEntry` dataclass (id, hash, size, timestamp, status)
- [ ] **T-1.1.4**: Define `FetchManifest` class with pages/media dicts
- [ ] **T-1.1.5**: Implement `add_page()`, `add_media()`, `remove_page()`, `remove_media()`
- [ ] **T-1.1.6**: Implement `get_page()`, `get_media()` with None fallback

### T-1.2: Implement Manifest I/O
- [ ] **T-1.2.1**: Create `manifest_schema.json` for validation
- [ ] **T-1.2.2**: Implement `FetchManifest.load(path)` classmethod
- [ ] **T-1.2.3**: Implement `FetchManifest.save(path)` method
- [ ] **T-1.2.4**: Add schema validation on load
- [ ] **T-1.2.5**: Handle missing/corrupt manifest gracefully

### T-1.3: Integrate into Fetcher
- [ ] **T-1.3.1**: Update `ExtendedWikiFetcher` to accept manifest parameter
- [ ] **T-1.3.2**: Update page entries in manifest during fetch
- [ ] **T-1.3.3**: Update media entries in manifest during download
- [ ] **T-1.3.4**: Save manifest at end of successful fetch
- [ ] **T-1.3.5**: Add `--no-manifest` CLI flag

### T-1.4: Manifest CLI Commands
- [ ] **T-1.4.1**: Add `--show-manifest` to display current state
- [ ] **T-1.4.2**: Add `--verify-manifest` to check integrity
- [ ] **T-1.4.3**: Add manifest summary to fetch completion output

---

## Phase 2: Change Detection

### T-2.1: Implement ChangeDetector
- [ ] **T-2.1.1**: Create `pipeline/01_wiki_fetcher/change_detector.py`
- [ ] **T-2.1.2**: Define `ChangeType` enum (ADDED, MODIFIED, DELETED, UNCHANGED)
- [ ] **T-2.1.3**: Define `PageChange` dataclass (page_id, type, old_rev, new_rev, magnitude)
- [ ] **T-2.1.4**: Implement `ChangeDetector.__init__(manifest, api_client)`
- [ ] **T-2.1.5**: Implement `detect_page_changes()` method
- [ ] **T-2.1.6**: Implement `detect_media_changes()` method
- [ ] **T-2.1.7**: Use revision timestamp as primary comparison
- [ ] **T-2.1.8**: Fall back to content hash for verification

### T-2.2: Optimize API Calls
- [ ] **T-2.2.1**: Batch revision queries (fetch page list with revisions)
- [ ] **T-2.2.2**: Cache namespace listings during detection
- [ ] **T-2.2.3**: Add `--parallel N` option for concurrent requests
- [ ] **T-2.2.4**: Implement request rate limiting

### T-2.3: Change Summary
- [ ] **T-2.3.1**: Define `ChangeSummary` dataclass
- [ ] **T-2.3.2**: Implement `ChangeDetector.get_summary()`
- [ ] **T-2.3.3**: Add change counts to progress tracker
- [ ] **T-2.3.4**: Output summary to console after detection

---

## Phase 3: Incremental Fetch

### T-3.1: Implement IncrementalFetcher
- [ ] **T-3.1.1**: Create `pipeline/01_wiki_fetcher/incremental_fetcher.py`
- [ ] **T-3.1.2**: Define `IncrementalFetcher` class
- [ ] **T-3.1.3**: Load existing manifest on init
- [ ] **T-3.1.4**: Run change detection before fetch
- [ ] **T-3.1.5**: Fetch only items in change list
- [ ] **T-3.1.6**: Update manifest with new entries

### T-3.2: Handle Edge Cases
- [ ] **T-3.2.1**: Mark deleted pages in manifest (soft delete)
- [ ] **T-3.2.2**: Detect renamed pages (same content, new ID)
- [ ] **T-3.2.3**: Handle new namespaces
- [ ] **T-3.2.4**: Handle namespace deletions

### T-3.3: Output Structure
- [ ] **T-3.3.1**: Add config option: merge vs separate dirs
- [ ] **T-3.3.2**: Implement merge mode (update existing fetch dir)
- [ ] **T-3.3.3**: Implement delta mode (new dir with changes only)
- [ ] **T-3.3.4**: Update statistics for incremental fetches

### T-3.4: Progress Tracking
- [ ] **T-3.4.1**: Add "change_detection" phase to progress
- [ ] **T-3.4.2**: Show "X changed pages found" in progress
- [ ] **T-3.4.3**: Separate progress for detection vs fetch
- [ ] **T-3.4.4**: Update progress_tracker.py with new phases

### T-3.5: CLI Integration
- [ ] **T-3.5.1**: Add `--incremental` flag (default if manifest exists)
- [ ] **T-3.5.2**: Add `--full` flag (force full fetch)
- [ ] **T-3.5.3**: Add `--dry-run` flag (show what would change)
- [ ] **T-3.5.4**: Update help text and README

---

## Phase 4: Change Reports & History

### T-4.1: ChangeReportGenerator
- [ ] **T-4.1.1**: Create `pipeline/01_wiki_fetcher/change_report.py`
- [ ] **T-4.1.2**: Define `ChangeReport` dataclass
- [ ] **T-4.1.3**: Implement `generate_report(changes, manifest)` function
- [ ] **T-4.1.4**: Include per-page change summaries
- [ ] **T-4.1.5**: Calculate change magnitude (minor/major/rewrite)
- [ ] **T-4.1.6**: Save to `data/logs/change_reports/`

### T-4.2: FetchHistory
- [ ] **T-4.2.1**: Create `pipeline/01_wiki_fetcher/fetch_history.py`
- [ ] **T-4.2.2**: Define `FetchHistoryEntry` dataclass
- [ ] **T-4.2.3**: Implement `FetchHistory` class with CRUD
- [ ] **T-4.2.4**: Track last N fetches (configurable)
- [ ] **T-4.2.5**: Link to manifests and change reports
- [ ] **T-4.2.6**: Implement cleanup of old entries

### T-4.3: Text Diff
- [ ] **T-4.3.1**: Create `pipeline/01_wiki_fetcher/diff_utils.py`
- [ ] **T-4.3.2**: Implement `generate_diff(old_content, new_content)`
- [ ] **T-4.3.3**: Generate unified diff format
- [ ] **T-4.3.4**: Calculate diff statistics (lines added/removed)
- [ ] **T-4.3.5**: Support HTML diff for dashboard

### T-4.4: Dashboard API
- [ ] **T-4.4.1**: Add `/api/change-report/{fetch_id}` endpoint
- [ ] **T-4.4.2**: Add `/api/fetch-history` endpoint
- [ ] **T-4.4.3**: Add `/api/page-diff/{page_id}` endpoint
- [ ] **T-4.4.4**: Update PipelineOrchestrator.php

---

## Phase 5: Content Evaluation

### T-5.1: ContentEvaluator
- [ ] **T-5.1.1**: Create `pipeline/02_deep_evaluation/evaluator.py`
- [ ] **T-5.1.2**: Define `EvaluationResult` dataclass
- [ ] **T-5.1.3**: Implement `ContentEvaluator` class
- [ ] **T-5.1.4**: Orchestrate analyzer pipeline
- [ ] **T-5.1.5**: Aggregate scores and flags

### T-5.2: Quality Analyzer
- [ ] **T-5.2.1**: Update `analyzers/quality_analyzer.py`
- [ ] **T-5.2.2**: Detect empty/stub pages (<100 chars)
- [ ] **T-5.2.3**: Detect template-only pages
- [ ] **T-5.2.4**: Check character ratio (special chars)
- [ ] **T-5.2.5**: Basic language detection

### T-5.3: Structure Analyzer
- [ ] **T-5.3.1**: Update `analyzers/structure_analyzer.py`
- [ ] **T-5.3.2**: Extract heading hierarchy
- [ ] **T-5.3.3**: Identify code blocks + languages
- [ ] **T-5.3.4**: Detect tables
- [ ] **T-5.3.5**: Calculate text-to-markup ratio

### T-5.4: Link Analyzer
- [ ] **T-5.4.1**: Update `analyzers/link_analyzer.py`
- [ ] **T-5.4.2**: Validate internal links (broken link detection)
- [ ] **T-5.4.3**: Identify orphan pages
- [ ] **T-5.4.4**: Calculate page importance (incoming links)
- [ ] **T-5.4.5**: Detect circular references

### T-5.5: Evaluation Report
- [ ] **T-5.5.1**: Create `pipeline/02_deep_evaluation/evaluation_report.py`
- [ ] **T-5.5.2**: Define report schema
- [ ] **T-5.5.3**: Generate per-page scores
- [ ] **T-5.5.4**: Generate embedding recommendations
- [ ] **T-5.5.5**: Save to `data/evaluated/`

### T-5.6: Integration
- [ ] **T-5.6.1**: Run evaluation after fetch (optional)
- [ ] **T-5.6.2**: Add `--evaluate` flag to fetcher
- [ ] **T-5.6.3**: Add evaluation to pipeline stages
- [ ] **T-5.6.4**: Update progress tracker for evaluation

---

## Phase 6: Dashboard UI

### T-6.1: Fetch Mode Selector
- [ ] **T-6.1.1**: Add toggle: Full / Incremental in admin.php
- [ ] **T-6.1.2**: Show last fetch timestamp and type
- [ ] **T-6.1.3**: Display estimated time for each mode
- [ ] **T-6.1.4**: Pass mode to run_stage API

### T-6.2: Change Summary Panel
- [ ] **T-6.2.1**: Add change summary section to pipeline card
- [ ] **T-6.2.2**: Show Added/Modified/Deleted counts
- [ ] **T-6.2.3**: List recent changes (last 10)
- [ ] **T-6.2.4**: Link to detailed change report

### T-6.3: Evaluation Panel
- [ ] **T-6.3.1**: Add evaluation section to pipeline card
- [ ] **T-6.3.2**: Show quality score gauge/meter
- [ ] **T-6.3.3**: List pages with warnings
- [ ] **T-6.3.4**: Show broken link count

### T-6.4: History Browser
- [ ] **T-6.4.1**: Add fetch history section
- [ ] **T-6.4.2**: List past fetches with stats
- [ ] **T-6.4.3**: Compare any two fetches
- [ ] **T-6.4.4**: Export history option

### T-6.5: CSS & Polish
- [ ] **T-6.5.1**: Style change summary panel
- [ ] **T-6.5.2**: Style evaluation panel
- [ ] **T-6.5.3**: Style history browser
- [ ] **T-6.5.4**: Responsive design check

---

## Testing Tasks

### Unit Tests
- [ ] **T-TEST-1**: Test FetchManifest CRUD
- [ ] **T-TEST-2**: Test ChangeDetector logic
- [ ] **T-TEST-3**: Test quality analyzers
- [ ] **T-TEST-4**: Test link analyzer
- [ ] **T-TEST-5**: Test diff generation

### Integration Tests
- [ ] **T-TEST-6**: Test full incremental fetch cycle
- [ ] **T-TEST-7**: Test Dashboard API endpoints
- [ ] **T-TEST-8**: Test Docker container with --incremental

### E2E Tests
- [ ] **T-TEST-9**: Full fetch → Incremental → Report workflow
- [ ] **T-TEST-10**: Error recovery scenarios

---

## Progress Tracking

### Phase Completion

| Phase | Tasks | Done | Progress |
|-------|-------|------|----------|
| 1. Manifest | 19 | 0 | 0% |
| 2. Detection | 12 | 0 | 0% |
| 3. Incremental | 16 | 0 | 0% |
| 4. Reports | 15 | 0 | 0% |
| 5. Evaluation | 21 | 0 | 0% |
| 6. Dashboard | 17 | 0 | 0% |
| Testing | 10 | 0 | 0% |
| **Total** | **110** | **0** | **0%** |

---

## Notes

- Tasks prefixed with T- are implementation tasks
- Tasks prefixed with T-TEST- are testing tasks
- Each task should be completable in 1-4 hours
- Mark tasks done as `[x]` when complete
- Update progress table after each session

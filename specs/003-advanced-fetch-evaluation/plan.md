# Feature 003: Implementation Plan

## Overview

| Field | Value |
|-------|-------|
| **Feature** | Advanced Fetch & Evaluation System |
| **Branch** | `003-advanced-fetch-evaluation` |
| **Estimated Duration** | 2-3 weeks |
| **Phases** | 5 |

---

## Phase 1: Fetch Manifest System (3-4 days)

### Goal
Create the foundation for tracking fetch state and enabling incremental updates.

### Components

```
pipeline/01_wiki_fetcher/
├── manifest.py              # FetchManifest class
├── manifest_schema.json     # JSON Schema for validation
└── fetch_full_wiki_extended.py  # Update to write manifest
```

### Tasks
1. **T-1.1**: Design FetchManifest class
   - Page tracking: id, revision, hash, timestamp
   - Media tracking: id, hash, size, timestamp
   - Merge capability for incremental updates

2. **T-1.2**: Implement manifest I/O
   - Load existing manifest
   - Save updated manifest
   - Schema validation

3. **T-1.3**: Integrate into fetcher
   - Write manifest after successful fetch
   - Include in fetch statistics
   - Add `--no-manifest` flag for testing

4. **T-1.4**: Add manifest commands
   - `--show-manifest`: Display current state
   - `--verify-manifest`: Check integrity

### Deliverables
- [ ] `FetchManifest` class with full CRUD
- [ ] Manifest written after every fetch
- [ ] CLI commands for manifest inspection

---

## Phase 2: Change Detection (2-3 days)

### Goal
Implement efficient detection of changed content using revision timestamps and hashes.

### Components

```
pipeline/01_wiki_fetcher/
├── change_detector.py       # ChangeDetector class
└── diff_utils.py            # Text diff utilities
```

### Tasks
1. **T-2.1**: Implement ChangeDetector
   - Compare current wiki state to manifest
   - Categorize: added, modified, deleted
   - Use revision timestamps as primary check
   - Fall back to content hash for verification

2. **T-2.2**: Optimize API calls
   - Batch revision queries
   - Cache namespace listings
   - Parallel page info requests

3. **T-2.3**: Generate change summary
   - Quick summary for dashboard
   - Detailed diff for review

### Deliverables
- [ ] `ChangeDetector` class
- [ ] Change detection in <10s for 200 pages
- [ ] Change summary output

---

## Phase 3: Incremental Fetch (3-4 days)

### Goal
Enable fetching only changed content, dramatically reducing sync time.

### Components

```
pipeline/01_wiki_fetcher/
├── incremental_fetcher.py   # IncrementalFetcher class
└── fetch_full_wiki_extended.py  # Add --incremental flag
```

### Tasks
1. **T-3.1**: Implement IncrementalFetcher
   - Inherits from/wraps ExtendedWikiFetcher
   - Uses ChangeDetector to identify targets
   - Fetches only changed items

2. **T-3.2**: Handle edge cases
   - Deleted pages (mark in manifest)
   - Renamed/moved pages
   - New namespaces

3. **T-3.3**: Update output structure
   - Merge incremental into existing fetch dir
   - Or create new timestamped dir with delta only
   - Configurable behavior

4. **T-3.4**: Progress tracking integration
   - Show "X changed pages" in progress
   - Different progress for detection vs fetch

5. **T-3.5**: CLI integration
   - `--incremental`: Use incremental mode
   - `--full`: Force full fetch (default if no manifest)
   - `--dry-run`: Show what would change

### Deliverables
- [ ] Incremental fetch working E2E
- [ ] <2 min for typical changes
- [ ] CLI flags documented

---

## Phase 4: Change Report & History (2-3 days)

### Goal
Generate detailed change reports and maintain fetch history.

### Components

```
pipeline/01_wiki_fetcher/
├── change_report.py         # ChangeReportGenerator
├── fetch_history.py         # FetchHistory manager
data/logs/
├── fetch_history.json       # History tracking
└── change_reports/          # Individual reports
    └── report_YYYYMMDD_HHMMSS.json
```

### Tasks
1. **T-4.1**: Implement ChangeReportGenerator
   - Generate JSON report
   - Include per-page summaries
   - Calculate change magnitude

2. **T-4.2**: Implement FetchHistory
   - Track last N fetches
   - Link to change reports
   - Cleanup old entries

3. **T-4.3**: Text diff generation
   - Side-by-side diff for review
   - Highlight additions/deletions
   - Summary statistics

4. **T-4.4**: Dashboard API
   - Endpoint for change report
   - Endpoint for fetch history
   - Endpoint for page diff

### Deliverables
- [ ] Change reports generated automatically
- [ ] History retained (configurable)
- [ ] API endpoints for dashboard

---

## Phase 5: Content Evaluation (3-4 days)

### Goal
Analyze fetched content quality before embedding.

### Components

```
pipeline/02_deep_evaluation/
├── evaluator.py             # ContentEvaluator class
├── analyzers/
│   ├── quality_analyzer.py  # Content quality checks
│   ├── structure_analyzer.py # Heading/code/table analysis
│   └── link_analyzer.py     # Link validation
└── evaluation_report.py     # Report generator
```

### Tasks
1. **T-5.1**: Implement ContentEvaluator
   - Orchestrates all analyzers
   - Aggregates scores
   - Generates recommendations

2. **T-5.2**: Quality Analysis
   - Empty/stub detection
   - Template-only pages
   - Character ratio checks
   - Language detection

3. **T-5.3**: Structure Analysis
   - Heading hierarchy
   - Code block extraction
   - Table detection
   - Text-to-markup ratio

4. **T-5.4**: Link Analysis
   - Broken link detection
   - Orphan page identification
   - Importance calculation
   - Circular reference check

5. **T-5.5**: Evaluation Report
   - Per-page scores
   - Flagged pages list
   - Embedding recommendations
   - Summary statistics

6. **T-5.6**: Dashboard Integration
   - Show quality score
   - List warnings
   - Drill-down capability

### Deliverables
- [ ] Evaluation runs after fetch
- [ ] Quality issues flagged
- [ ] Dashboard shows results

---

## Phase 6: Dashboard UI (2-3 days)

### Goal
Expose all new features in the Admin Dashboard.

### Components

```
dokuwiki_plugin/
├── dist/
│   ├── pipeline.js          # Update with new features
│   └── pipeline.css         # Styling for new elements
└── lib/
    └── PipelineOrchestrator.php  # New endpoints
```

### Tasks
1. **T-6.1**: Fetch mode selector
   - Toggle: Full / Incremental
   - Show last fetch info
   - Estimated time display

2. **T-6.2**: Change summary panel
   - Added/Modified/Deleted counts
   - Quick change list
   - Link to detailed report

3. **T-6.3**: Evaluation panel
   - Quality score gauge
   - Warning list
   - Recommendations

4. **T-6.4**: History browser
   - List past fetches
   - Compare any two fetches
   - Export capability

### Deliverables
- [ ] All features accessible from Dashboard
- [ ] Intuitive UI for fetch mode selection
- [ ] Clear visualization of changes

---

## Integration Points

### With Existing Systems

| System | Integration |
|--------|-------------|
| Orchestrator API | New endpoints for incremental, history, evaluation |
| Progress Tracker | Extended for change detection phase |
| Job Status | Include change counts, quality score |
| Docker module | Support `--incremental` flag |

### Configuration (env.yaml)

```yaml
PIPELINE:
  fetcher:
    incremental:
      enabled: true
      default_mode: "incremental"  # or "full"
    history:
      retain_count: 10
      retain_days: 30
    evaluation:
      auto_run: true
      quality_threshold: 0.5
      exclude_low_quality: false
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API rate limits during change detection | Batch requests, caching |
| Large number of changes | Chunked processing, progress updates |
| Manifest corruption | Backup before update, recovery mode |
| Network instability | Resume capability, partial saves |

---

## Testing Strategy

### Unit Tests
- Manifest CRUD operations
- Change detection logic
- Quality analyzers

### Integration Tests
- Full incremental fetch cycle
- Dashboard API endpoints
- Docker container execution

### E2E Tests
- Full fetch → Incremental → Report
- Dashboard workflow
- Error recovery scenarios

---

## Timeline

```
Week 1:
├── Phase 1: Manifest System (Mon-Thu)
└── Phase 2: Change Detection (Fri + overflow)

Week 2:
├── Phase 3: Incremental Fetch (Mon-Thu)
└── Phase 4: Change Reports (Fri + overflow)

Week 3:
├── Phase 5: Content Evaluation (Mon-Thu)
├── Phase 6: Dashboard UI (Thu-Fri)
└── Testing & Polish (overflow)
```

---

## Success Criteria

- [ ] Incremental fetch completes in <2 min for <20 changes
- [ ] Change report accurately shows all modifications
- [ ] Evaluation flags low-quality content
- [ ] Dashboard provides full control
- [ ] All features work in Docker and locally

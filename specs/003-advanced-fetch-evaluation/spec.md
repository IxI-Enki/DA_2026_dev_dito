# Feature 003: Advanced Fetch & Evaluation System

## Overview

| Field | Value |
|-------|-------|
| **Feature ID** | 003 |
| **Branch** | `003-advanced-fetch-evaluation` |
| **Status** | Draft |
| **Created** | 2026-02-01 |
| **Author** | Jan Ritt (IxI-Enki) |

## Problem Statement

### Current Situation
The existing wiki fetcher performs **full fetches** every time, downloading all 209+ pages and 335+ media files regardless of whether they changed. This is:
- **Slow**: ~12 minutes for a full fetch
- **Wasteful**: Re-downloads unchanged content
- **Blind**: No visibility into what actually changed between fetches
- **Incomplete**: No quality analysis of fetched content before embedding

### User Needs
As a **wiki administrator**, I need to:
1. Quickly sync only changed content (incremental updates)
2. See what changed since the last fetch (change tracking)
3. Understand content quality before embedding (evaluation)
4. Have confidence that embeddings reflect current wiki state

### Business Impact
- **Time Savings**: Reduce typical sync from 12 min to <1 min for incremental
- **Resource Efficiency**: Reduce network/storage by 90%+ for unchanged content
- **Quality Assurance**: Catch issues before they reach the vector database
- **Audit Trail**: Know exactly what changed and when

---

## Functional Requirements

### FR-1: Incremental Fetching

#### FR-1.1: Change Detection
| ID | Requirement |
|----|-------------|
| FR-1.1.1 | System SHALL compare page revision timestamps with last fetch |
| FR-1.1.2 | System SHALL identify new, modified, and deleted pages |
| FR-1.1.3 | System SHALL track media file hashes for change detection |
| FR-1.1.4 | System SHALL maintain a fetch manifest with last-known state |

#### FR-1.2: Delta Fetch Execution
| ID | Requirement |
|----|-------------|
| FR-1.2.1 | System SHALL fetch only pages with newer revision than manifest |
| FR-1.2.2 | System SHALL download only new/changed media files |
| FR-1.2.3 | System SHALL mark deleted pages in manifest (soft delete) |
| FR-1.2.4 | System SHALL support `--full` flag to force complete re-fetch |

#### FR-1.3: Fetch Manifest
| ID | Requirement |
|----|-------------|
| FR-1.3.1 | Manifest SHALL include: page_id, revision, hash, fetch_timestamp |
| FR-1.3.2 | Manifest SHALL be stored as `fetch_manifest.json` in fetch output |
| FR-1.3.3 | Manifest SHALL support merge from previous fetch |
| FR-1.3.4 | Manifest SHALL track fetch run metadata (duration, counts, errors) |

### FR-2: Change Tracking System

#### FR-2.1: Diff Generation
| ID | Requirement |
|----|-------------|
| FR-2.1.1 | System SHALL generate text diff between page versions |
| FR-2.1.2 | System SHALL categorize changes: content, structure, links, media |
| FR-2.1.3 | System SHALL calculate change magnitude (minor/major/rewrite) |
| FR-2.1.4 | System SHALL detect moved/renamed pages |

#### FR-2.2: Change Report
| ID | Requirement |
|----|-------------|
| FR-2.2.1 | System SHALL generate `change_report.json` after incremental fetch |
| FR-2.2.2 | Report SHALL include: added, modified, deleted page lists |
| FR-2.2.3 | Report SHALL include per-page change summary |
| FR-2.2.4 | Report SHALL be viewable in Dashboard UI |

#### FR-2.3: Change History
| ID | Requirement |
|----|-------------|
| FR-2.3.1 | System SHALL maintain history of last N fetches |
| FR-2.3.2 | System SHALL allow comparison between any two fetch states |
| FR-2.3.3 | History retention SHALL be configurable (default: 10 fetches) |

### FR-3: Content Evaluation

#### FR-3.1: Quality Analysis
| ID | Requirement |
|----|-------------|
| FR-3.1.1 | System SHALL analyze content for embedding suitability |
| FR-3.1.2 | System SHALL detect empty/stub pages |
| FR-3.1.3 | System SHALL identify template-only pages (low semantic value) |
| FR-3.1.4 | System SHALL flag pages with excessive special characters |

#### FR-3.2: Structure Analysis
| ID | Requirement |
|----|-------------|
| FR-3.2.1 | System SHALL extract heading hierarchy |
| FR-3.2.2 | System SHALL identify code blocks and their languages |
| FR-3.2.3 | System SHALL detect tables and structured data |
| FR-3.2.4 | System SHALL calculate text-to-markup ratio |

#### FR-3.3: Link Analysis
| ID | Requirement |
|----|-------------|
| FR-3.3.1 | System SHALL validate internal links (detect broken links) |
| FR-3.3.2 | System SHALL identify orphan pages (no incoming links) |
| FR-3.3.3 | System SHALL calculate page importance (incoming link count) |
| FR-3.3.4 | System SHALL detect circular reference patterns |

#### FR-3.4: Evaluation Report
| ID | Requirement |
|----|-------------|
| FR-3.4.1 | System SHALL generate `evaluation_report.json` |
| FR-3.4.2 | Report SHALL include quality scores per page |
| FR-3.4.3 | Report SHALL flag pages needing attention |
| FR-3.4.4 | Report SHALL provide embedding recommendations |

### FR-4: Dashboard Integration

#### FR-4.1: Fetch Mode Selection
| ID | Requirement |
|----|-------------|
| FR-4.1.1 | Dashboard SHALL offer "Full Fetch" and "Incremental Fetch" buttons |
| FR-4.1.2 | Dashboard SHALL show last fetch timestamp and type |
| FR-4.1.3 | Dashboard SHALL display estimated time for each fetch type |

#### FR-4.2: Change Visualization
| ID | Requirement |
|----|-------------|
| FR-4.2.1 | Dashboard SHALL display change summary after fetch |
| FR-4.2.2 | Dashboard SHALL show added/modified/deleted counts |
| FR-4.2.3 | Dashboard SHALL allow drill-down to individual page changes |

#### FR-4.3: Evaluation Display
| ID | Requirement |
|----|-------------|
| FR-4.3.1 | Dashboard SHALL show overall quality score |
| FR-4.3.2 | Dashboard SHALL list pages with quality warnings |
| FR-4.3.3 | Dashboard SHALL show broken link count |

---

## Non-Functional Requirements

### NFR-1: Performance
| ID | Requirement |
|----|-------------|
| NFR-1.1 | Incremental fetch SHALL complete in <60s for <20 changed pages |
| NFR-1.2 | Change detection SHALL complete in <10s for 200 pages |
| NFR-1.3 | Evaluation SHALL process 10 pages/second minimum |

### NFR-2: Storage
| ID | Requirement |
|----|-------------|
| NFR-2.1 | Manifest file SHALL be <1MB for 500 pages |
| NFR-2.2 | History SHALL use <100MB for 10 fetch runs |
| NFR-2.3 | System SHALL support cleanup of old fetch data |

### NFR-3: Reliability
| ID | Requirement |
|----|-------------|
| NFR-3.1 | Interrupted fetch SHALL be resumable |
| NFR-3.2 | Manifest corruption SHALL not prevent full re-fetch |
| NFR-3.3 | System SHALL handle wiki unavailability gracefully |

### NFR-4: Compatibility
| ID | Requirement |
|----|-------------|
| NFR-4.1 | System SHALL work with existing fetched data structure |
| NFR-4.2 | System SHALL not break existing embedding pipeline |
| NFR-4.3 | System SHALL support both Docker and local execution |

---

## User Stories

### US-1: Quick Sync
```
AS A wiki administrator
I WANT TO quickly sync only changed pages
SO THAT I can keep embeddings current without waiting for full fetch

ACCEPTANCE CRITERIA:
- [ ] Can run incremental fetch from Dashboard
- [ ] Only changed pages are downloaded
- [ ] Sync completes in under 2 minutes for typical changes
- [ ] Progress shows "X changed pages found"
```

### US-2: Change Awareness
```
AS A content manager
I WANT TO see what changed since last sync
SO THAT I can verify important updates are captured

ACCEPTANCE CRITERIA:
- [ ] Change report shows added/modified/deleted pages
- [ ] Can see summary of changes for each page
- [ ] Can compare content between versions
- [ ] Dashboard shows change count prominently
```

### US-3: Quality Gate
```
AS A system administrator
I WANT TO evaluate content before embedding
SO THAT I can ensure only quality content enters the vector database

ACCEPTANCE CRITERIA:
- [ ] Evaluation runs automatically after fetch
- [ ] Quality issues are flagged with severity
- [ ] Can exclude low-quality pages from embedding
- [ ] Broken links are reported
```

### US-4: Audit Trail
```
AS AN auditor
I WANT TO see history of all fetch operations
SO THAT I can track data lineage and changes over time

ACCEPTANCE CRITERIA:
- [ ] Can view list of past fetches with timestamps
- [ ] Can see what changed in each fetch
- [ ] History is retained for configured period
- [ ] Can export history for compliance
```

---

## Data Models

### Fetch Manifest Schema
```yaml
fetch_manifest:
  version: "1.0"
  created_at: "2026-02-01T10:00:00Z"
  updated_at: "2026-02-01T12:00:00Z"
  wiki_url: "https://leowiki.htl-leonding.ac.at"
  
  pages:
    - id: "start"
      revision: 1706789400
      content_hash: "sha256:abc123..."
      size_bytes: 4523
      last_fetched: "2026-02-01T12:00:00Z"
      status: "current"  # current | deleted | error
  
  media:
    - id: "wiki:logo.png"
      hash: "sha256:def456..."
      size_bytes: 34567
      last_fetched: "2026-02-01T12:00:00Z"
      status: "current"
  
  stats:
    total_pages: 209
    total_media: 335
    last_full_fetch: "2026-02-01T10:00:00Z"
    fetch_count: 5
```

### Change Report Schema
```yaml
change_report:
  fetch_id: "fetch_20260201_120000"
  compared_to: "fetch_20260201_100000"
  generated_at: "2026-02-01T12:05:00Z"
  
  summary:
    pages_added: 3
    pages_modified: 12
    pages_deleted: 1
    media_added: 5
    media_modified: 2
    media_deleted: 0
  
  changes:
    - page_id: "teacher:neulehrerinnenhandbuch:start"
      change_type: "modified"
      old_revision: 1706700000
      new_revision: 1706789400
      change_magnitude: "minor"  # minor | major | rewrite
      diff_summary: "Updated contact information"
```

### Evaluation Report Schema
```yaml
evaluation_report:
  fetch_id: "fetch_20260201_120000"
  evaluated_at: "2026-02-01T12:10:00Z"
  
  overall:
    quality_score: 0.85  # 0-1
    pages_evaluated: 209
    pages_flagged: 15
    broken_links: 23
    orphan_pages: 8
  
  pages:
    - id: "start"
      quality_score: 0.95
      flags: []
      embedding_recommendation: "include"
      
    - id: "archive:old_page"
      quality_score: 0.45
      flags:
        - type: "low_content"
          message: "Page has less than 100 characters"
        - type: "no_incoming_links"
          message: "Orphan page - no pages link here"
      embedding_recommendation: "exclude"
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Incremental fetch time | <2 min | Average for <20 changes |
| Change detection accuracy | >99% | Compared to full re-fetch |
| Quality flag precision | >90% | Manual review of flagged pages |
| User adoption | 80% | % of fetches using incremental |

---

## Edge Cases & Error Handling

### EC-1: First Run (No Manifest)
- Behavior: Perform full fetch, create initial manifest
- User sees: "No previous fetch found - performing full sync"

### EC-2: Wiki Structure Change
- Behavior: Detect namespace restructuring, flag for review
- User sees: "Namespace changes detected - review recommended"

### EC-3: Manifest Corruption
- Behavior: Log warning, offer full re-fetch
- User sees: "Manifest invalid - full sync required"

### EC-4: Network Timeout During Incremental
- Behavior: Save partial progress, allow resume
- User sees: "Sync interrupted - 45/67 pages complete. Resume?"

### EC-5: Page Deleted on Wiki
- Behavior: Mark as deleted in manifest, preserve local copy
- User sees: "3 pages deleted on wiki (local copies retained)"

---

## Dependencies

### Internal Dependencies
- `002-pipeline-orchestration` (merged) - Dashboard, Orchestrator API
- `pipeline/01_wiki_fetcher` - Existing fetch infrastructure
- `data/logs/pipeline_runs.json` - Job status tracking

### External Dependencies
- LeoWiki JSON-RPC API - Page revision info
- Qdrant (later phases) - For embedding storage

---

## Out of Scope (Future Features)

- Real-time sync (webhook-based)
- Multi-wiki federation
- Content versioning (beyond manifest)
- LLM-based content summarization
- Automatic embedding trigger

---

## Open Questions

1. **Q**: Should deleted pages be removed from embeddings immediately?
   **A**: TBD - Need to consider search relevance of historical content

2. **Q**: How to handle pages with access restrictions changing?
   **A**: TBD - May need ACL diff tracking

3. **Q**: Should evaluation be blocking for embedding?
   **A**: Recommendation: Non-blocking with warnings, configurable

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-02-01 | 1.0 | Jan Ritt | Initial specification |

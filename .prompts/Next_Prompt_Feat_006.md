
Diese Docker Stacks sind aktuell installiert und in Docker Desktop für den User auswählbar:
- stack-h-mcp
- stack-g-devdito
- stack-d-ai-core
- stack-b-wiki-core
- stack-a-wiki-sandbox

<local_paths old_partly_current_running_stacks>
D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/stacks
</local_paths>

---

<!--
| Stack Name | Service Name | Image | Container ID | Port(s) |
| ---------- | ------------ | ----- | ------------ | ------- |
|            |              |       |              |         |
-->

<docker_desktop current_stacks_list>
  <output gui_sketch>

| Stack Name           | Service Name              | Image                                 | Container ID | Port(s)        |
| -------------------- | ------------------------- | ------------------------------------- | ------------ | -------------- |
|                      |                           |                                       |              |                |
| stack-h-mcp          | semantic-search-wiki-core | stack-h-mcp-semantic-search-wiki-core | 65c218b8114c | 3000:3000      |
|                      |                           |                                       |              |                |
| stack-g-devdito      | dev-dito-wiki             | linuxserver/dokuwiki:latest           | 170267deb77f | 8080:80        |
| stack-g-devdito      | dev-dito-orchestrator     | stack-g-devdito-orchestrator          | 130a7d650d6d | 8089:8089      |
|                      |                           |                                       |              |                |
| stack-d-ai-core      | qdrant-main-vector-db     | qdrant/qdrant:v1.13.2                 | 8859ea582d6f | 6333:6333 (+1) |
| stack-d-ai-core      | qdrant-init               | stack-d-ai-core-qdrant-init           | 345e6c632aa5 |                |
|                      |                           |                                       |              |                |
| stack-b-wiki-core    | keycloak-server           | keycloak/keycloak:25.0                | 97d899cd90d2 | 8081:8080      |
|                      |                           |                                       |              |                |
| stack-a-wiki-sandbox | wiki-sandbox              | linuxserver/dokuwiki:latest           | a1e324b6b21f | 8090:80        |
|                      |                           |                                       |              |                |

  </output>
</docker_desktop>

---

## Architecture

### Design Principle: Stack Orchestration from Within

Dev Dito operates as a **central orchestrator** within the multi-stack Docker ecosystem. The architecture follows a critical constraint:

> **Dev Dito MUST be able to discover, connect to, and manage dependent Docker stacks from within its own containerized environment - without requiring Docker-in-Docker or direct Docker socket access.**

This architectural decision has the following implications:

1. **Pre-Installation Requirement**: All potentially required stacks (A through I) must be installed and available on the host system BEFORE Dev Dito can orchestrate them
2. **Network-Based Communication**: Stack management happens via HTTP APIs over the shared `leonidas-network`, not via Docker commands
3. **Service Discovery**: Dev Dito discovers available services through network probing and health endpoints
4. **Graceful Degradation**: Missing stacks result in reduced functionality, not installation failure

### Multi-Stack Ecosystem Overview

```
                    SHARED DOCKER NETWORK: leonidas-network
    ┌──────────────────────────────────────────────────────────────────────┐
    │                                                                      │
    │   INFRASTRUCTURE LAYER                                               │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
    │   │ Stack-A         │  │ Stack-B         │  │ Stack-C             │  │
    │   │ wiki-sandbox    │  │ wiki-core       │  │ extensions-extra    │  │
    │   │ Port: 8090      │  │ Port: 8081      │  │ (reserved)          │  │
    │   └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
    │                                                                      │
    │   AI & DATA LAYER                                                    │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
    │   │ Stack-D         │  │ Stack-E         │  │ Stack-F             │  │
    │   │ ai-core         │  │ ai-evaluation   │  │ observability       │  │
    │   │ Port: 6333      │  │ (reserved)      │  │ (reserved)          │  │
    │   └────────┬────────┘  └─────────────────┘  └─────────────────────┘  │
    │            │                                                         │
    │            │ uses Qdrant                                             │
    │            ▼                                                         │
    │   ┌───────────────────────────────────────────────────────────────┐  │
    │   │ Stack-G: DEV DITO (THIS PROJECT)                              │  │
    │   │ ┌─────────────────┐  ┌──────────────────────────────────────┐ │  │
    │   │ │ dev-dito-wiki   │  │ dev-dito-orchestrator                │ │  │
    │   │ │ Port: 8080      │  │ Port: 8089                           │ │  │
    │   │ │ DokuWiki +      │  │ Pipeline API + Module Management     │ │  │
    │   │ │ DevDito Plugin  │  │                                      │ │  │
    │   │ └─────────────────┘  └──────────────────────────────────────┘ │  │
    │   └───────────────────────────────────────────────────────────────┘  │
    │            │                                                         │
    │            │ provides MCP tools                                      │
    │            ▼                                                         │
    │   ┌─────────────────┐  ┌─────────────────────────────────────────┐   │
    │   │ Stack-H         │  │ Stack-I                                 │   │
    │   │ mcp-servers     │  │ leonidas-services                       │   │
    │   │ Port: 3000      │  │ (AI Chat Frontend)                      │   │
    │   └─────────────────┘  └─────────────────────────────────────────┘   │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘
```

### Required Stacks

The following stacks must be available for full Dev Dito functionality. The installation script will detect, validate, and optionally install missing stacks.

<stack_list>

<stack id="stack-a-wiki-sandbox">
  <stack_name>wiki-sandbox</stack_name>
  <stack_description>Isolated DokuWiki instance for testing and development. Provides a safe environment to test Dev Dito features without affecting production wikis.</stack_description>
  <requirement_level>OPTIONAL</requirement_level>
  <devdito_relationship>TARGET - Dev Dito can deploy its extension here for testing</devdito_relationship>
  <contained_services>
    <service name="wiki-sandbox">
      <image>linuxserver/dokuwiki:latest</image>
      <port>8090:80</port>
      <purpose>Standalone DokuWiki test instance</purpose>
      <status>ACTIVE</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:8090</health_endpoint>
</stack>

<stack id="stack-b-wiki-core">
  <stack_name>wiki-core-services</stack_name>
  <stack_description>Core authentication and identity services for the wiki ecosystem. Provides SSO capabilities across all wiki instances.</stack_description>
  <requirement_level>RECOMMENDED</requirement_level>
  <devdito_relationship>USES - Dev Dito uses Keycloak for admin authentication</devdito_relationship>
  <contained_services>
    <service name="keycloak-server">
      <image>keycloak/keycloak:25.0</image>
      <port>8081:8080</port>
      <purpose>Identity and Access Management (SSO, OAuth2, OIDC)</purpose>
      <status>ACTIVE</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:8081/health</health_endpoint>
</stack>

<stack id="stack-c-extensions-additional">
  <stack_name>extensions-additional-services</stack_name>
  <stack_description>Additional infrastructure services that extend wiki capabilities. Reserved for future expansion.</stack_description>
  <requirement_level>OPTIONAL</requirement_level>
  <devdito_relationship>NONE - Reserved for future integration</devdito_relationship>
  <contained_services>
    <service name="nginx-proxy">
      <image>nginx:alpine</image>
      <port>80:80, 443:443</port>
      <purpose>Reverse proxy and SSL termination</purpose>
      <status>PLANNED</status>
    </service>
    <service name="redis-cache">
      <image>redis:7-alpine</image>
      <port>6379:6379</port>
      <purpose>Caching layer for session and data</purpose>
      <status>PLANNED</status>
    </service>
  </contained_services>
  <health_endpoint>N/A</health_endpoint>
</stack>

<stack id="stack-d-ai-core">
  <stack_name>ai-core-services</stack_name>
  <stack_description>Core AI infrastructure providing vector database and LLM serving capabilities. Critical dependency for Dev Dito's RAG pipeline. This is the SHARED Qdrant instance used by multiple projects.</stack_description>
  <requirement_level>REQUIRED</requirement_level>
  <devdito_relationship>CRITICAL DEPENDENCY - Dev Dito stores and queries embeddings here (alternative to local dev-dito-qdrant)</devdito_relationship>
  <contained_services>
    <service name="qdrant-main-vector-db">
      <image>qdrant/qdrant:v1.13.2</image>
      <port>6333:6333, 6334:6334</port>
      <purpose>Primary shared vector database for semantic search and RAG across all projects</purpose>
      <status>ACTIVE</status>
    </service>
    <service name="qdrant-init">
      <image>stack-d-ai-core-qdrant-init</image>
      <port>none</port>
      <purpose>Initializes collections and schema in Qdrant on first startup</purpose>
      <status>ACTIVE</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:6333/health</health_endpoint>
  <api_endpoints>
    <endpoint path="http://qdrant-main-vector-db:6333" type="internal">Container-to-container via leonidas-network</endpoint>
    <endpoint path="http://localhost:6333" type="external">Host access for debugging</endpoint>
    <endpoint path="http://localhost:6334" type="external">gRPC endpoint</endpoint>
  </api_endpoints>
</stack>

<stack id="stack-e-ai-evaluation">
  <stack_name>ai-evaluation-services</stack_name>
  <stack_description>ML experiment tracking and RAG evaluation infrastructure. Used for measuring and improving Dev Dito pipeline quality.</stack_description>
  <requirement_level>OPTIONAL</requirement_level>
  <devdito_relationship>USES - Dev Dito reports evaluation metrics here</devdito_relationship>
  <contained_services>
    <service name="mlflow-server">
      <image>ghcr.io/mlflow/mlflow:latest</image>
      <port>5000:5000</port>
      <purpose>ML experiment tracking and model registry</purpose>
      <status>PLANNED</status>
    </service>
    <service name="ragas-evaluator">
      <image>custom</image>
      <port>5001:5001</port>
      <purpose>RAG evaluation metrics (faithfulness, relevancy, context precision)</purpose>
      <status>PLANNED</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:5000/health</health_endpoint>
</stack>

<stack id="stack-f-observability">
  <stack_name>observability-services</stack_name>
  <stack_description>Monitoring, logging, and metrics collection for the entire stack ecosystem.</stack_description>
  <requirement_level>OPTIONAL</requirement_level>
  <devdito_relationship>USES - Dev Dito exports metrics for monitoring</devdito_relationship>
  <contained_services>
    <service name="prometheus">
      <image>prom/prometheus:latest</image>
      <port>9090:9090</port>
      <purpose>Metrics collection and alerting</purpose>
      <status>PLANNED</status>
    </service>
    <service name="grafana">
      <image>grafana/grafana:latest</image>
      <port>3001:3000</port>
      <purpose>Metrics visualization and dashboards</purpose>
      <status>PLANNED</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:9090/-/healthy</health_endpoint>
</stack>

<stack id="stack-g-devdito">
  <stack_name>extension-dev-dito-services</stack_name>
  <stack_description>
    THIS PROJECT - Dev Dito Pipeline Manager for DokuWiki.
    
    Dev Dito is a DokuWiki extension that provides RAG-powered semantic search over wiki content.
    It fetches wiki pages, evaluates content quality, preprocesses for RAG, creates embeddings,
    and deploys to vector databases for semantic search.
    
    The stack includes:
    - Core Services: DokuWiki with plugin, Orchestrator API, local Qdrant
    - Pipeline Modules: On-demand containers for each processing stage
    - DokuWiki Plugin: Admin UI for pipeline control and monitoring
  </stack_description>
  <requirement_level>CORE - This is the main installation target</requirement_level>
  <devdito_relationship>THIS IS DEV DITO</devdito_relationship>
  
  <service_categories>
    
    <category name="Core Services" description="Always-running services that form the backbone of Dev Dito">
      
      <service name="dev-dito-qdrant" container_name="dev-dito-qdrant">
        <image>qdrant/qdrant:v1.13.2</image>
        <port>6334:6333</port>
        <port>6335:6334</port>
        <purpose>Local vector database for Dev Dito pipeline. Independent from stack-d-ai-core for isolated development and testing.</purpose>
        <status>ACTIVE</status>
        <restart_policy>unless-stopped</restart_policy>
        <volumes>
          <volume>dev-dito-qdrant-storage:/qdrant/storage</volume>
        </volumes>
        <healthcheck>
          <test>curl -f http://localhost:6333/health</test>
          <interval>30s</interval>
          <timeout>10s</timeout>
          <retries>3</retries>
        </healthcheck>
        <environment>
          <var name="QDRANT__SERVICE__GRPC_PORT">6334</var>
        </environment>
      </service>
      
      <service name="dev-dito-orchestrator" container_name="dev-dito-orchestrator">
        <image>stack-g-devdito-orchestrator (built from ./orchestrator)</image>
        <port>8089:8089</port>
        <purpose>
          Pipeline Orchestrator API - Central control plane for all Dev Dito operations.
          Manages pipeline execution, job scheduling, status tracking, and provides
          REST API for DokuWiki plugin communication.
        </purpose>
        <status>ACTIVE</status>
        <restart_policy>unless-stopped</restart_policy>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
          <volume>/var/run/docker.sock:/var/run/docker.sock:ro</volume>
        </volumes>
        <healthcheck>
          <test>curl -f http://localhost:8089/health</test>
          <interval>30s</interval>
          <timeout>10s</timeout>
          <retries>3</retries>
        </healthcheck>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="DOCKER_HOST">unix:///var/run/docker.sock</var>
        </environment>
        <api_endpoints>
          <endpoint method="GET" path="/health">Health check</endpoint>
          <endpoint method="GET" path="/status">Get all pipeline stage statuses</endpoint>
          <endpoint method="POST" path="/run/{stage}">Start pipeline stage (fetch|evaluate|preprocess|embed|deploy)</endpoint>
          <endpoint method="GET" path="/job/{job_id}">Get specific job status</endpoint>
          <endpoint method="GET" path="/progress">Get current job progress (live updates)</endpoint>
          <endpoint method="GET" path="/progress/{job_id}">Get progress for specific job</endpoint>
          <endpoint method="POST" path="/cancel/{job_id}">Cancel running job</endpoint>
        </api_endpoints>
      </service>
      
    </category>
    
    <category name="Pipeline Modules" description="On-demand containers started by orchestrator for specific pipeline stages. Profile: pipeline">
      
      <service name="dev-dito-module-fetcher" container_name="dev-dito-module-fetcher">
        <image>stack-g-devdito-module-fetcher (built from ./module_fetcher)</image>
        <port>none</port>
        <profile>pipeline</profile>
        <purpose>
          Stage 01: Wiki Fetcher
          Fetches content from DokuWiki instances via JSON-RPC API.
          Supports full fetch and incremental updates using manifest tracking.
          Handles authentication, SSL certificates, and rate limiting.
        </purpose>
        <status>ACTIVE</status>
        <pipeline_stage>fetch</pipeline_stage>
        <source_code>pipeline/01_wiki_fetcher/</source_code>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
          <volume>../pipeline/01_wiki_fetcher:/pipeline/01_wiki_fetcher:ro</volume>
          <volume>../config.py:/app/config.py:ro</volume>
        </volumes>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="PIPELINE_PATH">/pipeline/01_wiki_fetcher</var>
          <var name="OUTPUT_DIR">/data/fetched</var>
          <var name="TOKEN_PATH">/config/secrets/json_rpc_api.token</var>
          <var name="SSL_CERT_PATH">/config/secrets/ssl.cert</var>
          <var name="REQUESTS_CA_BUNDLE">/etc/ssl/certs/ca-certificates.crt</var>
          <var name="SSL_CERT_FILE">/etc/ssl/certs/ca-certificates.crt</var>
        </environment>
        <input>
          <source>DokuWiki JSON-RPC API</source>
          <credentials>config/secrets/json_rpc_api.token</credentials>
        </input>
        <output>
          <directory>data/fetched/fetched_at_{timestamp}/</directory>
          <files>
            <file>changes/ - Recent changes data</file>
            <file>media/ - Downloaded media files</file>
            <file>namespaces/ - Namespace structure</file>
            <file>page_backlinks/ - Backlink data per page</file>
            <file>page_content/ - Raw wiki syntax content</file>
            <file>page_html/ - Rendered HTML content</file>
            <file>page_links/ - Link data per page</file>
            <file>page_metadata/ - Page metadata (author, date, etc.)</file>
            <file>raw_json/ - Raw API responses</file>
            <file>fetch_manifest.json - Manifest for incremental updates</file>
          </files>
        </output>
        <capabilities>
          <capability>Full wiki fetch (all pages, all namespaces)</capability>
          <capability>Incremental fetch (only changed pages since last run)</capability>
          <capability>Media file caching and deduplication</capability>
          <capability>Progress tracking with resume capability</capability>
          <capability>Change detection and reporting</capability>
        </capabilities>
      </service>
      
      <service name="dev-dito-module-evaluator" container_name="dev-dito-module-evaluator">
        <image>stack-g-devdito-module-evaluator (built from ./module_evaluator)</image>
        <port>none</port>
        <profile>pipeline</profile>
        <purpose>
          Stage 02: Deep Evaluation
          Analyzes fetched wiki content for quality, RAG readiness, and cleanup strategies.
          Uses LLM for content classification and generates improvement recommendations.
        </purpose>
        <status>ACTIVE</status>
        <pipeline_stage>evaluate</pipeline_stage>
        <source_code>pipeline/02_deep_evaluation/</source_code>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
          <volume>../pipeline/02_deep_evaluation:/pipeline/02_deep_evaluation:ro</volume>
        </volumes>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="PIPELINE_PATH">/pipeline/02_deep_evaluation</var>
        </environment>
        <input>
          <directory>data/fetched/fetched_at_{timestamp}/</directory>
        </input>
        <output>
          <directory>data/evaluated/evaluation_fetched_at_{timestamp}/</directory>
          <files>
            <file>evaluation_report.json - Comprehensive evaluation results</file>
            <file>content_classifications.json - Page type classifications</file>
            <file>quality_scores.json - Quality metrics per page</file>
            <file>rag_readiness.json - RAG suitability assessment</file>
            <file>cleanup_strategies.json - Recommended improvements</file>
          </files>
        </output>
        <analyzers>
          <analyzer name="content_classifier">Classifies page content type (documentation, tutorial, reference, etc.)</analyzer>
          <analyzer name="document_deep_analyzer">Deep analysis of document structure and content</analyzer>
          <analyzer name="format_quality_analyzer">Evaluates formatting consistency and quality</analyzer>
          <analyzer name="media_deep_analyzer">Analyzes embedded media usage and quality</analyzer>
          <analyzer name="query_generator">Generates sample queries for RAG testing</analyzer>
          <analyzer name="rag_readiness_checker">Assesses suitability for RAG retrieval</analyzer>
          <analyzer name="temporal_analyzer">Analyzes content freshness and update patterns</analyzer>
          <analyzer name="wiki_deep_analyzer">Wiki-specific structural analysis</analyzer>
        </analyzers>
      </service>
      
      <service name="dev-dito-module-preprocessor" container_name="dev-dito-module-preprocessor">
        <image>stack-g-devdito-module-preprocessor (built from ./module_preprocessor)</image>
        <port>none</port>
        <profile>pipeline</profile>
        <purpose>
          Stage 03a: RAG Preprocessing
          Converts DokuWiki syntax to RAG-optimized Markdown with YAML frontmatter.
          Enriches content with metadata for improved retrieval.
        </purpose>
        <status>ACTIVE</status>
        <pipeline_stage>preprocess</pipeline_stage>
        <source_code>pipeline/03_rag_preprocessing/</source_code>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
          <volume>../pipeline/03_rag_preprocessing:/pipeline/03_rag_preprocessing:ro</volume>
        </volumes>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="PIPELINE_PATH">/pipeline/03_rag_preprocessing</var>
        </environment>
        <input>
          <directory>data/fetched/fetched_at_{timestamp}/</directory>
          <optional>data/evaluated/evaluation_fetched_at_{timestamp}/</optional>
        </input>
        <output>
          <directory>data/preprocessed/preprocess_at_{timestamp}/</directory>
          <files>
            <file>*.md - Converted Markdown files with YAML frontmatter</file>
            <file>preprocessing_manifest.json - Processing manifest</file>
            <file>metadata_index.json - Aggregated metadata for all pages</file>
          </files>
        </output>
        <transformations>
          <transformation>Wiki syntax to Markdown conversion</transformation>
          <transformation>YAML frontmatter generation (title, namespace, author, date, tags)</transformation>
          <transformation>Internal link resolution and normalization</transformation>
          <transformation>Code block language detection and annotation</transformation>
          <transformation>Table format normalization</transformation>
          <transformation>Metadata enrichment from evaluation results</transformation>
        </transformations>
      </service>
      
      <service name="dev-dito-module-embedder" container_name="dev-dito-module-embedder">
        <image>stack-g-devdito-module-embedder (built from ./module_embedder)</image>
        <port>none</port>
        <profile>pipeline</profile>
        <purpose>
          Stage 03b: Embeddings Creator
          Creates vector embeddings using OpenAI text-embedding-3-large model.
          Implements content-aware chunking for optimal retrieval.
        </purpose>
        <status>ACTIVE</status>
        <pipeline_stage>embed</pipeline_stage>
        <source_code>pipeline/03_embeddings_creator/</source_code>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
          <volume>../pipeline/03_embeddings_creator:/pipeline/03_embeddings_creator:ro</volume>
        </volumes>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="PIPELINE_PATH">/pipeline/03_embeddings_creator</var>
          <var name="OPENAI_API_KEY">${OPENAI_API_KEY}</var>
        </environment>
        <input>
          <directory>data/preprocessed/preprocess_at_{timestamp}/</directory>
        </input>
        <output>
          <directory>data/embeddings/</directory>
          <files>
            <file>embeddings_{timestamp}.json - Generated embeddings with metadata</file>
            <file>chunks_{timestamp}.json - Document chunks with text</file>
            <file>embedding_manifest.json - Processing manifest</file>
          </files>
        </output>
        <embedding_config>
          <model>text-embedding-3-large</model>
          <dimensions>3072</dimensions>
          <chunking_strategy>content-aware</chunking_strategy>
          <chunk_size>512 tokens (configurable)</chunk_size>
          <chunk_overlap>50 tokens (configurable)</chunk_overlap>
        </embedding_config>
        <components>
          <component name="content_aware_chunker">Intelligent document chunking based on content structure</component>
          <component name="document_loader">Loads preprocessed Markdown documents</component>
          <component name="embedder">OpenAI API integration for embedding generation</component>
          <component name="pipeline">Orchestrates the embedding workflow</component>
        </components>
      </service>
      
      <service name="dev-dito-module-deployer" container_name="dev-dito-module-deployer">
        <image>stack-g-devdito-module-deployer (built from ./module_deployer)</image>
        <port>none</port>
        <profile>pipeline</profile>
        <purpose>
          Stage 04: Qdrant Deployer
          Uploads embeddings to Qdrant vector database.
          Supports multiple deployment targets (local dev-dito-qdrant, stack-d-ai-core, remote).
        </purpose>
        <status>ACTIVE</status>
        <pipeline_stage>deploy</pipeline_stage>
        <source_code>pipeline/04_deploy/</source_code>
        <depends_on>
          <service>dev-dito-qdrant</service>
        </depends_on>
        <volumes>
          <volume>../config:/config:ro</volume>
          <volume>../data:/data</volume>
        </volumes>
        <environment>
          <var name="CONFIG_PATH">/config/env.yaml</var>
          <var name="DATA_PATH">/data</var>
          <var name="QDRANT_HOST">dev-dito-qdrant (default, configurable)</var>
          <var name="QDRANT_PORT">6333</var>
          <var name="COLLECTION_NAME">wiki_embeddings</var>
        </environment>
        <input>
          <directory>data/embeddings/</directory>
        </input>
        <output>
          <target>Qdrant collection: wiki_embeddings</target>
        </output>
        <deployment_targets>
          <target name="local" default="true">
            <host>dev-dito-qdrant</host>
            <port>6333</port>
            <description>Local Qdrant in Stack-G for isolated development</description>
          </target>
          <target name="shared">
            <host>qdrant-main-vector-db</host>
            <port>6333</port>
            <description>Shared Qdrant in Stack-D for production use</description>
          </target>
          <target name="remote">
            <host>configurable (e.g., raspberry-pi)</host>
            <port>6333</port>
            <description>Remote Qdrant instance for deployment</description>
          </target>
        </deployment_targets>
        <capabilities>
          <capability>Collection creation and schema management</capability>
          <capability>Batch upsert with progress tracking</capability>
          <capability>Incremental updates (update changed, add new, optionally remove deleted)</capability>
          <capability>Transfer verification</capability>
        </capabilities>
      </service>
      
    </category>
    
    <category name="DokuWiki Plugin" description="PHP plugin installed in DokuWiki instance">
      
      <component name="devdito-plugin" install_path="lib/plugins/devdito/">
        <purpose>
          DokuWiki Admin Extension providing web UI for Dev Dito pipeline management.
          Communicates with orchestrator via HTTP API.
        </purpose>
        <status>ACTIVE</status>
        <source_code>dokuwiki_plugin/</source_code>
        <files>
          <file name="action.php">Event hooks and AJAX handlers</file>
          <file name="admin.php">Admin page controller</file>
          <file name="plugin.info.txt">Plugin metadata</file>
          <file name="conf/default.php">Default configuration</file>
          <file name="conf/metadata.php">Configuration schema</file>
          <file name="lib/ConfigLoader.php">Configuration management</file>
          <file name="lib/JobStatusManager.php">Pipeline job status tracking</file>
          <file name="lib/PipelineOrchestrator.php">Orchestrator API client</file>
          <file name="dist/devdito.min.css">Compiled styles</file>
          <file name="dist/devdito.min.js">Compiled JavaScript</file>
          <file name="dist/pipeline.css">Pipeline UI styles</file>
          <file name="dist/pipeline.js">Pipeline UI logic</file>
          <file name="lang/de/lang.php">German translations</file>
          <file name="lang/de/settings.php">German settings labels</file>
          <file name="lang/en/lang.php">English translations</file>
          <file name="lang/en/settings.php">English settings labels</file>
        </files>
        <admin_pages>
          <page url="?do=admin&amp;page=devdito">Main Dev Dito Dashboard</page>
        </admin_pages>
        <features>
          <feature>Pipeline stage visualization and control</feature>
          <feature>Real-time job progress monitoring</feature>
          <feature>Service status dashboard</feature>
          <feature>Configuration management UI</feature>
          <feature>Log viewer and download</feature>
        </features>
      </component>
      
    </category>
    
  </service_categories>
  
  <health_endpoint>http://localhost:8089/health</health_endpoint>
  
  <api_summary>
    <orchestrator_api base_url="http://localhost:8089">
      <endpoint method="GET" path="/health">Health check - returns {status: "ok"}</endpoint>
      <endpoint method="GET" path="/status">Pipeline status - all stages with last run info</endpoint>
      <endpoint method="POST" path="/run/fetch">Start wiki fetch (full or incremental)</endpoint>
      <endpoint method="POST" path="/run/evaluate">Start content evaluation</endpoint>
      <endpoint method="POST" path="/run/preprocess">Start RAG preprocessing</endpoint>
      <endpoint method="POST" path="/run/embed">Start embedding generation</endpoint>
      <endpoint method="POST" path="/run/deploy">Start Qdrant deployment</endpoint>
      <endpoint method="GET" path="/job/{job_id}">Get job status by ID</endpoint>
      <endpoint method="GET" path="/progress">Current job progress (live)</endpoint>
      <endpoint method="POST" path="/cancel/{job_id}">Cancel running job</endpoint>
    </orchestrator_api>
    <dokuwiki_admin base_url="http://localhost:8080">
      <endpoint method="GET" path="/?do=admin&amp;page=devdito">Dev Dito Admin Dashboard</endpoint>
    </dokuwiki_admin>
  </api_summary>
  
  <volumes>
    <volume name="dev-dito-qdrant-storage">Persistent Qdrant data</volume>
  </volumes>
  
  <data_directories>
    <directory path="data/fetched/">Fetched wiki content (timestamped subdirs)</directory>
    <directory path="data/evaluated/">Evaluation results (timestamped subdirs)</directory>
    <directory path="data/preprocessed/">Preprocessed Markdown (timestamped subdirs)</directory>
    <directory path="data/embeddings/">Generated embeddings</directory>
    <directory path="data/logs/">Pipeline logs and status files</directory>
  </data_directories>
  
</stack>

<stack id="stack-h-mcp">
  <stack_name>mcp-servers-services</stack_name>
  <stack_description>
    Model Context Protocol (MCP) servers providing AI-accessible tools.
    Dev Dito contributes the semantic-search-wiki-core tool for semantic wiki search.
    Other projects can add additional MCP servers to this stack.
  </stack_description>
  <requirement_level>RECOMMENDED</requirement_level>
  <devdito_relationship>PROVIDES - Dev Dito contributes the semantic search MCP server</devdito_relationship>
  
  <contained_services>
    
    <service name="semantic-search-wiki-core" container_name="semantic-search-wiki-core">
      <image>stack-h-mcp-semantic-search-wiki-core (built from backend_services/wiki_dev_mcp_server/)</image>
      <port>3000:3000</port>
      <purpose>
        MCP server providing semantic wiki search tools for AI assistants.
        Implements JSON-RPC 2.0 protocol compatible with Leonidas MCPToolProxy.
        Queries Qdrant vector database for semantic similarity search.
      </purpose>
      <status>ACTIVE</status>
      <source_code>backend_services/wiki_dev_mcp_server/</source_code>
      <environment>
        <var name="QDRANT_HOST">qdrant_db (or dev-dito-qdrant, or qdrant-main-vector-db)</var>
        <var name="QDRANT_PORT">6333</var>
        <var name="COLLECTION_NAME">wiki_embeddings</var>
        <var name="OPENAI_API_KEY">${OPENAI_API_KEY}</var>
        <var name="MCP_SERVER_PORT">3000</var>
      </environment>
      <embedding_config>
        <model>text-embedding-3-large</model>
        <dimensions>3072</dimensions>
      </embedding_config>
    </service>
    
  </contained_services>
  
  <health_endpoint>http://localhost:3000/health</health_endpoint>
  
  <mcp_protocol>
    <transport>HTTP/JSON-RPC 2.0</transport>
    <endpoints>
      <endpoint method="POST" path="/">JSON-RPC endpoint</endpoint>
      <endpoint method="POST" path="/mcp">Alternative JSON-RPC endpoint</endpoint>
      <endpoint method="GET" path="/">Server info</endpoint>
      <endpoint method="GET" path="/health">Health check</endpoint>
    </endpoints>
    <methods>
      <method name="tools/list">List available MCP tools</method>
      <method name="tools/call">Execute an MCP tool</method>
      <method name="ping">Connection check (returns {ok: true})</method>
    </methods>
  </mcp_protocol>
  
  <mcp_tools>
    <tool name="semantic_wiki_search">
      <description>Semantische Suche im HTL Leonding Wiki (LeoWiki). Durchsucht Wiki-Inhalte basierend auf semantischer Aehnlichkeit.</description>
      <input_schema>
        <property name="query" type="string" required="true">Die Suchanfrage in natuerlicher Sprache</property>
        <property name="top_k" type="integer" default="5" min="1" max="20">Anzahl der zurueckzugebenden Ergebnisse</property>
        <property name="namespace_filter" type="string" required="false">Optional: Filter nach Wiki-Namespace</property>
      </input_schema>
      <output>Markdown-formatted search results with scores, titles, namespaces, and content snippets</output>
    </tool>
    <tool name="faceted_search">
      <description>Facettensuche im HTL Wiki. Verwende dieses Tool ZUERST bei JEDER Frage ueber HTL Lehrer, Kurse, Raeume, Stundenplaene oder Events.</description>
      <input_schema>
        <property name="query" type="string" required="true">Die Suchanfrage (Frage des Benutzers)</property>
        <property name="limit" type="integer" default="5">Maximale Anzahl der Ergebnisse</property>
      </input_schema>
      <output>Markdown-formatted search results optimized for LLM consumption</output>
    </tool>
  </mcp_tools>
  
</stack>

<stack id="stack-i-leonidas">
  <stack_name>extension-leonidas-services</stack_name>
  <stack_description>Leonidas AI Chat Frontend - consumes Dev Dito's semantic search capabilities to provide conversational wiki access. External project that integrates with Dev Dito via MCP.</stack_description>
  <requirement_level>OPTIONAL</requirement_level>
  <devdito_relationship>CONSUMER - Leonidas uses Dev Dito's MCP tools for semantic wiki search</devdito_relationship>
  <contained_services>
    <service name="leonidas-core">
      <image>custom (external project)</image>
      <port>8082:80</port>
      <purpose>AI-powered chat interface for wiki Q&amp;A using RAG</purpose>
      <status>EXTERNAL PROJECT</status>
    </service>
  </contained_services>
  <health_endpoint>http://localhost:8082/health</health_endpoint>
  <integration_points>
    <integration>Calls semantic-search-wiki-core MCP server via JSON-RPC</integration>
    <integration>Uses wiki_embeddings collection in Qdrant</integration>
  </integration_points>
</stack>

</stack_list>

### Stack Dependency Matrix

| Stack                   | Depends On       | Provides To                  | Requirement  |
| ----------------------- | ---------------- | ---------------------------- | ------------ |
| Stack-A (wiki-sandbox)  | -                | Stack-G (test target)        | OPTIONAL     |
| Stack-B (wiki-core)     | -                | Stack-G (auth)               | RECOMMENDED  |
| Stack-C (extensions)    | Stack-B          | -                            | OPTIONAL     |
| Stack-D (ai-core)       | -                | Stack-G, Stack-H (vector DB) | **REQUIRED** |
| Stack-E (ai-eval)       | Stack-D          | Stack-G (metrics)            | OPTIONAL     |
| Stack-F (observability) | -                | All stacks (monitoring)      | OPTIONAL     |
| Stack-G (dev-dito)      | Stack-D          | Stack-H (MCP tools)          | **CORE**     |
| Stack-H (mcp)           | Stack-D, Stack-G | Stack-I (AI tools)           | RECOMMENDED  |
| Stack-I (leonidas)      | Stack-H          | End users                    | OPTIONAL     |

### Network Configuration

All stacks communicate over a shared external Docker network:

```yaml
# Required in every docker-compose.yml
networks:
  leonidas-network:
    external: true

# Create once before any stack starts:
# docker network create --driver bridge --attachable leonidas-network
```

### Port Allocation Map

| Port | Stack   | Service                   | Protocol  |
| ---- | ------- | ------------------------- | --------- |
| 3000 | Stack-H | semantic-search-wiki-core | HTTP/MCP  |
| 5000 | Stack-E | mlflow-server             | HTTP      |
| 6333 | Stack-D | qdrant-main-vector-db     | HTTP/gRPC |
| 6334 | Stack-D | qdrant-main-vector-db     | gRPC      |
| 8080 | Stack-G | dev-dito-wiki             | HTTP      |
| 8081 | Stack-B | keycloak-server           | HTTP      |
| 8089 | Stack-G | dev-dito-orchestrator     | HTTP      |
| 8090 | Stack-A | wiki-sandbox              | HTTP      |
| 9090 | Stack-F | prometheus                | HTTP      |





---

## User Stories

### US-001: Easy Installation of Dev Dito (as Dev Dito Developer)

As Dev Dito Developer I want to easily install Dev Dito on my local machine so that I can start developing and testing Dev Dito.
I want to do this by cloning the latest - master branch (or release tag) repository - state and running the install script.

```powershell
git clone https://github.com/IxI-Enki/{{UPDATEN BITTE}}
cd {{UPDATEN BITTE}}
python install_dev.py -PathToWikiInstance <PATH_TO_WIKI_INSTANCE>  {{-FLAGS-TBD!}}

# Wanted FLAGS: (use: -FLAGNAME FLAGVALUE | [VALUE1,VALUE2,VALUE3,..] )
# Per default used flags:
#
- FindPathToWikiInstance | -fpi | --find-path-to-wiki <TRUE|FALSE>  # Per default TRUE, if TRUE, the install script will try to find the wiki instance looking for running docker services and smartly look for a dokuwiki instance, not just by name, and simultaneously search for an eventually locally running/hosted dokuwiki instance, we look for that to know where to install our dev dito extension exactly
# if FALSE, search is skipped (might be faster), but for a working program Paths must be set manually instead:
# Optional, per default unused flags:
-PathToWikiInstance | -ptw | --path-to-wiki <PATH_TO_WIKI_INSTANCE>  # e.g. -PathToWikiInstance "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki", -ptw "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki"
-PathToDevConfig  | -ptc | --path-to-config <PATH_TO_DEV_CONFIG>        # e.g. -PathToDevConfig "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki\config", -ptc "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki\config"

-Help | -h | --help       # Show help message, example usage, easy to complex examples, colorful, helpful and exit

-Force | -f | --force     # Force the installation, skip all confirmations and assumptions, use with care - Skips choices for defaults
-NoOutput | -q | --quiet  # for use in CLI pipelines, skips all output and progress indicators, only shows errors and warnings
-UpdateExisting | -u | --update-existing  # Update the existing Dev Dito installation, if it exists. Keep fetched, embedded data. Ensure Cached data gets resetted (specially during development)
```

The install script will:
- Check if Python and Docker are installed and running
  - If not installed: offer to install them right away or provide links for manual install or install-cancelation and exit
  - If not running: start Docker Desktop and wait for it to be ready

- Docker and Python are installed and running:
  - Check if the network `htl-wiki-network` exists
    - If not: create the network
    - If already exists: check connected containers and services
  
  - Check existing Docker Stacks related to Dev Dito
    - Check if the stack `stack-a-wiki-sandbox` exists
    - Check if the stack `stack-b-wiki-core` exists
    - Check if the stack `stack-d-ai-core` exists
    - Check if the stack `stack-g-devdito` exists
    - Check if the stack `stack-h-mcp` exists

  - Migrate existing, important data from all existing stacks into a temporary backup directory, so that we can restore them after we have updated/reinstalled Dev Dito Extension into the DokuWiki instance(s)
    - Backup data
    - Delete Extension from DokuWiki
    - Deploy latest Dev Dito Extension into the DokuWiki instance(s)
    - Restore data

  - Check for other DokuWiki instances running outside of the Docker Stacks and offer to install Dev Dito into them - user must accept (y/n)

  - Build Docker Images for stack-g-devdito
    - Build orchestrator image
    - Build module images (fetcher, evaluator, preprocessor, embedder, deployer)
    - Use `docker compose -p stack-g-devdito build`

  - Start stack-g-devdito Services
    - Start dev-dito-wiki (DokuWiki instance)
    - Start dev-dito-orchestrator (Pipeline API)
    - Connect to external services:
      - stack-d-ai-core (Qdrant vector DB on port 6333)
      - stack-h-mcp (semantic-search-wiki-core on port 3000)
    - Use `docker compose -p stack-g-devdito up -d`

  - Deploy DokuWiki Plugin
    - Check if dev-dito-wiki container is running
    - Copy dokuwiki_plugin/ contents to container's lib/plugins/devdito/
    - Set correct permissions
    - Activate plugin in DokuWiki admin panel

  - Health Check
    - Verify orchestrator API responds on http://localhost:8089/health
    - Verify DokuWiki accessible on http://localhost:8080
    - List all running Dev Dito containers with status
    - Check connectivity to dependent stacks (Qdrant, MCP)

  - Configuration Verification
    - Validate config/env.yaml exists and is parseable
    - Check config/sources.yaml for wiki sources
    - Verify secrets directory has required tokens (config/secrets/)

  - Display Success Summary
    - Show URLs for DokuWiki, Admin Panel, Orchestrator API
    - Provide useful docker compose commands for management
    - Log installation completion to data/logs/
  
Note:
- Destructive actions are only performed if user accepts (y/n)
- Log actions and progress
- Errortolerant and user friendly
- Graceful handling of errors and warnings

---

Current Structure of the Dev Dito Repository Files (except .directory files):

```tree
dev_dito/
├── backend_services/
│   ├── embeddings/
│   ├── module_deployer/
│   ├── module_embedder/
│   ├── module_evaluator/
│   ├── module_fetcher/
│   ├── module_preprocessor/
│   ├── orchestartor/
│   ├── qdrant_db/
│   ├── wiki_dev_mcp_server/
│   ├── Dockerfile.module.template
│   └── docker-compose.yml
│
├── config/
│   ├── env.yaml
│   ├── secrets/
│   │   ├── json_rpc_api.token
│   │   ├── ssl.cert
│   │   └── README.md
│   ├── env.development.yaml
│   ├── env.minimal.yaml
│   ├── PLACEHOLDER_env.yaml
│   ├── env.yaml
│   └── sources.yaml
│
├── data/
│   ├── fetched/
│   │   └── fetched_at_{{TIMESTAMP}}/   # YYYYMMDD_HHMMSS format, e.g. fetched_at_20260201_120240
│   │   |   ├── changes/
│   │   |   ├── media/
│   │   |   ├── namespaces/
│   │   |   ├── page_backlinks/
│   │   |   ├── page_content/
│   │   |   ├── page_html/
│   │   |   ├── page_links/
│   │   |   ├── page_metadata/
│   │   |   └── raw_json/
│   │   └ {{NEXT_FETCHES}}
│   │
│   ├── evaluated/
│   │   ├── evaluation_fetched_at_{{TIMESTAMP}}/   # YYYYMMDD_HHMMSS format, e.g. evaluation_fetched_at_20260201_120240
│   │   ├── preprocessing_eval_{{TIMESTAMP}}/      # YYYYMMDD_HHMMSS format, e.g. preprocessing_eval_20260201_120240
│   │   └── {{NEXT_EVALUATIONS}}
│   │
│   ├── embeddings/
│   │   └── gitkeep  # {{TBD}}
│   │
│   ├── preprocessed/
│   │   ├── preprocess_at_{{TIMESTAMP}}/   # YYYYMMDD_HHMMSS format, e.g. preprocess_at_20260201_194727
│   │   └── {{NEXT_PREPROCESSED}}
│   │
│   └── logs/
│       ├── embedding_process.log
│       ├── fetch_run.log
│       ├── pipeline_progress.json
│       ├── pipeline_runs.json
│       └── pipeline_runs.schema.json
│
├── dokuwiki_plugin/
│   ├── conf/
│   │   ├── default.php
│   │   └── metadata.php
│   ├── dist/
│   │   ├── devdito.min.css
│   │   ├── devdito.min.js
│   │   ├── pipeline.css
│   │   └── pipeline.js
│   ├── lang/
│   │   ├── de/
│   │   └── en/
│   │       └── lang.php
│   ├── lib/
│   │   ├── ConfigLoader.php
│   │   ├── JobStatusManager.php
│   │   └── PipelineOrchestrator.php
│   │
│   ├── action.php
│   ├── admin.php
│   ├── plugin.info.txt
│   ├── logo.png
│   └── conf/
│       └── default.php
│
├── pipeline/
│   ├── 01_wiki_fetcher/
│   │   ├── config/
│   │   │   ├── json_rpc_api.token
│   │   │   ├── ssl.cert
│   │   │   ├── env.yaml
│   │   │   ├── PLACEHOLDER_api.token
│   │   │   ├── PLACEHOLDER_ssl.cert
│   │   │   └── PLACEHOLDER_env.yaml
│   │   ├── fetch_full_wiki_extended.py
│   │   ├── incremental_fetcher.py
│   │   ├── api_client.py
│   │   ├── change_detector.py
│   │   ├── change_report.py
│   │   ├── config.py
│   │   ├── extract_links_from_html.py
│   │   ├── manifest.py
│   │   ├── media_cache.py
│   │   ├── progress_tracker.py
│   │   ├── resume_fetch.py
│   │   ├── README.md
│   │   └── requirements.txt
│   │
│   ├── 02_deep_evaluation/
│   │   ├── core/
│   │   │   ├── file_handler.py
│   │   │   └── llm_client.py
│   │   ├── analyzers/
│   │   │   ├── __init__.py
│   │   │   ├── content_classifier.py
│   │   │   ├── document_deep_analyzer.py
│   │   │   ├── format_quality_analyzer.py
│   │   │   ├── media_deep_analyzer.py
│   │   │   ├── query_generator.py
│   │   │   ├── format_quality_analyzer.py
│   │   │   ├── rag_readiness_checker.py
│   │   │   ├── temporal_analyzer.py
│   │   │   └── wiki_deep_analyzer.py
│   │   ├── generators/
│   │   │   └── strategy_generator.py
│   │   ├── check_models.py
│   │   ├── cleanup_strategies.py
│   │   ├── config.py
│   │   ├── env.yaml
│   │   ├── evaluator.py
│   │   ├── report_generator.py
│   │   ├── run_deep_evaluation.py
│   │   ├── run_evaluation.py
│   │   └── run_strategy_generation.py
│   │
│   ├── 03_embeddings_creator/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── content_aware_chunker.py
│   │   ├── document_loader.py
│   │   ├── embedder.py
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   └── requirements.txt
│   │
│   ├── 03_rag_preprocessing/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── env.yaml
│   │   ├── main.py
│   │   ├── metadata_enricher.py
│   │   ├── page_processor.py
│   │   └── requirements.txt
│   │
│   ├── 03b_preprocessing_eval/
│   │   ├── __init__.py
│   │   └── evaluator.py
│   │
│   └── 04_deploy/
│       ├── config.yaml
│       ├── transfer_to_pi.py
│       └── verify_transfer.py
│
├── config/
│   ├── secrets/
│   │   ├── .gitkeep
│   │   └── README.md
│   ├── env.yaml
│   ├── env.development.yaml
│   ├── env.minimal.yaml
│   ├── PLACEHOLDER_env.yaml
│   └── sources.yaml
│
├── scripts/
│   ├── deploy-plugin.ps1
│   ├── docker_manager.ps1
│   ├── migration.ps1
│   ├── network_setup.ps1
│   └── README.md
│
├── backend_services/
│   ├── embeddings/
│   │   └── README.md
│   ├── module_deployer/
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── module_embedder/
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── module_evaluator/
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── module_fetcher/
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   ├── install_cert.sh
│   │   └── requirements.txt
│   ├── module_preprocessor/
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── orchestrator/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   ├── qdrant_db/
│   │   ├── Dockerfile
│   │   ├── init_collection.py
│   │   ├── README.md
│   │   └── requirements.txt
│   ├── wiki_dev_mcp_server/
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   └── server.py
│   ├── docker-compose.yml
│   ├── Dockerfile.module.template
│   └── README.md
│
├── config.py
├── install.ps1
├── Prompt.md
├── README.md
├── README_ARCHITECTURE.md
└── sources_dev_dito.yaml

```





### US-002: Easy Installation of Dev Dito (as Wiki Admin)

{{TBD}}

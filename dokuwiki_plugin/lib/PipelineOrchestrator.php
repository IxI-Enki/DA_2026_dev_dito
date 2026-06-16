<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * PipelineOrchestrator - Executes pipeline stages via HTTP Orchestrator API
 *
 * This class handles the execution of pipeline modules and status reporting.
 * PHP cannot directly run Docker commands (security restriction), so it calls
 * the HTTP Orchestrator service running on the host.
 *
 * Constitution Article I: No direct PHP→Python calls
 * Constitution Article VII: Thin wrappers only
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     Jan Ritt <j.ritt@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Lib
 */
class PipelineOrchestrator
{
    /** @var array Stage definitions (in execution order) */
    private const STAGES = [
        'fetch' => [
            'container' => 'dev-dito-module-fetcher',
            'name' => 'Wiki Fetcher',
            'description' => 'Fetcht Wiki-Inhalte via JSON-RPC API'
        ],
        'evaluate' => [
            'container' => 'dev-dito-module-evaluator',
            'name' => 'Fetch Evaluation',
            'description' => 'Qualitaetsbewertung der gefetchten Daten'
        ],
        'preprocess' => [
            'container' => 'dev-dito-module-preprocessor',
            'name' => 'RAG Preprocessing',
            'description' => 'Konvertiert Wiki-Syntax zu Markdown mit Frontmatter'
        ],
        'embed' => [
            'container' => 'dev-dito-module-embedder',
            'name' => 'Embeddings Creator',
            'description' => 'Generiert Embeddings via OpenAI/lokales Model'
        ],
        'deploy' => [
            'container' => 'dev-dito-module-deployer',
            'name' => 'Qdrant Deploy',
            'description' => 'Laedt Embeddings in Qdrant hoch'
        ]
    ];

    /** @var JobStatusManager */
    private JobStatusManager $statusManager;

    /** @var string Orchestrator API URL */
    private string $orchestratorUrl;

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->statusManager = new JobStatusManager();
        
        // Orchestrator URL: env (Docker same-network) overrides config (host dev)
        $this->orchestratorUrl = getenv('DEVDITO_ORCHESTRATOR_URL') ?: ConfigLoader::get(
            'PIPELINE_ORCHESTRATION.orchestrator.url',
            'http://host.docker.internal:18089'
        );
    }

    /**
     * Get status of all pipeline stages
     *
     * @return array Pipeline status for dashboard
     */
    public function getStatus(): array
    {
        // #region agent log
        $__dbg = function(string $msg, array $data = []): void { $f = '/config/dokuwiki/lib/plugins/devdito/debug_agent.log'; @file_put_contents($f, json_encode(['ts'=>date('c'),'msg'=>$msg,'data'=>$data])."\n", FILE_APPEND); };
        $__dbg('getStatus:enter', ['orchestratorUrl'=>$this->orchestratorUrl, 'envOrchUrl'=>getenv('DEVDITO_ORCHESTRATOR_URL')?:null, 'envQdrantHost'=>getenv('DEVDITO_QDRANT_HOST')?:null, 'envQdrantPort'=>getenv('DEVDITO_QDRANT_PORT')?:null]);
        // #endregion

        // Try to get status from Orchestrator API first
        $apiStatus = $this->callOrchestratorApi('GET', '/status');
        
        // #region agent log
        $__dbg('getStatus:apiStatus', ['isNull'=>$apiStatus===null, 'hasStages'=>isset($apiStatus['stages']), 'stageCount'=>isset($apiStatus['stages'])?count($apiStatus['stages']):0, 'firstStageStatus'=>$apiStatus['stages'][0]['status']??'N/A']);
        // #endregion

        if ($apiStatus && isset($apiStatus['stages'])) {
            // Orchestrator is running - use its status
            $apiStatus['orchestrator_status'] = 'running';
            $apiStatus['orchestrator_url'] = $this->orchestratorUrl;
            $apiStatus['qdrant_info'] = $this->getQdrantInfo();
            return $apiStatus;
        }
        
        // Check if manifest exists for incremental fetch
        $hasManifest = $this->checkManifestExists();
        
        // Fallback: Read status from local file
        $stages = [];
        foreach (self::STAGES as $id => $info) {
            $lastRun = $this->statusManager->getLastRun($id);

            $stageData = [
                'id' => $id,
                'name' => $info['name'],
                'description' => $info['description'],
                'status' => $lastRun['status'] ?? 'never_run',
                'last_run' => $lastRun['finished_at'] ?? $lastRun['started_at'] ?? null,
                'duration_seconds' => $lastRun['duration_seconds'] ?? null,
                'output_dir' => $lastRun['output_dir'] ?? null,
                'stats' => $lastRun['stats'] ?? null,
                'error' => $lastRun['error'] ?? null,
            ];
            
            // Add manifest info for fetch stage
            if ($id === 'fetch') {
                $stageData['has_manifest'] = $hasManifest;
            }
            
            $stages[] = $stageData;
        }

        return [
            'stages' => $stages,
            'active_job' => $this->statusManager->getActiveJob(),
            'qdrant_info' => $this->getQdrantInfo(),
            'orchestrator_status' => 'not_running',
            'orchestrator_url' => $this->orchestratorUrl,
        ];
    }

    /**
     * Start a pipeline stage via HTTP Orchestrator
     *
     * @param string $stage Stage ID (fetch, evaluate, embed, deploy)
     * @param array $options Optional parameters
     * @return array{success: bool, job_id: string, message: string}
     */
    public function runStage(string $stage, array $options = []): array
    {
        // Validate stage
        if (!isset(self::STAGES[$stage])) {
            return [
                'success' => false,
                'job_id' => '',
                'message' => "Unbekannte Pipeline-Stufe: $stage"
            ];
        }

        // Call Orchestrator API — forward options so mode:incremental reaches the container (FR-001)
        $result = $this->callOrchestratorApi('POST', "/run/$stage", ['options' => $options]);
        
        // #region agent log
        $__dbg = function(string $msg, array $data = []): void { $f = '/config/dokuwiki/lib/plugins/devdito/debug_agent.log'; @file_put_contents($f, json_encode(['ts'=>date('c'),'msg'=>$msg,'data'=>$data])."\n", FILE_APPEND); };
        $__dbg('runStage:result', ['stage'=>$stage, 'options'=>$options, 'resultIsNull'=>$result===null, 'result'=>$result, 'orchestratorUrl'=>$this->orchestratorUrl, 'sentBody'=>json_encode(['options'=>$options])]);
        // #endregion
        
        if ($result === null) {
            return [
                'success' => false,
                'job_id' => '',
                'message' => "Orchestrator nicht erreichbar ({$this->orchestratorUrl}). " .
                            "Starte ihn mit: python backend_services/orchestrator/server.py"
            ];
        }
        
        if (isset($result['success']) && $result['success']) {
            return [
                'success' => true,
                'job_id' => $result['job_id'] ?? '',
                'message' => $result['message'] ?? self::STAGES[$stage]['name'] . " gestartet"
            ];
        }
        
        // Error from API
        return [
            'success' => false,
            'job_id' => $result['job_id'] ?? '',
            'message' => $result['detail'] ?? $result['message'] ?? 'Unbekannter Fehler'
        ];
    }

    /**
     * Get job status by ID
     *
     * @param string $jobId Job identifier
     * @return array|null Job data or null if not found
     */
    public function getJobStatus(string $jobId): ?array
    {
        // Try API first
        $result = $this->callOrchestratorApi('GET', "/job/$jobId");
        if ($result !== null) {
            return $result;
        }
        
        // Fallback to local status file
        $this->statusManager->clearCache();
        return $this->statusManager->getJob($jobId);
    }

    /**
     * Get live progress for current/specific job
     *
     * @param string|null $jobId Optional job ID (null = current progress)
     * @return array Progress data
     */
    public function getProgress(?string $jobId = null): array
    {
        $endpoint = $jobId ? "/progress/$jobId" : "/progress";
        $result = $this->callOrchestratorApi('GET', $endpoint);
        
        if ($result === null) {
            return [
                'status' => 'orchestrator_offline',
                'message' => 'Orchestrator nicht erreichbar'
            ];
        }
        
        return $result;
    }

    /**
     * Cancel a running job
     *
     * @param string $jobId Job identifier
     * @return array{success: bool, message: string}
     */
    public function cancelJob(string $jobId): array
    {
        // Try to cancel via Orchestrator API
        $result = $this->callOrchestratorApi('POST', "/cancel/$jobId");
        
        if ($result !== null) {
            return $result;
        }
        
        // Fallback: Update status locally
        $this->statusManager->updateJobStatus($jobId, [
            'status' => 'cancelled',
            'finished_at' => date('c'),
            'error' => 'Manuell abgebrochen'
        ]);
        
        return [
            'success' => true,
            'message' => 'Job als abgebrochen markiert (Prozess laeuft evtl. noch)'
        ];
    }

    /**
     * Call the Orchestrator HTTP API
     *
     * @param string $method HTTP method (GET, POST)
     * @param string $endpoint API endpoint (e.g., /status, /run/fetch)
     * @param array|null $data POST data (optional)
     * @return array|null Response data or null on error
     */
    private function callOrchestratorApi(string $method, string $endpoint, ?array $data = null): ?array
    {
        $url = rtrim($this->orchestratorUrl, '/') . $endpoint;
        
        $context = stream_context_create([
            'http' => [
                'method' => $method,
                'header' => "Content-Type: application/json\r\n",
                'content' => $data ? json_encode($data) : '',
                'timeout' => 5,
                'ignore_errors' => true  // Get response even on 4xx/5xx
            ]
        ]);
        
        $response = @file_get_contents($url, false, $context);
        
        if ($response === false) {
            return null;  // Connection failed
        }
        
        $decoded = json_decode($response, true);
        return is_array($decoded) ? $decoded : null;
    }

    /**
     * Get Qdrant collection information
     *
     * @return array Qdrant status
     */
    private function getQdrantInfo(): array
    {
        $endpoint = ServiceTester::resolveQdrantEndpoint();
        $collection = ConfigLoader::get('SERVICES.qdrant.collection', 'wiki_embeddings');
        $url = 'http://' . $endpoint['host'] . ':' . $endpoint['port'] . '/collections/' . $collection;

        // #region agent log
        $__dbg = function(string $msg, array $data = []): void { $f = '/config/dokuwiki/lib/plugins/devdito/debug_agent.log'; @file_put_contents($f, json_encode(['ts'=>date('c'),'msg'=>$msg,'data'=>$data])."\n", FILE_APPEND); };
        $__dbg('getQdrantInfo', ['host'=>$endpoint['host'], 'port'=>$endpoint['port'], 'collection'=>$collection, 'url'=>$url]);
        // #endregion

        try {
            $context = stream_context_create([
                'http' => [
                    'timeout' => 5,
                    'ignore_errors' => true
                ]
            ]);

            $response = @file_get_contents($url, false, $context);

            if ($response === false) {
                return [
                    'connected' => false,
                    'collection' => $collection,
                    'error' => 'Qdrant nicht erreichbar'
                ];
            }

            $data = json_decode($response, true);

            if (isset($data['result'])) {
                return [
                    'connected' => true,
                    'collection' => $collection,
                    'vectors' => $data['result']['points_count'] ?? 0,
                    'dimension' => $data['result']['config']['params']['vectors']['size'] ?? 0,
                    'status' => $data['result']['status'] ?? 'unknown'
                ];
            }

            return [
                'connected' => false,
                'collection' => $collection,
                'error' => 'Collection nicht gefunden'
            ];

        } catch (\Exception $e) {
            return [
                'connected' => false,
                'collection' => $collection,
                'error' => $e->getMessage()
            ];
        }
    }

    /**
     * Check if a fetch manifest exists (for incremental fetch)
     *
     * @return bool True if manifest exists
     */
    private function checkManifestExists(): bool
    {
        // Get data directory from config
        $dataDir = ConfigLoader::get('PATHS.data_dir', '');
        
        if (empty($dataDir)) {
            return false;
        }
        
        // Normalize path for the OS
        $dataDir = str_replace(['/', '\\'], DIRECTORY_SEPARATOR, $dataDir);
        $fetchedDir = $dataDir . DIRECTORY_SEPARATOR . 'fetched';
        
        if (!is_dir($fetchedDir)) {
            return false;
        }
        
        // Scan for directories with fetch_manifest.json
        $dirs = @scandir($fetchedDir, SCANDIR_SORT_DESCENDING);
        if ($dirs === false) {
            return false;
        }
        
        foreach ($dirs as $dir) {
            if ($dir === '.' || $dir === '..') {
                continue;
            }
            
            // Check if this is a fetch directory with a manifest
            if (strpos($dir, 'fetched_at_') === 0) {
                $manifestPath = $fetchedDir . DIRECTORY_SEPARATOR . $dir . DIRECTORY_SEPARATOR . 'fetch_manifest.json';
                if (file_exists($manifestPath)) {
                    return true;
                }
            }
        }
        
        return false;
    }

    /**
     * Get available stages
     *
     * @return array Stage definitions
     */
    public static function getStages(): array
    {
        return self::STAGES;
    }
}

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
    /** @var array Stage definitions */
    private const STAGES = [
        'fetch' => [
            'container' => 'dev-dito-module-fetcher',
            'name' => 'Wiki Fetcher',
            'description' => 'Fetcht Wiki-Inhalte via JSON-RPC API'
        ],
        'evaluate' => [
            'container' => 'dev-dito-module-evaluator',
            'name' => 'Deep Evaluation',
            'description' => 'LLM-gestuetzte Inhaltsanalyse'
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
        
        // Get Orchestrator URL from config
        // Default uses host.docker.internal for Docker container → Host communication
        $this->orchestratorUrl = ConfigLoader::get(
            'PIPELINE_ORCHESTRATION.orchestrator.url',
            'http://host.docker.internal:8089'
        );
    }

    /**
     * Get status of all pipeline stages
     *
     * @return array Pipeline status for dashboard
     */
    public function getStatus(): array
    {
        // Try to get status from Orchestrator API first
        $apiStatus = $this->callOrchestratorApi('GET', '/status');
        
        if ($apiStatus && isset($apiStatus['stages'])) {
            // Orchestrator is running - use its status
            $apiStatus['orchestrator_status'] = 'running';
            $apiStatus['orchestrator_url'] = $this->orchestratorUrl;
            $apiStatus['qdrant_info'] = $this->getQdrantInfo();
            return $apiStatus;
        }
        
        // Fallback: Read status from local file
        $stages = [];
        foreach (self::STAGES as $id => $info) {
            $lastRun = $this->statusManager->getLastRun($id);

            $stages[] = [
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

        // Call Orchestrator API to run the stage
        $result = $this->callOrchestratorApi('POST', "/run/$stage");
        
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
        $qdrantHost = ConfigLoader::get('SERVICES.qdrant.host', 'qdrant_db');
        $qdrantPort = ConfigLoader::get('SERVICES.qdrant.port', 6333);
        $collection = ConfigLoader::get('SERVICES.qdrant.collection', 'wiki_embeddings');

        // For local Docker network, use localhost if running from outside Docker
        // In production, this would be the Docker network hostname
        $host = ($qdrantHost === 'qdrant_db') ? 'localhost' : $qdrantHost;
        $url = "http://$host:$qdrantPort/collections/$collection";

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
     * Get available stages
     *
     * @return array Stage definitions
     */
    public static function getStages(): array
    {
        return self::STAGES;
    }
}

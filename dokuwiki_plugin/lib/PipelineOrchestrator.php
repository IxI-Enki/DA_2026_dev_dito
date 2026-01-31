<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * PipelineOrchestrator - Executes pipeline stages via Docker
 *
 * This class handles the execution of pipeline modules and status reporting.
 * Constitution Article I: No direct PHP→Python calls (uses Docker exec)
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

    /** @var string Docker compose path */
    private string $dockerComposePath;

    /**
     * Constructor
     */
    public function __construct()
    {
        $this->statusManager = new JobStatusManager();
        
        // Get Docker compose path from config
        $configPath = ConfigLoader::get('PIPELINE_ORCHESTRATION.docker.compose_path');
        if ($configPath && is_dir($configPath)) {
            $this->dockerComposePath = $configPath;
        } else {
            // Fallback to relative path
            $pluginDir = dirname(__DIR__);
            $this->dockerComposePath = dirname($pluginDir) . '/backend_services';
        }
    }

    /**
     * Get status of all pipeline stages
     *
     * @return array Pipeline status for dashboard
     */
    public function getStatus(): array
    {
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
            'docker_compose_path' => $this->dockerComposePath,
        ];
    }

    /**
     * Start a pipeline stage
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

        // Check if another job is running
        if ($this->statusManager->hasActiveJob()) {
            $activeJob = $this->statusManager->getActiveJob();
            return [
                'success' => false,
                'job_id' => '',
                'message' => "Eine andere Pipeline laeuft bereits: " . ($activeJob['job_id'] ?? 'unknown')
            ];
        }

        // Check Docker availability
        if (!$this->isDockerAvailable()) {
            return [
                'success' => false,
                'job_id' => '',
                'message' => 'Docker ist nicht verfuegbar. Pruefe Docker Desktop.'
            ];
        }

        // Generate job ID
        $jobId = $stage . '_' . date('Ymd_His');
        $container = self::STAGES[$stage]['container'];

        // Build and execute Docker command
        $result = $this->executeDockerRun($container, $jobId, $options);

        if ($result['success']) {
            return [
                'success' => true,
                'job_id' => $jobId,
                'message' => self::STAGES[$stage]['name'] . " gestartet. Job-ID: $jobId"
            ];
        } else {
            return [
                'success' => false,
                'job_id' => $jobId,
                'message' => 'Fehler beim Starten: ' . ($result['error'] ?? 'Unbekannter Fehler')
            ];
        }
    }

    /**
     * Get job status by ID
     *
     * @param string $jobId Job identifier
     * @return array|null Job data or null if not found
     */
    public function getJobStatus(string $jobId): ?array
    {
        $this->statusManager->clearCache();
        return $this->statusManager->getJob($jobId);
    }

    /**
     * Check if Docker is available
     *
     * @return bool
     */
    private function isDockerAvailable(): bool
    {
        $output = [];
        $returnCode = 0;
        
        exec('docker --version 2>&1', $output, $returnCode);
        
        return $returnCode === 0;
    }

    /**
     * Execute Docker run command
     *
     * @param string $container Container name
     * @param string $jobId Job identifier
     * @param array $options Additional options
     * @return array{success: bool, error?: string}
     */
    private function executeDockerRun(string $container, string $jobId, array $options = []): array
    {
        // Build Docker compose command
        // Using --profile pipeline to start only pipeline services
        $composeFile = escapeshellarg($this->dockerComposePath . '/docker-compose.yml');
        $containerArg = escapeshellarg($container);
        $jobIdArg = escapeshellarg($jobId);

        // Command: docker compose -f <file> --profile pipeline run --rm -d <container> <job_id>
        // Note: -d runs detached (background)
        $cmd = "docker compose -f $composeFile --profile pipeline run --rm -d $containerArg $jobIdArg 2>&1";

        // Log the command (without sensitive data)
        error_log("[DevDito] Executing: docker compose run $container $jobId");

        // Execute
        $output = [];
        $returnCode = 0;
        exec($cmd, $output, $returnCode);

        $outputStr = implode("\n", $output);

        if ($returnCode !== 0) {
            error_log("[DevDito] Docker command failed: $outputStr");
            return [
                'success' => false,
                'error' => $outputStr
            ];
        }

        return ['success' => true];
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

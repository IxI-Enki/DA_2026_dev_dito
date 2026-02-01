<?php

declare(strict_types=1);

/**
 * Dev Dito Plugin - Service Gateway & Pipeline Manager
 *
 * This plugin provides administrative tools for managing the Wiki Embedding Pipeline
 * and monitoring connections to external services (MCP Server, Qdrant, etc.).
 *
 * NOTE: This plugin does NOT provide user-facing search UI.
 * Semantic search functionality is provided by the Leonidas extension.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito
 * @version    0.1.1
 */

use dokuwiki\Extension\ActionPlugin;
use dokuwiki\Extension\Event;
use dokuwiki\Extension\EventHandler;

// Load library classes (Constitution Article II-B)
require_once __DIR__ . '/lib/ConfigLoader.php';
require_once __DIR__ . '/lib/JobStatusManager.php';
require_once __DIR__ . '/lib/PipelineOrchestrator.php';

use dokuwiki\plugin\devdito\lib\ConfigLoader;
use dokuwiki\plugin\devdito\lib\JobStatusManager;
use dokuwiki\plugin\devdito\lib\PipelineOrchestrator;

if (!defined('DOKU_INC')) {
    die();
}

/**
 * Action Plugin for Dev Dito Service Gateway.
 *
 * This plugin provides:
 * - AJAX endpoints for admin dashboard service tests
 * - Background health checks for monitored services
 *
 * User-facing features (search panel, etc.) are NOT part of this plugin.
 * See the Leonidas extension for semantic search functionality.
 */
class action_plugin_devdito extends ActionPlugin
{
    /** @var string Current plugin version */
    private const VERSION = '0.1.1';

    /**
     * Register event handlers with the DokuWiki event system.
     *
     * @param EventHandler $controller The event handler controller
     * @return void
     */
    public function register(EventHandler $controller): void
    {
        // Only register AJAX handler for admin operations
        $controller->register_hook('AJAX_CALL_UNKNOWN', 'BEFORE', $this, 'handleAjax');
    }

    /**
     * Handle AJAX requests for admin operations.
     *
     * @param Event $event The AJAX_CALL_UNKNOWN event
     * @return void
     */
    public function handleAjax(Event $event): void
    {
        $action = $event->data;

        // Only handle devdito AJAX calls
        if (!str_starts_with($action, 'devdito_')) {
            return;
        }

        $event->preventDefault();
        $event->stopPropagation();

        header('Content-Type: application/json; charset=utf-8');

        // Pipeline endpoints (public read, admin write)
        if ($this->handlePipelineAjax($action)) {
            return;
        }

        // Admin-only endpoints
        if (!str_starts_with($action, 'devdito_admin_')) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'unknown_action'], 400);
            return;
        }

        // Check admin authorization for admin_ endpoints
        global $INFO;
        if (!isset($INFO['isadmin']) || !$INFO['isadmin']) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'unauthorized'], 401);
            return;
        }

        // Route to appropriate handler
        switch ($action) {
            case 'devdito_admin_test':
                $this->handleServiceTest();
                break;
            case 'devdito_admin_status':
                $this->handleStatusCheck();
                break;
            default:
                $this->sendJsonResponse(['ok' => false, 'error' => 'unknown_action'], 400);
        }
    }

    /**
     * Handle Pipeline AJAX endpoints.
     *
     * @param string $action AJAX action name
     * @return bool True if handled, false otherwise
     */
    private function handlePipelineAjax(string $action): bool
    {
        switch ($action) {
            case 'devdito_pipeline_status':
                $this->handlePipelineStatus();
                return true;

            case 'devdito_run_stage':
                $this->handleRunStage();
                return true;

            case 'devdito_job_status':
                $this->handleJobStatus();
                return true;

            case 'devdito_progress':
                $this->handleProgress();
                return true;

            case 'devdito_cancel_job':
                $this->handleCancelJob();
                return true;

            default:
                return false;
        }
    }

    /**
     * Handle pipeline status request.
     * Returns status of all pipeline stages.
     *
     * @return void
     */
    private function handlePipelineStatus(): void
    {
        $orchestrator = new PipelineOrchestrator();
        $status = $orchestrator->getStatus();
        $this->sendJsonResponse($status);
    }

    /**
     * Handle run stage request.
     * Starts a pipeline stage as background job.
     * Requires admin authorization.
     *
     * @return void
     */
    private function handleRunStage(): void
    {
        // Admin check - use auth_isadmin() for AJAX context
        if (!$this->isUserAdmin()) {
            $this->sendJsonResponse(['success' => false, 'message' => 'Admin-Berechtigung erforderlich'], 401);
            return;
        }

        // Get stage from POST body
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);

        if (!isset($data['stage'])) {
            $this->sendJsonResponse(['success' => false, 'message' => 'Stage parameter fehlt'], 400);
            return;
        }

        $stage = $data['stage'];
        $options = $data['options'] ?? [];

        $orchestrator = new PipelineOrchestrator();
        $result = $orchestrator->runStage($stage, $options);

        $this->sendJsonResponse($result);
    }

    /**
     * Handle job status request.
     * Returns status of a specific job.
     *
     * @return void
     */
    private function handleJobStatus(): void
    {
        global $INPUT;
        $jobId = $INPUT->str('job_id');

        if (empty($jobId)) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'job_id parameter fehlt'], 400);
            return;
        }

        $orchestrator = new PipelineOrchestrator();
        $job = $orchestrator->getJobStatus($jobId);

        if ($job === null) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'Job nicht gefunden'], 404);
            return;
        }

        $this->sendJsonResponse(['ok' => true, 'job' => $job]);
    }

    /**
     * Handle live progress request.
     * Returns real-time progress of current/specific job.
     *
     * @return void
     */
    private function handleProgress(): void
    {
        global $INPUT;
        $jobId = $INPUT->str('job_id', '');

        $orchestrator = new PipelineOrchestrator();
        $progress = $orchestrator->getProgress($jobId ?: null);

        $this->sendJsonResponse($progress);
    }

    /**
     * Handle cancel job request.
     * Cancels a running pipeline job.
     * Requires admin authorization.
     *
     * @return void
     */
    private function handleCancelJob(): void
    {
        // Admin check
        if (!$this->isUserAdmin()) {
            $this->sendJsonResponse(['success' => false, 'message' => 'Admin-Berechtigung erforderlich'], 401);
            return;
        }

        // Get job_id from POST body
        $input = file_get_contents('php://input');
        $data = json_decode($input, true) ?: [];
        $jobId = $data['job_id'] ?? '';

        if (empty($jobId)) {
            $this->sendJsonResponse(['success' => false, 'message' => 'job_id fehlt'], 400);
            return;
        }

        $orchestrator = new PipelineOrchestrator();
        $result = $orchestrator->cancelJob($jobId);

        $this->sendJsonResponse($result);
    }

    /**
     * Handle service connection test request.
     *
     * @return void
     */
    private function handleServiceTest(): void
    {
        global $INPUT;

        $service = $INPUT->str('service');

        switch ($service) {
            case 'mcp':
                $result = $this->testMcpServer();
                break;
            case 'qdrant':
                $result = $this->testQdrant();
                break;
            case 'config':
                $result = $this->testConfig();
                break;
            default:
                $result = ['ok' => false, 'message' => 'Unknown service: ' . $service];
        }

        $this->sendJsonResponse($result);
    }

    /**
     * Handle status check request (returns all service statuses).
     *
     * @return void
     */
    private function handleStatusCheck(): void
    {
        $this->sendJsonResponse([
            'ok' => true,
            'services' => [
                'mcp' => $this->testMcpServer(),
                'qdrant' => $this->testQdrant(),
                'config' => $this->testConfig(),
            ],
            'timestamp' => date('c'),
        ]);
    }

    /**
     * Test MCP server connection.
     *
     * @return array{ok: bool, message: string, latency_ms?: int}
     */
    private function testMcpServer(): array
    {
        $mcpUrl = $this->getMcpUrl();
        if (empty($mcpUrl)) {
            return ['ok' => false, 'message' => 'MCP URL not configured'];
        }

        $startTime = microtime(true);
        $timeout = $this->getMcpTimeout();

        $payload = json_encode([
            'jsonrpc' => '2.0',
            'id'      => 'devdito_admin_ping',
            'method'  => 'ping',
        ], JSON_THROW_ON_ERROR);

        $context = stream_context_create([
            'http' => [
                'timeout'       => $timeout,
                'ignore_errors' => true,
                'method'        => 'POST',
                'header'        => "Content-Type: application/json\r\n",
                'content'       => $payload,
            ],
        ]);

        $result = @file_get_contents(rtrim($mcpUrl, '/'), false, $context);
        $latencyMs = (int) ((microtime(true) - $startTime) * 1000);

        if ($result === false) {
            return [
                'ok'         => false,
                'message'    => 'Connection failed',
                'latency_ms' => $latencyMs,
            ];
        }

        $decoded = json_decode($result, true);
        $isOk = is_array($decoded) && isset($decoded['result']['ok']) && $decoded['result']['ok'] === true;

        return [
            'ok'         => $isOk,
            'message'    => $isOk ? 'Connected' : 'Invalid response',
            'latency_ms' => $latencyMs,
        ];
    }

    /**
     * Test Qdrant connection.
     *
     * @return array{ok: bool, message: string, latency_ms?: int}
     */
    private function testQdrant(): array
    {
        $qdrantHost = ConfigLoader::get('SERVICES.qdrant.host', 'qdrant_db');
        $qdrantPort = ConfigLoader::get('SERVICES.qdrant.port', 6333);
        $qdrantUrl = 'http://' . $qdrantHost . ':' . $qdrantPort . '/collections';

        $startTime = microtime(true);

        $context = stream_context_create([
            'http' => [
                'timeout'       => 5,
                'ignore_errors' => true,
                'method'        => 'GET',
            ],
        ]);

        $result = @file_get_contents($qdrantUrl, false, $context);
        $latencyMs = (int) ((microtime(true) - $startTime) * 1000);

        if ($result === false) {
            return [
                'ok'         => false,
                'message'    => 'Connection failed (expected from browser)',
                'latency_ms' => $latencyMs,
            ];
        }

        $decoded = json_decode($result, true);
        $isOk = is_array($decoded) && isset($decoded['result']);

        return [
            'ok'         => $isOk,
            'message'    => $isOk ? 'Connected' : 'Invalid response',
            'latency_ms' => $latencyMs,
        ];
    }

    /**
     * Test central configuration.
     *
     * @return array{ok: bool, message: string}
     */
    private function testConfig(): array
    {
        $isValid = ConfigLoader::isValid();
        $version = ConfigLoader::get('APP.version', 'unknown');

        return [
            'ok'      => $isValid,
            'message' => $isValid ? "Config valid (v$version)" : 'Config invalid or missing',
        ];
    }

    /**
     * Get the configured MCP server URL.
     *
     * @return string|null The URL or null if not configured
     */
    private function getMcpUrl(): ?string
    {
        // First try DokuWiki config (for admin overrides)
        $url = $this->getConf('devdito_mcp_url');
        if (!empty($url)) {
            return $url;
        }

        // Fallback to central config (Constitution Article II-B)
        $centralUrl = ConfigLoader::get('SERVICES.mcp_server.url');
        if (!empty($centralUrl)) {
            return $centralUrl;
        }

        return null;
    }

    /**
     * Get the configured MCP request timeout.
     *
     * @return int Timeout in seconds
     */
    private function getMcpTimeout(): int
    {
        $timeout = ConfigLoader::get('SERVICES.mcp_server.timeout');
        if (is_int($timeout) && $timeout > 0) {
            return $timeout;
        }
        return 30;
    }

    /**
     * Check if current user is admin.
     * Works in both regular page and AJAX context.
     *
     * @return bool True if user is admin
     */
    private function isUserAdmin(): bool
    {
        // Method 1: Try DokuWiki's auth_isadmin() function
        if (function_exists('auth_isadmin')) {
            global $USERINFO;
            global $conf;
            
            // auth_isadmin needs username and groups
            if (isset($_SERVER['REMOTE_USER'])) {
                $user = $_SERVER['REMOTE_USER'];
                $groups = $USERINFO['grps'] ?? [];
                return auth_isadmin($user, $groups);
            }
        }
        
        // Method 2: Check $INFO (works on regular pages)
        global $INFO;
        if (isset($INFO['isadmin']) && $INFO['isadmin']) {
            return true;
        }
        
        // Method 3: Direct superuser check
        global $conf;
        if (isset($_SERVER['REMOTE_USER']) && isset($conf['superuser'])) {
            $superusers = array_map('trim', explode(',', $conf['superuser']));
            if (in_array($_SERVER['REMOTE_USER'], $superusers)) {
                return true;
            }
        }
        
        return false;
    }

    /**
     * Send a JSON response.
     *
     * @param array<string, mixed> $data Response data
     * @param int $statusCode HTTP status code
     * @return void
     */
    private function sendJsonResponse(array $data, int $statusCode = 200): void
    {
        http_response_code($statusCode);
        echo json_encode($data, JSON_THROW_ON_ERROR);
    }
}

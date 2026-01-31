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

// Load ConfigLoader for centralized configuration (Constitution Article II-B)
require_once __DIR__ . '/lib/ConfigLoader.php';
use dokuwiki\plugin\devdito\lib\ConfigLoader;

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

        // Only handle devdito admin AJAX calls
        if (!str_starts_with($action, 'devdito_admin_')) {
            return;
        }

        $event->preventDefault();
        $event->stopPropagation();

        header('Content-Type: application/json; charset=utf-8');

        // Check admin authorization
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

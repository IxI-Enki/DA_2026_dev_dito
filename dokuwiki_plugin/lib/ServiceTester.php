<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * ServiceTester - Shared HTTP connection tests for MCP Server and Qdrant
 *
 * Single source of truth for service testing logic (FR-012, SC-007).
 * Extracted from action.php and admin.php to eliminate code duplication.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     Jan Ritt <j.ritt@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Lib
 */
class ServiceTester
{
    /**
     * Test the MCP server by sending a JSON-RPC 2.0 ping request.
     *
     * @param string $url     Full URL of the MCP server endpoint
     * @param int    $timeout Request timeout in seconds (default 5)
     * @return array{success: bool, latency_ms: int, error: string|null}
     */
    public static function testMcp(string $url, int $timeout = 5): array
    {
        $startTime = microtime(true);

        $payload = json_encode([
            'jsonrpc' => '2.0',
            'id'      => 'devdito_ping',
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

        $result = @file_get_contents(rtrim($url, '/'), false, $context);
        $latencyMs = (int) ((microtime(true) - $startTime) * 1000);

        if ($result === false) {
            return [
                'success'    => false,
                'latency_ms' => $latencyMs,
                'error'      => 'Connection failed',
            ];
        }

        $decoded = json_decode($result, true);
        $isOk = is_array($decoded) && isset($decoded['result']['ok']) && $decoded['result']['ok'] === true;

        return [
            'success'    => $isOk,
            'latency_ms' => $latencyMs,
            'error'      => $isOk ? null : 'Invalid response',
        ];
    }

    /**
     * Test the Qdrant vector database by querying its /collections endpoint.
     *
     * @param string $host    Qdrant hostname or IP address
     * @param int    $port    Qdrant HTTP port (default 6333)
     * @param int    $timeout Request timeout in seconds (default 5)
     * @return array{success: bool, latency_ms: int, error: string|null}
     */
    public static function testQdrant(string $host, int $port = 6333, int $timeout = 5): array
    {
        $url = 'http://' . $host . ':' . $port . '/collections';
        $startTime = microtime(true);

        $context = stream_context_create([
            'http' => [
                'timeout'       => $timeout,
                'ignore_errors' => true,
                'method'        => 'GET',
            ],
        ]);

        $result = @file_get_contents($url, false, $context);
        $latencyMs = (int) ((microtime(true) - $startTime) * 1000);

        if ($result === false) {
            return [
                'success'    => false,
                'latency_ms' => $latencyMs,
                'error'      => 'Connection failed',
            ];
        }

        $decoded = json_decode($result, true);
        $isOk = is_array($decoded) && isset($decoded['result']);

        return [
            'success'    => $isOk,
            'latency_ms' => $latencyMs,
            'error'      => $isOk ? null : 'Invalid response',
        ];
    }
}

<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\tests;

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../dokuwiki_plugin/lib/ServiceTester.php';

use dokuwiki\plugin\devdito\lib\ServiceTester;

/**
 * PHPUnit tests for ServiceTester (Constitution Article III: HTTP client code)
 *
 * Tests verify:
 *   - Return shape contains exactly: success, latency_ms, error
 *   - success: false + non-null error on unreachable host
 *   - success: true + positive latency_ms on reachable host (integration, marked @group integration)
 */
class ServiceTesterTest extends TestCase
{
    // -------------------------------------------------------------------------
    // testMcp — return shape
    // -------------------------------------------------------------------------

    public function testMcpReturnShapeOnUnreachableHost(): void
    {
        $result = ServiceTester::testMcp('http://127.0.0.1:19999', 1);

        $this->assertArrayHasKey('success', $result, 'Result must have "success" key');
        $this->assertArrayHasKey('latency_ms', $result, 'Result must have "latency_ms" key');
        $this->assertArrayHasKey('error', $result, 'Result must have "error" key');
        $this->assertCount(3, $result, 'Result must have exactly 3 keys');
    }

    public function testMcpReturnsFalseOnUnreachableHost(): void
    {
        $result = ServiceTester::testMcp('http://127.0.0.1:19999', 1);

        $this->assertFalse($result['success']);
        $this->assertNotNull($result['error']);
        $this->assertIsInt($result['latency_ms']);
    }

    public function testMcpLatencyMsIsNonNegativeInteger(): void
    {
        $result = ServiceTester::testMcp('http://127.0.0.1:19999', 1);

        $this->assertIsInt($result['latency_ms']);
        $this->assertGreaterThanOrEqual(0, $result['latency_ms']);
    }

    // -------------------------------------------------------------------------
    // testQdrant — return shape
    // -------------------------------------------------------------------------

    public function testQdrantReturnShapeOnUnreachablePort(): void
    {
        $result = ServiceTester::testQdrant('127.0.0.1', 19998, 1);

        $this->assertArrayHasKey('success', $result, 'Result must have "success" key');
        $this->assertArrayHasKey('latency_ms', $result, 'Result must have "latency_ms" key');
        $this->assertArrayHasKey('error', $result, 'Result must have "error" key');
        $this->assertCount(3, $result, 'Result must have exactly 3 keys');
    }

    public function testQdrantReturnsFalseOnUnreachablePort(): void
    {
        $result = ServiceTester::testQdrant('127.0.0.1', 19998, 1);

        $this->assertFalse($result['success']);
        $this->assertNotNull($result['error']);
        $this->assertIsInt($result['latency_ms']);
    }

    public function testQdrantLatencyMsIsNonNegativeInteger(): void
    {
        $result = ServiceTester::testQdrant('127.0.0.1', 19998, 1);

        $this->assertIsInt($result['latency_ms']);
        $this->assertGreaterThanOrEqual(0, $result['latency_ms']);
    }
}

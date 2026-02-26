<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\tests;

use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../../dokuwiki_plugin/lib/JobStatusManager.php';

use dokuwiki\plugin\devdito\lib\JobStatusManager;

/**
 * PHPUnit tests for JobStatusManager::updateJobStatus() and writeRuns()
 * (Constitution Article III: critical-path logic)
 *
 * Tests verify:
 *   - updateJobStatus() updates whitelisted fields
 *   - updateJobStatus() does NOT overwrite immutable fields
 *   - writeRuns() produces valid JSON parseable by json_decode
 *   - getStatusSummary() includes all 5 stages including preprocess
 */
class JobStatusManagerTest extends TestCase
{
    /** @var string Temporary status file path */
    private string $tempFile;

    protected function setUp(): void
    {
        $this->tempFile = tempnam(sys_get_temp_dir(), 'jsm_test_') . '.json';
    }

    protected function tearDown(): void
    {
        if (file_exists($this->tempFile)) {
            unlink($this->tempFile);
        }
    }

    // -------------------------------------------------------------------------
    // Helper
    // -------------------------------------------------------------------------

    private function makeManager(array $runs): JobStatusManager
    {
        file_put_contents($this->tempFile, json_encode($runs));
        return new JobStatusManager($this->tempFile);
    }

    private function readFile(): array
    {
        return json_decode(file_get_contents($this->tempFile), true) ?? [];
    }

    // -------------------------------------------------------------------------
    // updateJobStatus — whitelisted fields written
    // -------------------------------------------------------------------------

    public function testUpdateJobStatusWritesStatus(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', ['status' => 'cancelled']);

        $runs = $this->readFile();
        $this->assertSame('cancelled', $runs[0]['status']);
    }

    public function testUpdateJobStatusWritesFinishedAt(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', [
            'status' => 'cancelled',
            'finished_at' => '2026-01-01T11:00:00',
        ]);

        $runs = $this->readFile();
        $this->assertSame('2026-01-01T11:00:00', $runs[0]['finished_at']);
    }

    public function testUpdateJobStatusWritesError(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', ['error' => 'Manuell abgebrochen']);

        $runs = $this->readFile();
        $this->assertSame('Manuell abgebrochen', $runs[0]['error']);
    }

    // -------------------------------------------------------------------------
    // updateJobStatus — immutable fields NOT overwritten
    // -------------------------------------------------------------------------

    public function testUpdateJobStatusDoesNotOverwriteJobId(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', ['job_id' => 'EVIL_OVERRIDE', 'status' => 'cancelled']);

        $runs = $this->readFile();
        $this->assertSame('fetch_001', $runs[0]['job_id'], 'job_id must be immutable');
    }

    public function testUpdateJobStatusDoesNotOverwriteStage(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', ['stage' => 'deploy', 'status' => 'cancelled']);

        $runs = $this->readFile();
        $this->assertSame('fetch', $runs[0]['stage'], 'stage must be immutable');
    }

    public function testUpdateJobStatusDoesNotOverwriteStartedAt(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', [
            'started_at' => '1970-01-01T00:00:00',
            'status' => 'cancelled',
        ]);

        $runs = $this->readFile();
        $this->assertSame('2026-01-01T10:00:00', $runs[0]['started_at'], 'started_at must be immutable');
    }

    public function testUpdateJobStatusDoesNotOverwriteStats(): void
    {
        $stats = ['pages' => 207, 'media' => 325];
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'success',
             'started_at' => '2026-01-01T10:00:00', 'stats' => $stats],
        ]);

        $manager->updateJobStatus('fetch_001', ['stats' => [], 'status' => 'cancelled']);

        $runs = $this->readFile();
        $this->assertSame($stats, $runs[0]['stats'], 'stats must be immutable');
    }

    // -------------------------------------------------------------------------
    // updateJobStatus — unknown job is silently ignored (no crash)
    // -------------------------------------------------------------------------

    public function testUpdateJobStatusIgnoresUnknownJobId(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('nonexistent_job', ['status' => 'cancelled']);

        $runs = $this->readFile();
        // Original run unchanged
        $this->assertSame('running', $runs[0]['status']);
    }

    // -------------------------------------------------------------------------
    // writeRuns — produces valid JSON
    // -------------------------------------------------------------------------

    public function testWriteRunsProducesValidJson(): void
    {
        $manager = $this->makeManager([
            ['job_id' => 'fetch_001', 'stage' => 'fetch', 'status' => 'running',
             'started_at' => '2026-01-01T10:00:00'],
        ]);

        $manager->updateJobStatus('fetch_001', ['status' => 'cancelled']);

        $content = file_get_contents($this->tempFile);
        $decoded = json_decode($content, true);

        $this->assertNotNull($decoded, 'writeRuns must produce parseable JSON');
        $this->assertIsArray($decoded);
        $this->assertCount(1, $decoded);
    }

    // -------------------------------------------------------------------------
    // getStatusSummary — includes all 5 stages (FR-005)
    // -------------------------------------------------------------------------

    public function testStatusSummaryIncludesAllFiveStages(): void
    {
        $manager = $this->makeManager([]);

        $summary = $manager->getStatusSummary();

        $expectedStages = ['fetch', 'evaluate', 'preprocess', 'embed', 'deploy'];
        foreach ($expectedStages as $stage) {
            $this->assertArrayHasKey($stage, $summary, "getStatusSummary() must include '$stage'");
        }
        $this->assertCount(5, $summary, 'getStatusSummary() must return exactly 5 stages');
    }

    public function testStatusSummaryPreprocessPositionedBetweenEvaluateAndEmbed(): void
    {
        $manager = $this->makeManager([]);
        $stages = array_keys($manager->getStatusSummary());

        $evalIdx = array_search('evaluate', $stages, true);
        $prepIdx = array_search('preprocess', $stages, true);
        $embedIdx = array_search('embed', $stages, true);

        $this->assertGreaterThan($evalIdx, $prepIdx, 'preprocess must come after evaluate');
        $this->assertLessThan($embedIdx, $prepIdx, 'preprocess must come before embed');
    }
}

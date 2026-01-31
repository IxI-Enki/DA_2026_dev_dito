<?php

declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * JobStatusManager - Reads pipeline job status from pipeline_runs.json
 *
 * This class provides read-only access to the pipeline status file.
 * Status updates are written by the Python pipeline modules.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     Jan Ritt <j.ritt@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Lib
 */
class JobStatusManager
{
    /** @var string Path to status file */
    private string $statusFile;

    /** @var array|null Cached runs data */
    private ?array $cachedRuns = null;

    /**
     * Constructor
     *
     * @param string|null $statusFile Path to pipeline_runs.json (auto-detect if null)
     */
    public function __construct(?string $statusFile = null)
    {
        if ($statusFile !== null) {
            $this->statusFile = $statusFile;
        } else {
            // Try ConfigLoader first, fallback to default path
            try {
                $configPath = ConfigLoader::get('PIPELINE_ORCHESTRATION.logging.status_file');
                if ($configPath && file_exists($configPath)) {
                    $this->statusFile = $configPath;
                } else {
                    $this->statusFile = $this->getDefaultStatusFile();
                }
            } catch (\Exception $e) {
                $this->statusFile = $this->getDefaultStatusFile();
            }
        }
    }

    /**
     * Get default status file path
     *
     * @return string
     */
    private function getDefaultStatusFile(): string
    {
        // Path relative to dokuwiki_plugin directory
        $pluginDir = dirname(__DIR__);
        $repoRoot = dirname($pluginDir);
        return $repoRoot . '/data/logs/pipeline_runs.json';
    }

    /**
     * Load all pipeline runs from JSON file
     *
     * @return array Array of run objects
     */
    public function getAllRuns(): array
    {
        if ($this->cachedRuns !== null) {
            return $this->cachedRuns;
        }

        if (!file_exists($this->statusFile)) {
            return [];
        }

        $content = file_get_contents($this->statusFile);
        if ($content === false) {
            return [];
        }

        $data = json_decode($content, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            error_log("[DevDito] Failed to parse pipeline_runs.json: " . json_last_error_msg());
            return [];
        }

        $this->cachedRuns = is_array($data) ? $data : [];
        return $this->cachedRuns;
    }

    /**
     * Get the most recent run for a specific stage
     *
     * @param string $stage Stage ID (fetch, evaluate, embed, deploy)
     * @return array|null Run data or null if not found
     */
    public function getLastRun(string $stage): ?array
    {
        $runs = $this->getAllRuns();

        // Filter by stage
        $stageRuns = array_filter($runs, fn($r) => ($r['stage'] ?? '') === $stage);

        if (empty($stageRuns)) {
            return null;
        }

        // Sort by started_at descending
        usort($stageRuns, function ($a, $b) {
            $aTime = $a['started_at'] ?? '';
            $bTime = $b['started_at'] ?? '';
            return strcmp($bTime, $aTime);
        });

        return reset($stageRuns) ?: null;
    }

    /**
     * Get currently active (running) job
     *
     * @return array|null Active job data or null if none running
     */
    public function getActiveJob(): ?array
    {
        $runs = $this->getAllRuns();

        foreach ($runs as $run) {
            if (($run['status'] ?? '') === 'running') {
                return $run;
            }
        }

        return null;
    }

    /**
     * Get job by ID
     *
     * @param string $jobId Job identifier
     * @return array|null Job data or null if not found
     */
    public function getJob(string $jobId): ?array
    {
        $runs = $this->getAllRuns();

        foreach ($runs as $run) {
            if (($run['job_id'] ?? '') === $jobId) {
                return $run;
            }
        }

        return null;
    }

    /**
     * Check if any job is currently running
     *
     * @return bool
     */
    public function hasActiveJob(): bool
    {
        return $this->getActiveJob() !== null;
    }

    /**
     * Get status summary for all stages
     *
     * @return array Array with stage IDs as keys and last status as values
     */
    public function getStatusSummary(): array
    {
        $stages = ['fetch', 'evaluate', 'embed', 'deploy'];
        $summary = [];

        foreach ($stages as $stage) {
            $lastRun = $this->getLastRun($stage);
            $summary[$stage] = [
                'status' => $lastRun['status'] ?? 'never_run',
                'last_run' => $lastRun['finished_at'] ?? $lastRun['started_at'] ?? null,
                'duration_seconds' => $lastRun['duration_seconds'] ?? null,
                'output_dir' => $lastRun['output_dir'] ?? null,
                'stats' => $lastRun['stats'] ?? null,
                'error' => $lastRun['error'] ?? null,
            ];
        }

        return $summary;
    }

    /**
     * Clear cached data (force reload on next access)
     *
     * @return void
     */
    public function clearCache(): void
    {
        $this->cachedRuns = null;
    }

    /**
     * Get the status file path (for debugging)
     *
     * @return string
     */
    public function getStatusFilePath(): string
    {
        return $this->statusFile;
    }
}

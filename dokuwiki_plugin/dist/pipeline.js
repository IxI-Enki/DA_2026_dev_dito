/**
 * Dev Dito Pipeline Dashboard
 * ===========================
 * Handles pipeline stage execution and status polling.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     Jan Ritt <j.ritt@htl-leonding.ac.at>
 * @version    0.1.0
 */

const DevDitoPipeline = {
    /** @type {number|null} Polling interval ID */
    pollInterval: null,

    /** @type {number|null} Progress polling interval ID */
    progressPollInterval: null,

    /** @type {number} Polling interval in milliseconds */
    pollIntervalMs: 5000,

    /** @type {number} Progress polling interval in milliseconds (faster) */
    progressPollIntervalMs: 2000,

    /** @type {boolean} Whether polling is active */
    isPolling: false,

    /** @type {string|null} Current active job ID */
    activeJobId: null,

    /**
     * Initialize the pipeline dashboard
     */
    init: function() {
        console.log('[DevDito] Pipeline dashboard initializing...');
        this.loadStatus();
        this.startPolling();
    },

    /**
     * Load pipeline status from server
     */
    loadStatus: function() {
        const url = DOKU_BASE + 'lib/exe/ajax.php?call=devdito_pipeline_status';

        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.renderStages(data);
                
                // Start progress polling if job is running
                if (data.active_job && data.active_job.job_id) {
                    this.activeJobId = data.active_job.job_id;
                    this.startProgressPolling();
                } else {
                    this.activeJobId = null;
                    this.stopProgressPolling();
                }
            })
            .catch(error => this.renderError(error));
    },

    /**
     * Load live progress from server
     */
    loadProgress: function() {
        const url = DOKU_BASE + 'lib/exe/ajax.php?call=devdito_progress';

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'running' || data.progress) {
                    this.updateProgressDisplay(data);
                } else if (data.status === 'success' || data.status === 'error') {
                    // Job completed - reload full status
                    this.stopProgressPolling();
                    this.loadStatus();
                }
            })
            .catch(error => {
                console.error('[DevDito] Progress fetch error:', error);
            });
    },

    /**
     * Start polling for live progress
     */
    startProgressPolling: function() {
        if (this.progressPollInterval) return;

        console.log('[DevDito] Starting progress polling');
        this.loadProgress(); // Initial load
        this.progressPollInterval = setInterval(() => this.loadProgress(), this.progressPollIntervalMs);
    },

    /**
     * Stop progress polling
     */
    stopProgressPolling: function() {
        if (this.progressPollInterval) {
            clearInterval(this.progressPollInterval);
            this.progressPollInterval = null;
            console.log('[DevDito] Stopped progress polling');
        }
    },

    /**
     * Update progress display with live data
     * @param {Object} progress Progress data from server
     */
    updateProgressDisplay: function(progress) {
        const container = document.querySelector('.devdito-active-job');
        if (!container) return;

        let html = `
            <h3><span class="devdito-spinner"></span> ${this.escapeHtml(progress.current_step || 'Laeuft...')}</h3>
            <p><strong>Job-ID:</strong> ${this.escapeHtml(progress.job_id || this.activeJobId)}</p>
            <p><strong>Stufe:</strong> ${this.escapeHtml(progress.stage || '?')}</p>
        `;

        if (progress.started_at) {
            const start = new Date(progress.started_at);
            html += `<p><strong>Gestartet:</strong> ${start.toLocaleString('de-DE')}</p>`;
        }

        // Progress bar
        const p = progress.progress || {};
        const percent = p.percentage || 0;
        const current = p.current || 0;
        const total = p.total || 0;

        html += `
            <div class="devdito-progress">
                <div class="devdito-progress-bar" style="width: ${percent}%"></div>
            </div>
            <p class="devdito-progress-text">${current} / ${total || '?'} (${percent}%)</p>
        `;

        // Message
        if (progress.message) {
            html += `<p class="devdito-progress-msg">${this.escapeHtml(progress.message)}</p>`;
        }

        // Substeps
        if (progress.substeps && progress.substeps.length > 0) {
            html += '<div class="devdito-substeps"><strong>Schritte:</strong><ul>';
            progress.substeps.slice(-5).forEach(step => {
                const icon = step.status === 'complete' ? '[OK]' : (step.status === 'running' ? '[...]' : '[ ]');
                html += `<li>${icon} ${this.escapeHtml(step.step)}</li>`;
            });
            html += '</ul></div>';
        }

        // Errors
        if (progress.errors && progress.errors.length > 0) {
            html += `<p class="devdito-progress-errors">Fehler: ${progress.errors.length}</p>`;
        }

        container.innerHTML = html;
    },

    /**
     * Render pipeline stages
     * @param {Object} data Pipeline status data
     */
    renderStages: function(data) {
        const container = document.getElementById('devdito-pipeline-stages');
        if (!container) {
            console.error('[DevDito] Pipeline container not found');
            return;
        }

        let html = '<div class="devdito-pipeline-grid">';

        if (data.stages && data.stages.length > 0) {
            data.stages.forEach((stage, index) => {
                html += this.renderStageCard(stage, index, data);
            });
        } else {
            html += '<p class="devdito-warning">Keine Pipeline-Stufen gefunden.</p>';
        }

        html += '</div>';

        // Qdrant info
        if (data.qdrant_info) {
            html += this.renderQdrantInfo(data.qdrant_info);
        }

        // Active job info
        if (data.active_job) {
            html += this.renderActiveJob(data.active_job);
        }

        container.innerHTML = html;
    },

    /**
     * Render a single stage card
     * @param {Object} stage Stage data
     * @param {number} index Stage index
     * @param {Object} data Full pipeline data
     * @returns {string} HTML string
     */
    renderStageCard: function(stage, index, data) {
        const statusClass = this.getStatusClass(stage.status);
        const canRun = this.canRunStage(stage, index, data);
        const isRunning = stage.status === 'running';

        let html = `
            <div class="devdito-stage-card ${statusClass}">
                <div class="devdito-stage-header">
                    <span class="devdito-stage-number">${index + 1}</span>
                    <h3>${this.escapeHtml(stage.name)}</h3>
                </div>
                <p class="devdito-stage-desc">${this.escapeHtml(stage.description)}</p>
                <div class="devdito-stage-status">
                    <span class="devdito-status-badge ${statusClass}">
                        ${isRunning ? '<span class="devdito-spinner"></span>' : ''}
                        ${this.getStatusLabel(stage.status)}
                    </span>
        `;

        if (stage.last_run) {
            const date = new Date(stage.last_run);
            html += `<span class="devdito-last-run">Zuletzt: ${date.toLocaleString('de-DE')}</span>`;
        }

        html += '</div>';

        // Stats
        if (stage.stats) {
            html += this.renderStats(stage.stats);
        }

        // Error message
        if (stage.error && stage.status === 'error') {
            html += `<div class="devdito-stage-error">${this.escapeHtml(stage.error.substring(0, 200))}</div>`;
        }

        // Duration
        if (stage.duration_seconds && stage.duration_seconds > 0) {
            html += `<div class="devdito-stage-duration">Dauer: ${this.formatDuration(stage.duration_seconds)}</div>`;
        }

        // Run buttons
        if (stage.id === 'fetch') {
            // Fetch stage gets two buttons: Full and Incremental
            html += `
                <div class="devdito-stage-buttons">
                    <button 
                        class="devdito-btn devdito-btn-run"
                        ${!canRun ? 'disabled' : ''}
                        onclick="DevDitoPipeline.runStage('${stage.id}', {mode: 'full'})"
                        title="Fetch all pages from wiki"
                    >
                        ${isRunning ? 'Laeuft...' : 'Full Fetch'}
                    </button>
                    <button 
                        class="devdito-btn devdito-btn-run devdito-btn-secondary"
                        ${!canRun || !stage.has_manifest ? 'disabled' : ''}
                        onclick="DevDitoPipeline.runStage('${stage.id}', {mode: 'incremental'})"
                        title="Only fetch changed pages (requires previous fetch)"
                    >
                        Incremental
                    </button>
                </div>
            `;
        } else {
            html += `
                <button 
                    class="devdito-btn devdito-btn-run"
                    ${!canRun ? 'disabled' : ''}
                    onclick="DevDitoPipeline.runStage('${stage.id}')"
                >
                    ${isRunning ? 'Laeuft...' : 'Starten'}
                </button>
            `;
        }
        html += '</div>';

        return html;
    },

    /**
     * Render stage statistics
     * @param {Object} stats Stage statistics
     * @returns {string} HTML string
     */
    renderStats: function(stats) {
        let html = '<div class="devdito-stage-stats">';
        for (const [key, value] of Object.entries(stats)) {
            if (value !== null && value !== undefined) {
                html += `<span><strong>${this.escapeHtml(key)}:</strong> ${this.escapeHtml(String(value))}</span>`;
            }
        }
        html += '</div>';
        return html;
    },

    /**
     * Render Qdrant collection info
     * @param {Object} info Qdrant info
     * @returns {string} HTML string
     */
    renderQdrantInfo: function(info) {
        const statusClass = info.connected ? 'status-success' : 'status-error';
        const statusIcon = info.connected ? '●' : '○';

        let html = `
            <div class="devdito-qdrant-info">
                <h3>Qdrant Vector Database</h3>
                <p>
                    <span class="${statusClass}">
                        ${statusIcon} ${info.connected ? 'Verbunden' : 'Nicht verbunden'}
                    </span>
                </p>
        `;

        if (info.connected) {
            html += `
                <p><strong>Collection:</strong> ${this.escapeHtml(info.collection)}</p>
                <p><strong>Vectors:</strong> ${info.vectors ? info.vectors.toLocaleString('de-DE') : '0'}</p>
                <p><strong>Dimension:</strong> ${info.dimension || 'N/A'}</p>
            `;
        } else if (info.error) {
            html += `<p class="devdito-error">${this.escapeHtml(info.error)}</p>`;
        }

        html += '</div>';
        return html;
    },

    /**
     * Render active job info
     * @param {Object} job Active job data
     * @returns {string} HTML string
     */
    renderActiveJob: function(job) {
        let html = `
            <div class="devdito-active-job">
                <h3><span class="devdito-spinner"></span> Laufender Job</h3>
                <p><strong>Job-ID:</strong> ${this.escapeHtml(job.job_id)}</p>
                <p><strong>Stufe:</strong> ${this.escapeHtml(job.stage)}</p>
        `;

        if (job.started_at) {
            const start = new Date(job.started_at);
            html += `<p><strong>Gestartet:</strong> ${start.toLocaleString('de-DE')}</p>`;
        }

        if (job.progress) {
            const percent = job.progress.total > 0 
                ? Math.round((job.progress.current / job.progress.total) * 100) 
                : 0;
            html += `
                <div class="devdito-progress">
                    <div class="devdito-progress-bar" style="width: ${percent}%"></div>
                </div>
                <p>${job.progress.current || 0} / ${job.progress.total || '?'} (${percent}%)</p>
            `;
            if (job.progress.message) {
                html += `<p class="devdito-progress-msg">${this.escapeHtml(job.progress.message)}</p>`;
            }
        }

        html += '</div>';
        return html;
    },

    /**
     * Run a pipeline stage
     * @param {string} stageId Stage identifier
     * @param {Object} options Optional parameters (e.g., { mode: 'incremental' })
     */
    runStage: function(stageId, options) {
        const url = DOKU_BASE + 'lib/exe/ajax.php?call=devdito_run_stage';

        // Disable all run buttons during request
        document.querySelectorAll('.devdito-btn-run').forEach(btn => btn.disabled = true);

        const body = { stage: stageId };
        if (options) {
            Object.assign(body, options);
        }

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('success', data.message);
                // Immediately reload status
                this.loadStatus();
            } else {
                this.showNotification('error', 'Fehler: ' + (data.message || 'Unbekannter Fehler'));
            }
        })
        .catch(error => {
            this.showNotification('error', 'Request fehlgeschlagen: ' + error.message);
        })
        .finally(() => {
            // Re-enable buttons (loadStatus will set correct states)
            this.loadStatus();
        });
    },

    /**
     * Start polling for status updates
     */
    startPolling: function() {
        if (this.isPolling) return;

        this.isPolling = true;
        this.pollInterval = setInterval(() => this.loadStatus(), this.pollIntervalMs);
        console.log('[DevDito] Status polling started (interval: ' + this.pollIntervalMs + 'ms)');
    },

    /**
     * Stop polling
     */
    stopPolling: function() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
        console.log('[DevDito] Status polling stopped');
    },

    /**
     * Get CSS class for status
     * @param {string} status Status string
     * @returns {string} CSS class
     */
    getStatusClass: function(status) {
        const classes = {
            'success': 'status-success',
            'error': 'status-error',
            'running': 'status-running',
            'interrupted': 'status-error',
            'never_run': 'status-pending'
        };
        return classes[status] || 'status-pending';
    },

    /**
     * Get display label for status
     * @param {string} status Status string
     * @returns {string} Display label
     */
    getStatusLabel: function(status) {
        const labels = {
            'success': 'Erfolgreich',
            'error': 'Fehler',
            'running': 'Laeuft...',
            'interrupted': 'Unterbrochen',
            'never_run': 'Nie ausgefuehrt'
        };
        return labels[status] || status;
    },

    /**
     * Check if a stage can be run
     * @param {Object} stage Stage data
     * @param {number} index Stage index
     * @param {Object} data Full pipeline data
     * @returns {boolean} True if stage can be run
     */
    canRunStage: function(stage, index, data) {
        // Can't run if any job is already running
        if (data.active_job) return false;

        // Fetch can always run
        if (stage.id === 'fetch') return true;

        // Other stages need previous stage to be successful
        if (index > 0 && data.stages[index - 1]) {
            const prevStage = data.stages[index - 1];
            return prevStage.status === 'success';
        }

        return false;
    },

    /**
     * Format duration in seconds to human readable
     * @param {number} seconds Duration in seconds
     * @returns {string} Formatted duration
     */
    formatDuration: function(seconds) {
        if (seconds < 60) {
            return seconds + ' Sek.';
        } else if (seconds < 3600) {
            const min = Math.floor(seconds / 60);
            const sec = seconds % 60;
            return min + ' Min. ' + sec + ' Sek.';
        } else {
            const hrs = Math.floor(seconds / 3600);
            const min = Math.floor((seconds % 3600) / 60);
            return hrs + ' Std. ' + min + ' Min.';
        }
    },

    /**
     * Show a notification message
     * @param {string} type 'success' or 'error'
     * @param {string} message Message text
     */
    showNotification: function(type, message) {
        // Use DokuWiki's msg system if available, otherwise alert
        if (typeof JSINFO !== 'undefined' && typeof msg === 'function') {
            msg(message, type === 'error' ? -1 : 1);
        } else {
            alert(message);
        }
    },

    /**
     * Render error state
     * @param {Error} error Error object
     */
    renderError: function(error) {
        const container = document.getElementById('devdito-pipeline-stages');
        if (container) {
            container.innerHTML = `
                <div class="devdito-error-box">
                    <h3>Fehler beim Laden des Pipeline-Status</h3>
                    <p>${this.escapeHtml(error.message)}</p>
                    <button class="devdito-btn" onclick="DevDitoPipeline.loadStatus()">Erneut versuchen</button>
                </div>
            `;
        }
    },

    /**
     * Escape HTML special characters
     * @param {string} text Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml: function(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => DevDitoPipeline.init());
} else {
    DevDitoPipeline.init();
}

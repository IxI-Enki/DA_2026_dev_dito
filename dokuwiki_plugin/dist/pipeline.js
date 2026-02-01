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
    
    /** @type {Object|null} Current active job data */
    activeJobData: null,
    
    /** @type {Object|null} Last received progress data */
    lastProgressData: null,

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
                
                // Note: progress polling is managed by updateActiveJobSection
                // to avoid duplicate polling and flickering
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
                } else if (data.status === 'success' || data.status === 'error' || data.status === 'not_found' || data.status === 'orchestrator_offline') {
                    // Job completed or not found - clear display and stop polling
                    this.lastProgressData = null;
                    this.activeJobId = null;
                    this.activeJobData = null;
                    this.stopProgressPolling();
                    
                    // Clear the job container
                    const container = document.getElementById('devdito-active-job-container');
                    if (container) {
                        container.innerHTML = '';
                    }
                    
                    // Reload full status to update stage cards
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
        // Store progress data for merge with job data
        this.lastProgressData = progress;
        
        const container = document.getElementById('devdito-active-job-container');
        if (!container) return;
        
        // Use the unified render function with both job and progress data
        const job = this.activeJobData || {
            job_id: progress.job_id || this.activeJobId || 'unknown',
            stage: progress.stage || '?',
            started_at: progress.started_at
        };
        
        container.innerHTML = this.renderActiveJobHtml(job, progress);
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

        // Check if container already has structure (avoid full rebuild)
        let gridContainer = container.querySelector('.devdito-pipeline-grid');
        let jobContainer = document.getElementById('devdito-active-job-container');
        
        // Build stages grid HTML
        let gridHtml = '';
        if (data.stages && data.stages.length > 0) {
            data.stages.forEach((stage, index) => {
                gridHtml += this.renderStageCard(stage, index, data);
            });
        } else {
            gridHtml = '<p class="devdito-warning">Keine Pipeline-Stufen gefunden.</p>';
        }

        // Only rebuild if structure doesn't exist yet
        if (!gridContainer || !jobContainer) {
            let html = '<div class="devdito-pipeline-grid">' + gridHtml + '</div>';

            // Qdrant info
            if (data.qdrant_info) {
                html += this.renderQdrantInfo(data.qdrant_info);
            }

            // Active job container (persistent - never destroyed)
            html += '<div id="devdito-active-job-container"></div>';

            container.innerHTML = html;
        } else {
            // Just update the grid content, preserve job container
            gridContainer.innerHTML = gridHtml;
        }
        
        // Update active job section separately (no flicker)
        this.updateActiveJobSection(data.active_job);
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
     * Tooltip explanations for statistics
     * Explains how each value is calculated
     */
    statTooltips: {
        // Fetch stage
        'pages': 'Anzahl der vom Wiki geholten Seiten via JSON-RPC API',
        'media': 'Anzahl der heruntergeladenen Mediendateien (Bilder, PDFs, etc.)',
        
        // Evaluation stage
        'pages_evaluated': 'Anzahl der analysierten Seiten',
        'overall_quality': 'Gewichteter Durchschnitt aus: Format-Qualitaet (30%), RAG-Eignung (40%), Inhaltsklassifikation (30%). Werte 0.0-1.0',
        'pages_to_include': 'Seiten mit Quality Score >= 0.5 (empfohlen fuer Embedding)',
        'pages_to_exclude': 'Seiten mit Quality Score < 0.3 oder als EXCLUDE markiert',
        'pages_to_review': 'Seiten mit Quality Score zwischen 0.3-0.5 (manuelle Pruefung empfohlen)',
        
        // Preprocessing stage
        'documents_processed': 'Anzahl der in Markdown konvertierten Dokumente',
        'pages_converted': 'Wiki-Seiten zu Markdown mit YAML Frontmatter konvertiert',
        'media_extracted': 'Text aus Mediendateien extrahiert (PDF, DOCX, XLSX)',
        'total_output_files': 'Gesamtzahl der erzeugten Dateien',
        
        // Embeddings stage
        'chunks': 'Anzahl der semantischen Text-Chunks (Content-Aware Chunking)',
        'vectors': 'Anzahl der generierten Embedding-Vektoren',
        'dimensions': 'Dimensionen pro Vektor (z.B. 3072 fuer text-embedding-3-large)',
        'cost_usd': 'Geschaetzte OpenAI API Kosten in USD',
        'model': 'Verwendetes Embedding-Modell',
        
        // Deploy stage
        'uploaded': 'Anzahl der in Qdrant hochgeladenen Vektoren',
        'collection': 'Name der Qdrant Collection'
    },

    /**
     * Render stage statistics with tooltips
     * @param {Object} stats Stage statistics
     * @returns {string} HTML string
     */
    renderStats: function(stats) {
        let html = '<div class="devdito-stage-stats">';
        for (const [key, value] of Object.entries(stats)) {
            if (value !== null && value !== undefined) {
                const tooltip = this.statTooltips[key] || 'Keine Erklaerung verfuegbar';
                html += `<span title="${this.escapeHtml(tooltip)}" class="devdito-stat-item">` +
                        `<strong>${this.escapeHtml(key)}:</strong> ${this.escapeHtml(String(value))}` +
                        `</span>`;
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
     * Update the active job section without causing flicker
     * Merges basic job info with live progress data
     * @param {Object} job Basic job data from status endpoint
     */
    updateActiveJobSection: function(job) {
        const container = document.getElementById('devdito-active-job-container');
        if (!container) return;
        
        // CRITICAL: If progress polling is active, let IT handle all rendering
        // Status polling should NOT touch the display to avoid toggle/flicker
        if (this.progressPollInterval) {
            // Just update the stored job data for reference
            if (job) {
                this.activeJobData = job;
            }
            return; // Progress polling handles the display
        }
        
        // If no active job from status endpoint
        if (!job) {
            // Clear display
            container.innerHTML = '';
            this.activeJobId = null;
            this.activeJobData = null;
            this.lastProgressData = null;
            return;
        }
        
        // Store job info
        this.activeJobId = job.job_id;
        this.activeJobData = job;
        
        // Start progress polling - it will take over rendering
        this.startProgressPolling();
        
        // Initial render only if container is empty (first time)
        if (container.innerHTML === '') {
            container.innerHTML = this.renderActiveJobHtml(job, null);
        }
    },
    
    /**
     * Render active job HTML (used by both status and progress updates)
     * @param {Object} job Basic job data
     * @param {Object} progress Live progress data (optional)
     * @returns {string} HTML string
     */
    renderActiveJobHtml: function(job, progress) {
        const p = progress || {};
        const currentStep = p.current_step || 'Laufender Job';
        
        let html = `
            <div class="devdito-active-job">
                <h3><span class="devdito-spinner"></span> ${this.escapeHtml(currentStep)}</h3>
                <p><strong>Job-ID:</strong> ${this.escapeHtml(job.job_id)}</p>
                <p><strong>Stufe:</strong> ${this.escapeHtml(job.stage)}</p>
        `;

        const startTime = p.started_at || job.started_at;
        if (startTime) {
            const start = new Date(startTime);
            html += `<p><strong>Gestartet:</strong> ${start.toLocaleString('de-DE')}</p>`;
        }

        // Progress bar - prefer live progress data
        const progData = p.progress || job.progress || {};
        const percent = progData.percentage || (progData.total > 0 
            ? Math.round((progData.current / progData.total) * 100) 
            : 0);
        const current = progData.current || 0;
        const total = progData.total || '?';
        
        html += `
            <div class="devdito-progress">
                <div class="devdito-progress-bar" style="width: ${percent}%"></div>
            </div>
            <p class="devdito-progress-text">${current} / ${total} (${percent}%)</p>
        `;
        
        // Message
        const message = p.message || (job.progress && job.progress.message);
        if (message) {
            html += `<p class="devdito-progress-msg">${this.escapeHtml(message)}</p>`;
        }

        // Substeps (from live progress)
        if (p.substeps && p.substeps.length > 0) {
            html += '<div class="devdito-substeps"><strong>Schritte:</strong><ul>';
            p.substeps.slice(-5).forEach(step => {
                const icon = step.status === 'complete' ? '[OK]' : (step.status === 'running' ? '[...]' : '[ ]');
                html += `<li>${icon} ${this.escapeHtml(step.step)}</li>`;
            });
            html += '</ul></div>';
        }

        // Errors
        if (p.errors && p.errors.length > 0) {
            html += `<p class="devdito-progress-errors">Fehler: ${p.errors.length}</p>`;
        }

        // Cancel button
        html += `
            <div class="devdito-job-actions">
                <button 
                    class="devdito-btn devdito-btn-cancel"
                    onclick="DevDitoPipeline.cancelJob('${this.escapeHtml(job.job_id)}')"
                    title="Job abbrechen"
                >
                    Abbrechen
                </button>
            </div>
        `;

        html += '</div>';
        return html;
    },
    
    /**
     * Cancel a running job
     * @param {string} jobId Job identifier
     */
    cancelJob: function(jobId) {
        if (!confirm('Job wirklich abbrechen?')) {
            return;
        }
        
        const url = DOKU_BASE + 'lib/exe/ajax.php?call=devdito_cancel_job';
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ job_id: jobId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('info', 'Job wird abgebrochen...');
                this.stopProgressPolling();
                this.loadStatus();
            } else {
                this.showNotification('error', 'Fehler: ' + (data.message || 'Konnte Job nicht abbrechen'));
            }
        })
        .catch(error => {
            this.showNotification('error', 'Request fehlgeschlagen: ' + error.message);
        });
    },
    
    /**
     * Legacy render function for compatibility
     * @deprecated Use updateActiveJobSection instead
     */
    renderActiveJob: function(job) {
        return this.renderActiveJobHtml(job, null);
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

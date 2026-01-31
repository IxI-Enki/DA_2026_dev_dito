<?php

declare(strict_types=1);

/**
 * Dev Dito Admin Plugin - Core Setup Dashboard
 *
 * Provides an admin interface for managing Dev Dito extension configuration,
 * service connections, and system status monitoring.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Admin
 * @version    0.1.0-alpha
 */

use dokuwiki\Extension\AdminPlugin;

// Load ConfigLoader for centralized configuration (Constitution Article II-B)
require_once __DIR__ . '/lib/ConfigLoader.php';
use dokuwiki\plugin\devdito\lib\ConfigLoader;

if (!defined('DOKU_INC')) {
    die();
}

/**
 * Admin Plugin for Dev Dito Core Setup.
 *
 * This plugin provides:
 * - Service status overview (MCP Server, Qdrant, etc.)
 * - Connection testing and diagnostics
 * - Configuration management
 * - Quick actions for common tasks
 */
class admin_plugin_devdito extends AdminPlugin
{
    /** @var string Current plugin version */
    private const VERSION = '0.2.0';

    /**
     * HTL Color Palette Constants
     */
    private const COLOR_BRAND_PRIMARY = '#B45140';
    private const COLOR_BRAND_DARK = '#8D3A29';
    private const COLOR_BRAND_LIGHT = '#C66451';
    private const COLOR_SUCCESS = '#4CAF50';
    private const COLOR_WARNING = '#FF9800';
    private const COLOR_ERROR = '#F44336';
    private const COLOR_BG_DARK = '#282828';
    private const COLOR_BG_ALT = '#404040';
    private const COLOR_TEXT_LIGHT = '#F0F0F0';
    private const COLOR_BORDER = '#555555';

    /**
     * Return the menu sort order for this admin plugin.
     *
     * @return int Sort order (lower = higher in menu)
     */
    public function getMenuSort()
    {
        return 500;
    }

    /**
     * Check if the current user may access this admin plugin.
     *
     * @return bool True if user has superuser or admin rights
     */
    public function forAdminOnly()
    {
        return true;
    }

    /**
     * Return the menu text for this admin plugin.
     *
     * @param string $language Current language code (unused, using fixed text)
     * @return string Menu text
     */
    public function getMenuText($language)
    {
        return 'Dev Dito Core Setup';
    }

    /**
     * Return the menu icon (SVG) for this admin plugin.
     *
     * @return string SVG icon markup
     */
    public function getMenuIcon()
    {
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">'
            . '<path fill="currentColor" d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/>'
            . '</svg>';
    }

    /**
     * Handle user request and render the admin page.
     *
     * @return void
     */
    public function handle()
    {
        global $INPUT;

        if (!$this->isAuthorized()) {
            return;
        }

        // Handle AJAX requests
        if ($INPUT->str('action') === 'devdito_admin_test') {
            $this->handleTestConnection();
            return;
        }
    }

    /**
     * Render the admin page HTML.
     *
     * @return void
     */
    public function html()
    {
        if (!$this->isAuthorized()) {
            echo '<div class="error">Access denied.</div>';
            return;
        }

        $this->renderStyles();
        $this->renderHeader();
        $this->renderPipelineSection();
        $this->renderServiceStatusSection();
        $this->renderConfigurationSection();
        $this->renderQuickActionsSection();
        $this->renderScripts();
    }

    /**
     * Check if current user is authorized.
     *
     * @return bool True if authorized
     */
    private function isAuthorized(): bool
    {
        global $INFO;
        return isset($INFO['isadmin']) && $INFO['isadmin'];
    }

    /**
     * Handle test connection AJAX request.
     *
     * @return void
     */
    private function handleTestConnection(): void
    {
        global $INPUT;

        header('Content-Type: application/json; charset=utf-8');

        $service = $INPUT->str('service');
        $result = $this->testService($service);

        echo json_encode($result, JSON_THROW_ON_ERROR);
        exit;
    }

    /**
     * Test a specific service connection.
     *
     * @param string $service Service identifier
     * @return array{ok: bool, message: string, latency_ms?: int}
     */
    private function testService(string $service): array
    {
        switch ($service) {
            case 'mcp':
                return $this->testMcpServer();
            case 'qdrant':
                return $this->testQdrant();
            default:
                return ['ok' => false, 'message' => 'Unknown service'];
        }
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

        $payload = json_encode([
            'jsonrpc' => '2.0',
            'id'      => 'admin_ping',
            'method'  => 'ping',
        ], JSON_THROW_ON_ERROR);

        $context = stream_context_create([
            'http' => [
                'timeout'       => 5,
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
        // Get Qdrant URL from central config (Constitution Article II-B)
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
                'message'    => 'Connection failed (expected in browser)',
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
     * Render inline CSS styles.
     *
     * @return void
     */
    private function renderStyles(): void
    {
        echo '<style>';

        // Container
        echo '.devdito-admin { max-width: 1200px; margin: 0 auto; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }';

        // Header
        echo '.devdito-admin-header { background: linear-gradient(135deg, ' . self::COLOR_BRAND_PRIMARY . ' 0%, ' . self::COLOR_BRAND_DARK . ' 100%); color: ' . self::COLOR_TEXT_LIGHT . '; padding: 24px; border-radius: 8px; margin-bottom: 24px; }';
        echo '.devdito-admin-header h1 { margin: 0 0 8px 0; font-size: 24px; font-weight: 600; }';
        echo '.devdito-admin-header p { margin: 0; opacity: 0.9; font-size: 14px; }';

        // Cards
        echo '.devdito-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }';
        echo '.devdito-card h2 { margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #333; border-bottom: 2px solid ' . self::COLOR_BRAND_PRIMARY . '; padding-bottom: 8px; }';

        // Status grid
        echo '.devdito-status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }';
        echo '.devdito-status-item { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; display: flex; align-items: center; gap: 12px; }';
        echo '.devdito-status-indicator { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }';
        echo '.devdito-status-indicator.online { background: ' . self::COLOR_SUCCESS . '; box-shadow: 0 0 8px ' . self::COLOR_SUCCESS . '; }';
        echo '.devdito-status-indicator.offline { background: ' . self::COLOR_ERROR . '; }';
        echo '.devdito-status-indicator.unknown { background: ' . self::COLOR_WARNING . '; }';
        echo '.devdito-status-info { flex: 1; }';
        echo '.devdito-status-name { font-weight: 600; font-size: 14px; color: #333; }';
        echo '.devdito-status-detail { font-size: 12px; color: #666; margin-top: 2px; }';

        // Buttons
        echo '.devdito-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; border-radius: 4px; font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s; }';
        echo '.devdito-btn-primary { background: ' . self::COLOR_BRAND_PRIMARY . '; color: #fff; }';
        echo '.devdito-btn-primary:hover { background: ' . self::COLOR_BRAND_DARK . '; }';
        echo '.devdito-btn-secondary { background: #e0e0e0; color: #333; }';
        echo '.devdito-btn-secondary:hover { background: #d0d0d0; }';
        echo '.devdito-btn:disabled { opacity: 0.6; cursor: not-allowed; }';

        // Config table
        echo '.devdito-config-table { width: 100%; border-collapse: collapse; }';
        echo '.devdito-config-table th, .devdito-config-table td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }';
        echo '.devdito-config-table th { font-weight: 600; color: #333; background: #f8f9fa; }';
        echo '.devdito-config-table td { color: #555; }';
        echo '.devdito-config-value { font-family: monospace; background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 13px; }';

        // Quick actions
        echo '.devdito-actions { display: flex; flex-wrap: wrap; gap: 12px; }';

        echo '</style>';
    }

    /**
     * Render page header.
     *
     * @return void
     */
    private function renderHeader(): void
    {
        echo '<div class="devdito-admin">';
        echo '<div class="devdito-admin-header">';
        echo '<h1>Dev Dito Core Setup</h1>';
        echo '<p>Manage Wiki Embedding Pipeline, service connections, and system status</p>';
        echo '</div>';
    }

    /**
     * Render pipeline orchestration section.
     *
     * @return void
     */
    private function renderPipelineSection(): void
    {
        // Load pipeline CSS and JS
        echo '<link rel="stylesheet" type="text/css" href="' . DOKU_BASE . 'lib/plugins/devdito/dist/pipeline.css">';
        echo '<script src="' . DOKU_BASE . 'lib/plugins/devdito/dist/pipeline.js" defer></script>';

        echo '<div class="devdito-card devdito-pipeline-card">';
        echo '<h2>Wiki Embedding Pipeline</h2>';
        echo '<p style="color: #666; margin-bottom: 16px;">Manage the Wiki content processing pipeline: Fetch, Evaluate, Embed, Deploy.</p>';
        
        // Container for JavaScript to populate
        echo '<div id="devdito-pipeline-stages">';
        echo '<p class="devdito-loading">Lade Pipeline-Status...</p>';
        echo '</div>';
        
        echo '</div>';
    }

    /**
     * Get the configured MCP server URL (DokuWiki config -> Central config).
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
     * Render service status section.
     *
     * @return void
     */
    private function renderServiceStatusSection(): void
    {
        $mcpUrl = $this->getMcpUrl() ?? 'Not configured';

        echo '<div class="devdito-card">';
        echo '<h2>Service Status</h2>';
        echo '<div class="devdito-status-grid">';

        // MCP Server status
        echo '<div class="devdito-status-item" id="devdito-status-mcp">';
        echo '<div class="devdito-status-indicator unknown" id="devdito-indicator-mcp"></div>';
        echo '<div class="devdito-status-info">';
        echo '<div class="devdito-status-name">MCP Server</div>';
        echo '<div class="devdito-status-detail" id="devdito-detail-mcp">Checking...</div>';
        echo '</div>';
        echo '<button class="devdito-btn devdito-btn-secondary" onclick="devditoTestService(\'mcp\')">Test</button>';
        echo '</div>';

        // Qdrant status
        echo '<div class="devdito-status-item" id="devdito-status-qdrant">';
        echo '<div class="devdito-status-indicator unknown" id="devdito-indicator-qdrant"></div>';
        echo '<div class="devdito-status-info">';
        echo '<div class="devdito-status-name">Qdrant Vector DB</div>';
        echo '<div class="devdito-status-detail" id="devdito-detail-qdrant">Checking...</div>';
        echo '</div>';
        echo '<button class="devdito-btn devdito-btn-secondary" onclick="devditoTestService(\'qdrant\')">Test</button>';
        echo '</div>';

        // DokuWiki status (always online if we're here)
        echo '<div class="devdito-status-item">';
        echo '<div class="devdito-status-indicator online"></div>';
        echo '<div class="devdito-status-info">';
        echo '<div class="devdito-status-name">DokuWiki</div>';
        echo '<div class="devdito-status-detail">Running</div>';
        echo '</div>';
        echo '</div>';

        echo '</div>'; // grid
        echo '</div>'; // card
    }

    /**
     * Render configuration section.
     *
     * Shows both DokuWiki config and central config values.
     *
     * @return void
     */
    private function renderConfigurationSection(): void
    {
        // DokuWiki config values
        $enabled = $this->getConf('devdito_enabled') ? 'Enabled' : 'Disabled';
        $mcpUrl = $this->getMcpUrl() ?? 'Not configured';
        $position = $this->getConf('devdito_panel_position');
        if (!$position) {
            $position = ConfigLoader::get('PLUGIN.panel_position', 'right');
        }

        // Central config info
        $configValid = ConfigLoader::isValid();
        $appVersion = ConfigLoader::get('APP.version', 'unknown');
        $qdrantHost = ConfigLoader::get('SERVICES.qdrant.host', 'qdrant_db');
        $qdrantPort = ConfigLoader::get('SERVICES.qdrant.port', 6333);
        $qdrantCollection = ConfigLoader::get('SERVICES.qdrant.collection', 'wiki_embeddings');

        echo '<div class="devdito-card">';
        echo '<h2>Current Configuration</h2>';
        echo '<table class="devdito-config-table">';
        echo '<tr><th>Setting</th><th>Value</th><th>Source</th></tr>';
        echo '<tr><td>Plugin Status</td><td><span class="devdito-config-value">' . hsc($enabled) . '</span></td><td>DokuWiki</td></tr>';
        echo '<tr><td>MCP Server URL</td><td><span class="devdito-config-value">' . hsc($mcpUrl) . '</span></td><td>Central/DokuWiki</td></tr>';
        echo '<tr><td>Panel Position</td><td><span class="devdito-config-value">' . hsc($position) . '</span></td><td>Central/DokuWiki</td></tr>';
        echo '<tr><td>Qdrant</td><td><span class="devdito-config-value">' . hsc($qdrantHost . ':' . $qdrantPort . '/' . $qdrantCollection) . '</span></td><td>Central</td></tr>';
        echo '<tr><td>Plugin Version</td><td><span class="devdito-config-value">' . self::VERSION . '</span></td><td>-</td></tr>';
        echo '<tr><td>App Version (env.yaml)</td><td><span class="devdito-config-value">' . hsc($appVersion) . '</span></td><td>Central</td></tr>';
        echo '<tr><td>Central Config</td><td><span class="devdito-config-value">' . ($configValid ? 'Valid' : 'Invalid/Missing') . '</span></td><td>-</td></tr>';
        echo '</table>';
        echo '<p style="margin-top: 16px; color: #666; font-size: 13px;">';
        echo 'DokuWiki settings: <a href="' . wl('', ['do' => 'admin', 'page' => 'config']) . '#plugin____devdito">Configuration Manager</a> | ';
        echo 'Central settings: <code>config/env.yaml</code>';
        echo '</p>';
        echo '</div>';
    }

    /**
     * Render quick actions section.
     *
     * @return void
     */
    private function renderQuickActionsSection(): void
    {
        echo '<div class="devdito-card">';
        echo '<h2>Quick Actions</h2>';
        echo '<div class="devdito-actions">';
        echo '<button class="devdito-btn devdito-btn-primary" onclick="devditoTestAll()">Test All Services</button>';
        echo '<a href="' . wl('', ['do' => 'admin', 'page' => 'config']) . '#plugin____devdito" class="devdito-btn devdito-btn-secondary">Open Configuration</a>';
        echo '<button class="devdito-btn devdito-btn-secondary" onclick="location.reload()">Refresh Status</button>';
        echo '</div>';
        echo '</div>';

        echo '</div>'; // close devdito-admin container
    }

    /**
     * Render JavaScript for status checks.
     *
     * @return void
     */
    private function renderScripts(): void
    {
        echo '<script>';
        echo 'function devditoTestService(service) {';
        echo '  var indicator = document.getElementById("devdito-indicator-" + service);';
        echo '  var detail = document.getElementById("devdito-detail-" + service);';
        echo '  indicator.className = "devdito-status-indicator unknown";';
        echo '  detail.textContent = "Testing...";';
        echo '  fetch(DOKU_BASE + "lib/exe/ajax.php?call=devdito_admin_test&action=devdito_admin_test&service=" + service)';
        echo '    .then(function(r) { return r.json(); })';
        echo '    .then(function(data) {';
        echo '      indicator.className = "devdito-status-indicator " + (data.ok ? "online" : "offline");';
        echo '      detail.textContent = data.message + (data.latency_ms ? " (" + data.latency_ms + "ms)" : "");';
        echo '    })';
        echo '    .catch(function(e) {';
        echo '      indicator.className = "devdito-status-indicator offline";';
        echo '      detail.textContent = "Error: " + e.message;';
        echo '    });';
        echo '}';
        echo 'function devditoTestAll() {';
        echo '  devditoTestService("mcp");';
        echo '  devditoTestService("qdrant");';
        echo '}';
        echo 'document.addEventListener("DOMContentLoaded", devditoTestAll);';
        echo '</script>';
    }
}

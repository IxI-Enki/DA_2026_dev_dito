<?php

declare(strict_types=1);

/**
 * Dev Dito Plugin - Development Documentation Tool
 *
 * Provides a semantic search interface for wiki content using the MCP server.
 * Uses HTL Leonidas color scheme from the official theme.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito
 * @version    0.1.0-alpha
 */

use dokuwiki\Extension\ActionPlugin;
use dokuwiki\Extension\Event;
use dokuwiki\Extension\EventHandler;

if (!defined('DOKU_INC')) {
    die();
}

/**
 * Action Plugin for Dev Dito semantic search functionality.
 *
 * This plugin provides:
 * - A toggle button in the user tools area
 * - A slide-out panel for semantic search
 * - AJAX endpoints for search and ping operations
 * - HTL Leonidas branded UI styling
 */
class action_plugin_devdito extends ActionPlugin
{
    /** @var bool Flag to prevent duplicate panel injection */
    private bool $panelInjected = false;

    /** @var string Current plugin version for cache busting */
    private const VERSION = '0.1.0';

    /**
     * HTL Color Palette Constants
     */
    private const COLOR_BRAND_PRIMARY = '#B45140';
    private const COLOR_BRAND_DARK = '#8D3A29';
    private const COLOR_BRAND_LIGHT = '#C66451';
    private const COLOR_ACCENT_GOLD = '#C59539';
    private const COLOR_ACCENT_BLUE_LIGHT = '#B4D2E5';
    private const COLOR_ACCENT_BLUE_DARK = '#2F4F7A';
    private const COLOR_BG_DARK = '#282828';
    private const COLOR_BG_ALT = '#404040';
    private const COLOR_TEXT_LIGHT = '#F0F0F0';
    private const COLOR_BORDER = '#555555';
    private const COLOR_MUTED = '#696969';
    private const COLOR_ERROR_BG = 'rgba(141, 33, 50, 0.2)';
    private const COLOR_ERROR_BORDER = '#8D2132';
    private const COLOR_ERROR_TEXT = '#D78775';

    /**
     * Register event handlers with the DokuWiki event system.
     *
     * @param EventHandler $controller The event handler controller
     * @return void
     */
    public function register(EventHandler $controller): void
    {
        $controller->register_hook('TPL_METAHEADER_OUTPUT', 'AFTER', $this, 'handleRegisterAssets');
        $controller->register_hook('TPL_ACT_RENDER', 'AFTER', $this, 'handleInjectPanel');
        $controller->register_hook('TPL_CONTENT_DISPLAY', 'AFTER', $this, 'handleInjectPanel');
        $controller->register_hook('AJAX_CALL_UNKNOWN', 'BEFORE', $this, 'handleAjax');
    }

    /**
     * Register CSS and JS assets in the page header.
     *
     * @param Event $event The TPL_METAHEADER_OUTPUT event
     * @return void
     */
    public function handleRegisterAssets(Event $event): void
    {
        if (!$this->isEnabled()) {
            return;
        }

        $basePath = DOKU_BASE . 'lib/plugins/devdito/dist/';

        $event->data['link'][] = [
            'rel'  => 'stylesheet',
            'type' => 'text/css',
            'href' => $basePath . 'devdito.min.css?v=' . self::VERSION,
        ];

        $event->data['script'][] = [
            'type'   => 'text/javascript',
            'src'    => $basePath . 'devdito.min.js?v=' . self::VERSION,
            '_data'  => '',
        ];
    }

    /**
     * Inject the Dev Dito panel and toggle button into the page.
     *
     * @param Event $event The TPL_ACT_RENDER or TPL_CONTENT_DISPLAY event
     * @return void
     */
    public function handleInjectPanel(Event $event): void
    {
        if ($this->panelInjected || !$this->isEnabled() || !$this->isUserLoggedIn()) {
            return;
        }

        $this->panelInjected = true;

        $position = $this->getConf('devdito_panel_position') ?: 'right';
        $mcpUrl = $this->getConf('devdito_mcp_url') ?: '';

        $this->renderFallbackAssets();
        $this->renderToggleButton();
        $this->renderPanel($position, $mcpUrl);
        $this->renderRelocationScript();
        $this->renderInlineStyles($position);
    }

    /**
     * Handle AJAX requests for semantic search operations.
     *
     * @param Event $event The AJAX_CALL_UNKNOWN event
     * @return void
     */
    public function handleAjax(Event $event): void
    {
        $action = $event->data;

        if ($action !== 'devdito_search' && $action !== 'devdito_ping') {
            return;
        }

        $event->preventDefault();
        $event->stopPropagation();

        header('Content-Type: application/json; charset=utf-8');

        if (!$this->isUserLoggedIn()) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'unauthorized'], 401);
            return;
        }

        if ($action === 'devdito_ping') {
            $this->handlePingRequest();
        } else {
            $this->handleSearchRequest();
        }
    }

    /**
     * Check if the plugin is enabled in configuration.
     *
     * @return bool True if enabled
     */
    private function isEnabled(): bool
    {
        return (bool) $this->getConf('devdito_enabled');
    }

    /**
     * Check if a user is currently logged in.
     *
     * @return bool True if user is logged in
     */
    private function isUserLoggedIn(): bool
    {
        return isset($_SERVER['REMOTE_USER']) && $_SERVER['REMOTE_USER'] !== '';
    }

    /**
     * Send a JSON response with optional HTTP status code.
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

    /**
     * Render fallback asset injection for themes that don't support TPL_METAHEADER_OUTPUT.
     *
     * @return void
     */
    private function renderFallbackAssets(): void
    {
        $basePath = DOKU_BASE . 'lib/plugins/devdito/dist/';
        ptln('<link rel="stylesheet" type="text/css" href="' . hsc($basePath . 'devdito.min.css?v=' . self::VERSION) . '">');
        ptln('<script type="text/javascript" src="' . hsc($basePath . 'devdito.min.js?v=' . self::VERSION) . '"></script>');
    }

    /**
     * Render the toggle button HTML.
     *
     * @return void
     */
    private function renderToggleButton(): void
    {
        ptln('<li class="action devdito" id="devdito-toggle-li">');
        ptln('  <button type="button" id="devdito-toggle" aria-label="Open or close Dev Dito panel" aria-controls="devdito-panel" aria-expanded="false" title="Semantische Wiki-Suche (Dev Dito)" class="devdito-toggle-btn">');
        ptln('    <svg class="devdito-btn-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">');
        ptln('      <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>');
        ptln('    </svg>');
        ptln('    <span class="devdito-btn-text">Wiki durchsuchen</span>');
        ptln('  </button>');
        ptln('</li>');
    }

    /**
     * Render the panel container HTML.
     *
     * @param string $position Panel position ('left' or 'right')
     * @param string $mcpUrl MCP server URL
     * @return void
     */
    private function renderPanel(string $position, string $mcpUrl): void
    {
        ptln('<aside id="devdito-panel" aria-hidden="true" aria-label="Dev Dito semantic search panel" role="complementary" data-position="' . hsc($position) . '" data-mcp-url="' . hsc($mcpUrl) . '" class="devdito-panel-' . hsc($position) . '"></aside>');
    }

    /**
     * Render JavaScript to relocate button to usertools.
     *
     * @return void
     */
    private function renderRelocationScript(): void
    {
        ptln('<script>');
        ptln('(function() {');
        ptln('  function relocateDevDito() {');
        ptln('    var devDitoLi = document.getElementById("devdito-toggle-li");');
        ptln('    var usertools = document.querySelector("#dokuwiki__usertools ul");');
        ptln('    if (usertools && devDitoLi && devDitoLi.parentNode !== usertools) {');
        ptln('      usertools.appendChild(devDitoLi);');
        ptln('    }');
        ptln('  }');
        ptln('  if (document.readyState === "loading") {');
        ptln('    document.addEventListener("DOMContentLoaded", relocateDevDito);');
        ptln('  } else {');
        ptln('    relocateDevDito();');
        ptln('  }');
        ptln('})();');
        ptln('</script>');
    }

    /**
     * Render inline CSS styles using HTL Leonidas color scheme.
     *
     * @param string $position Panel position ('left' or 'right')
     * @return void
     */
    private function renderInlineStyles(string $position): void
    {
        $panelPosition = $position === 'left' ? 'left' : 'right';
        $hiddenOffset = '-320px';
        $shadowDirection = $position === 'left' ? '2px' : '-2px';

        ptln('<style>');

        // Toggle button container
        $this->renderCssRule('#dokuwiki__usertools ul li.devdito', [
            'display'  => 'inline',
            'position' => 'static',
            'float'    => 'none',
        ]);

        // Toggle button
        $this->renderCssRule('#devdito-toggle.devdito-toggle-btn', [
            'position'        => 'static',
            'background'      => 'linear-gradient(180deg, ' . self::COLOR_BRAND_LIGHT . ' 0%, ' . self::COLOR_BRAND_PRIMARY . ' 100%)',
            'color'           => self::COLOR_TEXT_LIGHT,
            'padding'         => '0 0.8em',
            'cursor'          => 'pointer',
            'border'          => 'none',
            'border-radius'   => '3px',
            'font-family'     => 'inherit',
            'font-size'       => 'inherit',
            'font-weight'     => '500',
            'line-height'     => 'inherit',
            'transition'      => 'all 0.3s',
            'text-decoration' => 'none',
            'display'         => 'inline-flex',
            'align-items'     => 'center',
            'gap'             => '0.4em',
            'box-shadow'      => '0px 2px 5px 1px rgba(141, 58, 41, 0.3)',
            'height'          => '21px',
        ]);

        // Toggle button hover
        $this->renderCssRule('#devdito-toggle.devdito-toggle-btn:hover', [
            'background'      => 'linear-gradient(180deg, ' . self::COLOR_BRAND_PRIMARY . ' 0%, ' . self::COLOR_BRAND_DARK . ' 100%)',
            'color'           => '#fff',
            'text-decoration' => 'none',
            'box-shadow'      => '0 4px 16px rgba(141, 58, 41, 0.4)',
        ]);

        // Button icon and text
        $this->renderCssRule('.devdito-btn-icon', [
            'flex-shrink'     => '0',
            'vertical-align'  => 'middle',
            'color'           => self::COLOR_TEXT_LIGHT,
        ]);

        $this->renderCssRule('.devdito-btn-text', [
            'font-weight' => '400',
            'font-size'   => '12px',
            'color'       => self::COLOR_TEXT_LIGHT,
        ]);

        // Panel container
        $this->renderCssRule('#devdito-panel', [
            'position'       => 'fixed',
            'top'            => '0',
            $panelPosition   => $hiddenOffset,
            'width'          => '320px',
            'height'         => '100vh',
            'background'     => self::COLOR_BG_DARK,
            'box-shadow'     => $shadowDirection . ' 0 10px rgba(0,0,0,0.3)',
            'transition'     => $panelPosition . ' 0.3s ease',
            'z-index'        => '998',
            'overflow'       => 'auto',
            'padding'        => '0',
            'display'        => 'flex',
            'flex-direction' => 'column',
        ]);

        $this->renderCssRule('#devdito-panel[aria-hidden="false"]', [
            $panelPosition => '0',
        ]);

        // Panel header
        $this->renderCssRule('#devdito-header', [
            'display'         => 'flex',
            'justify-content' => 'space-between',
            'align-items'     => 'center',
            'padding'         => '12px 16px',
            'background'      => 'linear-gradient(180deg, ' . self::COLOR_BRAND_PRIMARY . ' 0%, ' . self::COLOR_BRAND_DARK . ' 100%)',
            'color'           => self::COLOR_TEXT_LIGHT,
            'flex-shrink'     => '0',
        ]);

        $this->renderCssRule('#devdito-header h3', [
            'margin'      => '0',
            'font-size'   => '14px',
            'font-weight' => '600',
            'color'       => self::COLOR_TEXT_LIGHT,
        ]);

        // Close button
        $this->renderCssRule('#devdito-close', [
            'background'      => 'rgba(255,255,255,0.2)',
            'border'          => 'none',
            'color'           => self::COLOR_TEXT_LIGHT,
            'width'           => '24px',
            'height'          => '24px',
            'border-radius'   => '4px',
            'cursor'          => 'pointer',
            'display'         => 'flex',
            'justify-content' => 'center',
            'align-items'     => 'center',
            'font-size'       => '16px',
            'transition'      => 'background 0.2s',
        ]);

        $this->renderCssRule('#devdito-close:hover', [
            'background' => 'rgba(255,255,255,0.3)',
        ]);

        // Search form
        $this->renderCssRule('#devdito-search-form', [
            'padding'       => '12px 16px',
            'border-bottom' => '1px solid ' . self::COLOR_BORDER,
            'background'    => self::COLOR_BG_ALT,
        ]);

        $this->renderCssRule('#devdito-search-input', [
            'width'         => '100%',
            'padding'       => '8px 12px',
            'border'        => '1px solid ' . self::COLOR_BORDER,
            'border-radius' => '6px',
            'font-size'     => '14px',
            'outline'       => 'none',
            'background'    => self::COLOR_BG_DARK,
            'color'         => self::COLOR_TEXT_LIGHT,
            'transition'    => 'border-color 0.2s, box-shadow 0.2s',
        ]);

        $this->renderCssRule('#devdito-search-input::placeholder', [
            'color' => self::COLOR_MUTED,
        ]);

        $this->renderCssRule('#devdito-search-input:focus', [
            'border-color' => self::COLOR_BRAND_PRIMARY,
            'box-shadow'   => '0 0 0 3px rgba(180, 81, 64, 0.2)',
        ]);

        // Search button
        $this->renderCssRule('#devdito-search-btn', [
            'width'         => '100%',
            'margin-top'    => '8px',
            'padding'       => '8px 16px',
            'background'    => self::COLOR_BRAND_PRIMARY,
            'color'         => self::COLOR_TEXT_LIGHT,
            'border'        => 'none',
            'border-radius' => '6px',
            'font-size'     => '14px',
            'font-weight'   => '500',
            'cursor'        => 'pointer',
            'transition'    => 'background 0.2s',
        ]);

        $this->renderCssRule('#devdito-search-btn:hover', [
            'background' => self::COLOR_BRAND_DARK,
        ]);

        $this->renderCssRule('#devdito-search-btn:disabled', [
            'background' => self::COLOR_BORDER,
            'cursor'     => 'not-allowed',
        ]);

        // Results area
        $this->renderCssRule('#devdito-results', [
            'flex'       => '1',
            'overflow-y' => 'auto',
            'padding'    => '12px 16px',
            'background' => self::COLOR_BG_DARK,
        ]);

        // Result items
        $this->renderCssRule('.devdito-result', [
            'padding'       => '12px',
            'margin-bottom' => '8px',
            'background'    => self::COLOR_BG_ALT,
            'border'        => '1px solid ' . self::COLOR_BORDER,
            'border-radius' => '6px',
            'transition'    => 'border-color 0.2s',
        ]);

        $this->renderCssRule('.devdito-result:hover', [
            'border-color' => self::COLOR_BRAND_PRIMARY,
        ]);

        $this->renderCssRule('.devdito-result-title', [
            'font-weight'   => '600',
            'font-size'     => '14px',
            'color'         => self::COLOR_ACCENT_BLUE_LIGHT,
            'margin-bottom' => '4px',
        ]);

        $this->renderCssRule('.devdito-result-title a', [
            'color'           => self::COLOR_ACCENT_BLUE_LIGHT,
            'text-decoration' => 'none',
        ]);

        $this->renderCssRule('.devdito-result-title a:hover', [
            'color'           => self::COLOR_ACCENT_GOLD,
            'text-decoration' => 'underline',
        ]);

        $this->renderCssRule('.devdito-result-score', [
            'font-size'     => '11px',
            'color'         => self::COLOR_MUTED,
            'margin-bottom' => '6px',
        ]);

        $this->renderCssRule('.devdito-result-text', [
            'font-size'   => '13px',
            'color'       => self::COLOR_TEXT_LIGHT,
            'line-height' => '1.5',
        ]);

        // Loading and status states
        $this->renderCssRule('.devdito-loading', [
            'text-align' => 'center',
            'padding'    => '20px',
            'color'      => self::COLOR_MUTED,
        ]);

        $this->renderCssRule('.devdito-error', [
            'padding'       => '12px',
            'background'    => self::COLOR_ERROR_BG,
            'border'        => '1px solid ' . self::COLOR_ERROR_BORDER,
            'border-radius' => '6px',
            'color'         => self::COLOR_ERROR_TEXT,
            'font-size'     => '13px',
        ]);

        $this->renderCssRule('.devdito-no-results', [
            'text-align' => 'center',
            'padding'    => '20px',
            'color'      => self::COLOR_MUTED,
            'font-style' => 'italic',
        ]);

        ptln('</style>');
    }

    /**
     * Helper method to render a CSS rule.
     *
     * @param string $selector CSS selector
     * @param array<string, string> $properties CSS properties
     * @return void
     */
    private function renderCssRule(string $selector, array $properties): void
    {
        ptln($selector . ' {');
        foreach ($properties as $property => $value) {
            ptln('  ' . $property . ': ' . $value . ';');
        }
        ptln('}');
    }

    /**
     * Handle ping request to check MCP server status.
     *
     * @return void
     */
    private function handlePingRequest(): void
    {
        $mcpUrl = $this->getMcpUrl();
        if ($mcpUrl === null) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'mcp_url_not_configured']);
            return;
        }

        $startTime = microtime(true);
        $timeout = 5;

        $payload = json_encode([
            'jsonrpc' => '2.0',
            'id'      => 'devdito_ping',
            'method'  => 'ping',
        ], JSON_THROW_ON_ERROR);

        $response = $this->sendMcpRequest($mcpUrl, $payload, $timeout);
        $latencyMs = $this->calculateLatency($startTime);

        if ($response['error'] !== null) {
            $this->sendJsonResponse([
                'ok'         => false,
                'error'      => $response['error'],
                'status'     => $response['status'],
                'latency_ms' => $latencyMs,
            ]);
            return;
        }

        $decoded = json_decode($response['body'], true);
        $isOk = is_array($decoded)
            && isset($decoded['result']['ok'])
            && $decoded['result']['ok'] === true;

        $this->sendJsonResponse([
            'ok'         => $isOk,
            'error'      => $isOk ? null : 'invalid_response',
            'latency_ms' => $latencyMs,
        ]);
    }

    /**
     * Handle semantic search request.
     *
     * @return void
     */
    private function handleSearchRequest(): void
    {
        $mcpUrl = $this->getMcpUrl();
        if ($mcpUrl === null) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'mcp_url_not_configured']);
            return;
        }

        $input = file_get_contents('php://input');
        if ($input === false) {
            $this->sendJsonResponse(['ok' => false, 'error' => 'invalid_request'], 400);
            return;
        }

        $body = json_decode($input, true);
        $query = isset($body['query']) && is_string($body['query']) ? trim($body['query']) : '';
        $limit = isset($body['limit']) && is_int($body['limit']) ? $body['limit'] : 5;

        if ($query === '') {
            $this->sendJsonResponse(['ok' => false, 'error' => 'query_empty'], 400);
            return;
        }

        $startTime = microtime(true);
        $timeout = 30;

        $payload = json_encode([
            'jsonrpc' => '2.0',
            'id'      => 'devdito_search_' . time(),
            'method'  => 'tools/call',
            'params'  => [
                'name'      => 'semantic_wiki_search',
                'arguments' => [
                    'query' => $query,
                    'top_k' => min(max($limit, 1), 20),
                ],
            ],
        ], JSON_THROW_ON_ERROR);

        $response = $this->sendMcpRequest($mcpUrl, $payload, $timeout);
        $latencyMs = $this->calculateLatency($startTime);

        if ($response['error'] !== null) {
            $this->sendJsonResponse([
                'ok'         => false,
                'error'      => $response['error'],
                'status'     => $response['status'],
                'latency_ms' => $latencyMs,
            ]);
            return;
        }

        $decoded = json_decode($response['body'], true);

        if (!is_array($decoded)) {
            $this->sendJsonResponse([
                'ok'         => false,
                'error'      => 'invalid_json',
                'latency_ms' => $latencyMs,
            ]);
            return;
        }

        if (isset($decoded['error'])) {
            $this->sendJsonResponse([
                'ok'         => false,
                'error'      => 'rpc_error',
                'message'    => $decoded['error']['message'] ?? 'Unknown error',
                'latency_ms' => $latencyMs,
            ]);
            return;
        }

        $content = $decoded['result']['content'] ?? [];
        $text = $this->extractTextContent($content);

        $this->sendJsonResponse([
            'ok'          => true,
            'query'       => $query,
            'raw_content' => $text,
            'latency_ms'  => $latencyMs,
        ]);
    }

    /**
     * Get the configured MCP server URL.
     *
     * @return string|null The URL or null if not configured
     */
    private function getMcpUrl(): ?string
    {
        $url = $this->getConf('devdito_mcp_url');
        return is_string($url) && $url !== '' ? $url : null;
    }

    /**
     * Send a request to the MCP server.
     *
     * @param string $url MCP server URL
     * @param string $payload JSON-RPC payload
     * @param int $timeout Request timeout in seconds
     * @return array{body: string|null, status: int, error: string|null}
     */
    private function sendMcpRequest(string $url, string $payload, int $timeout): array
    {
        $context = stream_context_create([
            'http' => [
                'timeout'       => $timeout,
                'ignore_errors' => true,
                'method'        => 'POST',
                'header'        => "Content-Type: application/json\r\nAccept: application/json\r\n",
                'content'       => $payload,
            ],
        ]);

        $result = @file_get_contents(rtrim($url, '/'), false, $context);

        $status = 0;
        if (isset($http_response_header) && is_array($http_response_header) && count($http_response_header) > 0) {
            if (preg_match('#\s(\d{3})\s#', $http_response_header[0], $matches)) {
                $status = (int) $matches[1];
            }
        }

        if ($result === false || $status < 200 || $status >= 300) {
            return [
                'body'   => null,
                'status' => $status,
                'error'  => 'connection_failed',
            ];
        }

        return [
            'body'   => $result,
            'status' => $status,
            'error'  => null,
        ];
    }

    /**
     * Calculate latency in milliseconds from start time.
     *
     * @param float $startTime Start time from microtime(true)
     * @return int Latency in milliseconds
     */
    private function calculateLatency(float $startTime): int
    {
        return (int) ((microtime(true) - $startTime) * 1000);
    }

    /**
     * Extract text content from MCP response content array.
     *
     * @param array<int, array{type?: string, text?: string}> $content Content array
     * @return string Combined text content
     */
    private function extractTextContent(array $content): string
    {
        $text = '';
        foreach ($content as $item) {
            if (isset($item['type']) && $item['type'] === 'text' && isset($item['text'])) {
                $text .= $item['text'];
            }
        }
        return $text;
    }
}

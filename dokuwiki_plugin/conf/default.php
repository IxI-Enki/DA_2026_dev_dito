<?php

declare(strict_types=1);

/**
 * Default configuration settings for the Dev Dito plugin.
 *
 * Note: Service URLs (MCP, Qdrant) are now loaded from central config (env.yaml)
 * per Constitution Article II-B. Only UI-related settings remain here.
 *
 * DokuWiki settings serve as OVERRIDES for the central config.
 * If empty, the central config value is used.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Conf
 */

// Plugin enabled/disabled (UI setting)
$conf['devdito_enabled'] = 1;

// MCP Server URL - Leave empty to use central config (config/env.yaml)
// Set a value here to override the central config
$conf['devdito_mcp_url'] = '';

// Panel position - Leave empty to use central config (config/env.yaml)
// Set 'left' or 'right' here to override
$conf['devdito_panel_position'] = '';

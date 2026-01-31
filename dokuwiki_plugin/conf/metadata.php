<?php

declare(strict_types=1);

/**
 * Configuration metadata for the Dev Dito plugin.
 *
 * Defines the configuration options available in the DokuWiki admin interface.
 * Note: Service URLs default to empty and use central config (env.yaml) as fallback.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Conf
 */

$meta['devdito_enabled'] = [
    'onoff',
];

// Empty string allowed (uses central config as fallback)
$meta['devdito_mcp_url'] = [
    'string',
    '_pattern' => '/^(https?:\/\/.+)?$/',  // Allow empty or valid URL
];

// Empty string allowed (uses central config as fallback)
$meta['devdito_panel_position'] = [
    'multichoice',
    '_choices' => ['', 'left', 'right'],  // Empty = use central config
];

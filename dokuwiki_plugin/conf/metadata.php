<?php

declare(strict_types=1);

/**
 * Configuration metadata for the Dev Dito plugin.
 *
 * Defines the configuration options available in the DokuWiki admin interface.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito\Conf
 */

$meta['devdito_enabled'] = [
    'onoff',
];

$meta['devdito_mcp_url'] = [
    'string',
    '_pattern' => '/^https?:\/\/.+/',
];

$meta['devdito_panel_position'] = [
    'multichoice',
    '_choices' => ['left', 'right'],
];

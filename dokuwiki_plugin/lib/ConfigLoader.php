<?php

declare(strict_types=1);

/**
 * ConfigLoader - Loads centralized configuration from settings.json
 *
 * Constitution Article II-B: All configuration from central config/env.yaml.
 * This PHP class reads the auto-generated settings.json file.
 *
 * @license    GPL 2 http://www.gnu.org/licenses/gpl-2.0.html
 * @author     HTL Leonding <dev@htl-leonding.ac.at>
 * @package    DokuWiki\Plugin\DevDito
 */

namespace dokuwiki\plugin\devdito\lib;

/**
 * Loads and provides access to centralized configuration.
 *
 * The configuration is loaded from config/settings.json which is
 * auto-generated from config/env.yaml by the Python config.py script.
 */
class ConfigLoader
{
    /** @var array<string, mixed>|null Cached configuration */
    private static ?array $config = null;

    /** @var string|null Path to the config file */
    private static ?string $configPath = null;

    /**
     * Get the complete configuration array.
     *
     * @return array<string, mixed> Configuration values
     */
    public static function getConfig(): array
    {
        if (self::$config === null) {
            self::$config = self::loadConfig();
        }
        return self::$config;
    }

    /**
     * Get a specific config value by dot-notation path.
     *
     * @param string $path Path using dot notation (e.g., "SERVICES.mcp_server.url")
     * @param mixed $default Default value if path not found
     * @return mixed Config value or default
     *
     * @example
     * ```php
     * $mcpUrl = ConfigLoader::get('SERVICES.mcp_server.url');
     * $timeout = ConfigLoader::get('SERVICES.mcp_server.timeout', 30);
     * ```
     */
    public static function get(string $path, mixed $default = null): mixed
    {
        $keys = explode('.', $path);
        $value = self::getConfig();

        foreach ($keys as $key) {
            if (!is_array($value) || !array_key_exists($key, $value)) {
                return $default;
            }
            $value = $value[$key];
        }

        return $value;
    }

    /**
     * Check if a config path exists.
     *
     * @param string $path Path using dot notation
     * @return bool True if the path exists
     */
    public static function has(string $path): bool
    {
        $keys = explode('.', $path);
        $value = self::getConfig();

        foreach ($keys as $key) {
            if (!is_array($value) || !array_key_exists($key, $value)) {
                return false;
            }
            $value = $value[$key];
        }

        return true;
    }

    /**
     * Get the path to the config file.
     *
     * @return string Absolute path to settings.json
     */
    public static function getConfigPath(): string
    {
        if (self::$configPath === null) {
            // Plugin is in dokuwiki_plugin/, config is in config/
            // Path: dokuwiki_plugin/lib/ConfigLoader.php -> ../../config/settings.json
            self::$configPath = dirname(__DIR__, 2) . '/config/settings.json';
        }
        return self::$configPath;
    }

    /**
     * Reload the configuration from disk.
     *
     * Useful after generating a new settings.json.
     *
     * @return void
     */
    public static function reload(): void
    {
        self::$config = null;
        self::$config = self::loadConfig();
    }

    /**
     * Check if config file exists and is valid.
     *
     * @return bool True if config is loadable
     */
    public static function isValid(): bool
    {
        $configPath = self::getConfigPath();
        if (!file_exists($configPath)) {
            return false;
        }

        $content = file_get_contents($configPath);
        if ($content === false) {
            return false;
        }

        $data = json_decode($content, true);
        return json_last_error() === JSON_ERROR_NONE && is_array($data);
    }

    /**
     * Load configuration from settings.json.
     *
     * @return array<string, mixed> Loaded configuration
     * @throws \RuntimeException If config cannot be loaded
     */
    private static function loadConfig(): array
    {
        $configPath = self::getConfigPath();

        // Check if file exists
        if (!file_exists($configPath)) {
            // Try to generate it
            self::tryGenerateSettingsJson();
        }

        if (!file_exists($configPath)) {
            // Return empty config with fallback values
            return self::getFallbackConfig();
        }

        $content = file_get_contents($configPath);
        if ($content === false) {
            return self::getFallbackConfig();
        }

        /** @var array<string, mixed>|null $config */
        $config = json_decode($content, true);

        if (json_last_error() !== JSON_ERROR_NONE || !is_array($config)) {
            return self::getFallbackConfig();
        }

        return $config;
    }

    /**
     * Try to generate settings.json by calling Python config.py.
     *
     * @return void
     */
    private static function tryGenerateSettingsJson(): void
    {
        $pythonScript = dirname(__DIR__, 2) . '/config.py';
        if (file_exists($pythonScript) && function_exists('exec')) {
            @exec('python "' . $pythonScript . '" 2>&1', $output, $returnCode);
        }
    }

    /**
     * Get fallback configuration when settings.json is not available.
     *
     * Uses default values that match the central PLACEHOLDER_env.yaml.
     *
     * @return array<string, mixed> Fallback configuration
     */
    private static function getFallbackConfig(): array
    {
        return [
            'APP' => [
                'name' => 'dev_dito',
                'version' => '0.0.0',
            ],
            'SERVICES' => [
                'mcp_server' => [
                    'url' => 'http://wiki_dev_mcp_server:3000',
                    'timeout' => 30,
                ],
                'qdrant' => [
                    'host' => 'qdrant_db',
                    'port' => 6333,
                    'collection' => 'wiki_embeddings',
                ],
            ],
            'PLUGIN' => [
                'enabled' => true,
                'panel_position' => 'right',
                'search_results_limit' => 5,
            ],
        ];
    }
}

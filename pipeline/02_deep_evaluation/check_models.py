"""
Check Models - Prüft verfügbare und geladene Modelle in LM Studio

Verwendet `lms list` (LM Studio CLI) um alle verfügbaren Modelle zu listen.
Alle Einstellungen werden aus config/env.yaml geladen.
"""

import json
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config


def check_lm_studio_models():
    """
    Prüft verfügbare Modelle in LM Studio mit `lms list`.
    
    Returns:
        dict: Dictionary mit verfügbaren und geladenen Modellen
    """
    config = get_config()
    llm_cfg = config.raw_config.get('LLM', {})
    lm_studio_cli = llm_cfg.get('lm_studio_cli', 'lms')
    
    result = {
        'available_models': [],
        'loaded_models': [],
        'error': None
    }
    
    try:
        # Run `lms list` command
        process = subprocess.run(
            [lm_studio_cli, 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if process.returncode != 0:
            result['error'] = f"Command failed: {process.stderr}"
            return result
        
        # Parse output (lms list outputs JSON)
        try:
            models_data = json.loads(process.stdout)
            
            # Extract available models
            if isinstance(models_data, list):
                for model in models_data:
                    model_info = {
                        'id': model.get('id', 'unknown'),
                        'name': model.get('name', 'unknown'),
                        'loaded': model.get('loaded', False)
                    }
                    result['available_models'].append(model_info)
                    
                    if model_info['loaded']:
                        result['loaded_models'].append(model_info)
            elif isinstance(models_data, dict):
                # Handle different output formats
                if 'models' in models_data:
                    for model in models_data['models']:
                        model_info = {
                            'id': model.get('id', 'unknown'),
                            'name': model.get('name', 'unknown'),
                            'loaded': model.get('loaded', False)
                        }
                        result['available_models'].append(model_info)
                        
                        if model_info['loaded']:
                            result['loaded_models'].append(model_info)
        except json.JSONDecodeError:
            # If output is not JSON, try to parse as text
            result['error'] = f"Could not parse JSON output: {process.stdout[:200]}"
            
    except FileNotFoundError:
        result['error'] = f"LM Studio CLI not found: '{lm_studio_cli}'. Is it installed and in PATH?"
    except subprocess.TimeoutExpired:
        result['error'] = "Command timed out after 30 seconds"
    except Exception as e:
        result['error'] = f"Unexpected error: {str(e)}"
    
    return result


def main():
    """Hauptfunktion: Zeigt verfügbare und geladene Modelle."""
    print("=" * 70)
    print("  LM STUDIO MODELS CHECK")
    print("=" * 70)
    
    config = get_config()
    llm_cfg = config.raw_config.get('LLM', {})
    base_url = llm_cfg.get('base_url', 'N/A')
    
    print(f"\n  LM Studio URL: {base_url}")
    print(f"  CLI Command:   {llm_cfg.get('lm_studio_cli', 'lms')}")
    print("\n  Checking models...\n")
    
    result = check_lm_studio_models()
    
    if result['error']:
        print(f"  ❌ ERROR: {result['error']}")
        print("\n  Tipp: Stelle sicher dass:")
        print("    - LM Studio installiert ist")
        print("    - `lms` CLI verfügbar ist (in PATH oder vollständiger Pfad in env.yaml)")
        print("    - LM Studio Server läuft")
        sys.exit(1)
    
    print(f"  ✅ Verfügbare Modelle: {len(result['available_models'])}")
    print(f"  ✅ Geladene Modelle:   {len(result['loaded_models'])}")
    
    if result['available_models']:
        print("\n  Verfügbare Modelle:")
        for model in result['available_models']:
            status = "🟢 GELADEN" if model['loaded'] else "⚪ Verfügbar"
            print(f"    {status} - {model['name']} ({model['id']})")
    
    if result['loaded_models']:
        print("\n  Geladene Modelle (für Evaluation verfügbar):")
        for model in result['loaded_models']:
            print(f"    ✅ {model['name']} ({model['id']})")
    else:
        print("\n  ⚠️  WARNUNG: Keine Modelle geladen!")
        print("     Bitte lade ein Modell in LM Studio bevor du die Evaluation startest.")
    
    print("\n" + "=" * 70)
    
    # Return exit code based on whether models are loaded
    return 0 if result['loaded_models'] else 1


if __name__ == "__main__":
    sys.exit(main())

# pipeline/03_rag_preprocessing/tests/test_config_root_dir.py
from pathlib import Path

import config as cfg


def test_root_dir_auto_resolves_to_repo_root(tmp_path, monkeypatch):
    env = tmp_path / "env.yaml"
    env.write_text(
        "PATHS:\n"
        "  root_dir: AUTO\n"
        "  fetched_dir: ${root_dir}/data/fetched\n"
        "  output_dir: ${root_dir}/data/preprocessed\n"
        "  log_dir: ${root_dir}/data/logs\n",
        encoding="utf-8",
    )
    resolved = cfg.load_yaml(env)
    resolved = cfg._apply_root_dir_fallback(resolved)  # helper added in Step 3
    repo_root = str(Path(cfg.__file__).resolve().parents[2])
    assert resolved["PATHS"]["root_dir"] == repo_root

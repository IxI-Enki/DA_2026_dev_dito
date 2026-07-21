# pipeline/04_embeddings_creator/tests/test_config_root_dir.py
from pathlib import Path

import config as cfg  # module under test lives in the package dir


def test_root_dir_auto_resolves_to_module_dir(tmp_path):
    env = tmp_path / "env.yaml"
    env.write_text(
        "PATHS:\n"
        "  root_dir: AUTO\n"
        "  config_dir: ${root_dir}\n"
        "  script_dir: ${root_dir}\n"
        "  output_dir: ${root_dir}/../../data/embeddings\n"
        "  log_dir: ${root_dir}/../../data/logs\n"
        "  preprocessed_base: ${root_dir}/../../data/preprocessed\n"
        "  input_dir: ${preprocessed_base}\n",
        encoding="utf-8",
    )
    resolved = cfg.load_config(str(env))
    module_dir = str(Path(cfg.__file__).resolve().parent)
    assert resolved["PATHS"]["root_dir"] == module_dir
    assert "AUTO" not in resolved["PATHS"]["output_dir"]

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from cyberdrop_dl.managers.manager import Manager

if TYPE_CHECKING:
    from pathlib import Path


def _build_manager(root: Path) -> Manager:
    manager = Manager(("--appdata-folder", str(root), "-d", str(root / "Downloads"), "--download-tiktok-audios"))
    manager.startup()
    return manager


def test_startup_migration_preserves_requested_config(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manager = _build_manager(tmp_path)

    shutil.copytree(manager.path_manager.config_folder / "Default", manager.path_manager.config_folder / "Zeta")
    manager.cache_manager.remove("simp_settings_adjusted")

    fresh_manager = _build_manager(tmp_path)

    assert fresh_manager.config_manager.loaded_config == "Default"


def test_change_config_preserves_cli_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    manager = Manager(
        (
            "--appdata-folder",
            str(tmp_path),
            "-d",
            str(tmp_path / "Downloads"),
            "--download-tiktok-audios",
            "--exclude-images",
        )
    )
    manager.startup()

    shutil.copytree(manager.path_manager.config_folder / "Default", manager.path_manager.config_folder / "Zeta")
    manager.config_manager.change_config("Zeta")

    assert manager.config_manager.settings_data.ignore_options.exclude_images is True

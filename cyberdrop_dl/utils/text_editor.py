from __future__ import annotations

import functools
import logging
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from pathlib import Path

type CMD = list[str] | tuple[str, ...]

# Ordered by preference
_UNIX_TEXT_EDITORS: tuple[CMD, ...] = (
    ("micro", "-keymenu", "true"),
    ("nano",),
    ("vim",),
)


@final
class OSDefaultCMD(str):
    __slots__ = ()


logger = logging.getLogger(__name__)


def open(file_path: Path) -> None:  # noqa: A001
    """Opens file in the OS's text editor."""
    cmd = editor_cmd()
    if not cmd:
        if sys.platform == "win32":
            logger.info("Opening '%s' with the OS's default editor...", file_path)
            os.startfile(file_path)  # noqa: S606
            return

        msg = "No default text editor found"
        raise ValueError(msg)

    cmd = *cmd, file_path
    bin_path = cmd[0]
    pretty_name = f"the OS's default editor ('{bin_path}')" if type(bin_path) is OSDefaultCMD else f"'{bin_path}'"
    logger.info("Opening '%s' with %s...", file_path, pretty_name)
    _ = subprocess.call(cmd, stderr=subprocess.DEVNULL)


@functools.cache
def editor_cmd() -> CMD | None:
    return _editor_cmd()


def _editor_cmd() -> CMD | None:
    if editor := os.environ.get("EDITOR"):
        if cmd := shutil.which(editor):
            return (cmd,)

        import shlex

        cmd, *args = shlex.split(editor)
        if cmd and (bin_path := shutil.which(cmd)):
            return bin_path, *args

        msg = f"Editor '{editor}' from env var $EDITOR is not available. Ignoring"
        logger.warning(msg)

    if sys.platform == "darwin":
        return OSDefaultCMD("open"), "-t", "-n", "-W"

    if sys.platform == "win32":
        return _find_win_editor()

    return _find_unix_editor()


def _find_win_editor() -> CMD | None:
    for path in map(
        os.path.expandvars,
        [
            "%PROGRAMFILES%/Notepad++/notepad++.exe",
            "%PROGRAMFILES(X86)%/Notepad++/notepad++.exe",
            "notepad++.exe",
        ],
    ):
        if notepad_pp := shutil.which(path):
            return notepad_pp, "-multiInst", "-noPlugin", "-notabbar", "-nosession"

    if notepad := shutil.which("notepad.exe"):
        return (notepad,)


def _find_unix_editor() -> CMD | None:
    has_desktop_enviroment = any(var in os.environ for var in ("DISPLAY", "WAYLAND_DISPLAY"))
    if has_desktop_enviroment and "SSH_CONNECTION" not in os.environ and shutil.which("xdg-open"):
        return (OSDefaultCMD("xdg-open"),)

    for bin_path, *args in _UNIX_TEXT_EDITORS:
        if full_path := shutil.which(bin_path):
            return full_path, *args


def xdg_query_default(mimetype: str) -> str:
    cmd = "xdg-mime", "query", "default", mimetype
    process = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return process.stdout.strip()

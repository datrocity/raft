"""Lineage metadata gatherers.

Each function returns a dict fragment ready to be added to a Manifest section.
None of these raise; missing information (no git, no user) yields empty or
best-effort output.
"""

import getpass
import os
import subprocess
import sys
from datetime import datetime, timezone


def timestamp_source():
    """Return the current UTC time as an ISO 8601 string.

    Returns
    -------
    dict
        ``{"created_at": "<ISO 8601 UTC ending in Z>"}``.
    """
    now = datetime.now(timezone.utc).isoformat()
    if now.endswith("+00:00"):
        now = now[: -len("+00:00")] + "Z"
    return {"created_at": now}


def detect_author():
    """Best-effort detection of the current OS user.

    Returns
    -------
    str
        The current OS username, or ``"unknown"`` on failure.
    """
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def detect_activity():
    """Best-effort detection of the running script or notebook name.

    Checks the ``JPY_SESSION_NAME`` environment variable first -- set by
    JupyterLab and Notebook 7+ to the notebook's path for the kernel behind
    it -- then falls back to the running script's filename. Returns None if
    neither is available: a plain REPL, ``python -c``, or an older Jupyter
    frontend that does not set ``JPY_SESSION_NAME``.

    Returns
    -------
    str or None
    """
    session_name = os.environ.get("JPY_SESSION_NAME")
    if session_name:
        return os.path.basename(session_name)
    main = sys.modules.get("__main__")
    script_path = getattr(main, "__file__", None)
    if script_path:
        return os.path.basename(script_path)
    return None


def author_source(author):
    """Return an author dict fragment for a manifest.

    Parameters
    ----------
    author : str

    Returns
    -------
    dict
        ``{"author": author}``.
    """
    return {"author": author}


def activity_source(activity):
    """Return an activity dict fragment for a manifest.

    Parameters
    ----------
    activity : str or None
        The script, notebook, or process name that produced this. None if it
        could not be determined and no override was given.

    Returns
    -------
    dict
        ``{"activity": activity}``.
    """
    return {"activity": activity}


def _git(args, cwd):
    return subprocess.check_output(
        ["git", *args], cwd=cwd, stderr=subprocess.DEVNULL, text=True
    ).strip()


def git_source(cwd=None):
    """Return git information for the repo containing ``cwd``.

    Parameters
    ----------
    cwd : str or pathlib.Path, optional
        Directory to run git from. Defaults to the process CWD.

    Returns
    -------
    dict
        Empty ``{}`` if not in a git repo or git is unavailable. Otherwise
        ``{"code": {"git_sha": str, "dirty": bool, "git_remote": str or None}}``.
    """
    try:
        sha = _git(["rev-parse", "HEAD"], cwd=cwd)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    try:
        status = _git(["status", "--porcelain"], cwd=cwd)
        dirty = bool(status)
    except subprocess.CalledProcessError:
        dirty = False
    try:
        remote = _git(["config", "--get", "remote.origin.url"], cwd=cwd) or None
    except subprocess.CalledProcessError:
        remote = None
    return {"code": {"git_sha": sha, "dirty": dirty, "git_remote": remote}}

"""raft command-line entry point."""

import argparse
import shutil
import sys
from pathlib import Path

import raft


def _install_skills(dest):
    """Copy shipped skill files into ``dest``, creating it if needed.

    Parameters
    ----------
    dest : str or pathlib.Path

    Returns
    -------
    list of pathlib.Path
        The copied file paths.
    """
    src = raft.skills_path()
    dest = Path(dest).expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for md in src.glob("*.md"):
        target = dest / md.name
        shutil.copy2(md, target)
        copied.append(target)
    return copied


def main(argv=None):
    """Command-line entry point for ``raft``.

    Parameters
    ----------
    argv : list of str, optional
        Command line args; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Exit code.
    """
    parser = argparse.ArgumentParser(prog="raft")
    sub = parser.add_subparsers(dest="cmd", required=True)

    install = sub.add_parser(
        "install-skills",
        help="Copy shipped AI skill files into ~/.claude/skills/raft/ (or --dest).",
    )
    install.add_argument(
        "--dest",
        default="~/.claude/skills/raft",
        help="Destination directory (default: ~/.claude/skills/raft)",
    )

    args = parser.parse_args(argv)

    if args.cmd == "install-skills":
        copied = _install_skills(args.dest)
        for p in copied:
            print(f"installed {p}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

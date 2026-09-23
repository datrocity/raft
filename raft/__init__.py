"""raft: experiment-first research catalog."""

from raft.experiment import Experiment
from raft.project import Project, init
from raft.runset import Run, RunSet


def experiment(
    project_name, exp_name, datastore=None, activity=None, author=None, **params
):
    """Short form: create a project and open/create an experiment in one call.

    Parameters
    ----------
    project_name : str
    exp_name : str
    datastore : str
        Filesystem path to the datastore root.
    activity : str, optional
        The script, notebook, or process producing this project's data.
        Auto-detected where possible if omitted.
    author : str, optional
        Overrides the auto-detected OS username.
    **params
        Experiment params as keyword args.

    Returns
    -------
    Experiment
    """
    if datastore is None:
        raise TypeError("datastore is required")
    proj = init(project_name, datastore=datastore, activity=activity, author=author)
    return proj.experiment(exp_name, **params)


def skills_path():
    """Return the path to the shipped ``raft/skills/`` directory.

    Useful for AI assistants that want to symlink or copy the skill files
    into their local skills directory.

    Returns
    -------
    pathlib.Path
    """
    from pathlib import Path

    return Path(__file__).parent / "skills"


__all__ = [
    "Experiment",
    "Project",
    "Run",
    "RunSet",
    "experiment",
    "init",
    "skills_path",
]

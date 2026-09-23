"""Project: the top-level scope for a research catalog."""

import weakref

from raft.artifact import get_artifact_for
from raft.conventions import MANIFEST_SUFFIX, latest_version, next_version
from raft.errors import ArtifactNotFound
from raft.manifest.lineage import (
    activity_source,
    author_source,
    detect_activity,
    detect_author,
    git_source,
    timestamp_source,
)
from raft.manifest.manifest import Manifest
from raft.storage.file_datastore import FileDatastore


class Project:
    """A named research workspace backed by a datastore.

    Parameters
    ----------
    name : str
        Project name, e.g. ``"walker"``.
    datastore : str or Datastore
        Filesystem path (string) or a ``Datastore`` instance.
    activity : str, optional
        The script, notebook, or process producing this project's data.
        Recorded in every manifest written by this project (and by any
        experiment created from it). If omitted, detected automatically
        where possible (see ``detect_activity``); otherwise None.
    author : str, optional
        Overrides the auto-detected OS username for every manifest written
        by this project (and by any experiment created from it).
    """

    def __init__(self, name, datastore, activity=None, author=None):
        self.name = name
        if isinstance(datastore, str):
            self._datastore = FileDatastore(datastore)
        else:
            self._datastore = datastore
        self._datastore.makedirs(name)
        self.author = author if author is not None else detect_author()
        self.activity = activity if activity is not None else detect_activity()
        # Experiments register here on __init__; project.load records loaded
        # URIs into every live entry. WeakSet: grid-loop cleanup is automatic.
        self._active_experiments = weakref.WeakSet()

    def _uri(self, artifact_name, version):
        return f"raft://{self.name}/global/{artifact_name}/v{version}"

    def _artifact_dir(self, artifact_name):
        return f"{self.name}/global/{artifact_name}"

    def _list_artifact_dir(self, artifact_name):
        """Return children of an artifact dir, or [] if the dir does not exist."""
        try:
            return self._datastore.list_dir(self._artifact_dir(artifact_name))
        except KeyError:
            return []

    def _next_version(self, artifact_name):
        return next_version(self._list_artifact_dir(artifact_name))

    def _latest_version(self, artifact_name):
        return latest_version(self._list_artifact_dir(artifact_name))

    def _business_card(self, name, version):
        """Build the stringified 'business card' embedded inside artifacts."""
        import json

        card = {
            "project": self.name,
            "experiment": "global",
            "artifact": name,
            "version": f"v{version}",
            "params": json.dumps({}),
        }
        code = git_source().get("code", {})
        if code:
            card["git_sha"] = code.get("git_sha", "")
            card["dirty"] = str(code.get("dirty", False))
        card.update(timestamp_source())
        card.update(author_source(self.author))
        if self.activity is not None:
            card["activity"] = self.activity
        return {k: str(v) for k, v in card.items()}

    def save(self, data, name, format=None):
        """Save an artifact at the project (global) scope.

        WRITE_ON_CHANGE semantics: if ``joblib.hash(data)`` matches the latest
        version's stored hash, no new version file is written; instead a run
        entry is appended to the existing manifest. Different data creates a
        new numbered version.

        Parameters
        ----------
        data : object
            The data to save. Its type determines the on-disk format via the
            artifact registry.
        name : str
            Artifact name, e.g. ``"processed_input"``.
        format : str, optional
            Opt-in format hint (e.g. ``"csv"`` for a human-readable DataFrame).
            When omitted, the default artifact class for the data type is used.
        """
        import joblib

        art_cls = get_artifact_for(data, format=format)
        art = art_cls()
        data_hash = joblib.hash(data)

        existing_version = self._latest_version(name) if self.has(name) else None
        if existing_version is not None:
            prev_manifest_path = (
                f"{self._artifact_dir(name)}/v{existing_version}{MANIFEST_SUFFIX}"
            )
            prev = Manifest.from_json(
                self._datastore.read(prev_manifest_path).decode("utf-8")
            )
            if prev.sections.get("data_hash") == data_hash:
                self._append_run_to_manifest(name, existing_version)
                return

        version = self._next_version(name)
        card = self._business_card(name, version)
        blob = art.write_bytes(data, metadata=card)
        path = f"{self._artifact_dir(name)}/v{version}.{art.extension}"
        self._datastore.write(path, blob)
        self._write_manifest(name, version, art.extension, data_hash)

    def load(self, name, version=None):
        """Load a version of a project-scope artifact.

        Parameters
        ----------
        name : str
        version : int, optional
            Version number to load (1-based). If omitted, loads the latest.

        Raises
        ------
        ArtifactNotFound
            If no such artifact exists, or the requested version does not exist.
        """
        if not self.has(name):
            raise ArtifactNotFound(f"no artifact '{name}' in project '{self.name}'")
        target = version if version is not None else self._latest_version(name)
        children = self._list_artifact_dir(name)
        try:
            data_file = next(
                c
                for c in children
                if c.startswith(f"v{target}.") and not c.endswith(MANIFEST_SUFFIX)
            )
        except StopIteration:
            raise ArtifactNotFound(
                f"artifact '{name}' has no version v{target} in project '{self.name}'"
            ) from None
        ext = data_file.split(".", 1)[1]
        blob = self._datastore.read(f"{self._artifact_dir(name)}/{data_file}")
        uri = self._uri(name, target)
        # Snapshot: __del__ during iteration or close() could mutate the set.
        for exp in list(self._active_experiments):
            exp._record_input(uri)
        art_cls = _artifact_class_for_extension(ext)
        return art_cls().read_bytes(blob)

    def has(self, name):
        """Return True if the artifact ``name`` exists in this project."""
        return self._latest_version(name) is not None

    def experiment(self, name, **params):
        """Create or reopen an experiment with the given name and params.

        Parameters
        ----------
        name : str
        **params
            Keyword args become the params dict; a single ``params=`` dict is
            also accepted.

        Returns
        -------
        Experiment
        """
        from raft.experiment import Experiment

        if "params" in params and len(params) == 1:
            params = params["params"]
        return Experiment(self, name, params)

    def compute_or_load(self, artifact_name):
        """Return a decorator that caches a zero-arg function as an artifact.

        First call computes and saves; later calls load.

        Parameters
        ----------
        artifact_name : str

        Returns
        -------
        callable
            Decorator to apply to a ``def`` returning the value.
        """
        from raft.compute_or_load import make_compute_or_load

        return make_compute_or_load(self)(artifact_name)

    def runs(self):
        """Return a RunSet of every experiment in this project.

        Returns
        -------
        RunSet
        """
        from raft.runset import load_runs

        return load_runs(self)

    def _write_manifest(self, name, version, extension, data_hash):
        m = Manifest()
        m.add("artifact", name)
        m.add("version", f"v{version}")
        m.add("project", self.name)
        m.add("scope", "global")
        m.add("extension", extension)
        m.add("data_hash", data_hash)
        m.merge("code", git_source().get("code", {}))
        m.merge("provenance", timestamp_source())
        m.merge("provenance", author_source(self.author))
        m.merge("provenance", activity_source(self.activity))
        m.append("runs", self._run_record())
        path = f"{self._artifact_dir(name)}/v{version}{MANIFEST_SUFFIX}"
        self._datastore.write(path, m.to_json().encode("utf-8"))

    def _run_record(self):
        return {
            **timestamp_source(),
            **author_source(self.author),
            **activity_source(self.activity),
        }

    def _append_run_to_manifest(self, name, version):
        path = f"{self._artifact_dir(name)}/v{version}{MANIFEST_SUFFIX}"
        text = self._datastore.read(path).decode("utf-8")
        m = Manifest.from_json(text)
        m.append("runs", self._run_record())
        self._datastore.write(path, m.to_json().encode("utf-8"))


def _artifact_class_for_extension(extension):
    """Find the artifact class registered for a file extension."""
    from raft.artifact import _DEFAULT_REGISTRY

    for cls in set(_DEFAULT_REGISTRY._by_type_and_format.values()):
        if cls.extension == extension:
            return cls
    raise ValueError(f"no artifact class registered for extension '{extension}'")


def init(name, datastore, activity=None, author=None):
    """Create a Project handle.

    Parameters
    ----------
    name : str
    datastore : str or Datastore
    activity : str, optional
        The script, notebook, or process producing this project's data.
        Auto-detected where possible if omitted.
    author : str, optional
        Overrides the auto-detected OS username.

    Returns
    -------
    Project
    """
    return Project(name, datastore, activity=activity, author=author)

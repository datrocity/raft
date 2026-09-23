"""Experiment: a named run with frozen params, backed by a folder."""

import datetime as dt
import json

from raft.artifact import get_artifact_for
from raft.conventions import (
    EXPERIMENT_MANIFEST_FILENAME,
    MANIFEST_SUFFIX,
    PARAMS_FILENAME,
    experiment_folder_name,
    latest_version,
    next_version,
)
from raft.errors import ArtifactNotFound
from raft.manifest.lineage import (
    activity_source,
    author_source,
    git_source,
    timestamp_source,
)
from raft.manifest.manifest import Manifest


class Experiment:
    """A named experiment with frozen params.

    Identity is ``(project, name, params)``. Re-invoking with the same identity
    returns a handle to the existing folder; a subsequent save appends to the
    ``runs:`` list in the affected artifact manifests.

    Parameters
    ----------
    project : Project
    name : str
    params : dict
    """

    def __init__(self, project, name, params):
        self._project = project
        self._datastore = project._datastore
        self.name = name
        self.params = dict(params)
        # dict-as-ordered-set: keys are URIs, values ignored. Preserves
        # insertion order and dedups on repeat loads.
        self._loaded_inputs = {}

        folder_name = experiment_folder_name(dt.date.today(), name, params)
        base = f"{project.name}/{folder_name}"
        actual = self._find_existing_folder(project, name, params)
        if actual is not None:
            self._folder = actual
        else:
            self._folder = base
            self._datastore.makedirs(self._folder)
            self._datastore.write(
                f"{self._folder}/{PARAMS_FILENAME}",
                (json.dumps(self.params, sort_keys=True, indent=2) + "\n").encode(
                    "utf-8"
                ),
            )
            self._write_experiment_manifest()

        project._active_experiments.add(self)

    def __getattr__(self, name):
        """Expose params as attributes: ``exp.lr`` returns ``self.params["lr"]``."""
        try:
            return self.__dict__["params"][name]
        except KeyError:
            raise AttributeError(name) from None

    def _uri(self, artifact_name, version):
        return f"raft://{self._project.name}/{self.name}/{artifact_name}/v{version}"

    def _record_input(self, uri):
        """Add a URI to the experiment's cumulative loaded-inputs set."""
        self._loaded_inputs[uri] = None

    def _resolve_input_name(self, name_or_uri):
        """Turn a user-supplied inputs= entry into a URI.

        Full URIs (``raft://...``) pass through. Short names are resolved to
        this experiment's latest version of that artifact.
        """
        if name_or_uri.startswith("raft://"):
            return name_or_uri
        latest = self._latest_version(name_or_uri)
        if latest is None:
            raise ArtifactNotFound(
                f"cannot resolve inputs='{name_or_uri}': no such artifact "
                f"in experiment '{self.name}'"
            )
        return self._uri(name_or_uri, latest)

    def close(self):
        """Stop tracking loads from ``proj.load`` into this experiment.

        Called automatically when the experiment goes out of Python scope
        (via the ``weakref.WeakSet`` on the project). Explicit ``close()`` is
        only needed when you still hold a reference but want to stop
        cross-scope input tracking.
        """
        self._project._active_experiments.discard(self)

    def __enter__(self):
        """Context-manager sugar: ``with proj.experiment(...) as exp:``."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Auto-close on ``with``-block exit."""
        self.close()
        return False

    def _find_existing_folder(self, project, name, params):
        from raft.conventions import params_hash

        suffix = f"__{name}__{params_hash(params)}"
        try:
            entries = self._datastore.list_dir(project.name)
        except KeyError:
            return None
        for entry in entries:
            if entry == "global":
                continue
            if entry.endswith(suffix):
                return f"{project.name}/{entry}"
        return None

    def _write_experiment_manifest(self):
        m = Manifest()
        m.add("project", self._project.name)
        m.add("experiment", self.name)
        m.add("params", dict(self.params))
        m.merge("code", git_source().get("code", {}))
        m.merge("provenance", timestamp_source())
        m.merge("provenance", author_source(self._project.author))
        m.merge("provenance", activity_source(self._project.activity))
        self._datastore.write(
            f"{self._folder}/{EXPERIMENT_MANIFEST_FILENAME}",
            m.to_json().encode("utf-8"),
        )

    def _artifact_dir(self, artifact_name):
        return f"{self._folder}/{artifact_name}"

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
        card = {
            "project": self._project.name,
            "experiment": self.name,
            "artifact": name,
            "version": f"v{version}",
            "params": json.dumps(self.params, sort_keys=True),
        }
        code = git_source().get("code", {})
        if code:
            card["git_sha"] = code.get("git_sha", "")
            card["dirty"] = str(code.get("dirty", False))
        card.update(timestamp_source())
        card.update(author_source(self._project.author))
        if self._project.activity is not None:
            card["activity"] = self._project.activity
        return {k: str(v) for k, v in card.items()}

    def save(self, data, name, format=None, inputs=None):
        """Save an artifact in this experiment.

        WRITE_ON_CHANGE semantics: identical ``data_hash`` appends a run
        record to the existing manifest; different data creates a new version.

        Parameters
        ----------
        data : object
        name : str
        format : str, optional
            Opt-in format hint (e.g. ``"csv"`` for a human-readable DataFrame).
            When omitted, the default artifact class for the data type is used.
        inputs : list of str, optional
            Override the auto-tracked cumulative inputs. Entries may be short
            artifact names (resolved to the latest version in this experiment)
            or full ``raft://`` URIs. If ``None`` (default), the manifest uses
            the experiment's cumulative loaded-inputs set.
        """
        import joblib

        art_cls = get_artifact_for(data, format=format)
        art = art_cls()
        data_hash = joblib.hash(data)

        if inputs is not None:
            resolved_inputs = [self._resolve_input_name(x) for x in inputs]
        else:
            resolved_inputs = list(self._loaded_inputs)

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
        self._write_artifact_manifest(
            name, version, art.extension, data_hash, resolved_inputs
        )

    def load(self, name, version=None):
        """Load an artifact from this experiment.

        Parameters
        ----------
        name : str
        version : int, optional
            Version to load. Defaults to the latest.

        Raises
        ------
        ArtifactNotFound
        """
        if not self.has(name):
            raise ArtifactNotFound(
                f"no artifact '{name}' in experiment '{self.name}'"
            )
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
                f"artifact '{name}' has no version v{target} "
                f"in experiment '{self.name}'"
            ) from None
        ext = data_file.split(".", 1)[1]
        from raft.project import _artifact_class_for_extension

        blob = self._datastore.read(f"{self._artifact_dir(name)}/{data_file}")
        self._record_input(self._uri(name, target))
        return _artifact_class_for_extension(ext)().read_bytes(blob)

    def has(self, name):
        """Return True if the artifact ``name`` exists in this experiment."""
        return self._latest_version(name) is not None

    def compute_or_load(self, artifact_name):
        """Return a decorator that caches a zero-arg function in this experiment.

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

    def _write_artifact_manifest(self, name, version, extension, data_hash, inputs):
        m = Manifest()
        m.add("artifact", name)
        m.add("version", f"v{version}")
        m.add("project", self._project.name)
        m.add("experiment", self.name)
        m.add("extension", extension)
        m.add("data_hash", data_hash)
        m.add("params", dict(self.params))
        m.merge("code", git_source().get("code", {}))
        m.merge("provenance", timestamp_source())
        m.merge("provenance", author_source(self._project.author))
        m.merge("provenance", activity_source(self._project.activity))
        m.append("runs", self._run_record())
        if inputs:
            m.add("inputs", list(inputs))
        path = f"{self._artifact_dir(name)}/v{version}{MANIFEST_SUFFIX}"
        self._datastore.write(path, m.to_json().encode("utf-8"))

    def _run_record(self):
        return {
            **timestamp_source(),
            **author_source(self._project.author),
            **activity_source(self._project.activity),
        }

    def _append_run_to_manifest(self, name, version):
        path = f"{self._artifact_dir(name)}/v{version}{MANIFEST_SUFFIX}"
        text = self._datastore.read(path).decode("utf-8")
        m = Manifest.from_json(text)
        m.append("runs", self._run_record())
        self._datastore.write(path, m.to_json().encode("utf-8"))

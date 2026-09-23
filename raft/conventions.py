"""Path conventions, write modes, and canonicalization helpers.

Pure functions and enums only. No I/O.
"""

import enum
import hashlib
import json

PARAMS_FILENAME = "params.json"
EXPERIMENT_MANIFEST_FILENAME = "manifest.json"
MANIFEST_SUFFIX = ".manifest.json"


class WriteMode(enum.Enum):
    """Behavior when writing an artifact that may already have a prior version.

    v1 ships a single mode; the enum is kept for future extension.
    """

    WRITE_ON_CHANGE = "write_on_change"


def canonicalize_params(params):
    """Serialize a params dict in a canonical form: sorted keys, JSON.

    Parameters
    ----------
    params : dict
        Mapping of JSON-safe values.

    Returns
    -------
    str
        Canonical JSON string with sorted keys at every level.
    """
    return json.dumps(params, sort_keys=True, separators=(", ", ": "))


def params_hash(params):
    """Compute a short stable hash of a params dict.

    Parameters
    ----------
    params : dict

    Returns
    -------
    str
        First 8 hex chars of the SHA-256 of the canonical form (~4B possible
        values -- collisions are vanishingly unlikely for research-scale use).
    """
    canonical = canonicalize_params(params).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()[:8]


def experiment_folder_name(creation_date, name, params):
    """Compose an experiment folder name from date, name, and params hash.

    Parameters
    ----------
    creation_date : datetime.date
        The date the experiment folder was first created.
    name : str
        Human-chosen experiment name.
    params : dict
        Params used to compute the disambiguating hash.

    Returns
    -------
    str
        A folder name in the form ``YYYY-MM-DD__<name>__<hash>``.
    """
    return f"{creation_date.isoformat()}__{name}__{params_hash(params)}"


def is_data_file(filename):
    """Return True if ``filename`` is a versioned artifact data file.

    Excludes the per-version manifest file (``v{N}.manifest.json``), which
    shares the ``v{N}`` prefix but is not the data file itself.

    Parameters
    ----------
    filename : str

    Returns
    -------
    bool
    """
    return filename.startswith("v") and not filename.endswith(MANIFEST_SUFFIX)


def parse_version(filename):
    """Extract the version number from a versioned filename like ``v3.parquet``.

    Parameters
    ----------
    filename : str

    Returns
    -------
    int or None
        None if the filename does not start with ``v<digits>``.
    """
    try:
        return int(filename.split(".")[0][1:])
    except ValueError:
        return None


def latest_version(children):
    """Return the highest existing version number among data files.

    Parameters
    ----------
    children : iterable of str
        Filenames in an artifact directory.

    Returns
    -------
    int or None
        None if there are no data files.
    """
    nums = [n for n in (parse_version(c) for c in children if is_data_file(c))
            if n is not None]
    return max(nums) if nums else None


def next_version(children):
    """Return the version number to use for a new save.

    Parameters
    ----------
    children : iterable of str
        Filenames in an artifact directory.

    Returns
    -------
    int
        One past the current latest version, or 1 if there are none yet.
    """
    latest = latest_version(children)
    return (latest + 1) if latest is not None else 1

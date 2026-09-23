"""Manifest: a container of named metadata sections that round-trips through JSON."""

import json


class Manifest:
    """A named collection of metadata sections.

    Sections can be dicts (merged), lists (appended), or scalars (replaced).
    The manifest serializes to JSON with insertion-preserving key order.
    """

    def __init__(self, sections=None):
        self.sections = dict(sections) if sections else {}

    def add(self, section, data):
        """Set or replace a section.

        Parameters
        ----------
        section : str
        data : dict, list, or scalar
        """
        self.sections[section] = data

    def merge(self, section, data):
        """Merge a dict into a section, creating the section if missing.

        Parameters
        ----------
        section : str
        data : dict
        """
        existing = self.sections.setdefault(section, {})
        existing.update(data)

    def append(self, section, entry):
        """Append ``entry`` to a list-valued section, creating it if missing.

        Parameters
        ----------
        section : str
        entry : any
        """
        existing = self.sections.setdefault(section, [])
        existing.append(entry)

    def to_json(self):
        """Return the manifest as a JSON string."""
        return json.dumps(self.sections, indent=2) + "\n"

    @classmethod
    def from_json(cls, text):
        """Parse a JSON string into a Manifest.

        Returns
        -------
        Manifest
        """
        data = json.loads(text) or {}
        return cls(sections=data)

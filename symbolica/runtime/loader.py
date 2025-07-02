"""
symbolica.runtime.loader
========================
Load and hot-reload a *rule-pack* produced by the Symbolica compiler.

v1 format  (JSON bytes, UTF-8):

{
  "header": {
      "version": "1",
      "built":   "2025-07-01T13:00:55Z",
      "status_precedence": ["REJECTED","ESCALATE","PARTIAL","APPROVED"],
      "agents": {                       # agent → list[int]  (rule indices)
          "PolicyValidator": [0, 3, 5],
          "DriverVerifier":  [1, 2],
          "ClaimDecider":   [0,1,2,3,4,5]
      }
  },
  "rules": [ {id:..., priority:..., if:..., then:{set:{...}}}, ... ]
}

The loader mmaps the file (read-only) so large rule-packs cost ~0 extra RAM.
"""


from __future__ import annotations

import json
import mmap
import pathlib
import threading
import time
from typing import Any, Dict, List

_LOCK = threading.RLock()


class RulePack:
    """
    In-memory view of a rule-pack.

    Only *header* is parsed to real Python objects.  The *rules* list lives
    in the mmapped bytes until first access, then is cached.
    """

    def __init__(self, path: str | pathlib.Path):
        self.path = pathlib.Path(path)
        self._mmap: mmap.mmap | None = None
        self.header: Dict[str, Any] = {}
        self.rules: List[Dict[str, Any]] = []
        self._mtime: float = 0.0
        self._load()

    # ───────────────────────────── internal helpers ──────────────────────────
    def _load(self) -> None:
        """(Re)load file into mmap + parse JSON."""
        if self._mmap:
            self._mmap.close()

        with self.path.open("rb") as fh:
            self._mmap = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            data = json.loads(self._mmap[:])  # small (< MB) so ok to parse

        self.header = data["header"]
        self.rules = data["rules"]
        self._mtime = self.path.stat().st_mtime

    # ───────────────────────────── public api ────────────────────────────────
    def reload_if_modified(self) -> None:
        """Hot-reload if the rule-pack file was replaced."""
        if self.path.stat().st_mtime != self._mtime:
            with _LOCK:
                if self.path.stat().st_mtime != self._mtime:  # double-check
                    self._load()

    def dag_for_agent(self, agent: str) -> List[int]:
        """
        Return the list of rule indices for *agent* in priority order.
        Raises KeyError if agent unknown.
        """
        return self.header["agents"][agent]


# ───────────────────────────── module-level singleton ───────────────────────
_PACK: RulePack | None = None


def load_pack(path: str | pathlib.Path) -> RulePack:
    """
    Load the given rule-pack file and replace any previously loaded pack.

    Call this once at service start-up **or** during CLI compile→run flows.
    """
    global _PACK
    _PACK = RulePack(path)
    return _PACK


def get_pack() -> RulePack:
    """Return the currently loaded RulePack, or raise if none loaded."""
    if _PACK is None:
        raise RuntimeError("RulePack not loaded; call symbolica.load_pack()")
    _PACK.reload_if_modified()
    return _PACK

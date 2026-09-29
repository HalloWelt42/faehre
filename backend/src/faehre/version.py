"""Liest die Version aus version.json, der einzigen Quelle der Wahrheit."""

import json
from functools import lru_cache

from pydantic import BaseModel

from faehre.config import PROJEKT_WURZEL


class Version(BaseModel):
    version: str
    id: str
    voll: str


@lru_cache(maxsize=1)
def lies_version() -> Version:
    daten = json.loads((PROJEKT_WURZEL / "version.json").read_text(encoding="utf-8"))
    return Version.model_validate(daten)

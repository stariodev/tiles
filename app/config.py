import os
from dataclasses import dataclass, fields
from typing import Any


@dataclass(frozen=True, slots=True)
class Config:
    """Every setting. A new setting is one field with a default.

    `from_env` reads each field from the env var of the same name in capitals
    (`frame_ancestors` from `FRAME_ANCESTORS`) and casts it to the type of the default.
    """

    # Origins that may show the board in an <iframe>, separated by spaces, e.g.
    # "https://stario.dev". Empty: no other site may frame it.
    frame_ancestors: str = ""

    @classmethod
    def from_env(cls) -> Config:
        values: dict[str, Any] = {}
        for f in fields(cls):
            raw = os.environ.get(f.name.upper())
            if raw is None:
                continue
            if isinstance(f.default, bool):
                values[f.name] = raw.lower() in ("1", "true", "yes")
            else:
                values[f.name] = type(f.default)(raw)
        return cls(**values)

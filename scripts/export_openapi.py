"""CLI to dump the application's OpenAPI schema to ``docs/openapi.json``.

Run from the project root so ``app`` is importable::

    python -m scripts.export_openapi

The output is deterministic (keys sorted, 2-space indent) so the committed
snapshot only changes when the API surface actually changes. The docs CI job
runs this to validate that the app imports and the schema generates.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

_OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths = len(schema.get("paths", {}))
    print(f"Wrote {_OUTPUT} ({paths} paths, OpenAPI {schema.get('openapi')})")


if __name__ == "__main__":
    main()

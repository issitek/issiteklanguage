"""Exporta el contrato OpenAPI de la API a `packages/shared/openapi.json`.

Uso (desde `services/api`, con el venv activo):

    python scripts/export_openapi.py

El archivo se versiona y CI verifica que no haya drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
OUTPUT = REPO_ROOT / "packages" / "shared" / "openapi.json"

sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI escrito en {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

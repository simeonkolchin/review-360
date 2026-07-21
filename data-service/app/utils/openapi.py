import os

import yaml
from fastapi import FastAPI

SPEC_DIR = "openapi_spec"


def save_openapi_spec(app: FastAPI, filename: str = "data-service-1.0.0.yaml") -> None:
    """Persist the generated OpenAPI spec next to the service, like the reference project."""
    try:
        os.makedirs(SPEC_DIR, exist_ok=True)
        with open(os.path.join(SPEC_DIR, filename), "w", encoding="utf-8") as file:
            yaml.dump(app.openapi(), file, allow_unicode=True, sort_keys=False)
    except Exception:
        # Never let spec dumping break startup.
        pass

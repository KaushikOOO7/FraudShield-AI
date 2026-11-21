"""Export the executable schema, never a fabricated investigation response."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.core.config import PROJECT_ROOT, Settings
from backend.app.main import create_app


def main():
    app = create_app(Settings(app_env="test", _env_file=None))
    destination = PROJECT_ROOT / "docs/openapi.json"
    destination.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print("Exported", destination.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()

"""Developer utility: freeze the first schema, refusing to overwrite revisions."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

from backend.app.core.config import PROJECT_ROOT
from backend.app.database.models import Base


def main():
    for name, dialect in (("sqlite", sqlite.dialect()), ("postgresql", postgresql.dialect())):
        path = PROJECT_ROOT / "backend/migrations" / name / "0001_core.sql"
        if path.exists():
            raise SystemExit("Initial migrations already exist; use a new revision")
        path.parent.mkdir(parents=True, exist_ok=True)
        statements = []
        for table in Base.metadata.sorted_tables:
            statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
            for index in sorted(table.indexes, key=lambda x: x.name):
                statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        path.write_text("-- Frozen initial schema. Do not edit after deployment.\n" + "\n\n-- statement-breakpoint\n\n".join(statements) + "\n")
        print("Created", path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()

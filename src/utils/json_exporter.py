from pathlib import Path
from typing import Any, Iterable, List
import json

class JsonExporter:
    @staticmethod
    def write_array(path: Path, records: List[Any]) -> None:
        """
        Write the full dataset as a JSON array with UTF-8 encoding and stable formatting.
        """
        path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def write_lines(path: Path, records: Iterable[Any]) -> None:
        """
        Write JSON Lines format (one object per line).
        """
        with path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
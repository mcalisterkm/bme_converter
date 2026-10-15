"""Generic container reader for Bosch UDF files."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class UDFContainer:
    """UDF metadata and opaque binary payload."""

    version: str
    fields: List[Dict[str, Any]]
    binary_data: bytes
    source_path: Path


class UDFContainerReader:
    """Read the common metadata/payload envelope of a UDF file."""

    METADATA_DELIMITER = b"\r\n\r\n\r\n"
    FIELD_PATTERN = re.compile(
        r"^(\d+):\s*([^:]+):\s*(\d+):\s*([^:]+):\s*"
        r"([^:]+):\s*([^:]+):\s*([^:]+):\s*(.+)$"
    )

    def read(self, file_path: str) -> UDFContainer:
        path = Path(file_path)
        with path.open("rb") as input_file:
            content = input_file.read()

        delimiter_position = content.find(self.METADATA_DELIMITER)
        if delimiter_position == -1:
            raise ValueError("Could not find metadata delimiter in UDF file")

        metadata = content[:delimiter_position].decode("utf-8", errors="ignore")
        binary_start = delimiter_position + len(self.METADATA_DELIMITER)
        version, fields = self._parse_metadata(metadata)
        return UDFContainer(
            version=version,
            fields=fields,
            binary_data=content[binary_start:],
            source_path=path,
        )

    @classmethod
    def _parse_metadata(
        cls, metadata: str
    ) -> tuple:
        lines = metadata.strip().splitlines()
        if not lines or not lines[0].strip():
            raise ValueError("Empty metadata section in UDF file")

        version = lines[0].strip()
        fields = []
        for line in lines[1:]:
            match = cls.FIELD_PATTERN.match(line.strip())
            if match is None:
                continue

            fields.append(
                {
                    "id": int(match.group(1)),
                    "name": match.group(2).strip(),
                    "size": int(match.group(3)),
                    "type": match.group(4).strip(),
                    "flags": match.group(5).strip(),
                    "val1": match.group(6).strip(),
                    "val2": match.group(7).strip(),
                    "status": match.group(8).strip(),
                }
            )
        return version, fields

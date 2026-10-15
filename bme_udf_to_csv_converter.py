"""Convert collection UDF files to CSV through the canonical session model."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bme_udf_parser import BMEUDFParser


def parse_udf_file(
    file_path: str,
) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]]]:
    """Parse a collection UDF and return canonical records and metadata."""
    parser = BMEUDFParser(file_path)
    version, fields, _ = parser.parse()
    return parser.extract_records(), version, fields


def save_to_csv(records: List[Dict[str, Any]], output_path: str) -> None:
    """Save canonical collection records to CSV."""
    if not records:
        raise ValueError("No records to save")

    fieldnames = list(records[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert collection BME .udf files to CSV"
    )
    parser.add_argument("input_file", help="Input .udf file")
    parser.add_argument("-o", "--output", help="Output CSV file")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".csv")
    records, _, _ = parse_udf_file(str(input_path))
    save_to_csv(records, str(output_path))
    print(f"CSV saved: {output_path}")
    print(f"Done! {len(records)} records converted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

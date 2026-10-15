"""Collection UDF parser backed by the canonical packed-record decoder."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from bme_udf_to_rawdata import UDFToRawDataConverter


class BMEUDFParser:
    """Read collection UDF files through the canonical session pipeline."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.converter = UDFToRawDataConverter(str(self.file_path))
        self.version = None
        self.fields = []
        self.binary_data = None
        self._session = None

    def parse(self) -> Tuple[str, List[Dict[str, Any]], bytes]:
        self.version, self.fields, self.binary_data = self.converter.parse_udf()
        return self.version, self.fields, self.binary_data

    def extract_records(self) -> List[Dict[str, Any]]:
        session = self._read_session()
        column_names = [column.name for column in session.measurements.columns]
        return [
            {
                name: value
                for name, value in zip(column_names, row)
            }
            for row in session.measurements.data.loc[
                :, column_names
            ].itertuples(index=False, name=None)
        ]

    def to_csv(self, output_path: str = None) -> str:
        output = Path(output_path) if output_path else self.file_path.with_suffix(".csv")
        self._read_session().measurements.data.to_csv(output, index=False)
        return str(output)

    def to_excel(self, output_path: str = None) -> str:
        output = Path(output_path) if output_path else self.file_path.with_suffix(".xlsx")
        self._read_session().measurements.data.to_excel(
            output,
            index=False,
            engine="openpyxl",
        )
        return str(output)

    def _read_session(self):
        if self._session is None:
            self._session = self.converter.read_session()
            self.version = self.converter.udf_version
            self.fields = self.converter.udf_fields
            self.binary_data = self.converter.binary_data
        return self._session


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse collection BME .udf files and convert to CSV or Excel"
    )
    parser.add_argument("input_file", help="Input .udf file")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "excel"],
        default="csv",
        help="Output format (default: csv)",
    )
    args = parser.parse_args()

    parser_obj = BMEUDFParser(args.input_file)
    output = (
        parser_obj.to_csv(args.output)
        if args.format == "csv"
        else parser_obj.to_excel(args.output)
    )
    print(f"Created: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert a BME AI Studio Mobile test ``.udf`` to ``.aipredictions``.

Like the Bosch converter, this needs the ``.udf``, the ``.aiconfig`` and the
board configuration (``.bmeconfig``). The ``.bmerawdata`` is written alongside.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from bme_ai_predictions import (
    NoPredictionsError,
    extract_predictions,
    validate_ai_config,
)
from bme_aipredictions_writer import AIPredictionsWriter
from bme_board_config_reader import BoardConfigReader
from bme_udf_frames import read_device_info
from bme_udf_to_rawdata import UDFToRawDataConverter


def _single_match(directory: Path, patterns: List[str], what: str) -> Path:
    matches = sorted({p for pattern in patterns for p in directory.glob(pattern)})
    if len(matches) != 1:
        found = "none found" if not matches else ", ".join(p.name for p in matches)
        raise FileNotFoundError(
            f"Could not auto-detect the {what} in {directory} ({found}). "
            "Please specify it explicitly."
        )
    return matches[0]


def default_output_stem(udf_path: Path) -> str:
    """Bosch names outputs ``bme_*`` for ``bsec_*`` UDF logs."""
    stem = udf_path.stem
    return "bme_" + stem[len("bsec_"):] if stem.startswith("bsec_") else stem


def convert_ai_test(
    udf_path: str,
    ai_config_path: Optional[str] = None,
    board_config_path: Optional[str] = None,
    labelinfo_path: Optional[str] = None,
    output_dir: Optional[str] = None,
    write_rawdata: bool = True,
) -> Tuple[str, Optional[str]]:
    """Return ``(aipredictions_path, bmerawdata_path_or_None)``."""
    udf = Path(udf_path)
    directory = udf.parent
    output_directory = Path(output_dir) if output_dir else directory
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = default_output_stem(udf)

    ai_config_file = (
        Path(ai_config_path)
        if ai_config_path
        else _single_match(directory, ["*.aiconfig"], ".aiconfig file")
    )
    if board_config_path is None:
        board_config_path = str(
            _single_match(directory, ["*.bmeconfig"], "board configuration")
        )
    if labelinfo_path is None:
        for candidate in (
            directory / f"{stem}.bmelabelinfo",
            directory / f"{stem}.labelinfo",
        ):
            if candidate.exists():
                labelinfo_path = str(candidate)
                break

    with open(ai_config_file, "r", encoding="utf-8-sig") as handle:
        ai_config = json.load(handle)
    model_type = validate_ai_config(ai_config)
    BoardConfigReader().read(board_config_path)

    converter = UDFToRawDataConverter(
        str(udf), board_config_path, labelinfo_path
    )
    converter.load_config()
    converter.parse_udf()
    rawdata_records = converter.extract_records()
    stream = converter.frame_stream

    try:
        predictions = extract_predictions(stream, model_type)
    except NoPredictionsError as error:
        if write_rawdata:
            rawdata_path = converter.save(
                str(output_directory / f"{stem}.bmerawdata")
            )
            raise NoPredictionsError(
                f"{error} Only the .bmerawdata was written: {rawdata_path}"
            ) from error
        raise
    bsec_version = read_device_info(stream).get(
        "bsec_version",
        ai_config["aiConfigBody"].get("trainingResults", {}).get("bsecVersion", ""),
    )

    predictions_path = AIPredictionsWriter().write(
        ai_config,
        converter.generate_raw_data_header(),
        bsec_version,
        predictions,
        str(output_directory / f"{stem}.aipredictions"),
    )

    rawdata_path = None
    if write_rawdata:
        rawdata_path = converter.save(str(output_directory / f"{stem}.bmerawdata"))
    return predictions_path, rawdata_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert BME AI Studio Mobile test .udf files to "
        ".aipredictions (and .bmerawdata)"
    )
    parser.add_argument("input_file", help="Input .udf file")
    parser.add_argument("-a", "--aiconfig", help=".aiconfig file (auto-detected)")
    parser.add_argument("-c", "--config", help=".bmeconfig file (auto-detected)")
    parser.add_argument("-l", "--labelinfo", help=".labelinfo/.bmelabelinfo file")
    parser.add_argument(
        "-o", "--output-dir", help="Output directory (default: next to the .udf)"
    )
    parser.add_argument(
        "--no-rawdata", action="store_true", help="Do not write the .bmerawdata"
    )
    args = parser.parse_args()

    try:
        predictions_path, rawdata_path = convert_ai_test(
            args.input_file,
            args.aiconfig,
            args.config,
            args.labelinfo,
            args.output_dir,
            not args.no_rawdata,
        )
    except NoPredictionsError as error:
        print(f"No .aipredictions produced: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Predictions: {predictions_path}")
    if rawdata_path:
        print(f"Raw data:    {rawdata_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Extract AI model predictions from a UDF frame stream."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bme_udf_frames import UDFFrameStream, decode_value

# Gas 1-4 estimate fields carry the class/target predictions (float + accuracy)
PREDICTION_FIELD_IDS = (22, 23, 24, 25)

_REQUIRED_FIELD_IDS = (26, 40, 41, 44, 45)

DATA_COLUMNS: List[Dict[str, Any]] = [
    {"name": "Sensor Index", "unit": "", "format": "integer", "key": "sensor_index"},
    {"name": "Sensor ID", "unit": "", "format": "integer", "key": "sensor_id"},
    {
        "name": "Start Time Since PowerOn",
        "unit": "Milliseconds",
        "format": "integer",
        "key": "start_time_since_poweron",
    },
    {
        "name": "End Time Since PowerOn",
        "unit": "Milliseconds",
        "format": "integer",
        "key": "end_time_since_poweron",
    },
    *[
        {
            "name": f"Class/Target {n} prediction",
            "unit": "",
            "format": "float",
            "key": f"classtarget_{n}_prediction",
        }
        for n in range(1, 5)
    ],
    {
        "name": "Prediction accuracy",
        "unit": "",
        "format": "integer",
        "key": "prediction_accuracy",
    },
    {"name": "IAQ", "unit": "", "format": "float", "key": "iaq"},
    {"name": "IAQ accuracy", "unit": "", "format": "integer", "key": "iaq_accuracy"},
    {"name": "Error code", "unit": "", "format": "integer", "key": "error_code"},
    {
        "name": "Ground truth",
        "unit": "classId",
        "format": "integer",
        "key": "ground_truth",
    },
]
for _index, _column in enumerate(DATA_COLUMNS, start=1):
    _column["colId"] = _index


class NoPredictionsError(ValueError):
    """The UDF does not contain the data needed to build predictions."""


@dataclass
class AIPredictions:
    columns: List[Dict[str, Any]]
    rows: List[List[Any]]


def validate_ai_config(document: Dict[str, Any]) -> str:
    """Check the ``.aiconfig`` structure and return the model type."""
    body = document.get("aiConfigBody")
    if not isinstance(document.get("aiConfigHeader"), dict) or not isinstance(
        body, dict
    ):
        raise ValueError(
            "AI config must contain 'aiConfigHeader' and 'aiConfigBody'"
        )
    model_type = body.get("type")
    if model_type not in ("classification", "regression"):
        raise ValueError(f"Unsupported AI model type: {model_type!r}")
    return model_type


def _round_prediction(value: float) -> Any:
    """Match Bosch output: 8 decimal places, integral values as ints."""
    rounded = round(value, 8)
    return int(rounded) if rounded.is_integer() else rounded


def extract_predictions(
    stream: UDFFrameStream, model_type: Optional[str] = None
) -> AIPredictions:
    """Build one prediction row per sensor per completed scanning cycle."""
    schema = stream.schema
    missing_schema = [
        field_id
        for field_id in PREDICTION_FIELD_IDS + _REQUIRED_FIELD_IDS
        if field_id not in schema
    ]
    if missing_schema:
        raise NoPredictionsError(
            "UDF schema does not define field ids "
            + ", ".join(map(str, missing_schema))
        )

    def value(frame, field_id):
        return decode_value(frame.fields[field_id], schema[field_id]["type"])

    cycle_start_ms: Dict[int, int] = {}
    rows: List[List[Any]] = []
    for frame in stream.frames:
        if not all(field_id in frame.fields for field_id in _REQUIRED_FIELD_IDS):
            continue
        sensor_index = value(frame, 40)[0]
        if value(frame, 26)[0] == 0 or sensor_index not in cycle_start_ms:
            cycle_start_ms[sensor_index] = frame.timestamp_ms

        if not all(field_id in frame.fields for field_id in PREDICTION_FIELD_IDS):
            continue
        estimates = [value(frame, field_id) for field_id in PREDICTION_FIELD_IDS]
        rows.append(
            [
                sensor_index,
                value(frame, 41)[0],
                cycle_start_ms[sensor_index],
                frame.timestamp_ms,
                *[_round_prediction(estimate[0]) for estimate in estimates],
                estimates[0][1],
                None,
                None,
                value(frame, 45)[0],
                value(frame, 44)[0],
            ]
        )

    if not rows:
        if model_type == "regression":
            raise NoPredictionsError(
                "This is a regression model test. Regression outputs are "
                "computed on the device and are not logged in the .udf "
                "(no class/target prediction fields are present), so an "
                ".aipredictions file cannot be produced."
            )
        raise NoPredictionsError(
            "The .udf contains no AI prediction frames (fields 22-25); an "
            ".aipredictions file cannot be produced."
        )
    return AIPredictions(columns=[dict(c) for c in DATA_COLUMNS], rows=rows)

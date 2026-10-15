"""Writer for Bosch collection ``.bmerawdata`` files."""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from bme_model import SessionModel


class BMERawDataWriter:
    """Serialize a canonical collection session as Bosch raw data JSON."""

    def write(self, session: SessionModel, output_path: str) -> str:
        if not session.raw_document:
            raise ValueError("Session does not contain a source raw-data document")

        document = copy.deepcopy(session.raw_document)
        document["configHeader"] = dict(session.board_config.header)
        document["configBody"] = self._configuration_body(session)

        raw_data_body = document.setdefault("rawDataBody", {})
        raw_data_body["dataColumns"] = [
            column.to_dict() for column in session.measurements.columns
        ]
        raw_data_body["dataBlock"] = self._data_block(session)

        path = Path(output_path)
        with path.open("w", encoding="utf-8") as output_file:
            json.dump(document, output_file, indent=2, ensure_ascii=False)
            output_file.write("\n")
        return str(path)

    @staticmethod
    def _configuration_body(session: SessionModel) -> Dict[str, Any]:
        raw_body = session.board_config.raw.get("configBody", {})
        body = dict(raw_body)
        body["heaterProfiles"] = session.board_config.heater_profiles
        body["dutyCycleProfiles"] = session.board_config.duty_cycle_profiles
        body["sensorConfigurations"] = session.board_config.sensor_configurations
        return body

    @staticmethod
    def _data_block(session: SessionModel) -> List[List[Any]]:
        data = session.measurements.data
        column_names = [column.name for column in session.measurements.columns]
        missing_columns = [
            column_name for column_name in column_names if column_name not in data
        ]
        if missing_columns:
            raise ValueError(
                "Measurement data is missing canonical columns: "
                + ", ".join(missing_columns)
            )

        return [
            [_json_value(value) for value in row]
            for row in data.loc[:, column_names].itertuples(index=False, name=None)
        ]


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value

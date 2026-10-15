"""Readers that normalize Bosch collection files into the canonical model."""

from pathlib import Path
from typing import Optional

from bme_board_config_reader import BoardConfigReader
from bme_model import (
    DataColumn,
    LabelModel,
    MeasurementModel,
    SessionModel,
    VersionMetadata,
)
from bme_parser import BMEFileParser
from bme_processor import BMEDataProcessor
from bme_validation import validate_session


class BMERawDataReader:
    """Read a Bosch ``.bmerawdata`` file into a :class:`SessionModel`."""

    def __init__(self, parser: Optional[BMEFileParser] = None):
        self.parser = parser or BMEFileParser()

    def read(
        self,
        rawdata_path: str,
        labelinfo_path: Optional[str] = None,
    ) -> SessionModel:
        path = Path(rawdata_path)
        raw_document = self.parser.parse_rawdata_file(str(path))

        label_model = None
        label_lookup = None
        if labelinfo_path is None:
            labelinfo_path = self.parser.find_matching_labelinfo(str(path))
        if labelinfo_path is not None:
            label_path = Path(labelinfo_path)
            if label_path.exists():
                label_document = self.parser.parse_labelinfo_file(str(label_path))
                label_lookup = BMEDataProcessor.create_label_lookup(label_document)
                label_model = LabelModel(
                    labels=label_document.get("labelInformation", []),
                    header=label_document.get("labelInfoHeader", {}),
                    raw=label_document,
                )

        raw_data_body = raw_document.get("rawDataBody", {})
        column_definitions = raw_data_body.get("dataColumns", [])
        columns = [
            DataColumn.from_dict(column, index)
            for index, column in enumerate(column_definitions)
        ]
        data = BMEDataProcessor.create_dataframe(
            raw_data_body.get("dataBlock", []),
            column_definitions,
            label_lookup,
        )
        data = BMEDataProcessor.format_column_by_type(data, column_definitions)

        board_config = BoardConfigReader.from_document(raw_document)
        config_header = board_config.header

        raw_data_header = raw_document.get("rawDataHeader", {})
        versions = VersionMetadata(
            config_version=_optional_string(
                config_header, "version", "configVersion"
            ),
            raw_data_version=_optional_string(
                raw_data_header, "version", "rawDataVersion"
            ),
            app_version=_optional_string(
                config_header, "appVersion"
            ),
            firmware_version=_optional_string(
                raw_data_header, "firmwareVersion"
            ),
        )

        session = SessionModel(
            board_config=board_config,
            measurements=MeasurementModel(data=data, columns=columns),
            labels=label_model,
            raw_data_header=raw_data_header,
            versions=versions,
            source_path=path,
            raw_document=raw_document,
        )
        validate_session(session)
        return session


def _optional_string(values: dict, *keys: str) -> Optional[str]:
    for key in keys:
        value = values.get(key)
        if value is not None:
            return str(value)
    return None

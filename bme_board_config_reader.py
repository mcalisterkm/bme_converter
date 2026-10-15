"""Reader for Bosch board configuration data."""

from pathlib import Path
from typing import Any, Dict

from bme_model import BoardConfigModel
from bme_parser import BMEFileParser


class BoardConfigReader:
    """Normalize standalone or embedded Bosch board configuration."""

    def __init__(self, parser: BMEFileParser = None):
        self.parser = parser or BMEFileParser()

    def read(self, file_path: str) -> BoardConfigModel:
        path = Path(file_path)
        document = self.parser.parse_config_file(str(path))
        return self.from_document(document)

    @staticmethod
    def from_document(document: Dict[str, Any]) -> BoardConfigModel:
        config_header = document.get("configHeader", {})
        config_body = document.get("configBody", {})
        return BoardConfigModel(
            header=config_header,
            heater_profiles=config_body.get("heaterProfiles", []),
            duty_cycle_profiles=config_body.get("dutyCycleProfiles", []),
            sensor_configurations=config_body.get("sensorConfigurations", []),
            raw={
                "configHeader": config_header,
                "configBody": config_body,
            },
        )

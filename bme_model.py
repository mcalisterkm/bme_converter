"""Canonical models for Bosch collection data."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class VersionMetadata:
    """Version and compatibility metadata retained from source files."""

    config_version: Optional[str] = None
    raw_data_version: Optional[str] = None
    udf_version: Optional[str] = None
    app_version: Optional[str] = None
    firmware_version: Optional[str] = None


@dataclass(frozen=True)
class DataColumn:
    """Description of one measurement column."""

    name: str
    unit: str = ""
    format: str = ""
    key: Optional[str] = None
    column_id: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Dict[str, Any], index: int) -> "DataColumn":
        return cls(
            name=value.get("name", f"Column_{value.get('colId', index)}"),
            unit=value.get("unit", ""),
            format=value.get("format", ""),
            key=value.get("key"),
            column_id=value.get("colId"),
            raw=dict(value),
        )

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.raw) if self.raw else {
            "name": self.name,
            "unit": self.unit,
            "format": self.format,
            "key": self.key,
            "colId": self.column_id,
        }


@dataclass(frozen=True)
class HeaterStep:
    """One heater temperature/time step."""

    temperature_c: Any
    time_units: Any

    @classmethod
    def from_value(cls, value: List[Any]) -> "HeaterStep":
        if len(value) != 2:
            raise ValueError("Heater step must contain temperature and time")
        return cls(temperature_c=value[0], time_units=value[1])

    def to_value(self) -> List[Any]:
        return [self.temperature_c, self.time_units]


@dataclass(frozen=True)
class HeaterProfile:
    """Typed heater profile definition."""

    profile_id: Any
    time_base: Any
    steps: List[HeaterStep]

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "HeaterProfile":
        return cls(
            profile_id=value.get("id", ""),
            time_base=value.get("timeBase", 1),
            steps=[
                HeaterStep.from_value(step)
                for step in value.get("temperatureTimeVectors", [])
            ],
        )


@dataclass(frozen=True)
class DutyCycleProfile:
    """Typed duty-cycle profile definition."""

    profile_id: Any
    scanning_cycles: Any
    sleeping_cycles: Any

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "DutyCycleProfile":
        return cls(
            profile_id=value.get("id", ""),
            scanning_cycles=value.get("numberScanningCycles", 0),
            sleeping_cycles=value.get("numberSleepingCycles", 0),
        )


@dataclass(frozen=True)
class SensorConfiguration:
    """Typed sensor-to-profile allocation."""

    sensor_index: Any
    heater_profile: Any
    duty_cycle_profile: Any

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "SensorConfiguration":
        return cls(
            sensor_index=value.get("sensorIndex", ""),
            heater_profile=value.get("heaterProfile", ""),
            duty_cycle_profile=value.get("dutyCycleProfile", ""),
        )


@dataclass(frozen=True)
class Label:
    """Typed collection label."""

    tag: Any
    name: str
    description: str

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "Label":
        return cls(
            tag=value.get("labelTag"),
            name=value.get("labelName", ""),
            description=value.get("labelDescription", ""),
        )


@dataclass
class BoardConfigModel:
    """Board configuration used by a collection session."""

    header: Dict[str, Any]
    heater_profiles: List[Dict[str, Any]]
    duty_cycle_profiles: List[Dict[str, Any]]
    sensor_configurations: List[Dict[str, Any]]
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def board_type(self) -> str:
        return self.header.get("boardType", "unknown")

    @property
    def typed_heater_profiles(self) -> List[HeaterProfile]:
        return [HeaterProfile.from_dict(value) for value in self.heater_profiles]

    @property
    def typed_duty_cycle_profiles(self) -> List[DutyCycleProfile]:
        return [
            DutyCycleProfile.from_dict(value)
            for value in self.duty_cycle_profiles
        ]

    @property
    def typed_sensor_configurations(self) -> List[SensorConfiguration]:
        return [
            SensorConfiguration.from_dict(value)
            for value in self.sensor_configurations
        ]


@dataclass
class MeasurementModel:
    """Tabular sensor measurements and their Bosch column schema."""

    data: pd.DataFrame
    columns: List[DataColumn]


@dataclass
class LabelModel:
    """Labels associated with a collection session."""

    labels: List[Dict[str, Any]]
    header: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionModel:
    """Canonical representation of one Bosch collection session."""

    board_config: BoardConfigModel
    measurements: MeasurementModel
    labels: Optional[LabelModel]
    raw_data_header: Dict[str, Any]
    versions: VersionMetadata
    source_path: Optional[Path] = None
    source_format: str = "bmerawdata"
    raw_document: Dict[str, Any] = field(default_factory=dict)

#!/usr/bin/env python3
"""
BME UDF to Raw Data Converter
Converts .udf binary files to .bmerawdata JSON format
Reuses existing parsing code from bme_udf_parser.py
"""

import json
import struct
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse
import sys

from bme_board_config_reader import BoardConfigReader
from bme_model import (
    DataColumn,
    LabelModel,
    MeasurementModel,
    SessionModel,
    VersionMetadata,
)
from bme_processor import BMEDataProcessor
from bme_rawdata_writer import BMERawDataWriter
from bme_labelinfo_reader import generate_seed, read_labelinfo
from bme_udf_container import UDFContainerReader
from bme_udf_frames import (
    UDFFrame,
    UDFFrameDecoder,
    decode_value,
    read_device_info,
)
from bme_validation import validate_session


class UDFToRawDataConverter:
    """Converter from .udf binary format to .bmerawdata JSON format"""
    
    # Mapping of UDF field names to standard bmerawdata column names
    FIELD_NAME_MAP = {
        'Sensor Index': 'Sensor Index',
        'Sensor ID': 'Sensor ID',
        'Time Since PowerOn': 'Time Since PowerOn',
        'Real time clock': 'Real time clock',
        'Raw temperature [deg C]': 'Temperature',
        'Temperature': 'Temperature',
        'Pressure [Pa]': 'Pressure',
        'Raw humidity [%rH]': 'Relative Humidity',
        'Humidity': 'Relative Humidity',
        'Gas resistance [ohm]': 'Resistance Gassensor',
        'Gas heater index': 'Heater Profile Step Index',
        'Scanning Mode Enabled': 'Scanning Mode Enabled',
        'Scanning Cycle Index': 'Scanning Cycle Index',
        'Label Tag': 'Label Tag',
        'error_code': 'Error Code',
    }
    
    # Unit mapping for common fields
    UNIT_MAP = {
        'Sensor Index': '',
        'Sensor ID': '',
        'Time Since PowerOn': 'Milliseconds',
        'Real time clock': 'Unix Timestamp: seconds since Jan 01 1970. (UTC); 0 = missing',
        'Temperature': 'DegreesCelcius',
        'Pressure': 'Hectopascals',
        'Relative Humidity': 'Percent',
        'Resistance Gassensor': 'Ohms',
        'Heater Profile Step Index': '',
        'Scanning Mode Enabled': '',
        'Scanning Cycle Index': '',
        'Label Tag': '',
        'Error Code': '',
    }
    
    # UDF field ids that make up a complete measurement frame
    MEASUREMENT_FIELDS = frozenset({6, 7, 8, 9, 26, 40, 41, 42, 43, 44, 45})

    # Format mapping
    FORMAT_MAP = {
        'Sensor Index': 'integer',
        'Sensor ID': 'integer',
        'Time Since PowerOn': 'integer',
        'Real time clock': 'integer',
        'Temperature': 'float',
        'Pressure': 'float',
        'Relative Humidity': 'float',
        'Resistance Gassensor': 'float',
        'Heater Profile Step Index': 'integer',
        'Scanning Mode Enabled': 'boolean',
        'Scanning Cycle Index': 'integer',
        'Label Tag': 'integer',
        'Error Code': 'integer',
    }
    
    def __init__(self, udf_path: str, config_path: Optional[str] = None, labelinfo_path: Optional[str] = None):
        """
        Initialize converter
        
        Args:
            udf_path: Path to .udf file
            config_path: Optional path to .bmeconfig file (auto-detected if not provided)
            labelinfo_path: Optional path to .bmelabelinfo file (auto-detected if not provided)
        """
        self.udf_path = Path(udf_path)
        self.config_path = Path(config_path) if config_path else None
        self.labelinfo_path = Path(labelinfo_path) if labelinfo_path else None
        self.config_data = None
        self.labelinfo_data = None
        self.udf_version = None
        self.udf_fields = []
        self.binary_data = None
        self.container = None
        self.frame_stream = None
        self.raw_data_header = None
        self._warned_truncated = False
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load BoardConfiguration.bmeconfig file
        
        Returns:
            Configuration dictionary
        """
        if self.config_path is None:
            # Auto-detect config file in same directory or parent
            search_paths = [
                self.udf_path.parent / 'BoardConfiguration.bmeconfig',
                self.udf_path.parent.parent / 'BoardConfiguration.bmeconfig',
            ]
            
            for path in search_paths:
                if path.exists():
                    self.config_path = path
                    break
            
            if self.config_path is None:
                raise FileNotFoundError(
                    f"Could not find BoardConfiguration.bmeconfig in {self.udf_path.parent} "
                    f"or parent directory. Please specify with -c option."
                )
        
        with open(self.config_path, 'r') as f:
            self.config_data = json.load(f)
        
        return self.config_data
    
    def load_labelinfo(self) -> Dict[str, Any]:
        """
        Load .bmelabelinfo file
        
        Returns:
            Label info dictionary
        """
        if self.labelinfo_path is None:
            # Auto-detect labelinfo file in same directory
            # Try with same base name as UDF file
            base_name = self.udf_path.stem
            search_paths = [
                self.udf_path.parent / f'{base_name}.bmelabelinfo',
                self.udf_path.parent / f'{base_name}.labelinfo',
            ]
            
            for path in search_paths:
                if path.exists():
                    self.labelinfo_path = path
                    break
            
            if self.labelinfo_path is None:
                print(f"Warning: Could not find .bmelabelinfo file for {self.udf_path.name}", file=sys.stderr)
                return {}
        
        self.labelinfo_data = read_labelinfo(str(self.labelinfo_path))
        
        return self.labelinfo_data
    
    def parse_udf(self) -> Tuple[str, List[Dict], bytes]:
        """
        Parse UDF file to extract metadata and binary data
        
        Returns:
            Tuple of (version, field_definitions, binary_data)
        """
        container = UDFContainerReader().read(str(self.udf_path))
        self.container = container
        self.udf_version = container.version
        self.udf_fields = container.fields
        self.binary_data = container.binary_data
        
        return self.udf_version, self.udf_fields, self.binary_data
    
    def extract_records(self) -> List[List[Any]]:
        """
        Extract and parse binary records from UDF data
        
        Returns:
            List of record arrays matching bmerawdata format
        """
        if self.binary_data is None:
            raise ValueError("No binary data. Call parse_udf() first.")
        
        self.frame_stream = UDFFrameDecoder().decode(self.container)
        if self.frame_stream.truncated and not self._warned_truncated:
            self._warned_truncated = True
            print(
                f"Warning: {self.udf_path.name} ends with an incomplete frame "
                f"({self.frame_stream.error}); it was ignored.",
                file=sys.stderr,
            )

        records = []
        for frame in self.frame_stream.frames:
            if self.MEASUREMENT_FIELDS <= frame.fields.keys():
                records.append(self._measurement_record(frame))
        return records

    def _measurement_record(self, frame: UDFFrame) -> List[Any]:
        """Build a 13-column bmerawdata row from a measurement frame."""
        schema = self.frame_stream.schema

        def value(field_id: int) -> Any:
            return decode_value(frame.fields[field_id], schema[field_id]["type"])[0]

        return [
            value(40),
            value(41),
            frame.timestamp_ms,
            0,  # BME690 has no real-time clock
            value(6),
            value(7),
            value(8),
            value(9),
            value(26),
            value(42),
            value(43),
            value(44),
            value(45),
        ]
    
    def generate_data_columns(self) -> List[Dict[str, Any]]:
        """
        Generate dataColumns array for rawDataBody
        
        Returns:
            List of column definitions
        """
        # Standard columns for BME690 data
        columns = [
            {
                "name": "Sensor Index",
                "unit": "",
                "format": "integer",
                "key": "sensor_index",
                "colId": 1
            },
            {
                "name": "Sensor ID",
                "unit": "",
                "format": "integer",
                "key": "sensor_id",
                "colId": 2
            },
            {
                "name": "Time Since PowerOn",
                "unit": "Milliseconds",
                "format": "integer",
                "key": "timestamp_since_poweron",
                "colId": 3
            },
            {
                "name": "Real time clock",
                "unit": "Unix Timestamp: seconds since Jan 01 1970. (UTC); 0 = missing",
                "format": "integer",
                "key": "real_time_clock",
                "colId": 4
            },
            {
                "name": "Temperature",
                "unit": "DegreesCelcius",
                "format": "float",
                "key": "temperature",
                "colId": 5
            },
            {
                "name": "Pressure",
                "unit": "Hectopascals",
                "format": "float",
                "key": "pressure",
                "colId": 6
            },
            {
                "name": "Relative Humidity",
                "unit": "Percent",
                "format": "float",
                "key": "relative_humidity",
                "colId": 7
            },
            {
                "name": "Resistance Gassensor",
                "unit": "Ohms",
                "format": "float",
                "key": "resistance_gassensor",
                "colId": 8
            },
            {
                "name": "Heater Profile Step Index",
                "unit": "",
                "format": "integer",
                "key": "heater_profile_step_index",
                "colId": 9
            },
            {
                "name": "Scanning Mode Enabled",
                "unit": "",
                "format": "boolean",
                "key": "scanning_enabled",
                "colId": 10
            },
            {
                "name": "Scanning Cycle Index",
                "unit": "",
                "format": "integer",
                "key": "scanning_cycle_index",
                "colId": 11
            },
            {
                "name": "Label Tag",
                "unit": "",
                "format": "integer",
                "key": "label_tag",
                "colId": 12
            },
            {
                "name": "Error Code",
                "unit": "",
                "format": "integer",
                "key": "error_code",
                "colId": 13
            }
        ]
        
        return columns
    
    def generate_raw_data_header(self) -> Dict[str, Any]:
        """
        Generate rawDataHeader section from labelinfo file
        
        Returns:
            Raw data header dictionary
        """
        if self.raw_data_header is not None:
            return self.raw_data_header

        labelinfo = self.load_labelinfo()
        labelinfo_header = labelinfo.get('labelInfoHeader', {})
        device_info = (
            read_device_info(self.frame_stream) if self.frame_stream else {}
        )

        seed = labelinfo_header.get('seedPowerOnOff') or generate_seed()
        counter_poweron = labelinfo_header.get('counterPowerOnOff', 1)
        firmware_version = labelinfo_header.get(
            'firmwareVersion', device_info.get('firmware_version', '3.1.0')
        )
        board_id = labelinfo_header.get(
            'boardId', device_info.get('board_type', 'unknown')
        )
        
        self.raw_data_header = {
            "counterPowerOnOff": counter_poweron,
            "seedPowerOnOff": seed,
            "counterFileLimit": 1,
            "firmwareVersion": firmware_version,
            "boardId": board_id
        }
        return self.raw_data_header
    
    def convert(self) -> Dict[str, Any]:
        """
        Main conversion method
        
        Returns:
            Complete .bmerawdata dictionary structure
        """
        # Load configuration
        config = self.load_config()
        
        # Parse UDF file
        self.parse_udf()
        
        # Extract records
        records = self.extract_records()
        
        # Build output structure
        rawdata = {
            "configHeader": config.get("configHeader", {}),
            "configBody": config.get("configBody", {}),
            "rawDataHeader": self.generate_raw_data_header(),
            "rawDataBody": {
                "dataColumns": self.generate_data_columns(),
                "dataBlock": records
            }
        }
        
        return rawdata

    def read_session(self) -> SessionModel:
        """Decode collection UDF data into the canonical session model."""
        rawdata = self.convert()
        labelinfo = self.labelinfo_data or {}
        column_definitions = rawdata["rawDataBody"]["dataColumns"]
        label_lookup = BMEDataProcessor.create_label_lookup(labelinfo)
        data = BMEDataProcessor.create_dataframe(
            rawdata["rawDataBody"]["dataBlock"],
            column_definitions,
            label_lookup,
        )
        data = BMEDataProcessor.format_column_by_type(data, column_definitions)

        board_config = BoardConfigReader.from_document(rawdata)
        config_header = board_config.header
        label_model = None
        if labelinfo:
            label_model = LabelModel(
                labels=labelinfo.get("labelInformation", []),
                header=labelinfo.get("labelInfoHeader", {}),
                raw=labelinfo,
            )

        session = SessionModel(
            board_config=board_config,
            measurements=MeasurementModel(
                data=data,
                columns=[
                    DataColumn.from_dict(column, index)
                    for index, column in enumerate(column_definitions)
                ],
            ),
            labels=label_model,
            raw_data_header=rawdata["rawDataHeader"],
            versions=VersionMetadata(
                udf_version=self.udf_version,
                app_version=config_header.get("appVersion"),
                firmware_version=rawdata["rawDataHeader"].get("firmwareVersion"),
            ),
            source_path=self.udf_path,
            source_format="collection_udf",
            raw_document=rawdata,
        )
        validate_session(session)
        return session
    
    def save(self, output_path: Optional[str] = None) -> str:
        """
        Convert and save to .bmerawdata file
        
        Args:
            output_path: Optional output file path (defaults to input name with .bmerawdata extension)
            
        Returns:
            Path to output file
        """
        if output_path is None:
            output_path = self.udf_path.with_suffix('.bmerawdata')
        
        output_path = Path(output_path)
        
        session = self.read_session()
        return BMERawDataWriter().write(session, str(output_path))


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Convert BME .udf files to .bmerawdata JSON format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bme_udf_to_rawdata.py data.udf
  python bme_udf_to_rawdata.py data.udf -c BoardConfiguration.bmeconfig
  python bme_udf_to_rawdata.py data.udf -o output.bmerawdata
        """
    )
    
    parser.add_argument('input_file', help='Input .udf file')
    parser.add_argument('-c', '--config', help='Path to BoardConfiguration.bmeconfig file (auto-detected if not specified)')
    parser.add_argument('-o', '--output', help='Output .bmerawdata file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    try:
        if args.verbose:
            print(f"Converting: {args.input_file}")
        
        converter = UDFToRawDataConverter(args.input_file, args.config)
        output_file = converter.save(args.output)
        
        if args.verbose:
            print(f"Config file: {converter.config_path}")
            print(f"UDF version: {converter.udf_version}")
            print(f"Field definitions: {len(converter.udf_fields)}")
            print(f"Binary data: {len(converter.binary_data)} bytes")
        
        # Count records
        with open(output_file, 'r') as f:
            data = json.load(f)
            record_count = len(data['rawDataBody']['dataBlock'])
        
        print(f"Converted {record_count} records to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

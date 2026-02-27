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
        
        with open(self.labelinfo_path, 'r') as f:
            self.labelinfo_data = json.load(f)
        
        return self.labelinfo_data
    
    def parse_udf(self) -> Tuple[str, List[Dict], bytes]:
        """
        Parse UDF file to extract metadata and binary data
        
        Returns:
            Tuple of (version, field_definitions, binary_data)
        """
        with open(self.udf_path, 'rb') as f:
            content = f.read()
        
        # Find metadata delimiter
        delimiter = b'\r\n\r\n\r\n'
        delim_pos = content.find(delimiter)
        
        if delim_pos == -1:
            raise ValueError("Could not find metadata delimiter in UDF file")
        
        # Parse metadata
        metadata = content[:delim_pos].decode('utf-8', errors='ignore')
        self.binary_data = content[delim_pos + len(delimiter):]
        
        # Parse metadata fields
        self.udf_version, self.udf_fields = self._parse_metadata(metadata)
        
        return self.udf_version, self.udf_fields, self.binary_data
    
    def _parse_metadata(self, metadata: str) -> Tuple[str, List[Dict]]:
        """Parse metadata section to extract field definitions"""
        import re
        
        lines = [l.strip() for l in metadata.split('\n') if l.strip()]
        version = lines[0] if lines else "unknown"
        
        fields = []
        # Format: ID: Name: Size: Type: Flags: Val1: Val2: Status
        field_pattern = re.compile(r'^(\d+):\s*([^:]+):\s*(\d+):\s*([^:]+):')
        
        for line in lines[1:]:
            match = field_pattern.match(line)
            if match:
                field_id = int(match.group(1))
                name = match.group(2).strip()
                size = int(match.group(3))
                type_spec = match.group(4).strip()
                
                fields.append({
                    'id': field_id,
                    'name': name,
                    'size': size,
                    'type': type_spec
                })
        
        return version, fields
    
    def extract_records(self) -> List[List[Any]]:
        """
        Extract and parse binary records from UDF data
        
        Returns:
            List of record arrays matching bmerawdata format
        """
        if self.binary_data is None:
            raise ValueError("No binary data. Call parse_udf() first.")
        
        # Detect record structure
        header_size, record_size = self._detect_record_size()
        
        # Parse all records, skipping the header
        bmerawdata_records = []
        offset = header_size  # Skip header
        
        while offset + record_size <= len(self.binary_data):
            rec_data = self.binary_data[offset:offset + record_size]
            record = self._parse_record_61_byte(rec_data)
            if record is not None:
                bmerawdata_records.append(record)
            offset += record_size
        
        return bmerawdata_records
    
    def _detect_record_size(self) -> Tuple[int, int]:
        """Detect record size from binary data patterns
        
        Returns:
            Tuple of (header_size, record_size)
        """
        # Look for 0x00FF pattern markers
        marker = b'\x00\xff'
        positions = []
        
        for i in range(min(1000, len(self.binary_data) - 1)):
            if self.binary_data[i:i+2] == marker:
                positions.append(i)
                if len(positions) >= 10:
                    break
        
        if len(positions) >= 2:
            # First interval is header size, rest are data record size
            header_size = positions[1] - positions[0]
            intervals = [positions[i+1] - positions[i] for i in range(1, len(positions)-1)]
            if intervals:
                # Most common interval is the data record size
                record_size = max(set(intervals), key=intervals.count)
                return header_size, record_size
        
        # Default fallback: 28-byte header, 61-byte records
        return 28, 61
    
    def _parse_record_61_byte(self, data: bytes) -> Optional[List[Any]]:
        """
        Parse a single 61-byte binary record using known field offsets
        
        Args:
            data: Binary record data (61 bytes)
            
        Returns:
            List of 13 values matching bmerawdata format, or None if invalid
        """
        try:
            if len(data) < 61:
                return None
            
            # Packed 61-byte structure (little-endian):
            # [0-1]   Marker (0x00FF)
            # [2-9]   Time Since PowerOn (u64 nanoseconds)
            # [10-13] Real Time Clock (u32, always 0 for BME690 - no RTC)
            # [12]    Heater Profile Step Index (u8)
            # [15-18] Gas Resistance (float)
            # [21-24] Relative Humidity (float)
            # [27-30] Pressure (float)
            # [33-36] Temperature (float)
            # [39]    Scanning Cycle Index (u8)
            # [39]    Scanning Mode Enabled (u8) - always 1
            # [45-48] Sensor ID (u32)
            # [51-54] Label Tag (u32)
            # [53]    Error Code (u8)\n            # [60]    Sensor Index (u8)
            
            # [0] Sensor Index (u8) at offset 60
            sensor_index = data[60]
            
            # [1] Sensor ID (u32) at offset 45
            sensor_id = struct.unpack('<I', data[45:49])[0]
            
            # [2] Time Since PowerOn (u64 nanoseconds -> milliseconds) at offset 2
            time_ns = struct.unpack('<Q', data[2:10])[0]
            time_ms = time_ns // 1000000
            
            # [3] Real time clock (u32) at offset 10 (always 0 for BME690 - no RTC)
            real_time_clock = 0
            
            # [4] Temperature (float) at offset 33
            temperature = struct.unpack('<f', data[33:37])[0]
            
            # [5] Pressure (float) at offset 27
            pressure = struct.unpack('<f', data[27:31])[0]
            
            # [6] Relative Humidity (float) at offset 21
            humidity = struct.unpack('<f', data[21:25])[0]
            
            # [7] Resistance Gassensor (float) at offset 15
            gas_resistance = struct.unpack('<f', data[15:19])[0]
            
            # [8] Heater Profile Step Index (u8) at offset 12
            heater_step = data[12]
            
            # [9] Scanning Mode Enabled (u8) - always 1 (not stored in binary)
            scanning_enabled = 1
            
            # [10] Scanning Cycle Index (u8) at offset 39
            scanning_cycle = data[39]
            
            # [11] Label Tag (u32) at offset 51
            label_tag = struct.unpack('<I', data[51:55])[0]
            
            # [12] Error Code (s8) at offset 53
            error_code = struct.unpack('<b', data[53:54])[0]
            
            return [
                sensor_index,
                sensor_id,
                time_ms,
                real_time_clock,
                temperature,
                pressure,
                humidity,
                gas_resistance,
                heater_step,
                scanning_enabled,
                scanning_cycle,
                label_tag,
                error_code
            ]
            
        except Exception as e:
            print(f"Warning: Failed to parse record: {e}", file=sys.stderr)
            return None
    
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
        # Load labelinfo to get seedPowerOnOff and other header data
        labelinfo = self.load_labelinfo()
        
        # Extract from labelinfo header, with defaults
        labelinfo_header = labelinfo.get('labelInfoHeader', {})
        
        seed = labelinfo_header.get('seedPowerOnOff', 'unknown')
        counter_poweron = labelinfo_header.get('counterPowerOnOff', 1)
        firmware_version = labelinfo_header.get('firmwareVersion', '3.1.0')
        board_id = labelinfo_header.get('boardId', 'unknown')
        
        return {
            "counterPowerOnOff": counter_poweron,
            "seedPowerOnOff": seed,
            "counterFileLimit": 1,
            "firmwareVersion": firmware_version,
            "boardId": board_id
        }
    
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
        
        # Perform conversion
        rawdata = self.convert()
        
        # Write JSON file with formatting matching Bosch files
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rawdata, f, indent='\t')
        
        return str(output_path)


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

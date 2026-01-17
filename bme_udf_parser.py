#!/usr/bin/env python3
"""
Bosch Sensortec BME UDF File Parser
Parses .udf files containing binary sensor data with ASCII metadata header
"""

import struct
from pathlib import Path
from typing import Dict, List, Tuple, Any, BinaryIO
import re


class BMEUDFParser:
    """Parser for BME .udf binary format files"""
    
    # Type mappings to struct format characters and sizes
    TYPE_MAP = {
        'u8': ('B', 1),    # unsigned char
        's8': ('b', 1),    # signed char
        'u16': ('H', 2),   # unsigned short
        's16': ('h', 2),   # signed short
        'u32': ('I', 4),   # unsigned int
        's32': ('i', 4),   # signed int
        'f': ('f', 4),     # float
    }
    
    METADATA_DELIMITER = b'\r\n\r\n\r\n'
    
    def __init__(self, file_path: str):
        """
        Initialize parser with UDF file path
        
        Args:
            file_path: Path to .udf file
        """
        self.file_path = Path(file_path)
        self.version = None
        self.fields = []
        self.binary_data = None
        
    def parse(self) -> Tuple[str, List[Dict[str, Any]], bytes]:
        """
        Parse the UDF file
        
        Returns:
            Tuple of (version, field_definitions, binary_data)
        """
        with open(self.file_path, 'rb') as f:
            # Read entire file
            content = f.read()
            
            # Find delimiter between metadata and binary data
            delimiter_pos = content.find(self.METADATA_DELIMITER)
            
            if delimiter_pos == -1:
                raise ValueError("Could not find metadata delimiter in UDF file")
            
            # Split into metadata and binary sections
            metadata_bytes = content[:delimiter_pos]
            binary_start = delimiter_pos + len(self.METADATA_DELIMITER)
            self.binary_data = content[binary_start:]
            
            # Parse metadata as text
            metadata_text = metadata_bytes.decode('utf-8', errors='ignore')
            self._parse_metadata(metadata_text)
            
        return self.version, self.fields, self.binary_data
    
    def _parse_metadata(self, metadata: str) -> None:
        """
        Parse ASCII metadata section
        
        Args:
            metadata: Metadata text content
        """
        lines = metadata.strip().split('\n')
        
        if not lines:
            raise ValueError("Empty metadata section")
        
        # First line is version
        self.version = lines[0].strip()
        
        # Parse field definitions
        # Format: ID: Name: Size: Type: Flags: Val1: Val2: Status
        field_pattern = re.compile(
            r'^(\d+):\s*([^:]+):\s*(\d+):\s*([^:]+):\s*([^:]+):\s*([^:]+):\s*([^:]+):\s*(.+)$'
        )
        
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
                
            match = field_pattern.match(line)
            if match:
                field_id = int(match.group(1))
                field_name = match.group(2).strip()
                size = int(match.group(3))
                type_spec = match.group(4).strip()
                flags = match.group(5).strip()
                val1 = match.group(6).strip()
                val2 = match.group(7).strip()
                status = match.group(8).strip()
                
                self.fields.append({
                    'id': field_id,
                    'name': field_name,
                    'size': size,
                    'type': type_spec,
                    'flags': flags,
                    'val1': val1,
                    'val2': val2,
                    'status': status
                })
    
    def _parse_type_spec(self, type_spec: str, size: int) -> List[Tuple[str, str, int]]:
        """
        Parse type specification into struct format
        
        Args:
            type_spec: Type specification (e.g., 'f', 'u8', 'f,u8')
            size: Total size in bytes
            
        Returns:
            List of (name_suffix, format_char, byte_size) tuples
        """
        types = [t.strip() for t in type_spec.split(',')]
        result = []
        
        for i, type_name in enumerate(types):
            if type_name in self.TYPE_MAP:
                fmt, type_size = self.TYPE_MAP[type_name]
                suffix = '' if i == 0 else f'_{i}'
                result.append((suffix, fmt, type_size))
            else:
                # Unknown type - treat as raw bytes
                result.append((f'_raw_{i}', f'{size}s', size))
        
        return result
    
    def extract_records(self) -> List[Dict[str, Any]]:
        """
        Extract records from binary data
        
        Returns:
            List of dictionaries, each containing parsed field values
        """
        if self.binary_data is None:
            raise ValueError("No binary data loaded. Call parse() first.")
        
        # Calculate record size from field definitions
        record_size = self._calculate_record_size()
        
        if record_size == 0:
            raise ValueError("Could not calculate record size from field definitions")
        
        # Extract records
        records = []
        offset = 0
        record_num = 0
        
        while offset + record_size <= len(self.binary_data):
            record_data = self.binary_data[offset:offset + record_size]
            record = self._parse_record(record_data, record_num)
            records.append(record)
            offset += record_size
            record_num += 1
        
        return records
    
    def _calculate_record_size(self) -> Tuple[int, int]:
        """
        Calculate record size based on actual data analysis
        
        Returns:
            Tuple of (first_record_size, subsequent_record_size)
        """
        # Based on analysis of 0x00FF pattern markers:
        # First record is shorter (28 bytes - likely header)
        # Subsequent records are 61 bytes each
        
        # But let's detect this dynamically
        if not self.binary_data or len(self.binary_data) < 100:
            return (61, 61)  # Default guess
        
        # Find positions of 0x00FF pattern
        marker = b'\x00\xff'
        positions = []
        for i in range(min(1000, len(self.binary_data) - 1)):
            if self.binary_data[i:i+2] == marker:
                positions.append(i)
                if len(positions) >= 10:
                    break
        
        if len(positions) >= 2:
            intervals = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
            # Most common interval is the record size
            if intervals:
                subsequent_size = max(set(intervals), key=intervals.count)
                first_size = positions[0] + subsequent_size if positions[0] < subsequent_size else subsequent_size
                return (first_size, subsequent_size)
        
        # Fallback: assume 61 bytes based on empirical observation
        return (28, 61)
    
    def _parse_record(self, data: bytes, record_num: int) -> Dict[str, Any]:
        """
        Parse a single record from binary data
        
        Args:
            data: Binary data for one record
            record_num: Record number (0-indexed)
            
        Returns:
            Dictionary of field_name: value pairs
        """
        record = {'_record_num': record_num}
        offset = 0
        
        for field in self.fields:
            field_name = field['name']
            field_id = field['id']
            field_size = field['size']
            type_spec = field['type']
            
            # Extract bytes for this field
            field_data = data[offset:offset + field_size]
            
            if len(field_data) < field_size:
                # Not enough data
                record[f"{field_id}_{field_name}"] = None
                offset += field_size
                continue
            
            # Parse based on type
            try:
                value = self._parse_field_value(field_data, type_spec, field_size)
                record[f"{field_id}_{field_name}"] = value
            except Exception as e:
                # Failed to parse - store as hex
                record[f"{field_id}_{field_name}"] = field_data.hex()
            
            offset += field_size
        
        return record
    
    def _parse_field_value(self, data: bytes, type_spec: str, size: int) -> Any:
        """
        Parse field value based on type specification
        
        Args:
            data: Binary data for the field
            type_spec: Type specification string
            size: Expected size in bytes
            
        Returns:
            Parsed value
        """
        # Handle compound types (e.g., 'f,u8')
        types = [t.strip() for t in type_spec.split(',')]
        
        if len(types) == 1:
            # Single type
            type_name = types[0]
            if type_name in self.TYPE_MAP:
                fmt, _ = self.TYPE_MAP[type_name]
                value = struct.unpack('<' + fmt, data)[0]  # Little-endian
                return value
            else:
                # Unknown type - return hex
                return data.hex()
        else:
            # Compound type - return tuple or dict
            values = []
            offset = 0
            for type_name in types:
                if type_name in self.TYPE_MAP:
                    fmt, type_size = self.TYPE_MAP[type_name]
                    if offset + type_size <= len(data):
                        value = struct.unpack('<' + fmt, data[offset:offset + type_size])[0]
                        values.append(value)
                        offset += type_size
                    else:
                        values.append(None)
                else:
                    values.append(data[offset:].hex())
                    break
            return tuple(values) if len(values) > 1 else values[0] if values else None
    
    def to_csv(self, output_path: str = None) -> str:
        """
        Convert parsed data to CSV file
        
        Args:
            output_path: Optional output CSV file path
            
        Returns:
            Path to created CSV file
        """
        import csv
        
        records = self.extract_records()
        
        if not records:
            raise ValueError("No records extracted from binary data")
        
        if output_path is None:
            output_path = self.file_path.with_suffix('.csv')
        
        output_path = Path(output_path)
        
        # Get all field names
        fieldnames = list(records[0].keys())
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)
        
        return str(output_path)
    
    def to_excel(self, output_path: str = None) -> str:
        """
        Convert parsed data to Excel file
        
        Args:
            output_path: Optional output Excel file path
            
        Returns:
            Path to created Excel file
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas openpyxl")
        
        records = self.extract_records()
        
        if not records:
            raise ValueError("No records extracted from binary data")
        
        if output_path is None:
            output_path = self.file_path.with_suffix('.xlsx')
        
        output_path = Path(output_path)
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Write to Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        return str(output_path)


def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Parse BME .udf binary files and convert to CSV/Excel'
    )
    parser.add_argument('input_file', help='Input .udf file')
    parser.add_argument('-o', '--output', help='Output file path')
    parser.add_argument('-f', '--format', choices=['csv', 'excel'], default='csv',
                        help='Output format (default: csv)')
    
    args = parser.parse_args()
    
    try:
        print(f"Parsing {args.input_file}...")
        parser_obj = BMEUDFParser(args.input_file)
        version, fields, binary_data = parser_obj.parse()
        
        print(f"Version: {version}")
        print(f"Fields: {len(fields)}")
        print(f"Binary data size: {len(binary_data)} bytes")
        
        if args.format == 'csv':
            output_path = parser_obj.to_csv(args.output)
            print(f"CSV file created: {output_path}")
        else:
            output_path = parser_obj.to_excel(args.output)
            print(f"Excel file created: {output_path}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

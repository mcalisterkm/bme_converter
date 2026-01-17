#!/usr/bin/env python3
"""
Simple BME UDF to CSV Converter
Extracts binary sensor data from .udf files
"""

import struct
import csv
from pathlib import Path


def parse_metadata_fields(metadata_text):
    """Parse field definitions from metadata"""
    import re
    
    lines = [l.strip() for l in metadata_text.split('\n') if l.strip()]
    version = lines[0] if lines else "unknown"
    
    fields = []
    for line in lines[1:]:
        if not line or not line[0].isdigit():
            continue
        
        parts = [p.strip() for p in line.split(':')]
        if len(parts) >= 8:
            try:
                field_id = int(parts[0])
                name = parts[1]
                size = int(parts[2])
                type_spec = parts[3]
                fields.append({
                    'id': field_id,
                    'name': name,
                    'size': size,
                    'type': type_spec
                })
            except:
                pass
    
    return version, fields


def parse_udf_file(file_path):
    """Parse a .udf file and extract records"""
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Find metadata delimiter
    delimiter = b'\r\n\r\n\r\n'
    delim_pos = content.find(delimiter)
    
    if delim_pos == -1:
        raise ValueError("Could not find metadata delimiter")
    
    # Parse metadata
    metadata = content[:delim_pos].decode('utf-8', errors='ignore')
    version, field_defs = parse_metadata_fields(metadata)
    
    # Extract binary data
    binary_data = content[delim_pos + len(delimiter):]
    
    print(f"Version: {version}")
    print(f"Metadata: {len(field_defs)} field definitions")
    print(f"Binary data: {len(binary_data)} bytes")
    
    # Detect record structure by finding 0x00FF markers
    marker = b'\x00\xff'
    marker_positions = [i for i in range(min(1000, len(binary_data) - 1)) 
                        if binary_data[i:i+2] == marker]
    
    if len(marker_positions) < 2:
        raise ValueError("Could not detect record structure")
    
    # Calculate record sizes
    intervals = [marker_positions[i+1] - marker_positions[i] 
                 for i in range(len(marker_positions)-1)]
    
    # Most common interval is the record size
    record_size = max(set(intervals), key=intervals.count)
    first_record_size = marker_positions[0] + record_size if marker_positions[0] < record_size else record_size
    
    print(f"First record: {first_record_size} bytes")
    print(f"Subsequent records: {record_size} bytes")
    
    # Extract all records
    records = []
    offset = 0
    record_num = 0
    
    # Parse first record
    if offset + first_record_size <= len(binary_data):
        rec_data = binary_data[offset:offset + first_record_size]
        record = parse_record(rec_data, record_num, record_size=first_record_size, field_defs=field_defs)
        records.append(record)
        offset += first_record_size
        record_num += 1
    
    # Parse subsequent records
    while offset + record_size <= len(binary_data):
        rec_data = binary_data[offset:offset + record_size]
        record = parse_record(rec_data, record_num, record_size=record_size, field_defs=field_defs)
        records.append(record)
        offset += record_size
        record_num += 1
    
    print(f"Extracted {len(records)} records")
    
    return records, version, field_defs


def parse_record(data, record_num, record_size, field_defs=None):
    """Parse a single record using field definitions if available"""
    
    record = {
        'record_num': record_num,
        'marker': data[0:2].hex() if len(data) >= 2 else '',
    }
    
    offset = 2  # Skip first 2 bytes (marker/header)
    
    # If we have field definitions, try to match the record structure
    # The 61-byte record likely contains a subset of fields
    # Common structure from observation: timestamp info + sensor readings
    
    field_num = 0
    
    # Parse remaining bytes as 4-byte chunks (float or int)
    while offset + 4 <= len(data):
        chunk = data[offset:offset + 4]
        
        # Determine field name if we have metadata
        field_name = f'f{field_num}'
        if field_defs and field_num < len(field_defs):
            # Use actual field name from metadata
            field_name = field_defs[field_num]['name']
        
        # Try as float first
        try:
            val_f = struct.unpack('<f', chunk)[0]
            # Check if it's a reasonable float value
            if not (val_f != val_f or abs(val_f) > 1e20):
                record[field_name] = round(val_f, 6)
            else:
                # Try as unsigned int
                val_u = struct.unpack('<I', chunk)[0]
                record[field_name] = val_u
        except:
            # Store as hex if parsing fails
            record[field_name] = chunk.hex()
        
        offset += 4
        field_num += 1
    
    # Handle remaining bytes (1-3 bytes)
    if offset < len(data):
        remaining = data[offset:]
        for i, byte in enumerate(remaining):
            record[f'byte_{i}'] = byte
    
    return record


def save_to_csv(records, output_path):
    """Save records to CSV file"""
    
    if not records:
        raise ValueError("No records to save")
    
    # Get all field names from all records (in case they vary)
    all_fields = set()
    for record in records:
        all_fields.update(record.keys())
    
    # Sort fields logically
    ordered_fields = ['record_num', 'marker']
    other_fields = sorted([f for f in all_fields if f not in ordered_fields])
    fieldnames = ordered_fields + other_fields
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    print(f"CSV saved: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert BME .udf files to CSV')
    parser.add_argument('input_file', help='Input .udf file')
    parser.add_argument('-o', '--output', help='Output CSV file')
    
    args = parser.parse_args()
    
    try:
        input_path = Path(args.input_file)
        output_path = Path(args.output) if args.output else input_path.with_suffix('.csv')
        
        print(f"Processing: {input_path}")
        records, version, field_defs = parse_udf_file(input_path)
        
        save_to_csv(records, output_path)
        print(f"Done! {len(records)} records converted.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

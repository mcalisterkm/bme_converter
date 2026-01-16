#!/usr/bin/env python3
"""
Bosch Sensortec BME to Excel Converter
Converts .bmerawdata and .bmelabelinfo files to Excel spreadsheets

Usage:
    python bme_converter.py input.bmerawdata -o output.xlsx
    python bme_converter.py input.bmerawdata -l input.bmelabelinfo -o output.xlsx
    python bme_converter.py --dir /path/to/data
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from bme_parser import BMEFileParser
from bme_processor import BMEDataProcessor
from bme_excel_writer import BMEExcelWriter


def convert_bme_to_excel(rawdata_path: str, 
                         labelinfo_path: Optional[str] = None,
                         output_path: Optional[str] = None) -> str:
    """
    Convert BME raw data file to Excel
    
    Args:
        rawdata_path: Path to .bmerawdata file
        labelinfo_path: Optional path to .bmelabelinfo file
        output_path: Optional output Excel file path
        
    Returns:
        Path to created Excel file
    """
    rawdata_path = Path(rawdata_path)
    
    # Validate input file
    if not rawdata_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {rawdata_path}")
    
    # Auto-detect labelinfo file if not provided
    if labelinfo_path is None:
        labelinfo_path = BMEFileParser.find_matching_labelinfo(str(rawdata_path))
    
    # Generate output path if not provided
    if output_path is None:
        output_path = rawdata_path.with_suffix('.xlsx')
    
    print(f"Converting: {rawdata_path.name}")
    if labelinfo_path:
        print(f"Using labels: {Path(labelinfo_path).name}")
    
    # Parse files
    parser = BMEFileParser()
    
    print("Parsing raw data file...")
    rawdata = parser.parse_rawdata_file(str(rawdata_path))
    
    label_lookup = None
    labels_df = None
    if labelinfo_path and Path(labelinfo_path).exists():
        print("Parsing label info file...")
        labelinfo = parser.parse_labelinfo_file(str(labelinfo_path))
        label_lookup = BMEDataProcessor.create_label_lookup(labelinfo)
        labels_df = BMEDataProcessor.create_label_dataframe(labelinfo)
    
    # Extract data
    print("Processing data...")
    column_info = parser.extract_column_info(rawdata)
    data_block = parser.extract_data_block(rawdata)
    board_type = parser.get_board_type(rawdata)
    
    # Process data
    processor = BMEDataProcessor()
    
    # Create data DataFrame
    data_df = processor.create_dataframe(data_block, column_info, label_lookup)
    data_df = processor.format_column_by_type(data_df, column_info)
    
    # Create configuration DataFrames
    config_df = processor.create_config_dataframe(rawdata)
    
    heater_profiles = parser.get_heater_profiles(rawdata)
    heater_df = processor.create_heater_profile_dataframe(heater_profiles)
    
    duty_profiles = parser.get_duty_cycle_profiles(rawdata)
    duty_df = processor.create_duty_cycle_dataframe(duty_profiles)
    
    sensor_configs = parser.get_sensor_configurations(rawdata)
    sensor_df = processor.create_sensor_config_dataframe(sensor_configs)
    
    # Create Excel workbook
    print(f"Creating Excel file: {output_path}")
    writer = BMEExcelWriter(str(output_path))
    
    # Add sheets
    writer.add_configuration_sheet(
        config_df, heater_df, duty_df, sensor_df,
        board_type, rawdata_path.name
    )
    
    if labels_df is not None:
        writer.add_labels_sheet(labels_df)
    
    writer.add_sensor_data_sheet(data_df, column_info)
    
    # Save workbook
    output_file = writer.save()
    
    print(f"✓ Successfully created: {output_file}")
    print(f"  - {len(data_df)} data rows")
    print(f"  - {len(column_info)} columns")
    print(f"  - Board type: {board_type}")
    
    return output_file


def batch_convert_directory(directory: str):
    """
    Batch convert all .bmerawdata files in a directory
    
    Args:
        directory: Path to directory containing BME files
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)
    
    # Find all .bmerawdata files
    rawdata_files = list(directory.glob("*.bmerawdata"))
    
    if not rawdata_files:
        print(f"No .bmerawdata files found in {directory}")
        sys.exit(1)
    
    print(f"Found {len(rawdata_files)} file(s) to convert\n")
    
    success_count = 0
    error_count = 0
    
    for rawdata_file in rawdata_files:
        try:
            convert_bme_to_excel(str(rawdata_file))
            success_count += 1
            print()
        except Exception as e:
            print(f"✗ Error converting {rawdata_file.name}: {e}\n")
            error_count += 1
    
    print(f"\nConversion complete:")
    print(f"  ✓ Success: {success_count}")
    if error_count > 0:
        print(f"  ✗ Errors: {error_count}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Convert Bosch Sensortec BME files to Excel spreadsheets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single file (auto-detect label file)
  python bme_converter.py data.bmerawdata
  
  # Convert with specific label file and output name
  python bme_converter.py data.bmerawdata -l labels.bmelabelinfo -o output.xlsx
  
  # Batch convert all files in directory
  python bme_converter.py --dir /path/to/data
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Input .bmerawdata file'
    )
    
    parser.add_argument(
        '-l', '--labelinfo',
        help='Input .bmelabelinfo file (optional, auto-detected if not provided)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output Excel file path (optional, defaults to input filename with .xlsx extension)'
    )
    
    parser.add_argument(
        '--dir',
        help='Directory to batch process (converts all .bmerawdata files)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.dir:
        # Batch mode
        batch_convert_directory(args.dir)
    elif args.input_file:
        # Single file mode
        try:
            convert_bme_to_excel(args.input_file, args.labelinfo, args.output)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

# Bosch Sensortec BME to Excel Converter

Convert Bosch Sensortec BME raw data files (`.bmerawdata`) and label information files (`.bmelabelinfo`) to formatted Excel spreadsheets.

## Features

- ✓ Parse `.bmerawdata`, `.bmelabelinfo`, and `.bmeconfig` files
- ✓ Generate Excel workbooks with multiple sheets:
  - **Configuration**: Board type, heater profiles, duty cycles, sensor configurations
  - **Labels**: Label tag definitions with names and descriptions
  - **Sensor Data**: Complete sensor measurements with formatted columns
- ✓ Auto-detect matching label files
- ✓ Color-coded sensor data rows (8 different colors for sensors 0-7)
- ✓ Decode heater profiles with actual timing in milliseconds
- ✓ Dynamic column headers from data files
- ✓ Proper data type formatting (integer, float, boolean)
- ✓ Auto-sized columns and frozen headers
- ✓ Batch processing of directories

## Installation

### Requirements
- Python 3.7 or higher
- pandas
- openpyxl

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install pandas openpyxl
```
### Virtual environment

On most systems today you will need to create a virtual env
 ```
 $ python3 -m venv --system-site-packages <name>
 $ cd <name>
 $ source bin/activate
 <name> $ pip install -q pandas openpyxl
 ```
 Replace <name> with youir own label e.g. dconv
 The pip install will be local to your venv.
 
 To deactivate the venv.
 ```
 <name>$ deactivate
```
### Python files
 
 Three files make up this pckage:
 - bme_converter.py
 - bme_processor.py
 - bme_parser.py
 - bme_excel_writer.py

## Usage

### Convert Single File

Convert a single `.bmerawdata` file (auto-detects matching `.bmelabelinfo` file):

```bash
python bme_converter.py bme_690_data_2.bmerawdata
```

This creates `bme_690_data_2.xlsx` in the same directory.

### Convert with Specific Label File

Specify a label file explicitly:

```bash
python bme_converter.py bme_690_data_2.bmerawdata -l bme_690_data_2.bmelabelinfo
```

### Custom Output Path

Specify output file name:

```bash
python bme_converter.py bme_690_data_2.bmerawdata -o my_output.xlsx
```

### Batch Convert Directory

Convert all `.bmerawdata` files in a directory:

```bash
python bme_converter.py --dir /path/to/data
```

This creates one Excel file for each `.bmerawdata` file found.

## File Structure

### Input Files

**`.bmeconfig`** - Board configuration
- Board type (BME688 or BME690)
- Heater profiles with temperature/time vectors
- Duty cycle profiles
- Sensor configurations

**`.bmelabelinfo`** - Label definitions
- Label tags with friendly names
- Label descriptions
- Hardware button mappings

**`.bmerawdata`** - Sensor measurements
- Configuration metadata
- Column definitions (dynamic)
- Raw sensor data block

### Output Excel Structure

Each Excel workbook contains three sheets:

#### 1. Configuration Sheet
- Configuration details (date, app version, board type, board mode)
- **Heater Profiles**: Decoded timing with steps showing:
  - Temperature (°C)
  - Time units and multiplier (timeBase)
  - Calculated time in milliseconds and seconds
- **Duty Cycle Profiles**: Scanning and sleeping cycles
- **Sensor Configurations**: Which profile is assigned to each sensor (0-7)

#### 2. Labels Sheet
- Label Tag (numeric identifier)
- Label Name (friendly name)
- Label Description

#### 3. Sensor Data Sheet
- Dynamic columns based on data file (typically 13-14 columns)
- Common columns include:
  - Sensor Index (0-7)
  - Sensor ID
  - Time Since PowerOn (ms)
  - Real time clock (Unix timestamp)
  - Temperature (°C)
  - Pressure (hPa)
  - Relative Humidity (%)
  - Resistance Gassensor (Ω)
  - Heater Profile Step Index
  - Scanning Mode Enabled
  - Scanning Cycle Index
  - Label Tag
  - Error Code
  - Label Name (added if label file provided)
  - Label Description (added if label file provided)
- Color-coded rows by sensor index
- Auto-filter enabled
- Frozen header row
- Column units available in cell comments

## Examples

### Example 1: Quick Convert
```bash
python bme_converter.py bme_690_data_2.bmerawdata
```

Output:
```
Converting: bme_690_data_2.bmerawdata
Using labels: bme_690_data_2.bmelabelinfo
Parsing raw data file...
Parsing label info file...
Processing data...
Creating Excel file: bme_690_data_2.xlsx
✓ Successfully created: bme_690_data_2.xlsx
  - 8 data rows
  - 13 columns
  - Board type: board_690
```

### Example 2: Batch Process
```bash
python bme_converter.py --dir /home/kpi/bmerawdata2xls
```

Output:
```
Found 2 file(s) to convert

Converting: bme_690_data_2.bmerawdata
...
✓ Successfully created: bme_690_data_2.xlsx

Converting: default.bmerawdata
...
✓ Successfully created: default.xlsx

Conversion complete:
  ✓ Success: 2
```

## Understanding Heater Profiles

Heater profiles define temperature steps and durations. The converter automatically decodes these:

- **Profile ID**: e.g., `heater_324` → HP-324 in AI Studio
- **Time Base**: Multiplier in milliseconds (e.g., 140 ms)
- **Temperature/Time Vectors**: Pairs of [temperature, time_units]
  - Example: `[70, 64]` means 70°C for 64 × 140ms = 8960ms = 8.96 seconds

Available profiles in AI Studio: HP-323, HP-324, HP-331, HP-332, HP-354, HP-411, HP-412, HP-413, HP-414, HP-501, HP-502, HP-503, HP-504

## Understanding Duty Cycles

Duty cycles control the scanning pattern:

- **duty_2_6**: 2 scanning cycles with heater ON, 6 sleeping cycles with heater OFF
- Reduces power consumption while maintaining data collection

## Board Types

- **board_690**: BME690 Development Kit (8 sensors)
- **board_688**: BME688 Development Kit (8 sensors)

## Troubleshooting

### Missing Dependencies
```bash
pip install pandas openpyxl
```

### File Not Found
Ensure the `.bmerawdata` file path is correct:
```bash
python bme_converter.py /full/path/to/file.bmerawdata
```

### Label File Not Found
The converter auto-detects matching label files. If not found, it continues without labels.

## Module Documentation

### `bme_parser.py`
Parses JSON files and extracts structured data.

### `bme_processor.py`
Processes raw data into pandas DataFrames with proper formatting.

### `bme_excel_writer.py`
Creates formatted Excel workbooks with styling and multiple sheets.

### `bme_converter.py`
Main CLI program that orchestrates the conversion process.

## License
See LICENCE file. 

## Version
1.0.0

## Author
Specified by Keith McAlister, generated by Claud 4.5. Created for converting Bosch AI Studio Desktop BME sensor data files.

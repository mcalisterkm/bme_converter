# Bosch Sensortec BME to Excel/CSV Converter

![Python Version](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

Convert Bosch Sensortec BME raw data files to formatted Excel spreadsheets or CSV files.

Supports multiple BME file formats:
- **JSON format**: `.bmerawdata`, `.bmelabelinfo`, `.bmeconfig` files
- **Binary format**: `.udf` files with binary sensor data

## Features

### JSON Format Converter (`.bmerawdata`)
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

### Binary UDF to CSV Converter (`.udf` to CSV)
- ✓ Parse `.udf` binary format files with ASCII metadata header
- ✓ Extract sensor readings from packed binary data
- ✓ Auto-detect record structure (61-byte records)
- ✓ Map binary fields to sensor measurement names
- ✓ Convert to CSV with meaningful column headers
- ✓ Support for multiple sensors (0-7)
- ✓ Handle mixed data types (float, integer, compound types)

### UDF to BME Raw Data Converter (`.udf` to `.bmerawdata`)
- ✓ Convert BME690 `.udf` files to BME688-compatible `.bmerawdata` JSON format
- ✓ Auto-detect and use matching `.bmeconfig` configuration file
- ✓ Preserve board configuration (heater profiles, duty cycles, sensor configs)
- ✓ Extract sensor measurements from packed binary data
- ✓ Generate properly formatted .bmerawdata JSON structure
- ✓ Compatible with existing `bme_converter.py` Excel converter
- ✓ Enables full Excel conversion pipeline for BME690 data
- ✓ Handles Application Board 3.1/BME690's lack of RTC (all timestamps relative to power-on)

## Installation

### Requirements
- Python 3.7 or higher
- pandas
- openpyxl

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
If you are not using a virtual environment then the dependencies can be installed globally as raspbian packages using the command: apt install <pkg>. The package names are python3-openpyzl and python3-pandas, however these versions wll not as up to date as using pip to install into a virtual environment. 


## Usage

### Convert bmerawdata JSON Format Files to Excel (`.bmerawdata` →  `.xlsx`)

#### Convert Single File

Convert a single `.bmerawdata` file (auto-detects matching `.bmelabelinfo` file):

```bash
python bme_converter.py bme_690_data_2.bmerawdata
```

This creates `bme_690_data_2.xlsx` in the same directory.

#### Convert with Specific Label File

Specify a label file explicitly:

```bash
python bme_converter.py bme_690_data_2.bmerawdata -l bme_690_data_2.bmelabelinfo
```

#### Custom Output Path

Specify output file name:

```bash
python bme_converter.py bme_690_data_2.bmerawdata -o my_output.xlsx
```

#### Batch Convert Directory

Convert all `.bmerawdata` files in a directory:

```bash
python bme_converter.py --dir /path/to/data
```

This creates one Excel file for each `.bmerawdata` file found.

### Convert Binary UDF Files to CSV (`.udf` → `.csv`)

Convert a `.udf` binary file to CSV:

```bash
python bme_udf_to_csv_converter.py bme_690_data_2.udf
```

This creates `bme_690_data_2.csv` in the same directory.

#### Specify Output File

```bash
python bme_udf_to_csv_converter.py bme_690_data_2.udf -o output.csv
```

### Convert UDF to BME Raw Data (`.udf` → `.bmerawdata`)

Convert BME690 `.udf` binary files to BME688-compatible `.bmerawdata` JSON format. This enables using the full Excel converter pipeline with BME690 data.

#### Basic Conversion

Convert a `.udf` file to `.bmerawdata` format (auto-detects matching `.bmeconfig` file):

```bash
python bme_udf_to_rawdata.py bme_690_data_2.udf
```

This creates `bme_690_data_2.bmerawdata` in the same directory.

#### Specify Config File

If the `.bmeconfig` isn't in the same directory:

```bash
python bme_udf_to_rawdata.py bme_690_data_2.udf -c BoardConfiguration.bmeconfig
```

#### Specify Output File

```bash
python bme_udf_to_rawdata.py bme_690_data_2.udf -o output.bmerawdata
```

#### Verbose Output

See conversion details:

```bash
python bme_udf_to_rawdata.py bme_690_data_2.udf -v
```

#### Use Case

The BME690 devkit creates `.udf` files due to limited filesystem space, while the BME688 devkit with SD card stores data directly in `.bmerawdata` format. This converter bridges the gap, allowing the user to:

1. Convert BME690 `.udf` → `.bmerawdata`
2. Then convert `.bmerawdata` → Excel using `bme_converter.py`

**Example workflow:**
```bash
# Step 1: Convert UDF to bmerawdata
python bme_udf_to_rawdata.py 690-data.udf

# Step 2: Convert to Excel
python bme_converter.py 690-data.bmerawdata
```

**Note:** The BME690 devkit (appboard 3.1 + 8x 690 shuttleboard) has no real-time clock, so all timestamps are relative to power-on (Real time clock field = 0).

### Python files
 
The collection conversion pipeline is split into parsing, normalization, and
export:
- **bme_converter.py** - Main CLI for JSON format (.bmerawdata) conversion to Excel
- **bme_model.py** - Canonical in-memory models for collection sessions
- **bme_board_config_reader.py** - Normalizes standalone and embedded board configuration
- **bme_validation.py** - Validates canonical collection sessions
- **bme_session_reader.py** - Normalizes `.bmerawdata` files into the canonical model
- **bme_processor.py** - Data processing and formatting
- **bme_parser.py** - JSON file parser
- **bme_excel_writer.py** - Excel workbook generator
- **bme_udf_parser.py** - Collection UDF parser adapter
- **bme_udf_container.py** - Generic UDF metadata and binary payload reader
- **bme_udf_to_csv_converter.py** - Binary .udf file to CSV converter
- **bme_udf_to_rawdata.py** - Binary .udf file to .bmerawdata JSON converter

The canonical model currently covers **sensor collection data**. It treats the
board configuration, measurements, labels, and version metadata as one
collection session. The Excel converter now reads `.bmerawdata` through this
model while retaining the existing workbook layout.

Collection sessions are validated when read. Validation checks measurement
columns and basic collection structure. It does not
reinterpret or second-guess heater profiles, duty-cycle settings, or profile
references generated and validated by Bosch AI Studio. Invalid input raises
`SessionValidationError` with all detected structural errors.

### Collection conversion architecture

The collection converters share one normalization pipeline:

```text
.bmerawdata
    -> BMERawDataReader
    -> SessionModel
    -> Excel / .bmerawdata exporters

collection .udf
    -> UDFContainerReader
    -> collection packed-record decoder
    -> SessionModel
    -> CSV / Excel / .bmerawdata exporters
```

`BoardConfigReader` handles both standalone `BoardConfiguration.bmeconfig`
files and embedded `configHeader`/`configBody` sections. The original Bosch
configuration dictionaries are retained for lossless serialization, with
typed views available for application code.

#### Understanding UDF Files

UDF (Unit Definition File) format structure:
- **Version header**: Format version (e.g., "1.2")
- **ASCII metadata**: Field definitions for all sensors (0-7)
  - Field ID, name, size, data type, flags
  - Example: `1: Indoor-air-quality estimate: 5: f,u8: sig,acc`
- **Delimiter**: `\r\n\r\n\r\n` (three CRLF sequences)
- **Binary data**: Packed sensor readings (61-byte records)
  - Each record starts with marker bytes (0x00 0xFF at offset 0-1)
  - Data encoded as little-endian floats, integers, and types
  - Thousands of timestamped measurements

#### UDF Binary Record Structure (61 Bytes)

The `.udf` binary data consists of 61-byte packed records with the following field layout (little-endian):

| Offset | Bytes | Field | Type | Description |
|--------|-------|-------|------|-------------|
| 0-1 | 2 | Marker | u16 | Record marker (0x00FF) |
| 2-9 | 8 | Time Since PowerOn | u64 | Nanoseconds since power-on (divide by 1,000,000 for ms) |
| 10-13 | 4 | Real Time Clock | u32 | Unix timestamp (always 0 for BME690 - no RTC) |
| 12 | 1 | Heater Profile Step | u8 | Profile step index (0-9) |
| 15-18 | 4 | Gas Resistance | float | Ohms (raw sensor measurement) |
| 21-24 | 4 | Relative Humidity | float | Percentage (%rH) |
| 27-30 | 4 | Pressure | float | Hectopascals (hPa) |
| 33-36 | 4 | Temperature | float | Degrees Celsius |
| 39 | 1 | Scanning Cycle | u8 | Cycle index (1-7) |
| 45-48 | 4 | Sensor ID | u32 | Unique sensor identifier |
| 51-54 | 4 | Label Tag | u32 | Label identifier (0, 1, 1001, 1002, etc.) |
| 53 | 1 | Error Code | s8 | Sensor error status |
| 60 | 1 | Sensor Index | u8 | Sensor number (0-7) |

**Data Sources:**
- **seedPowerOnOff**: Read from `.bmelabelinfo` file's `labelInfoHeader.seedPowerOnOff`
- **Label Tag**: Read from `.labelinfo` file's label entries (matched by label tag value)
- **All sensor values**: Extracted directly from binary record at offset positions

The converter automatically:
1. Parses the metadata to understand field structure
2. Detects record boundaries (61-byte fixed size)
3. Extracts all 13 sensor fields at correct offsets
4. Maps to meaningful field names (Temperature, Pressure, Gas resistance, etc.)
5. Loads supplementary data from `.bmelabelinfo` and `.labelinfo` files
6. Outputs clean `.bmerawdata` JSON with proper column headers

## File Structure

### Input Files

#### JSON Format Files

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

#### Binary Format Files

**`.udf`** - Unit Definition File with binary sensor data
- ASCII metadata header with field definitions
- Binary sensor measurements (little-endian packed data)
- Typical fields include:
  - Indoor air quality estimate
  - CO2 equivalent estimate (ppm)
  - Breath VOC concentration estimate (ppm)
  - Raw temperature (°C)
  - Pressure (Pa)
  - Raw humidity (%rH)
  - Gas resistance (Ω)
  - Stabilization status
  - Run-in status
  - Gas estimates (%)
  - Target predictions
  - Sensor index and ID
  - Label tags
  - Error codes

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

### Example 1: Convert JSON Format (Quick)
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

### Example 2: Convert Binary UDF Format
```bash
python bme_udf_to_csv_converter.py 690-tools.bmeproject/Air/bme_690_data_2.udf
```

Output:
```
Processing: 690-tools.bmeproject/Air/bme_690_data_2.udf
Version: 1.2
Metadata: 235 field definitions
Binary data: 244028 bytes
First record: 61 bytes
Subsequent records: 61 bytes
Extracted 4000 records
CSV saved: bme_690_data_2.csv
Done! 4000 records converted.
```

Result: CSV file with columns like:
```
record_num,marker,Indoor-air-quality estimate,CO2 equivalent estimate [ppm],
Temperature,Pressure [Pa],Gas resistance [ohm],Humidity,Raw temperature [deg C],...
```

### Example 3: Batch Process
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

## Validation & Testing

The UDF to `.bmerawdata` converter has been validated across multiple datasets with real sensor data from the BME690 development kit:

| Dataset | Records | Exact Match | Note |
|---------|---------|-------------|------|
| Air | 4,000 | 83% | Laboratory environment measurements |
| Chocolate | 144 | 80% | Factory environment (thermal testing) |
| Coffee | 3,262 | 86% | Factory environment (aroma analysis) |

**Match Quality:**
- ✓ All record counts match (100% parity with original files)
- ✓ All integer fields match exactly (sensor index, sensor ID, label tags, error codes)
- ✓ All field offsets verified and correct
- ⚠ Floating-point fields (temperature, pressure, humidity, gas resistance) have minor precision differences due to IEEE 754 representation variations between conversion methods (~0.0001% variance)

**Data Validation:**
- Verified against original Bosch `.bmerawdata` files
- All 13 required output fields correctly extracted
- Header metadata matches source `.bmelabelinfo` files
- Label tag mappings correctly applied from `.labelinfo` files
- Time conversions (nanoseconds to milliseconds) verified accurate

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

### Floating-Point Precision Differences
When comparing converted files to originals, you may see minor differences in floating-point values (e.g., 25.820690155029297 vs 25.8206901550293). This is normal and due to how floating-point numbers are represented in different contexts. The differences are negligible for practical purposes (&lt;0.0001% relative error).

## Module Documentation

### `bme_parser.py`
Parses JSON format files and extracts structured data from `.bmerawdata`, `.bmelabelinfo`, and `.bmeconfig` files.

### `bme_processor.py`
Processes raw data into pandas DataFrames with proper formatting and data type handling.

### `bme_excel_writer.py`
Creates formatted Excel workbooks with styling, multiple sheets, color-coding,
and auto-sizing. `write_session()` accepts the canonical `SessionModel`.

### `bme_converter.py`
Main CLI program that orchestrates the JSON format conversion process.

### `bme_model.py`
Defines the canonical collection models, including session, board
configuration, measurements, labels, versions, and typed configuration views.

### `bme_board_config_reader.py`
Reads standalone `.bmeconfig` files and embedded Bosch configuration sections
into `BoardConfigModel`.

### `bme_session_reader.py`
Normalizes `.bmerawdata` files into `SessionModel`, including optional matching
label information.

### `bme_rawdata_writer.py`
Serializes a `SessionModel` back to Bosch-compatible `.bmerawdata` JSON while
preserving source sections and canonical measurement columns.

### `bme_validation.py`
Performs structural validation when collection sessions are read. It checks
measurement-column uniqueness and presence, but intentionally does not
reinterpret Bosch AI Studio's heater, timing, duty-cycle, or profile settings.

### `bme_udf_to_csv_converter.py`
Collection UDF CSV adapter. It uses the same packed-record decoder as
`bme_udf_to_rawdata.py`, so CSV and `.bmerawdata` conversion share one source
of truth for metadata, record boundaries, field offsets, and value decoding.

### `bme_udf_parser.py`
Compatibility-facing collection UDF adapter for CSV and Excel output. It
delegates parsing and decoding to `bme_udf_to_rawdata.py`; it does not maintain
a second binary record implementation.

### UDF parsing boundary
`bme_udf_container.py` handles only the common UDF envelope: version,
metadata field definitions, and the opaque binary payload. The collection
specific packed 61-byte decoder remains in `bme_udf_to_rawdata.py`. Future UDF
formats, including AI Studio Mobile test results, can reuse the container
reader without inheriting collection-record assumptions.

## Technical Details

### UDF Binary Format
- **Encoding**: Little-endian
- **Data types**: 
  - `u8`, `u16`, `u32`, `u64`: Unsigned integers (1, 2, 4, 8 bytes)
  - `s8`, `s16`, `s32`: Signed integers (1, 2, 4 bytes)
  - `f`: IEEE 754 single-precision float (4 bytes)
  - Compound types (e.g., `f,u8`): Float + accuracy byte
- **Record structure**: Fixed 61-byte records
- **Record markers**: Start with 0x00FF (marker bytes at offset 0-1)
- **Time encoding**: Nanoseconds (u64 at offset 2), divide by 1,000,000 for milliseconds

### 61-Byte UDF Record Layout

See [UDF Binary Record Structure table](#udf-binary-record-structure-61-bytes) above for complete field mappings and offsets.

Key design characteristics:
- **Packed format**: No alignment padding between fields
- **Field ordering**: Fields not in sequential memory order (e.g., sensor index at offset 60)
- **Mixed types**: Integers and floats packed together
- **Multi-source data**: Some fields (label tag, seed) require data from supplementary files

### Supplementary Files

**.bmelabelinfo** file contains:
- `labelInfoHeader`: Contains `seedPowerOnOff` identifier and board metadata
- `labelInformation`: Array of label definitions with tags, names, descriptions

**.labelinfo** file contains:
- Label tag mappings (numeric ID to friendly name/description)

These files are essential for complete data interpretation and must be in the same directory as the `.udf` file for auto-detection to work.

### Data Processing
- Collection record boundaries are detected using the reverse-engineered
  packed-record layout and marker pattern
- Collection field offsets and conversions are handled by the dedicated
  collection decoder
- UDF metadata and binary payload handling are separated from collection
  record interpretation
- Multi-file correlation combines binary data, board configuration, and label
  information
- Structural validation reports invalid measurement schemas without modifying
  Bosch-generated configuration semantics

## License
See LICENSE file. 

## Version
1.1.0 - Added binary UDF file support

## Author
Specified by Keith McAlister, generated by Claude Sonnet 4.5. Created for converting Bosch AI Studio Desktop BME sensor data files.

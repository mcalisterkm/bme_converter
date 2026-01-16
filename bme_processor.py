"""
Bosch Sensortec BME Data Processor
Processes and transforms BME data for Excel export
"""
import pandas as pd
from typing import Dict, List, Any, Optional


class BMEDataProcessor:
    """Processor for BME sensor data"""
    
    @staticmethod
    def create_label_lookup(labelinfo: Dict[str, Any]) -> Dict[int, Dict[str, str]]:
        """
        Create label lookup dictionary from label info
        
        Args:
            labelinfo: Parsed label information dictionary
            
        Returns:
            Dictionary mapping label tag to label name and description
        """
        label_lookup = {}
        label_list = labelinfo.get('labelInformation', [])
        
        for label in label_list:
            tag = label.get('labelTag')
            if tag is not None:
                label_lookup[tag] = {
                    'name': label.get('labelName', ''),
                    'description': label.get('labelDescription', '')
                }
        
        return label_lookup
    
    @staticmethod
    def decode_heater_profile(heater_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decode heater profile with actual times in milliseconds
        
        Args:
            heater_profile: Heater profile dictionary
            
        Returns:
            List of decoded temperature/time steps
        """
        profile_id = heater_profile.get('id', '')
        time_base = heater_profile.get('timeBase', 1)
        temp_time_vectors = heater_profile.get('temperatureTimeVectors', [])
        
        decoded_steps = []
        for i, (temp, time_units) in enumerate(temp_time_vectors):
            actual_time_ms = time_units * time_base
            decoded_steps.append({
                'step': i + 1,
                'temperature_c': temp,
                'time_units': time_units,
                'time_ms': actual_time_ms,
                'time_seconds': actual_time_ms / 1000.0
            })
        
        return decoded_steps
    
    @staticmethod
    def create_dataframe(data_block: List[List[Any]], 
                        column_info: List[Dict[str, Any]],
                        label_lookup: Optional[Dict[int, Dict[str, str]]] = None) -> pd.DataFrame:
        """
        Create pandas DataFrame from data block with proper column names
        
        Args:
            data_block: List of data rows
            column_info: Column definitions from rawDataBody
            label_lookup: Optional label lookup dictionary
            
        Returns:
            pandas DataFrame with sensor data
        """
        # Extract column names from column_info
        column_names = [col.get('name', f'Column_{col.get("colId", i)}') 
                       for i, col in enumerate(column_info)]
        
        # Create DataFrame
        if not data_block:
            return pd.DataFrame(columns=column_names)
        
        df = pd.DataFrame(data_block, columns=column_names)
        
        # Add label name and description if lookup provided
        if label_lookup and 'Label Tag' in df.columns:
            df['Label Name'] = df['Label Tag'].map(
                lambda x: label_lookup.get(x, {}).get('name', '')
            )
            df['Label Description'] = df['Label Tag'].map(
                lambda x: label_lookup.get(x, {}).get('description', '')
            )
        
        return df
    
    @staticmethod
    def create_config_dataframe(config_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Create DataFrame with configuration information
        
        Args:
            config_data: Parsed configuration data
            
        Returns:
            pandas DataFrame with configuration details
        """
        config_header = config_data.get('configHeader', {})
        
        config_rows = []
        for key, value in config_header.items():
            config_rows.append({
                'Section': 'Configuration Header',
                'Property': key,
                'Value': str(value)
            })
        
        return pd.DataFrame(config_rows)
    
    @staticmethod
    def create_heater_profile_dataframe(heater_profiles: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Create DataFrame with heater profile information
        
        Args:
            heater_profiles: List of heater profile definitions
            
        Returns:
            pandas DataFrame with heater profile details
        """
        rows = []
        
        for profile in heater_profiles:
            profile_id = profile.get('id', '')
            time_base = profile.get('timeBase', 1)
            
            # Add profile header
            rows.append({
                'Profile ID': profile_id,
                'Time Base (ms)': time_base,
                'Step': '',
                'Temperature (°C)': '',
                'Time Units': '',
                'Time (ms)': '',
                'Time (s)': ''
            })
            
            # Decode and add steps
            decoded_steps = BMEDataProcessor.decode_heater_profile(profile)
            for step in decoded_steps:
                rows.append({
                    'Profile ID': '',
                    'Time Base (ms)': '',
                    'Step': step['step'],
                    'Temperature (°C)': step['temperature_c'],
                    'Time Units': step['time_units'],
                    'Time (ms)': step['time_ms'],
                    'Time (s)': step['time_seconds']
                })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def create_duty_cycle_dataframe(duty_cycle_profiles: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Create DataFrame with duty cycle profile information
        
        Args:
            duty_cycle_profiles: List of duty cycle profile definitions
            
        Returns:
            pandas DataFrame with duty cycle details
        """
        rows = []
        
        for profile in duty_cycle_profiles:
            rows.append({
                'Profile ID': profile.get('id', ''),
                'Scanning Cycles': profile.get('numberScanningCycles', 0),
                'Sleeping Cycles': profile.get('numberSleepingCycles', 0)
            })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def create_sensor_config_dataframe(sensor_configs: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Create DataFrame with sensor configuration information
        
        Args:
            sensor_configs: List of sensor configuration definitions
            
        Returns:
            pandas DataFrame with sensor configuration details
        """
        rows = []
        
        for config in sensor_configs:
            rows.append({
                'Sensor Index': config.get('sensorIndex', ''),
                'Heater Profile': config.get('heaterProfile', ''),
                'Duty Cycle Profile': config.get('dutyCycleProfile', '')
            })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def create_label_dataframe(labelinfo: Dict[str, Any]) -> pd.DataFrame:
        """
        Create DataFrame with label information
        
        Args:
            labelinfo: Parsed label information dictionary
            
        Returns:
            pandas DataFrame with label details
        """
        label_list = labelinfo.get('labelInformation', [])
        
        rows = []
        for label in label_list:
            rows.append({
                'Label Tag': label.get('labelTag', ''),
                'Label Name': label.get('labelName', ''),
                'Label Description': label.get('labelDescription', '')
            })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def format_column_by_type(df: pd.DataFrame, column_info: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Format DataFrame columns based on their data types
        
        Args:
            df: DataFrame to format
            column_info: Column definitions with format information
            
        Returns:
            Formatted DataFrame
        """
        for col_def in column_info:
            col_name = col_def.get('name')
            col_format = col_def.get('format', '')
            
            if col_name not in df.columns:
                continue
            
            try:
                if col_format == 'integer':
                    df[col_name] = df[col_name].astype('Int64')
                elif col_format == 'float':
                    df[col_name] = df[col_name].astype(float)
                elif col_format == 'boolean':
                    df[col_name] = df[col_name].astype(bool)
            except Exception:
                # If conversion fails, keep original type
                pass
        
        return df

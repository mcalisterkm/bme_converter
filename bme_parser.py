"""
Bosch Sensortec BME File Parser
Parses .bmeconfig, .bmelabelinfo, and .bmerawdata JSON files
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class BMEFileParser:
    """Parser for Bosch Sensortec BME files"""
    
    @staticmethod
    def parse_config_file(file_path: str) -> Dict[str, Any]:
        """
        Parse .bmeconfig file
        
        Args:
            file_path: Path to .bmeconfig file
            
        Returns:
            Dictionary containing configuration data
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return data
    
    @staticmethod
    def parse_labelinfo_file(file_path: str) -> Dict[str, Any]:
        """
        Parse .bmelabelinfo file
        
        Args:
            file_path: Path to .bmelabelinfo file
            
        Returns:
            Dictionary containing label information
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return data
    
    @staticmethod
    def parse_rawdata_file(file_path: str) -> Dict[str, Any]:
        """
        Parse .bmerawdata file
        
        Args:
            file_path: Path to .bmerawdata file
            
        Returns:
            Dictionary containing raw data and configuration
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return data
    
    @staticmethod
    def extract_column_info(rawdata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract column information from raw data file
        
        Args:
            rawdata: Parsed raw data dictionary
            
        Returns:
            List of column definitions
        """
        return rawdata.get('rawDataBody', {}).get('dataColumns', [])
    
    @staticmethod
    def extract_data_block(rawdata: Dict[str, Any]) -> List[List[Any]]:
        """
        Extract data block from raw data file
        
        Args:
            rawdata: Parsed raw data dictionary
            
        Returns:
            List of data rows
        """
        return rawdata.get('rawDataBody', {}).get('dataBlock', [])
    
    @staticmethod
    def get_board_type(data: Dict[str, Any]) -> str:
        """
        Extract board type from configuration
        
        Args:
            data: Parsed configuration data
            
        Returns:
            Board type string (e.g., 'board_690', 'board_688')
        """
        return data.get('configHeader', {}).get('boardType', 'unknown')
    
    @staticmethod
    def get_heater_profiles(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract heater profiles from configuration
        
        Args:
            data: Parsed configuration data
            
        Returns:
            List of heater profile definitions
        """
        return data.get('configBody', {}).get('heaterProfiles', [])
    
    @staticmethod
    def get_duty_cycle_profiles(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract duty cycle profiles from configuration
        
        Args:
            data: Parsed configuration data
            
        Returns:
            List of duty cycle profile definitions
        """
        return data.get('configBody', {}).get('dutyCycleProfiles', [])
    
    @staticmethod
    def get_sensor_configurations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract sensor configurations
        
        Args:
            data: Parsed configuration data
            
        Returns:
            List of sensor configuration definitions
        """
        return data.get('configBody', {}).get('sensorConfigurations', [])
    
    @staticmethod
    def find_matching_labelinfo(rawdata_path: str) -> Optional[str]:
        """
        Find matching .bmelabelinfo file for a .bmerawdata file
        
        Args:
            rawdata_path: Path to .bmerawdata file
            
        Returns:
            Path to matching .bmelabelinfo file if found, None otherwise
        """
        rawdata_path = Path(rawdata_path)
        base_name = rawdata_path.stem
        labelinfo_path = rawdata_path.parent / f"{base_name}.bmelabelinfo"
        
        if labelinfo_path.exists():
            return str(labelinfo_path)
        
        return None

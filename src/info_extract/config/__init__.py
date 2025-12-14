"""
Configuration module for info_extract project.
This module provides access to configuration data stored in the standard.db SQLite database.
"""
from .config_utils import (get_cached_mapping_sql,
                           save_mapping_sql)
from .profile_manager import profile_manager

__all__ = ["get_cached_mapping_sql", 
           "save_mapping_sql",
           "profile_manager"]

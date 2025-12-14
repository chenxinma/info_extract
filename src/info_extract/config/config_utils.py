"""
Utility functions for converting configuration data between database and file formats.
"""
from .config_db import ConfigDB

def get_cached_mapping_sql(config_db: ConfigDB, hash_key: str) -> str|None:
    """
    从standard.db读取hash_key(表头完全一致)的sql
    """
    return config_db.get_mapping_sql_by_hash_key(hash_key)

def save_mapping_sql(config_db: ConfigDB, hash_key:str, sql_code: str):
    """
    保存生成的sql到standard.db
    """
    config_db.save_mapping_sql(hash_key=hash_key, sql_code=sql_code)
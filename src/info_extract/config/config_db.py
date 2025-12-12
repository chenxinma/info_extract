"""
Configuration database interface for info_extract project.
Provides methods to access configuration data stored in the standard.db SQLite database.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config_models import InfoItem, Example
from langextract.data import Extraction


class ConfigDB:
    """Interface to access configuration data from the standard.db SQLite database."""

    def __init__(self, db_path: Optional[str] = None, active_profile_id: int = 1):
        """
        Initialize the ConfigDB instance.

        Args:
            db_path: Path to the SQLite database. If None, uses default path.
            active_profile_id: ID of the profile to use for queries. Default is 1 (default profile).
        """
        if db_path is None:
            # Default to the standard.db in the config directory
            project_root = Path(__file__).parent.parent.parent
            self.db_path = project_root / "config" / "standard.db"
        else:
            self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Configuration database not found at {self.db_path}")
        
        self.active_profile_id = active_profile_id
    
    
    def get_info_items(self) -> List[InfoItem]:
        """
        Get all information items from the database for the active profile.

        Returns:
            List of InfoItem objects
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id, label, describe, data_type, sort_no, sample_col_name
                FROM info_item
                WHERE profile_id = ?
                ORDER BY sort_no
            """, (self.active_profile_id,))

            rows = cursor.fetchall()

            return [
                InfoItem(
                    id=row['id'],
                    label=row['label'],
                    describe=row['describe'],
                    data_type=row['data_type'],
                    sort_no=row['sort_no'],
                    sample_col_name=row['sample_col_name']
                )
                for row in rows
            ]
        finally:
            if conn:
                conn.close()
    
    
    def get_examples(self) -> List[Example]:
        """
        Get all examples from the database for the active profile.

        Returns:
            List of Example objects
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, fragment FROM example WHERE profile_id = ?", (self.active_profile_id,))

            rows = cursor.fetchall()
            data = [
                Example(
                    id=row['id'],
                    fragment=row['fragment']
                )
                for row in rows
            ]
            return data
        finally:
            if conn:
                conn.close()

    def get_extractions_by_example_id(self, example_id: int) -> List[Tuple[int, Extraction]]:
        """
        Get all extractions for a specific example in the active profile.

        Args:
            example_id: ID of the example

        Returns:
            List of Extraction objects
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    e.id,
                    ii.label as extraction_class,
                    e.extraction_text
                FROM extraction e
                INNER join info_item ii
                ON
                    e.extraction_info_item_id = ii.id
                WHERE e.example_id = ? AND e.profile_id = ?
            """, (example_id, self.active_profile_id))

            rows = cursor.fetchall()
            data = [
                (
                    row["id"],
                    Extraction(
                    extraction_class=row['extraction_class'],
                    extraction_text=row['extraction_text']
                    )
                )
                for row in rows
            ]
            return data
        finally:
            if conn:
                conn.close()


    def get_attributes_by_extraction_id(self, extraction_id:int) -> dict[str, str] | None:
        """
        Get all attributes for a specific extraction in the active profile.

        Args:
            extraction_id: ID of the extraction

        Returns:
            Dictionary of attributes if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    ea."key",
                    ea.value
                FROM
                    ext_attribute ea
                WHERE
                    ea.extraction_id = ? AND ea.profile_id = ?
            """, (extraction_id, self.active_profile_id))

            rows = cursor.fetchall()
            attributes = {}
            for row in rows:
                attributes[row["key"]] = row["value"]

            return attributes
        finally:
            if conn:
                conn.close()

    def get_mapping_sql_by_hash_key(self, hash_key:str) -> str|None:
        """
        Get the mapping SQL code for a specific hash key.

        Args:
            hash_key: Hash key for the mapping

        Returns:
            Mapping SQL code if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    mc.sql_code
                FROM
                    mapping_cache mc
                WHERE
                    mc.hash_key = ?
            """, (hash_key,))
            row = cursor.fetchone()
            if row:
                return row["sql_code"]
        finally:
            if conn:
                conn.close()

    def save_mapping_sql(self, hash_key:str, sql_code:str):
        """
        Save the mapping SQL code to the database.

        Args:
            hash_key: Hash key for the mapping
            sql_code: SQL code for the mapping
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
            INSERT INTO mapping_cache (hash_key, sql_code) values (?, ?)
            """,  (hash_key, sql_code,))
            conn.commit()
        finally:
            if conn:
                conn.close()

    def add_item(self, new_item: InfoItem) -> int:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO info_item (label, describe, data_type, sort_no, sample_col_name, profile_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                new_item.label,
                new_item.describe,
                new_item.data_type,
                new_item.sort_no,
                new_item.sample_col_name,
                self.active_profile_id
            ))

            new_id = cursor.lastrowid
            conn.commit()
            return new_id # type: ignore
        finally:
            if conn:
                conn.close()

    def update_item(self, item: InfoItem):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                    UPDATE info_item
                    SET label=?, describe=?, data_type=?, sort_no=?, sample_col_name=?
                    WHERE id=? AND profile_id=?
                """, (
                    item.label,
                    item.describe,
                    item.data_type,
                    item.sort_no,
                    item.sample_col_name,
                    item.id,
                    self.active_profile_id
                ))

            if cursor.rowcount == 0:
                return 0
            conn.commit()
            return 1
        finally:
            if conn:
                conn.close()

    def update_items_sort(self, item_orders: List[Dict[str, int]]):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for item in item_orders:
                cursor.execute(
                    "UPDATE info_item SET sort_no=? WHERE id=? AND profile_id=?",
                    (item['sort_no'], item['id'], self.active_profile_id)
                )

            if cursor.rowcount == 0:
                return 0
            conn.commit()
            return 1
        finally:
            if conn:
                conn.close()

    def delete_item(self, item_id:int):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM info_item WHERE id=? AND profile_id=?", (item_id, self.active_profile_id))

            if cursor.rowcount == 0:
                return 0
            conn.commit()
            return 1
        finally:
            if conn:
                conn.close()

    def get_available_profiles(self):
        """
        Get all available profiles from the database.

        Returns:
            List of profile records
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, is_default FROM profile ORDER BY name")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            if conn:
                conn.close()

    def get_profile_by_id(self, profile_id: int):
        """
        Get a specific profile by its ID.

        Args:
            profile_id: ID of the profile to retrieve

        Returns:
            Profile record if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description, is_default FROM profile WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            if conn:
                conn.close()

    def create_profile(self, name: str, description: str | None = None) -> int:
        """
        Create a new profile.

        Args:
            name: Name of the new profile
            description: Optional description of the new profile

        Returns:
            ID of the newly created profile
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO profile (name, description, is_default)
                VALUES (?, ?, 0)
            """, (name, description))
            new_id = cursor.lastrowid
            conn.commit()
            return new_id # type: ignore
        finally:
            if conn:
                conn.close()
        return -1

    def set_active_profile(self, profile_id: int):
        """
        Set the active profile ID for this instance.

        Args:
            profile_id: ID of the profile to activate
        """
        self.active_profile_id = profile_id
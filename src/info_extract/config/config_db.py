"""
Configuration database interface for info_extract project.
Provides methods to access configuration data stored in the standard.db SQLite database.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config_models import InfoItem, Example, ExtractionRecord, ExtractionAttribute
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
                    id, label, describe, data_type, sort_no, sample_col_name, profile_id
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
                    sample_col_name=row['sample_col_name'],
                    profile_id=row['profile_id']
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
            cursor.execute("SELECT id, fragment, profile_id FROM example WHERE profile_id = ?", (self.active_profile_id,))

            rows = cursor.fetchall()
            data = [
                Example(
                    id=row['id'],
                    fragment=row['fragment'],
                    profile_id=row['profile_id']
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



    def get_example_by_id(self, example_id: int) -> Optional[Example]:
        """
        Get a specific example text by its ID.

        Args:
            example_id: ID of the example text to retrieve

        Returns:
            ExampleText object if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, fragment, profile_id FROM example WHERE id = ? AND profile_id = ?",
                          (example_id, self.active_profile_id))

            row = cursor.fetchone()
            if row:
                return Example(
                    id=row['id'],
                    fragment=row['fragment'],
                    profile_id=row['profile_id']
                )
            return None
        finally:
            if conn:
                conn.close()

    def create_example(self, fragment: str) -> int:
        """
        Create a new example text.

        Args:
            fragment: The text fragment to store

        Returns:
            ID of the newly created example text
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO example (fragment, profile_id)
                VALUES (?, ?)
            """, (fragment, self.active_profile_id))

            new_id = cursor.lastrowid
            conn.commit()
            return new_id # type: ignore
        finally:
            if conn:
                conn.close()

    def update_example(self, example_id: int, fragment: str) -> int:
        """
        Update an existing example text.

        Args:
            example_id: ID of the example text to update
            fragment: New text fragment

        Returns:
            Number of affected rows (0 if not found, 1 if updated)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE example
                SET fragment = ?
                WHERE id = ? AND profile_id = ?
            """, (fragment, example_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()

    def delete_example(self, example_id: int) -> int:
        """
        Delete an example text and all associated extractions.

        Args:
            example_id: ID of the example text to delete

        Returns:
            Number of affected rows (0 if not found, 1 if deleted)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Delete associated attributes first
            cursor.execute("DELETE FROM ext_attribute WHERE exists (SELECT 1 FROM extraction WHERE example_id = ?) AND profile_id = ?",
                          (example_id, self.active_profile_id))
            # First delete associated extractions
            cursor.execute("DELETE FROM extraction WHERE example_id = ? AND profile_id = ?",
                          (example_id, self.active_profile_id))
            # Then delete the example text
            cursor.execute("DELETE FROM example WHERE id = ? AND profile_id = ?",
                          (example_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()

    def get_extraction_records_by_example_id(self, example_id: int) -> List[ExtractionRecord]:
        """
        Get all extraction records for a specific example text.

        Args:
            example_id: ID of the example text

        Returns:
            List of ExtractionRecord objects
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    extraction.id, 
                    extraction.example_id, 
                    extraction.extraction_info_item_id, 
                    extraction.extraction_text, 
                    extraction.profile_id,
                    info_item.label info_item_label
                FROM extraction
                INNER JOIN info_item
                ON extraction_info_item_id = info_item.id
                WHERE extraction.example_id = ? AND extraction.profile_id = ?
                ORDER BY extraction.id
            """, (example_id, self.active_profile_id))

            rows = cursor.fetchall()
            data = [
                ExtractionRecord(
                    id=row['id'],
                    example_id=row['example_id'],
                    extraction_info_item_id=row['extraction_info_item_id'],
                    extraction_text=row['extraction_text'],
                    profile_id=row['profile_id'],
                    info_item_label=row['info_item_label']
                )
                for row in rows
            ]
            return data
        finally:
            if conn:
                conn.close()

    def get_extraction_record_by_id(self, extraction_id: int) -> Optional[ExtractionRecord]:
        """
        Get a specific extraction record by its ID.

        Args:
            extraction_id: ID of the extraction record to retrieve

        Returns:
            ExtractionRecord object if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    extraction.id, 
                    extraction.example_id, 
                    extraction.extraction_info_item_id, 
                    extraction.extraction_text, 
                    extraction.profile_id,
                    info_item.label info_item_label
                FROM extraction
                INNER JOIN info_item
                ON extraction_info_item_id = info_item.id
                WHERE extraction.id = ? AND extraction.profile_id = ?
            """, (extraction_id, self.active_profile_id))

            row = cursor.fetchone()
            if row:
                return ExtractionRecord(
                    id=row['id'],
                    example_id=row['example_id'],
                    extraction_info_item_id=row['extraction_info_item_id'],
                    extraction_text=row['extraction_text'],
                    profile_id=row['profile_id'],
                    info_item_label=row['info_item_label']
                )
            return None
        finally:
            if conn:
                conn.close()

    def create_extraction_record(self, example_id: int, extraction_info_item_id: int, extraction_text: str) -> int:
        """
        Create a new extraction record.

        Args:
            example_id: ID of the example text this extraction belongs to
            extraction_info_item_id: ID of the info item extracted
            extraction_text: The extracted text

        Returns:
            ID of the newly created extraction record
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO extraction (example_id, extraction_info_item_id, extraction_text, profile_id)
                VALUES (?, ?, ?, ?)
            """, (example_id, extraction_info_item_id, extraction_text, self.active_profile_id))

            new_id = cursor.lastrowid
            conn.commit()
            return new_id # type: ignore
        finally:
            if conn:
                conn.close()

    def update_extraction_record(self, extraction_id: int, extraction_text: str) -> int:
        """
        Update an existing extraction record.

        Args:
            extraction_id: ID of the extraction record to update
            extraction_text: New extracted text

        Returns:
            Number of affected rows (0 if not found, 1 if updated)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE extraction
                SET extraction_text = ?
                WHERE id = ? AND profile_id = ?
            """, (extraction_text, extraction_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()

    def delete_extraction_record(self, extraction_id: int) -> int:
        """
        Delete an extraction record and its attributes.

        Args:
            extraction_id: ID of the extraction record to delete

        Returns:
            Number of affected rows (0 if not found, 1 if deleted)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Delete associated attributes first
            cursor.execute("DELETE FROM ext_attribute WHERE extraction_id = ? AND profile_id = ?",
                          (extraction_id, self.active_profile_id))
            # Then delete the extraction record
            cursor.execute("DELETE FROM extraction WHERE id = ? AND profile_id = ?",
                          (extraction_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()

    def get_extraction_attributes_by_extraction_id(self, extraction_id: int) -> List[ExtractionAttribute]:
        """
        Get all attributes for a specific extraction record.

        Args:
            extraction_id: ID of the extraction record

        Returns:
            List of ExtractionAttribute objects
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, extraction_id, "key", value, profile_id
                FROM ext_attribute
                WHERE extraction_id = ? AND profile_id = ?
                ORDER BY id
            """, (extraction_id, self.active_profile_id))

            rows = cursor.fetchall()
            data = [
                ExtractionAttribute(
                    id=row['id'],
                    extraction_id=row['extraction_id'],
                    key=row['key'],
                    value=row['value'],
                    profile_id=row['profile_id']
                )
                for row in rows
            ]
            return data
        finally:
            if conn:
                conn.close()

    def get_extraction_attribute_by_id(self, attribute_id: int) -> Optional[ExtractionAttribute]:
        """
        Get a specific extraction attribute by its ID.

        Args:
            attribute_id: ID of the extraction attribute to retrieve

        Returns:
            ExtractionAttribute object if found, None otherwise
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, extraction_id, "key", value, profile_id
                FROM ext_attribute
                WHERE id = ? AND profile_id = ?
            """, (attribute_id, self.active_profile_id))

            row = cursor.fetchone()
            if row:
                return ExtractionAttribute(
                    id=row['id'],
                    extraction_id=row['extraction_id'],
                    key=row['key'],
                    value=row['value'],
                    profile_id=row['profile_id']
                )
            return None
        finally:
            if conn:
                conn.close()

    def create_extraction_attribute(self, extraction_id: int, key: str, value: str) -> int:
        """
        Create a new extraction attribute.

        Args:
            extraction_id: ID of the extraction record this attribute belongs to
            key: Attribute key
            value: Attribute value

        Returns:
            ID of the newly created extraction attribute
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ext_attribute (extraction_id, "key", value, profile_id)
                VALUES (?, ?, ?, ?)
            """, (extraction_id, key, value, self.active_profile_id))

            new_id = cursor.lastrowid
            conn.commit()
            return new_id # type: ignore
        finally:
            if conn:
                conn.close()

    def update_extraction_attribute(self, attribute_id: int, key: str, value: str) -> int:
        """
        Update an existing extraction attribute.

        Args:
            attribute_id: ID of the extraction attribute to update
            key: New attribute key
            value: New attribute value

        Returns:
            Number of affected rows (0 if not found, 1 if updated)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ext_attribute
                SET "key" = ?, value = ?
                WHERE id = ? AND profile_id = ?
            """, (key, value, attribute_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()

    def delete_extraction_attribute(self, attribute_id: int) -> int:
        """
        Delete an extraction attribute.

        Args:
            attribute_id: ID of the extraction attribute to delete

        Returns:
            Number of affected rows (0 if not found, 1 if deleted)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ext_attribute WHERE id = ? AND profile_id = ?",
                          (attribute_id, self.active_profile_id))

            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows
        finally:
            if conn:
                conn.close()
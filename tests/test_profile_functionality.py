"""
Unit tests for the profile-based configuration system.
"""
import os
import tempfile
import unittest
import sqlite3
from pathlib import Path

from src.info_extract.config.config_db import ConfigDB
from src.info_extract.config.profile_manager import ProfileManager
from src.info_extract.config.config_models import InfoItem
from src.info_extract.config.config_utils import initialize_profile_manager, output_info_items


class TestProfileFunctionality(unittest.TestCase):
    """Test cases for profile-based configuration functionality."""
    
    def setUp(self):
        """Set up test database with sample data."""
        # Create a temporary database file
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        
        # Create the database with the updated schema
        conn = sqlite3.connect(self.temp_db_path)
        
        # Create tables (mimicking the migration)
        conn.execute("""
            CREATE TABLE profile (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.execute("""
            CREATE TABLE info_item (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                describe TEXT,
                data_type TEXT,
                sort_no INTEGER,
                sample_col_name TEXT,
                profile_id INTEGER NOT NULL DEFAULT 1
            );
        """)
        
        conn.execute("""
            CREATE TABLE example (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                fragment TEXT,
                profile_id INTEGER NOT NULL DEFAULT 1
            );
        """)
        
        conn.execute("""
            CREATE TABLE extraction (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                example_id INTEGER,
                extraction_info_item_id INTEGER,
                extraction_text TEXT,
                profile_id INTEGER NOT NULL DEFAULT 1
            );
        """)
        
        conn.execute("""
            CREATE TABLE ext_attribute (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                extraction_id INTEGER,
                "key" TEXT NOT NULL,
                value TEXT NOT NULL,
                profile_id INTEGER NOT NULL DEFAULT 1
            );
        """)
        
        conn.execute("""
            CREATE TABLE mapping_cache (
                id INTEGER NOT NULL,
                hash_key TEXT(32) NOT NULL,
                sql_code TEXT,
                CONSTRAINT mapping_cache_pk PRIMARY KEY (id)
            );
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX idx_info_item_profile ON info_item(profile_id);")
        conn.execute("CREATE INDEX idx_example_profile ON example(profile_id);")
        conn.execute("CREATE INDEX idx_extraction_profile ON extraction(profile_id);")
        conn.execute("CREATE INDEX idx_ext_attribute_profile ON ext_attribute(profile_id);")
        
        # Insert default profile
        conn.execute("INSERT INTO profile (id, name, description, is_default) VALUES (1, 'Default', 'Default profile', 1);")
        
        # Insert sample data for default profile
        conn.execute("""
            INSERT INTO info_item (label, describe, data_type, sort_no, sample_col_name, profile_id)
            VALUES ('Test Field', 'A test field', 'string', 1, 'test_field', 1);
        """)
        
        conn.execute("""
            INSERT INTO example (fragment, profile_id) 
            VALUES ('This is a test example', 1);
        """)
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up test database."""
        os.close(self.temp_db_fd)
        os.unlink(self.temp_db_path)
    
    def test_config_db_profile_filtering(self):
        """Test that ConfigDB filters data by profile."""
        # Test with default profile (ID 1) - should return data
        config_db = ConfigDB(self.temp_db_path, active_profile_id=1)
        info_items = config_db.get_info_items()
        self.assertEqual(len(info_items), 1)
        self.assertEqual(info_items[0].label, 'Test Field')
        
        # Test with non-existent profile (ID 2) - should return empty list
        config_db_other = ConfigDB(self.temp_db_path, active_profile_id=2)
        info_items_other = config_db_other.get_info_items()
        self.assertEqual(len(info_items_other), 0)
    
    def test_profile_manager_creation(self):
        """Test ProfileManager creation and basic functionality."""
        profile_manager = ProfileManager(self.temp_db_path)
        
        # Check current profile is default
        current_profile = profile_manager.get_current_profile()
        if current_profile:
            self.assertEqual(current_profile['id'], 1)
            self.assertEqual(current_profile['name'], 'Default')
        else:
            self.fail("get_current_profile is None")
        
        # Get available profiles
        available_profiles = profile_manager.get_available_profiles()
        self.assertEqual(len(available_profiles), 1)
        self.assertEqual(available_profiles[0]['id'], 1)
    
    def test_profile_switching(self):
        """Test profile creation and switching."""
        profile_manager = ProfileManager(self.temp_db_path)
        
        # Create a new profile
        new_profile_id = profile_manager.create_profile("Test Profile", "A test profile")
        self.assertGreater(new_profile_id, 1)
        
        # Verify the new profile exists
        all_profiles = profile_manager.get_available_profiles()
        self.assertEqual(len(all_profiles), 2)
        
        # Switch to the new profile
        success = profile_manager.switch_profile(new_profile_id)
        self.assertTrue(success)
        
        # Verify current profile has changed
        current_profile = profile_manager.get_current_profile()
        if current_profile:
            self.assertEqual(current_profile['id'], new_profile_id)
            self.assertEqual(current_profile['name'], 'Test Profile')
        else:
            self.fail("get_current_profile is None")
    
    def test_config_utils_backward_compatibility(self):
        """Test that config_utils functions work with default profile."""
        # Initialize with test database
        initialize_profile_manager(self.temp_db_path, 1)
        
        # Test that output_info_items works (should return default profile data)
        items = output_info_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Test Field')
    
    def test_config_db_profile_isolation(self):
        """Test that profiles are isolated from each other."""
        profile_manager = ProfileManager(self.temp_db_path)
        
        # Add an item to the default profile
        default_config_db = profile_manager.get_config_db()
        new_item = InfoItem(
            id=0,
            label='Default Profile Field',
            describe='Field in default profile',
            data_type='string',
            sort_no=2,
            sample_col_name='default_field'
        )
        item_id = default_config_db.add_item(new_item)
        self.assertGreater(item_id, 0)
        
        # Create and switch to a new profile
        new_profile_id = profile_manager.create_profile("Isolation Test", "Profile for testing isolation")
        profile_manager.switch_profile(new_profile_id)
        
        # Check that the new profile has no items
        new_profile_config_db = profile_manager.get_config_db()
        new_profile_items = new_profile_config_db.get_info_items()
        self.assertEqual(len(new_profile_items), 0)
        
        # Switch back to default and verify original items still exist
        profile_manager.switch_profile(1)
        default_profile_items = profile_manager.get_config_db().get_info_items()
        self.assertEqual(len(default_profile_items), 2)  # Original + newly added item
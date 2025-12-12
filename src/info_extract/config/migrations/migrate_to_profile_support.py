"""
Database migration script to add profile support to the configuration database.

This script adds:
1. profile table to store profile information
2. profile_id column to existing config tables (info_item, example, extraction, ext_attribute)
3. foreign key constraints
4. default profile record
5. migrates existing data to the default profile
"""
import sqlite3
from pathlib import Path


def migrate_database(db_path: str = "./config/standard.db"):
    """
    Execute the database migration to add profile support.
    
    Args:
        db_path: Path to the SQLite database file
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # 1. Create profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_default BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Create profile_metadata table (optional)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile_metadata (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                CONSTRAINT fk_profile_metadata_profile 
                    FOREIGN KEY (profile_id) REFERENCES profile(id)
            );
        """)
        
        # 3. Add profile_id column to info_item (with default value)
        cursor.execute("ALTER TABLE info_item ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1;")
        
        # 4. Add profile_id column to example (with default value)
        cursor.execute("ALTER TABLE example ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1;")
        
        # 5. Add profile_id column to extraction (with default value)
        cursor.execute("ALTER TABLE extraction ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1;")
        
        # 6. Add profile_id column to ext_attribute (with default value)
        cursor.execute("ALTER TABLE ext_attribute ADD COLUMN profile_id INTEGER NOT NULL DEFAULT 1;")
        
        # 7. Insert default profile if it doesn't exist
        cursor.execute("""
            INSERT OR IGNORE INTO profile (id, name, description, is_default) 
            VALUES (1, 'Default', 'Default profile containing existing configuration', 1);
        """)
        
        # 8. Update existing records to associate with default profile
        cursor.execute("UPDATE info_item SET profile_id = 1 WHERE profile_id IS NULL OR profile_id = 0;")
        cursor.execute("UPDATE example SET profile_id = 1 WHERE profile_id IS NULL OR profile_id = 0;")
        cursor.execute("UPDATE extraction SET profile_id = 1 WHERE profile_id IS NULL OR profile_id = 0;")
        cursor.execute("UPDATE ext_attribute SET profile_id = 1 WHERE profile_id IS NULL OR profile_id = 0;")
        
        # 9. Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_info_item_profile ON info_item(profile_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_example_profile ON example(profile_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_extraction_profile ON extraction(profile_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ext_attribute_profile ON ext_attribute(profile_id);")
        
        # Commit transaction
        conn.commit()
        print("Database migration completed successfully!")
        print("Default profile has been created with ID 1")
        print("All existing configuration data has been associated with the default profile")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    # Use a relative path from the current directory
    migrate_database("./config/standard.db")
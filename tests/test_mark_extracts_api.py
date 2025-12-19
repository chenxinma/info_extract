"""
Test module for the mark_extracts API endpoints.
"""
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Add the src directory to the path so we can import the modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.info_extract.ui import UI
from src.info_extract.config.profile_manager import ProfileManager


def setup_test_database():
    """Create a temporary database for testing."""
    # Create temporary database file
    temp_db_fd, temp_db_path = tempfile.mkstemp(suffix='.db')
    
    # Copy the standard.db to the temp location
    standard_db_path = Path(__file__).parent.parent / "config" / "standard.db"
    if standard_db_path.exists():
        with open(standard_db_path, 'rb') as src:
            with open(temp_db_path, 'wb') as dst:
                dst.write(src.read())
    
    os.close(temp_db_fd)  # Close the file descriptor
    return temp_db_path


def test_mark_extracts_api():
    """Test the mark_extracts API endpoints."""
    # Set up temporary database for testing
    temp_db_path = setup_test_database()
    
    try:
        # Initialize profile manager with test database
        profile_manager = ProfileManager(db_path=str(temp_db_path))
        
        # Create UI instance
        ui = UI(db_path=str(temp_db_path))
        client = TestClient(ui.app)
        
        # Test getting available info items
        response = client.get("/config/info_item")
        assert response.status_code == 200
        info_items = response.json()
        assert isinstance(info_items, list)
        
        # Test creating an example text
        response = client.post("/config/example", params={"fragment": "This is a test example text."})
        assert response.status_code == 200
        example_data = response.json()
        assert "id" in example_data
        assert example_data["fragment"] == "This is a test example text."
        
        example_id = example_data["id"]
        
        # Test getting all example texts
        response = client.get("/config/example_texts")
        assert response.status_code == 200
        examples = response.json()
        assert isinstance(examples, list)
        assert len(examples) >= 1
        
        # If we have at least one info item, test creating an extraction
        if info_items:
            info_item_id = info_items[0]["id"]
            
            # Test creating an extraction record
            response = client.post("/config/extractions", 
                                 params={
                                     "example_id": example_id,
                                     "extraction_info_item_id": info_item_id,
                                     "extraction_text": "test extraction"
                                 })
            assert response.status_code == 200
            extraction_data = response.json()
            assert "id" in extraction_data
            assert extraction_data["extraction_text"] == "test extraction"
            
            extraction_id = extraction_data["id"]
            
            # Test getting extractions by example ID
            response = client.get(f"/config/example/{example_id}/extractions")
            assert response.status_code == 200
            extractions = response.json()
            assert isinstance(extractions, list)
            assert len(extractions) >= 1
            
            # Test creating an extraction attribute
            response = client.post(f"/config/extractions/{extraction_id}/attributes",
                                 params={
                                     "key": "test_key",
                                     "value": "test_value"
                                 })
            assert response.status_code == 200
            attribute_data = response.json()
            assert "id" in attribute_data
            assert attribute_data["key"] == "test_key"
            assert attribute_data["value"] == "test_value"
            
            attribute_id = attribute_data["id"]
            
            # Test getting attributes for an extraction
            response = client.get(f"/config/extractions/{extraction_id}/attributes")
            assert response.status_code == 200
            attributes = response.json()
            assert isinstance(attributes, list)
            assert len(attributes) >= 1
            
            # Test updating the example text
            response = client.put(f"/config/example/{example_id}",
                                params={"fragment": "Updated example text."})
            assert response.status_code == 200
            updated_example = response.json()
            assert updated_example["fragment"] == "Updated example text."
            
            # Test updating the extraction
            response = client.put(f"/config/extractions/{extraction_id}",
                                params={"extraction_text": "Updated extraction text"})
            assert response.status_code == 200
            updated_extraction = response.json()
            assert updated_extraction["extraction_text"] == "Updated extraction text"
            
            # Test updating the attribute
            response = client.put(f"/config/extractions/attributes/{attribute_id}",
                                params={"key": "updated_key", "value": "updated_value"})
            assert response.status_code == 200
            updated_attribute = response.json()
            assert updated_attribute["key"] == "updated_key"
            assert updated_attribute["value"] == "updated_value"
            
            # Test deleting the attribute
            response = client.delete(f"/config/extractions/attributes/{attribute_id}")
            assert response.status_code == 200
            
            # Test deleting the extraction
            response = client.delete(f"/config/extractions/{extraction_id}")
            assert response.status_code == 200
            
            # Test deleting the example text
            response = client.delete(f"/config/example/{example_id}")
            assert response.status_code == 200
            
        print("All API endpoints working correctly!")
        
    finally:
        # Clean up temporary database
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


if __name__ == "__main__":
    test_mark_extracts_api()
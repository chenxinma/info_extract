"""
Tests for the UI module and its components.
"""
import asyncio
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import unittest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.info_extract.config import profile_manager
from src.info_extract.ui import UI
from src.info_extract.config.config_db import ConfigDB
from src.info_extract.config.config_models import InfoItem


class TestUIInitialization(unittest.TestCase):
    """Tests for UI class initialization."""

    def setUp(self):
        self.db_path = ":memory:"  # Use in-memory database for testing
        self.work_dir = tempfile.mkdtemp()

    def test_ui_initialization(self):
        """Test that UI initializes with correct components."""
        ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        
        self.assertIsInstance(profile_manager.config_db, ConfigDB)
        self.assertEqual(ui.work_dir, self.work_dir)
        self.assertEqual(len(ui.tasks), 0)

    def test_ui_with_default_parameters(self):
        """Test UI initialization with default parameters."""
        ui = UI()
        
        self.assertIsInstance(profile_manager.config_db, ConfigDB)
        self.assertEqual(ui.work_dir, "./workdir")
        self.assertEqual(len(ui.tasks), 0)


class TestUIRoutesConfig(unittest.TestCase):
    """Tests for configuration-related routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

        # Create a test config item
        self.test_item = InfoItem(
            id=0,
            label="Test Label",
            describe="Test Description",
            data_type="str",
            sort_no=1,
            sample_col_name="test_sample"
        )
        
        self.created_id = profile_manager.config_db.add_item(self.test_item)

    def test_get_info_items(self):
        """Test retrieving all info items."""
        response = self.client.get("/config/info_item")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["label"], "Test Label")
        self.assertEqual(data[0]["data_type"], "str")

    def test_get_info_items_error(self):
        """Test error handling in get_info_items."""
        with patch.object(profile_manager.config_db, 'get_info_items', side_effect=Exception("Database error")):
            response = self.client.get("/config/info_item")
            
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.json())

    def test_create_info_item_success(self):
        """Test creating a new info item."""
        new_item_data = {
            "label": "New Label",
            "describe": "New Description",
            "data_type": "numeric",
            "sort_no": 2,
            "sample_col_name": "new_sample"
        }
        
        response = self.client.post("/config/info_item", json=new_item_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["label"], "New Label")
        self.assertEqual(data["data_type"], "numeric")
        self.assertIsNotNone(data["id"])

    def test_create_info_item_missing_required_fields(self):
        """Test creating an info item without required fields."""
        incomplete_data = {
            "describe": "Missing label and data_type",
            # Missing 'label' and 'data_type'
        }
        
        response = self.client.post("/config/info_item", json=incomplete_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_update_info_item_success(self):
        """Test updating an existing info item."""
        update_data = {
            "label": "Updated Label",
            "describe": "Updated Description",
            "data_type": "date",
            "sort_no": 5,
            "sample_col_name": "updated_sample"
        }
        
        response = self.client.put(f"/config/info_item/{self.created_id}", json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.created_id)
        self.assertEqual(data["label"], "Updated Label")
        self.assertEqual(data["data_type"], "date")

    def test_update_info_item_not_found(self):
        """Test updating a non-existent info item."""
        update_data = {
            "label": "Updated Label",
            "data_type": "str"
        }
        
        response = self.client.put("/config/info_item/999", json=update_data)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_update_info_item_missing_required_fields(self):
        """Test updating an item without required fields."""
        update_data = {
            "describe": "Updated without required fields"
            # Missing 'label' and 'data_type'
        }
        
        response = self.client.put(f"/config/info_item/{self.created_id}", json=update_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_delete_info_item_success(self):
        """Test deleting an existing info item."""
        response = self.client.delete(f"/config/info_item/{self.created_id}")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Info item deleted successfully")
        
        # Verify the item was actually deleted
        items = profile_manager.config_db.get_info_items()
        self.assertEqual(len(items), 0)

    def test_delete_info_item_not_found(self):
        """Test deleting a non-existent info item."""
        response = self.client.delete("/config/info_item/999")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_update_sort_order_success(self):
        """Test updating the sort order of info items."""
        # Create additional items to sort
        item2 = InfoItem(id=0, label="Item 2", data_type="str", sort_no=2, describe="", sample_col_name="")
        item3 = InfoItem(id=0, label="Item 3", data_type="str", sort_no=3, describe="object3", sample_col_name="obj3")
        id2 = profile_manager.config_db.add_item(item2)
        id3 = profile_manager.config_db.add_item(item3)
        
        sort_data = {
            "items": [
                {"id": self.created_id, "sort_no": 1},
                {"id": id2, "sort_no": 2},
                {"id": id3, "sort_no": 3}
            ]
        }
        
        response = self.client.post("/config/info_item/sort", json=sort_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Sort order updated successfully")
        
        # Verify the sort order was updated
        items = profile_manager.config_db.get_info_items()
        for item in items:
            if item.id == self.created_id:
                self.assertEqual(item.sort_no, 1)
            elif item.id == id2:
                self.assertEqual(item.sort_no, 2)
            elif item.id == id3:
                self.assertEqual(item.sort_no, 3)

    def test_update_sort_order_no_items(self):
        """Test updating sort order without providing items."""
        sort_data = {
            "items": []
        }
        
        response = self.client.post("/config/info_item/sort", json=sort_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())


class TestUIRoutesMain(unittest.TestCase):
    """Tests for main UI routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

    def test_serve_config_ui(self):
        """Test serving the config UI page."""
        response = self.client.get("/config/info_item_ui")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_serve_main_ui(self):
        """Test serving the main UI page."""
        response = self.client.get("/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_serve_tasks_ui(self):
        """Test serving the tasks UI page."""
        response = self.client.get("/tasks")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.head("/")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Health"], "OK")

    def test_favicon(self):
        """Test favicon endpoint."""
        # Create a mock favicon file for testing
        favicon_path = Path(self.ui.template_dir) / "favicon.png"
        favicon_path.touch()  # Create an empty file
        
        try:
            response = self.client.get("/favicon.ico")
            self.assertEqual(response.status_code, 200)
        finally:
            # Clean up
            if favicon_path.exists():
                favicon_path.unlink()


class TestUIRoutesWorkingDirectory(unittest.TestCase):
    """Tests for working directory routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

    def test_get_working_directory(self):
        """Test getting the current working directory."""
        response = self.client.get("/api/working-directory")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["working_directory"], self.work_dir)

    def test_set_working_directory_success(self):
        """Test setting a new working directory."""
        new_work_dir = tempfile.mkdtemp()
        request_data = {"path": new_work_dir}
        
        response = self.client.post("/api/working-directory", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["working_directory"], new_work_dir)

    def test_set_working_directory_invalid_path(self):
        """Test setting an invalid working directory."""
        request_data = {"path": "/nonexistent/path"}
        
        response = self.client.post("/api/working-directory", json=request_data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_set_working_directory_error_handling(self):
        """Test error handling when setting working directory."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isdir', return_value=True):
            with patch.object(Path, 'resolve', side_effect=Exception("Path error")):
                request_data = {"path": "/some/valid/path"}
                response = self.client.post("/api/working-directory", json=request_data)
                
                self.assertEqual(response.status_code, 500)
                self.assertIn("error", response.json())


class TestUIRoutesFileBrowsing(unittest.TestCase):
    """Tests for file browsing routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

        # Create test files and directory structure
        self.test_file = Path(self.work_dir) / "test.eml"
        self.test_file.write_text("test content")
        self.test_dir = Path(self.work_dir) / "test_subdir"
        self.test_dir.mkdir()

    def test_get_directory_contents_success(self):
        """Test getting directory contents."""
        response = self.client.get("/api/files")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)  # At least test.eml and test_subdir
        
        # Find our test file in the response
        test_file_found = False
        test_dir_found = False
        for item in data:
            if item["name"] == "test.eml" and not item["is_directory"]:
                test_file_found = True
                self.assertEqual(item["size"], 12)  # Size of "test content"
            elif item["name"] == "test_subdir" and item["is_directory"]:
                test_dir_found = True
        
        self.assertTrue(test_file_found, "Test file not found in response")
        self.assertTrue(test_dir_found, "Test directory not found in response")

    def test_get_directory_contents_with_path_parameter(self):
        """Test getting directory contents with path parameter."""
        response = self.client.get(f"/api/files?path={self.test_dir}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_get_directory_contents_invalid_path(self):
        """Test getting directory contents with invalid path."""
        response = self.client.get("/api/files?path=/nonexistent/path")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_get_directory_contents_access_denied(self):
        """Test getting directory contents with path outside allowed boundaries."""
        # Try to access a path outside the working directory
        outside_path = tempfile.mkdtemp()
        response = self.client.get(f"/api/files?path={outside_path}")
        
        # This should be denied if our security check works properly
        # However, the security check in the actual code is based on the working directory
        # so if we set work_dir to a parent of outside_path, it would be allowed
        # Let's test the case where path is not relative to work_dir
        response = self.client.get(f"/api/files?path={outside_path}")
        # The actual result depends on the implementation in the API
        # If the path is outside the allowed boundaries, it should return 403
        # This is tested by patching the Path.relative_to method to raise ValueError
        with patch.object(Path, 'is_relative_to', return_value=False):
            response = self.client.get(f"/api/files?path={self.work_dir}")
            self.assertEqual(response.status_code, 403)


class TestUIRoutesTaskManagement(unittest.TestCase):
    """Tests for task management routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

    def test_get_tasks_empty(self):
        """Test getting tasks when none exist."""
        response = self.client.get("/api/tasks")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])

    def test_create_task_stream(self):
        """Test creating a task via streaming endpoint."""
        # Mock the executor to avoid actual processing
        with patch('src.info_extract.executor.Executor') as mock_executor_class:
            # Create a mock executor instance
            mock_executor = MagicMock()
            mock_executor.destination_dir = self.work_dir
            mock_executor.run = AsyncMock(return_value=asyncio.StreamReader())
            mock_executor_class.return_value = mock_executor
            mock_executor_class.return_value.destination_dir = self.work_dir
            
            # Create a temporary file for processing
            test_file = Path(self.work_dir) / "test.eml"
            test_file.write_text("test content")
            
            request_data = {
                "working_directory": self.work_dir,
                "files": [str(test_file)]
            }
            
            response = self.client.post("/api/tasks/stream", json=request_data)
            
            # The streaming endpoint should return 200 with streaming content
            self.assertEqual(response.status_code, 200)
            # Check if content type is text/plain for streaming
            self.assertIn("text/plain", response.headers["content-type"])

    def test_get_specific_task(self):
        """Test getting a specific task."""
        # Create a task manually
        task_id = "test-task-id"
        task_data = {
            'id': task_id,
            'status': 'completed',
            'progress': 100,
            'created_at': '2022-01-01T00:00:00',
            'started_at': '2022-01-01T00:00:00',
            'completed_at': '2022-01-01T00:01:00',
            'error': None,
            'result_files': [],
            'files': []
        }
        self.ui.tasks[task_id] = task_data
        
        response = self.client.get(f"/api/tasks/{task_id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], task_id)
        self.assertEqual(data["status"], "completed")

    def test_get_specific_task_not_found(self):
        """Test getting a non-existent task."""
        response = self.client.get("/api/tasks/nonexistent-task-id")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_cancel_task_success(self):
        """Test canceling an existing task."""
        task_id = "test-task-id"
        task_data = {
            'id': task_id,
            'status': 'processing',  # Task must be in a cancellable state
            'progress': 50,
            'created_at': '2022-01-01T00:00:00',
            'started_at': '2022-01-01T00:00:00',
            'completed_at': None,
            'error': None,
            'result_files': [],
            'files': []
        }
        self.ui.tasks[task_id] = task_data
        
        response = self.client.post(f"/api/tasks/{task_id}/cancel")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "cancelled")
        self.assertIsNotNone(data["completed_at"])

    def test_cancel_completed_task(self):
        """Test canceling a completed task (should fail)."""
        task_id = "test-task-id"
        task_data = {
            'id': task_id,
            'status': 'completed',  # Completed tasks should not be cancellable
            'progress': 100,
            'created_at': '2022-01-01T00:00:00',
            'started_at': '2022-01-01T00:00:00',
            'completed_at': '2022-01-01T00:01:00',
            'error': None,
            'result_files': [],
            'files': []
        }
        self.ui.tasks[task_id] = task_data
        
        response = self.client.post(f"/api/tasks/{task_id}/cancel")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_cancel_task_not_found(self):
        """Test canceling a non-existent task."""
        response = self.client.post("/api/tasks/nonexistent-task-id/cancel")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_cancel_running_task_with_executor(self):
        """Test canceling a running task with actual executor cancellation."""
        import threading
        import time
        
        task_id = "test-task-id"
        task_data = {
            'id': task_id,
            'status': 'processing',  # Task must be in a cancellable state
            'progress': 50,
            'created_at': '2022-01-01T00:00:00',
            'started_at': '2022-01-01T00:00:00',
            'completed_at': None,
            'error': None,
            'result_files': [],
            'files': []
        }
        self.ui.tasks[task_id] = task_data
        
        # Create a mock executor and cancellation event
        mock_executor = MagicMock()
        cancellation_event = threading.Event()
        self.ui.running_executors[task_id] = (mock_executor, cancellation_event)
        
        # Verify cancellation event is not set initially
        self.assertFalse(cancellation_event.is_set())
        
        # Call cancel API
        response = self.client.post(f"/api/tasks/{task_id}/cancel")
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "cancelled")
        self.assertIsNotNone(data["completed_at"])
        
        # Verify cancellation event was set
        self.assertTrue(cancellation_event.is_set())
        
        # Verify task was removed from running_executors
        self.assertNotIn(task_id, self.ui.running_executors)


class TestUIRoutesResults(unittest.TestCase):
    """Tests for results routes."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

        # Create a test result file
        self.result_file = Path(self.work_dir) / "test_result.xlsx"
        self.result_file.write_text("test result content")

        # Create a task that generated the result file
        self.task_id = "test-task-id"
        self.task_data = {
            'id': self.task_id,
            'status': 'completed',
            'progress': 100,
            'created_at': '2022-01-01T00:00:00',
            'started_at': '2022-01-01T00:00:00',
            'completed_at': '2022-01-01T00:01:00',
            'error': None,
            'result_files': ["test_result.xlsx"],
            'files': []
        }
        self.ui.tasks[self.task_id] = self.task_data

    def test_get_result_file_success(self):
        """Test downloading a result file."""
        response = self.client.get("/api/results/test_result.xlsx")
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("test result content", response.text)

    def test_get_result_file_invalid_filename(self):
        """Test downloading a result file with invalid path (path traversal)."""
        # Attempt path traversal
        response = self.client.get("/api/results/../../../etc/passwd")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_get_result_file_not_found(self):
        """Test downloading a non-existent result file."""
        response = self.client.get("/api/results/nonexistent.xlsx")
        
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_get_result_file_error_handling(self):
        """Test error handling when getting result file."""
        with patch('os.path.exists', return_value=True), \
             patch('os.path.isfile', return_value=True):
            with patch('pathlib.Path.open', side_effect=PermissionError("Permission denied")):
                response = self.client.get("/api/results/test_result.xlsx")
                
                # Should still return 404 since the file can't be accessed
                self.assertEqual(response.status_code, 404)


class TestUIRunMethod(unittest.TestCase):
    """Tests for the run method of UI class."""

    def test_run_method(self):
        """Test that run method correctly calls uvicorn."""
        ui = UI()
        
        # Mock uvicorn.run to avoid actually starting the server
        with patch('uvicorn.run') as mock_run:
            ui.run()
            
            # Verify that uvicorn.run was called with correct parameters
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], ui.app)
            self.assertEqual(kwargs["host"], ui._host)
            self.assertEqual(kwargs["port"], ui._port)


class TestUICORSConfiguration(unittest.TestCase):
    """Tests for CORS configuration."""

    def setUp(self):
        self.db_path = ":memory:"
        self.work_dir = tempfile.mkdtemp()
        self.ui = UI(db_path=self.db_path, work_dir=self.work_dir)
        self.client = TestClient(self.ui.app)

    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        # Make a request with origin header to check CORS
        headers = {"Origin": "http://example.com"}
        response = self.client.get("/", headers=headers)
        
        # Check if CORS headers are present
        self.assertIn("access-control-allow-origin", response.headers)


if __name__ == '__main__':
    unittest.main()
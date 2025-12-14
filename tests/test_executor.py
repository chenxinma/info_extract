"""
Tests for the Executor class and its components.
"""
import asyncio
import tempfile
import os
from unittest.mock import MagicMock, patch, AsyncMock
import unittest
from threading import Event

from src.info_extract.executor import Executor
from src.info_extract.config.profile_manager import ProfileManager


class TestExecutor(unittest.IsolatedAsyncioTestCase):
    """Tests for Executor class."""

    def setUp(self):
        self.work_dir = tempfile.mkdtemp()
        self.profile_manager = MagicMock(spec=ProfileManager)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.work_dir)

    def test_executor_initialization(self):
        """Test that Executor initializes with correct components."""
        executor = Executor(self.work_dir)
        
        self.assertEqual(executor.source_dir, os.path.join(self.work_dir, 'source'))
        self.assertEqual(executor.processing_dir, os.path.join(self.work_dir, 'processing'))
        self.assertEqual(executor.destination_dir, os.path.join(self.work_dir, 'destination'))
        
        # Verify directories are created
        self.assertTrue(os.path.exists(executor.source_dir))
        self.assertTrue(os.path.exists(executor.processing_dir))
        self.assertTrue(os.path.exists(executor.destination_dir))

    def test_executor_with_specific_files(self):
        """Test Executor initialization with specific files."""
        specific_files = ['file1.eml', 'file2.xlsx']
        executor = Executor(self.work_dir, specific_files=specific_files)
        
        self.assertEqual(executor.specific_files, specific_files)

    async def test_executor_run_without_cancellation(self):
        """Test Executor run method without cancellation."""
        executor = Executor(self.work_dir)
        
        # Mock the pipeline steps to avoid actual processing
        with patch.object(executor.pipeline, 'source', []), \
             patch.object(executor.pipeline, 'extractors', []), \
             patch.object(executor.pipeline, 'destination', []):
            
            # Run without cancellation event
            result = []
            async for progress in executor.run(self.profile_manager):
                result.append(progress)
            
            # Should complete without errors
            self.assertEqual(len(result), 0)  # No steps to process

    async def test_executor_run_with_early_cancellation(self):
        """Test Executor run method with early cancellation."""
        executor = Executor(self.work_dir)
        
        # Create cancellation event
        cancellation_event = Event()
        cancellation_event.set()  # Set cancellation before starting
        
        # Mock the pipeline steps
        mock_source_step = MagicMock()
        mock_source_step.run = AsyncMock()
        
        with patch.object(executor.pipeline, 'source', [('mock_source', mock_source_step)]), \
             patch.object(executor.pipeline, 'extractors', []), \
             patch.object(executor.pipeline, 'destination', []):
            
            # Run with cancellation event
            result = []
            async for progress in executor.run(self.profile_manager, cancellation_event=cancellation_event):
                result.append(progress)
            
            # Should not process any steps
            self.assertEqual(len(result), 0)
            mock_source_step.run.assert_not_called()

    async def test_executor_run_with_mid_process_cancellation(self):
        """Test Executor run method with cancellation during processing."""
        executor = Executor(self.work_dir)
        
        # Create cancellation event
        cancellation_event = Event()
        
        # Mock a source step that yields multiple results
        async def mock_source_run(profile_manager):
            for i in range(5):
                # Simulate processing delay
                await asyncio.sleep(0.1)
                # Check if cancellation event is set
                if cancellation_event.is_set():
                    return
                yield (f"file{i}.eml", {})
        
        mock_source_step = MagicMock()
        mock_source_step.run = mock_source_run
        
        with patch.object(executor.pipeline, 'source', [('mock_source', mock_source_step)]), \
             patch.object(executor.pipeline, 'extractors', []), \
             patch.object(executor.pipeline, 'destination', []):
            
            # Run with cancellation event
            result = []
            # Start processing and cancel after 0.2 seconds
            async def cancel_after_delay():
                await asyncio.sleep(0.2)
                cancellation_event.set()
            
            # Run both coroutines concurrently
            cancel_task = asyncio.create_task(cancel_after_delay())
            process_task = asyncio.create_task(self._collect_executor_results(executor, result))
            
            await asyncio.gather(cancel_task, process_task)
            
            # Should have processed some steps but not all
            self.assertGreater(len(result), 0)
            self.assertLess(len(result), 5)  # Should be cancelled before processing all 5 files

    async def _collect_executor_results(self, executor, result_list):
        """Helper method to collect executor results into a list."""
        async for progress in executor.run(self.profile_manager, cancellation_event=Event()):
            result_list.append(progress)

    def test_clean_processing_dir(self):
        """Test Executor clean_processing_dir method."""
        executor = Executor(self.work_dir)
        
        # Create some test files and directories
        test_file1 = os.path.join(executor.processing_dir, 'test1.txt')
        test_file2 = os.path.join(executor.processing_dir, 'subdir', 'test2.txt')
        os.makedirs(os.path.dirname(test_file2), exist_ok=True)
        
        with open(test_file1, 'w') as f:
            f.write('test content')
        with open(test_file2, 'w') as f:
            f.write('test content')
        
        # Verify files exist before cleaning
        self.assertTrue(os.path.exists(test_file1))
        self.assertTrue(os.path.exists(test_file2))
        
        # Clean processing directory
        executor.clean_processing_dir()
        
        # Verify files and directories are removed
        self.assertFalse(os.path.exists(test_file1))
        self.assertFalse(os.path.exists(test_file2))
        self.assertFalse(os.path.exists(os.path.dirname(test_file2)))


if __name__ == '__main__':
    unittest.main()

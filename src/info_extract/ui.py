"""
UI module for the info_extract project.
Provides a web interface for configuring the info_item table in standard.db and
managing file processing tasks.
"""
import logging
import os
import json
from threading import Timer
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import webbrowser
from importlib.resources import files

from fastapi import Depends, FastAPI, Request, Response
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config.profile_manager import ProfileManager
from .config.config_models import InfoItem
from .pipeline import Pipeline

logger = logging.getLogger(__name__)


class UI:
    """
    UI interface for info_extract project configuration and task management.
    Provides a web interface to manage the info_item table in standard.db
    and to process files through the pipeline.
    """

    def __init__(self, host:str = "127.0.0.1", port:int = 5000,db_path: str|None = None, work_dir:str = "./workdir"):
        """
        Initialize the UI instance.

        Args:
            db_path: Path to the SQLite database. If None, uses default path.
        """

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            def open_browser():
                url = f"http://{self._host}:{str(self._port)}"
                try:
                    webbrowser.open_new_tab(url)
                    print(f"✅ 已自动打开浏览器: {url}")
                except Exception as e:
                    print(f"⚠️ 无法自动打开浏览器: {e}")
                    print(f"请手动访问: {url}")
            
            # 延迟0.5秒确保服务器就绪
            Timer(0.5, open_browser).start()
        
            # Initialize the profile manager and make it available to the UI
            from .config import profile_manager
            yield  {'profile_manager': profile_manager}
            
            # ==================== Shutdown ====================
            # 在这里执行清理操作（如关闭数据库连接）
            print("应用正在关闭...")
        
        self.app = FastAPI(title="Info Extract UI",
                           description="Web interface for info extract project",
                           lifespan=lifespan)


        # Navigate to web directory to find the template
        self.template_dir = Path(__file__).parent / "web"
        print("template dir", self.template_dir)

        

        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.template_dir)), name="static")

        # Task management
        self.tasks: Dict[str, Dict] = {}
        self.work_dir: str = work_dir

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self._host = host
        self._port = port

        self._setup_routes()
    
    async def get_profile_manager(self, request: Request) -> ProfileManager:
        return request.state.profile_manager
    
    def _setup_routes(self):
        """Set up the FastAPI routes for the UI."""

        # Configuration-related routes
        @self.app.get('/config/info_item')
        async def get_info_items(profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Get all info items from the database."""
            try:
                # Get the config_db instance from the profile manager to ensure we're using the active profile
                config_db = profile_manager.get_config_db()
                info_items = config_db.get_info_items()
                return [{
                    'id': item.id,
                    'label': item.label,
                    'describe': item.describe,
                    'data_type': item.data_type,
                    'sort_no': item.sort_no,
                    'sample_col_name': item.sample_col_name
                } for item in info_items]
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.get('/favicon.ico')
        async def favicon():
            favicon_path = self.template_dir / 'favicon.png'
            if favicon_path.exists():
                return FileResponse(str(favicon_path))
            else:
                return JSONResponse(content={'error': 'Favicon not found'}, status_code=404)
    
        @self.app.head("/", include_in_schema=False)  # Hide from API docs
        async def health_check():
            return Response(
                status_code=200,
                headers={"X-Health": "OK"}
            )

        @self.app.post('/config/info_item')
        async def create_info_item(request: Request, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Create a new info item in the database."""
            try:
                # Get the config_db instance from the profile manager to ensure we're using the active profile
                config_db = profile_manager.get_config_db()

                data = await request.json()
                # Add validation for required fields
                if not data.get('label') or not data.get('data_type'):
                    return JSONResponse(content={'error': 'Label and data_type are required'}, status_code=400)

                # Use the ConfigDB method to create the item
                new_item = InfoItem(
                    id=0,  # Will be set by the database
                    label=data['label'],
                    describe=data.get('describe'),
                    data_type=data['data_type'],
                    sort_no=data.get('sort_no'),
                    sample_col_name=data.get('sample_col_name', '')
                )

                # Return the created item with the new ID
                return {
                    'id': config_db.add_item(new_item),
                    'label': new_item.label,
                    'describe': new_item.describe,
                    'data_type': new_item.data_type,
                    'sort_no': new_item.sort_no,
                    'sample_col_name': new_item.sample_col_name
                }
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.put('/config/info_item/{item_id}')
        async def update_info_item(item_id: int, request: Request, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Update an existing info item in the database."""
            try:
                # Get the config_db instance from the profile manager to ensure we're using the active profile
                config_db = profile_manager.get_config_db()

                data = await request.json()
                # Add validation for required fields
                if not data.get('label') or not data.get('data_type'):
                    return JSONResponse(content={'error': 'Label and data_type are required'}, status_code=400)

                rowcount = config_db.update_item(InfoItem(
                    id = item_id,
                    label = data['label'],
                    describe = data.get('describe'),
                    data_type = data['data_type'],
                    sort_no = data.get('sort_no'),
                    sample_col_name = data.get('sample_col_name', ''),
                ))
                if rowcount == 0:
                    return JSONResponse(content={'error': 'Info item not found'}, status_code=404)

                # Return the updated item
                return {
                    'id': item_id,
                    'label': data['label'],
                    'describe': data.get('describe'),
                    'data_type': data['data_type'],
                    'sort_no': data.get('sort_no'),
                    'sample_col_name': data.get('sample_col_name', '')
                }
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.delete('/config/info_item/{item_id}')
        async def delete_info_item(item_id: int, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Delete an info item from the database."""
            try:
                # Get the config_db instance from the profile manager to ensure we're using the active profile
                config_db = profile_manager.get_config_db()

                rowcount = config_db.delete_item(item_id)

                if rowcount == 0:
                    return JSONResponse(content={'error': 'Info item not found'}, status_code=404)

                return {'message': 'Info item deleted successfully'}
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.get('/config/info_item_ui', response_class=HTMLResponse)
        async def serve_config_ui():
            """Serve the configuration UI page."""
            config_ui_path = self.template_dir / 'info_item.html'
            if config_ui_path.exists():
                return FileResponse(str(config_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Configuration UI not found", status_code=404)

        # Route to handle sorting updates
        @self.app.post('/config/info_item/sort')
        async def update_sort_order(request: Request, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Update the sort order of info items."""
            try:
                # Get the config_db instance from the profile manager to ensure we're using the active profile
                config_db = profile_manager.get_config_db()

                data = await request.json()
                item_orders = data.get('items', [])

                if not item_orders:
                    return JSONResponse(content={'error': 'No items provided'}, status_code=400)

                config_db.update_items_sort(item_orders)

                return {'message': 'Sort order updated successfully'}
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        # Main UI routes
        @self.app.get('/', response_class=HTMLResponse)
        async def serve_main_ui():
            """Serve the main UI page."""
            main_ui_path = self.template_dir / 'main.html'
            if main_ui_path.exists():
                return FileResponse(str(main_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Main UI not found", status_code=404)

        @self.app.get('/tasks', response_class=HTMLResponse)
        async def serve_tasks_ui():
            """Serve the tasks UI page."""
            # For now, redirect to the main page since tasks.html doesn't exist
            # In the future, a dedicated tasks page could be created
            main_ui_path = self.template_dir / 'main.html'
            if main_ui_path.exists():
                return FileResponse(str(main_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Main UI not found", status_code=404)

        # File browsing API
        @self.app.get('/api/working-directory')
        async def get_working_directory():
            """Get the current working directory."""
            return {'working_directory': self.work_dir}

        @self.app.post('/api/working-directory')
        async def set_working_directory(request: Request):
            """Set the working directory."""
            try:
                data = await request.json()
                new_path = data.get('path', '')

                # Validate the path to prevent directory traversal
                if not os.path.exists(new_path) or not os.path.isdir(new_path):
                    return JSONResponse(content={'error': 'Invalid directory path'}, status_code=400)

                # Security check: ensure the path is within allowed boundaries
                if not Path(new_path).resolve().is_relative_to(Path(self.work_dir).resolve()):
                    # If the new directory is not within the current working directory, update it
                    self.work_dir = new_path

                return {'working_directory': self.work_dir}
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.get('/api/files')
        async def get_directory_contents(path: str|None = None):
            """Get contents of a directory."""
            try:
                # Use the path from query parameter or default to the working directory
                path = path or self.work_dir

                # Security: validate path is within allowed boundaries
                requested_path = Path(path).resolve()
                base_path = Path(self.work_dir).resolve()

                if not requested_path.is_relative_to(base_path):
                    return JSONResponse(content={'error': 'Access denied'}, status_code=403)

                if not os.path.exists(path) or not os.path.isdir(path):
                    return JSONResponse(content={'error': 'Directory does not exist'}, status_code=400)

                contents = []
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    is_dir = os.path.isdir(item_path)

                    # Only include files with allowed extensions or directories
                    if is_dir or item.lower().endswith(('.eml', '.msg', '.xlsx')):
                        contents.append({
                            'name': item,
                            'path': item_path,
                            'is_directory': is_dir,
                            'size': os.path.getsize(item_path) if not is_dir else 0,
                            'modified': os.path.getmtime(item_path)
                        })

                return contents
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        # Task management API
        @self.app.get('/api/tasks')
        async def get_tasks():
            """Get all tasks."""
            return list(self.tasks.values())

        # Streaming task processing API
        @self.app.post('/api/tasks/stream')
        async def create_task_stream(request: Request):
            """Create a new processing task and stream progress updates."""
            data = await request.json()
            work_dir: str = data.get('working_directory', self.work_dir)
            files: List[str] = data.get('files', [])

            # Generate a unique task ID
            task_id = str(uuid.uuid4())

            # Create task object
            task = {
                'id': task_id,
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'error': None,
                'result_files': [],
                'files': files
            }

            self.tasks[task_id] = task

            async def generate_progress_stream():
                """Generate a stream of progress updates."""
                # Yield initial task info
                yield f"data: {json.dumps({'type': 'task_info', 'data': task})}\n\n"

                # Update task status to started
                task['status'] = 'processing'
                task['started_at'] = datetime.now().isoformat()

                # Yield status update
                yield f"data: {json.dumps({'type': 'status_update', 'data': {'task_id': task_id, 'status': 'processing', 'progress': 0}})}\n\n"

                try:
                    # Import source modules dynamically to process different file types
                    from .executor import Executor

                    executor = Executor(work_dir, specific_files=files)
                    executor.clean_processing_dir()

                    p = 0

                    # Process all files at once using the executor
                    async for txt in executor.pipeline.run():
                        p += int((100 - p) / 10)
                        task['progress'] = p
                        yield f"data: {json.dumps({'type': 'progress_update', 'data': {'task_id': task_id, 'progress': p, 'log': txt}})}\n\n"

                    # Update progress to 100% after processing
                    task['progress'] = 100

                    # Yield progress update
                    yield f"data: {json.dumps({'type': 'progress_update', 'data': {'task_id': task_id, 'progress': 100}})}\n\n"

                    # Update task status to completed
                    task['status'] = 'completed'
                    task['completed_at'] = datetime.now().isoformat()
                    task['progress'] = 100
                    # Add the result files to the task
                    task['result_files'] = [f for f in os.listdir(executor.destination_dir) if os.path.isfile(os.path.join(executor.destination_dir, f))]

                    # Yield completion update
                    yield f"data: {json.dumps({'type': 'completion', 'data': {'task_id': task_id, 'status': 'completed', 'progress': 100, 'result_files': task['result_files']}})}\n\n"

                except Exception as e:
                    # Update task status to failed
                    task['status'] = 'failed'
                    task['error'] = str(e)
                    task['completed_at'] = datetime.now().isoformat()

                    # Yield error update
                    yield f"data: {json.dumps({'type': 'error', 'data': {'task_id': task_id, 'status': 'failed', 'error': str(e)}})}\n\n"

            # Return the streaming response
            return StreamingResponse(generate_progress_stream(), media_type="text/plain")

        @self.app.get('/api/tasks/{task_id}')
        async def get_task(task_id: str):
            """Get a specific task."""
            task = self.tasks.get(task_id)
            if not task:
                return JSONResponse(content={'error': 'Task not found'}, status_code=404)
            return task

        @self.app.post('/api/tasks/{task_id}/cancel')
        async def cancel_task(task_id: str):
            """Cancel a specific task."""
            task = self.tasks.get(task_id)
            if not task:
                return JSONResponse(content={'error': 'Task not found'}, status_code=404)

            if task['status'] in ['completed', 'failed']:
                return JSONResponse(content={'error': 'Cannot cancel completed or failed task'}, status_code=400)

            # Update task status to cancelled
            task['status'] = 'cancelled'
            task['completed_at'] = datetime.now().isoformat()

            return task

        # Results API
        @self.app.get('/api/results/{filename:path}')
        async def get_result_file(filename: str):
            """Download a result file."""
            try:
                # Security: ensure the filename doesn't contain path traversal
                if '..' in filename or filename.startswith('/'):
                    return JSONResponse(content={'error': 'Invalid filename'}, status_code=400)

                # Find the file in task results
                for task in self.tasks.values():
                    if filename in task.get('result_files', []):
                        filepath = os.path.join(task.get('working_directory', self.work_dir), filename)
                        if os.path.exists(filepath):
                            return FileResponse(path=filepath, filename=os.path.basename(filepath))

                return JSONResponse(content={'error': 'File not found'}, status_code=404)
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        # Profile management endpoints
        @self.app.get('/api/config/profiles')
        async def get_profiles(profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Get all available profiles."""
            try:
                profiles = profile_manager.get_available_profiles()
                return profiles
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.post('/api/config/profiles/switch')
        async def switch_profile(request: Request, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Switch to a different profile."""
            try:
                data = await request.json()
                profile_id = data.get('profile_id')

                if not profile_id:
                    return JSONResponse(content={'error': 'profile_id is required'}, status_code=400)

                success = profile_manager.switch_profile(profile_id)
                if not success:
                    return JSONResponse(content={'error': 'Profile not found'}, status_code=404)

                return {'success': True, 'message': f'Profile switched to ID {profile_id}'}
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.get('/api/config/profiles/current')
        async def get_current_profile(profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Get the current active profile."""
            try:
                current_profile = profile_manager.get_current_profile()
                return current_profile
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

        @self.app.post('/api/config/profiles')
        async def create_profile(request: Request, profile_manager: ProfileManager = Depends(self.get_profile_manager)):
            """Create a new profile."""
            try:
                data = await request.json()
                name = data.get('name')
                description = data.get('description', '')

                if not name:
                    return JSONResponse(content={'error': 'name is required'}, status_code=400)

                # Check if profile with this name already exists
                existing_profiles = profile_manager.get_available_profiles()
                for profile in existing_profiles:
                    if profile['name'] == name:
                        return JSONResponse(content={'error': f'Profile with name "{name}" already exists'}, status_code=400)

                new_profile_id = profile_manager.create_profile(name, description)
                return {
                    'id': new_profile_id,
                    'name': name,
                    'description': description,
                    'is_default': False,
                    'isActive': False
                }
            except Exception as e:
                return JSONResponse(content={'error': str(e)}, status_code=500)

    def run(self):
        """Run the FastAPI app using uvicorn."""
        import uvicorn
        uvicorn.run(self.app, host=self._host, port=self._port)


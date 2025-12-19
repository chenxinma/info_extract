

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import threading
from typing import Dict, List, Tuple
import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from ..executor import Executor

from ..config.profile_manager import ProfileManager

from .tools import get_history_tasks, get_profile_manager, get_work_dir


task_router = APIRouter()

running_executors: Dict[str, Tuple[Executor, threading.Event]] = {}


# File browsing API
@task_router.get('/working-directory')
async def get_working_directory(work_dir:str = Depends(get_work_dir)):
    """Get the current working directory."""
    return {'working_directory': work_dir}

@task_router.post('/working-directory')
async def set_working_directory(request: Request, work_dir:str = Depends(get_work_dir)):
    """Set the working directory."""
    try:
        data = await request.json()
        new_path = data.get('path', '')

        # Validate the path to prevent directory traversal
        if not os.path.exists(new_path) or not os.path.isdir(new_path):
            return JSONResponse(content={'error': 'Invalid directory path'}, status_code=400)

        # Security check: ensure the path is within allowed boundaries
        if not Path(new_path).resolve().is_relative_to(Path(work_dir).resolve()):
            # If the new directory is not within the current working directory, update it
            request.state.work_dir = new_path

        return {'working_directory': new_path}
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

@task_router.get('/files')
async def get_directory_contents(path: str|None = None, work_dir:str = Depends(get_work_dir)):
    """Get contents of a directory."""
    try:
        # Use the path from query parameter or default to the working directory
        path = path or work_dir

        # Security: validate path is within allowed boundaries
        requested_path = Path(path).resolve()
        base_path = Path(work_dir).resolve()

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
@task_router.get('/tasks')
async def get_tasks(tasks = Depends(get_history_tasks)):
    """Get all tasks."""
    return list(tasks.values())

# Streaming task processing API
@task_router.post('/tasks/stream')
async def create_task_stream(request: Request, 
                             profile_manager: ProfileManager = Depends(get_profile_manager), 
                             setted_work_dir:str = Depends(get_work_dir),
                             tasks = Depends(get_history_tasks)):
    """Create a new processing task and stream progress updates."""
    data = await request.json()
    work_dir: str = data.get('working_directory', setted_work_dir)
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

    tasks[task_id] = task

    async def generate_progress_stream():
        """Generate a stream of progress updates."""
        # Yield initial task info
        yield f"data: {json.dumps({'type': 'task_info', 'data': task})}\n\n"
        await asyncio.sleep(0.1)
        # Update task status to started
        task['status'] = 'processing'
        task['started_at'] = datetime.now().isoformat()

        # Yield status update
        yield f"data: {json.dumps({'type': 'status_update', 'data': {'task_id': task_id, 'status': 'processing', 'progress': 0}})}\n\n"
        await asyncio.sleep(0.1)
        try:
            # Import source modules dynamically to process different file types
            from ..executor import Executor
            import threading

            executor = Executor(work_dir, specific_files=files)
            executor.clean_processing_dir()
            
            # Create cancellation event
            cancellation_event = threading.Event()
            # Store executor and cancellation event
            running_executors[task_id] = (executor, cancellation_event)

            p = 0

            # Process all files at once using the executor with cancellation support
            async for txt in executor.run(profile_manager, cancellation_event=cancellation_event):
                # Check if task was cancelled
                if cancellation_event.is_set():
                    break
                    
                p += int((100 - p) / 10)
                task['progress'] = p
                yield f"data: {json.dumps({'type': 'progress_update', 'data': {'task_id': task_id, 'progress': p, 'log': txt}})}\n\n"
                await asyncio.sleep(1)

            # Check if task was cancelled
            if cancellation_event.is_set():
                # Update task status to cancelled
                task['status'] = 'cancelled'
                task['completed_at'] = datetime.now().isoformat()
                # Yield cancellation update
                yield f"data: {json.dumps({'type': 'cancellation', 'data': {'task_id': task_id, 'status': 'cancelled'}})}\n\n"
            else:
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
        finally:
            # Remove from running executors
            if task_id in running_executors:
                del running_executors[task_id]

    # Return the streaming response
    return StreamingResponse(generate_progress_stream(), media_type="text/plain")

@task_router.get('/tasks/{task_id}')
async def get_task(task_id: str, tasks = Depends(get_history_tasks)):
    """Get a specific task."""
    task = tasks.get(task_id)
    if not task:
        return JSONResponse(content={'error': 'Task not found'}, status_code=404)
    return task

@task_router.post('/tasks/{task_id}/cancel')
async def cancel_task(task_id: str, tasks = Depends(get_history_tasks)):
    """Cancel a specific task."""
    task = tasks.get(task_id)
    if not task:
        return JSONResponse(content={'error': 'Task not found'}, status_code=404)

    if task['status'] in ['completed', 'failed']:
        return JSONResponse(content={'error': 'Cannot cancel completed or failed task'}, status_code=400)

    # Set cancellation event if task is running
    if task_id in running_executors:
        _, cancellation_event = running_executors[task_id]
        cancellation_event.set()

    # Update task status to cancelled
    task['status'] = 'cancelled'
    task['completed_at'] = datetime.now().isoformat()

    return task

# Results API
@task_router.get('/results/{filename:path}')
async def get_result_file(filename: str, tasks = Depends(get_history_tasks), work_dir:str = Depends(get_work_dir)):
    """Download a result file."""
    try:
        # Security: ensure the filename doesn't contain path traversal
        if '..' in filename or filename.startswith('/'):
            return JSONResponse(content={'error': 'Invalid filename'}, status_code=400)

        # Find the file in task results
        for task in tasks.values():
            if filename in task.get('result_files', []):
                filepath = os.path.join(task.get('working_directory', work_dir), filename)
                if os.path.exists(filepath):
                    return FileResponse(path=filepath, filename=os.path.basename(filepath))

        return JSONResponse(content={'error': 'File not found'}, status_code=404)
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

# Profile management endpoints
@task_router.get('/config/profiles')
async def get_profiles(profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get all available profiles."""
    try:
        profiles = profile_manager.get_available_profiles()
        return profiles
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

@task_router.post('/config/profiles/switch')
async def switch_profile(request: Request, profile_manager: ProfileManager = Depends(get_profile_manager)):
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

@task_router.get('/config/profiles/current')
async def get_current_profile(profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get the current active profile."""
    try:
        current_profile = profile_manager.get_current_profile()
        return current_profile
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

@task_router.post('/config/profiles')
async def create_profile(request: Request, profile_manager: ProfileManager = Depends(get_profile_manager)):
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
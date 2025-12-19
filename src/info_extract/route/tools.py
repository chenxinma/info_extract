from typing import List, Dict, Any, TypeAlias
from fastapi import Request
from ..config.profile_manager import ProfileManager

TaskList : TypeAlias = Dict[str, Dict[str, Any]]

async def get_profile_manager(request: Request) -> ProfileManager:
    return request.state.profile_manager

async def get_work_dir(request: Request) -> str:
    return request.state.work_dir

async def get_history_tasks(request: Request) -> TypeAlias:
    return request.state.tasks
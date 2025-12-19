"""
UI module for the info_extract project.
Provides a web interface for configuring the info_item table in standard.db and
managing file processing tasks.
"""
import logging
from threading import Timer
import threading
from pathlib import Path
from typing import Dict, Tuple
import webbrowser

from fastapi import FastAPI, Response
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from .executor import Executor
from .route import task_router, config_router


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
            yield  {
                        'profile_manager': profile_manager, 
                        'work_dir': work_dir,
                        'tasks' : {}
                   }
            
            # ==================== Shutdown ====================
            # 在这里执行清理操作（如关闭数据库连接）
            print("应用正在关闭...")
        
        self.app = FastAPI(title="Info Extract UI",
                           description="Web interface for info extract project",
                           lifespan=lifespan,
                           docs_url=None)


        # Navigate to web directory to find the template
        self.template_dir = Path(__file__).parent / "web"
        print("template dir", self.template_dir)

        # Mount static files
        self.app.mount("/static", StaticFiles(directory=str(self.template_dir)), name="static")

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

    
    def _setup_routes(self):
        """Set up the FastAPI routes for the UI."""
        

        @self.app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url=self.app.openapi_url, # type: ignore
                title=self.app.title + " - Swagger UI",
                oauth2_redirect_url=self.app.swagger_ui_oauth2_redirect_url,
                swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
                swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
            )

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

        @self.app.get('/config/info_item_list', response_class=HTMLResponse)
        async def serve_config_ui():
            """Serve the configuration UI page."""
            config_ui_path = self.template_dir / 'info_item.html'
            if config_ui_path.exists():
                return FileResponse(str(config_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Configuration UI not found", status_code=404)
        
        @self.app.get('/config/mark_extracts', response_class=HTMLResponse)
        async def serve_mark_extracts_ui():
            """Serve the configuration UI page."""
            config_ui_path = self.template_dir / 'mark_extracts.html'
            if config_ui_path.exists():
                return FileResponse(str(config_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Mark Extracts UI not found", status_code=404)

        # Main UI routes
        @self.app.get('/', response_class=HTMLResponse)
        async def serve_main_ui():
            """Serve the main UI page."""
            main_ui_path = self.template_dir / 'main.html'
            if main_ui_path.exists():
                return FileResponse(str(main_ui_path), media_type="text/html")
            else:
                return HTMLResponse(content="Main UI not found", status_code=404)


        # Include the mark_extracts API routes
        self.app.include_router(task_router, prefix="/api", tags=["task"])
        self.app.include_router(config_router, prefix="/config", tags=["task"])



    def run(self):
        """Run the FastAPI app using uvicorn."""
        import uvicorn
        uvicorn.run(self.app, host=self._host, port=self._port)


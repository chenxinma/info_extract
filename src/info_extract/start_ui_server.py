#!/usr/bin/env python3
"""
Script to start the UI server for manual testing.
"""
from pathlib import Path
from info_extract.ui import UI

def start_server():
    """Start the UI server."""
    print("Starting UI server...")
    
    # Initialize the UI with the correct database path
    db_path = Path("./config") / "standard.db"
    ui = UI(db_path=str(db_path))
    
    print("Available routes:")
    for rule in ui.app.url_map.iter_rules():
        if rule.methods:
            methods = ', '.join(rule.methods)
            print(f"  {rule.rule} -> {methods}")
    
    print(f"\nHTML template is served from: {ui.template_dir}")
    print("Starting server on http://127.0.0.1:5000/config/info_item_ui")
    print("Press Ctrl+C to stop the server")
    
    # Run the server
    ui.run(host='127.0.0.1', port=5000, debug=True)


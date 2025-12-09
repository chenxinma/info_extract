"""
UI module for the info_extract project.
Provides a web interface for configuring the info_item table in standard.db.
"""
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from .config.config_db import ConfigDB
from .config.config_models import InfoItem


class UI:
    """
    UI interface for info_extract project configuration.
    Provides a web interface to manage the info_item table in standard.db.
    """

    def __init__(self, db_path: str|None = None):
        """
        Initialize the UI instance.

        Args:
            db_path: Path to the SQLite database. If None, uses default path.
        """
        self.config_db = ConfigDB(db_path)
        self.app = Flask(__name__)

        # Get the directory of this file to locate the HTML template
        current_dir = Path(__file__).parent
        # Navigate to web directory to find the template
        self.template_dir = current_dir.parent.parent / "web"

        self._setup_routes()
    
    def _setup_routes(self):
        """Set up the Flask routes for the UI."""
        @self.app.route('/config/info_item', methods=['GET'])
        def get_info_items():
            """Get all info items from the database."""
            try:
                info_items = self.config_db.get_info_items()
                return jsonify([{
                    'id': item.id,
                    'label': item.label,
                    'describe': item.describe,
                    'data_type': item.data_type,
                    'sort_no': item.sort_no,
                    'sample_col_name': item.sample_col_name
                } for item in info_items])
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            
        @self.app.route('/favicon.ico')
        def favicon():
            return send_from_directory(str(self.template_dir), 'favicon.png')
        
        @self.app.route('/config/info_item', methods=['POST'])
        def create_info_item():
            """Create a new info item in the database."""
            try:
                data = request.json
                # Add validation for required fields
                if not data.get('label') or not data.get('data_type'):
                    return jsonify({'error': 'Label and data_type are required'}), 400

                # Use the ConfigDB method to create the item
                new_item = InfoItem(
                    id=0,  # Will be set by the database
                    label=data['label'],
                    describe=data.get('describe'),
                    data_type=data['data_type'],
                    sort_no=data.get('sort_no'),
                    sample_col_name=data.get('sample_col_name', '')
                )

                # We need to add a method in ConfigDB to add a new item
                # For now, implementing with raw SQL that matches the expected return
                import sqlite3
                conn = sqlite3.connect(self.config_db.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO info_item (label, describe, data_type, sort_no, sample_col_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_item.label,
                    new_item.describe,
                    new_item.data_type,
                    new_item.sort_no,
                    new_item.sample_col_name
                ))

                new_id = cursor.lastrowid
                conn.commit()
                conn.close()

                # Return the created item with the new ID
                return jsonify({
                    'id': new_id,
                    'label': new_item.label,
                    'describe': new_item.describe,
                    'data_type': new_item.data_type,
                    'sort_no': new_item.sort_no,
                    'sample_col_name': new_item.sample_col_name
                }), 201
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/config/info_item/<int:item_id>', methods=['PUT'])
        def update_info_item(item_id: int):
            """Update an existing info item in the database."""
            try:
                data = request.json
                # Add validation for required fields
                if not data.get('label') or not data.get('data_type'):
                    return jsonify({'error': 'Label and data_type are required'}), 400

                # Get connection and update
                import sqlite3
                conn = sqlite3.connect(self.config_db.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE info_item
                    SET label=?, describe=?, data_type=?, sort_no=?, sample_col_name=?
                    WHERE id=?
                """, (
                    data['label'],
                    data.get('describe'),
                    data['data_type'],
                    data.get('sort_no'),
                    data.get('sample_col_name', ''),
                    item_id
                ))

                if cursor.rowcount == 0:
                    conn.close()
                    return jsonify({'error': 'Info item not found'}), 404

                conn.commit()
                conn.close()

                # Return the updated item
                return jsonify({
                    'id': item_id,
                    'label': data['label'],
                    'describe': data.get('describe'),
                    'data_type': data['data_type'],
                    'sort_no': data.get('sort_no'),
                    'sample_col_name': data.get('sample_col_name', '')
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/config/info_item/<int:item_id>', methods=['DELETE'])
        def delete_info_item(item_id: int):
            """Delete an info item from the database."""
            try:
                import sqlite3
                conn = sqlite3.connect(self.config_db.db_path)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM info_item WHERE id=?", (item_id,))
                
                if cursor.rowcount == 0:
                    conn.close()
                    return jsonify({'error': 'Info item not found'}), 404
                
                conn.commit()
                conn.close()
                
                return jsonify({'message': 'Info item deleted successfully'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/config/info_item_ui', methods=['GET'])
        def serve_config_ui():
            """Serve the configuration UI page."""
            try:
                return send_from_directory(str(self.template_dir), 'info_item.html')
            except FileNotFoundError:
                return "Configuration UI not found", 404
        
        # Route to handle sorting updates
        @self.app.route('/config/info_item/sort', methods=['POST'])
        def update_sort_order():
            """Update the sort order of info items."""
            try:
                data = request.json
                item_orders = data.get('items', [])
                
                if not item_orders:
                    return jsonify({'error': 'No items provided'}), 400
                
                import sqlite3
                conn = sqlite3.connect(self.config_db.db_path)
                cursor = conn.cursor()
                
                for item in item_orders:
                    cursor.execute(
                        "UPDATE info_item SET sort_no=? WHERE id=?",
                        (item['sort_no'], item['id'])
                    )
                
                conn.commit()
                conn.close()
                
                return jsonify({'message': 'Sort order updated successfully'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def run(self, host='127.0.0.1', port=5000, debug=False):
        """Run the Flask app."""
        self.app.run(host=host, port=port, debug=debug)
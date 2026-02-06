# Vavoo Blueprint Integration for MacReplayXC
# This file wraps the vavoo2.py Flask app as a Blueprint

import os
import sys
from flask import Blueprint

# Add vavoo directory to path
vavoo_dir = os.path.join(os.path.dirname(__file__), 'vavoo')
sys.path.insert(0, vavoo_dir)

# Import vavoo app
try:
    # Change to vavoo directory for relative imports
    original_cwd = os.getcwd()
    os.chdir(vavoo_dir)
    
    # Import the vavoo Flask app
    from vavoo2 import app as vavoo_app
    
    # Change back to original directory
    os.chdir(original_cwd)
    
    # Create Blueprint from vavoo app
    vavoo_blueprint = Blueprint(
        'vavoo',
        __name__,
        url_prefix='/vavoo',
        template_folder=os.path.join(vavoo_dir, 'templates') if os.path.exists(os.path.join(vavoo_dir, 'templates')) else None,
        static_folder=os.path.join(vavoo_dir, 'static') if os.path.exists(os.path.join(vavoo_dir, 'static')) else None
    )
    
    # Copy all routes from vavoo app to blueprint
    for rule in vavoo_app.url_map.iter_rules():
        if rule.endpoint != 'static':
            # Get the view function
            view_func = vavoo_app.view_functions[rule.endpoint]
            
            # Remove leading slash from rule
            rule_str = str(rule.rule)
            if rule_str.startswith('/'):
                rule_str = rule_str[1:]
            
            # Add route to blueprint
            vavoo_blueprint.add_url_rule(
                rule_str if rule_str else '/',
                endpoint=rule.endpoint,
                view_func=view_func,
                methods=rule.methods - {'HEAD', 'OPTIONS'}
            )
    
    print("✅ Vavoo Blueprint created successfully")
    
except Exception as e:
    print(f"❌ Error creating Vavoo Blueprint: {e}")
    vavoo_blueprint = None

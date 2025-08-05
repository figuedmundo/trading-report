#!/usr/bin/python3.13
# import sys
# import os

# # IMPORTANT: Replace 'yourusername' with your actual username
# username = 'figuedmundo' 
# project_name = 'trading-report'

# # Add your project directory to Python path
# path = f'/home/{username}/{project_name}'
# if path not in sys.path:
#     sys.path.insert(0, path)

# # Set environment variables
# os.environ['FLASK_APP'] = 'run.py'
# os.environ['PYTHONPATH'] = path

# # Python 3.13 specific optimizations
# # Enable the new JIT compiler if available
# os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import your Flask application
from app import create_app
application = create_app()

# For debugging (remove in production)
# if __name__ == "__main__":
#     application.run()
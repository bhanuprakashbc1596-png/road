import os
import sys

# Add project root to sys.path so we can import app and its modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../road_complaint_system'))

from app import app
import serverless_wsgi

def handler(event, context):
    return serverless_wsgi.handle_request(app, event, context)

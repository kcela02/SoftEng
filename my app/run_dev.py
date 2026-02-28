"""
Development server runner
Run this file to start the Flask application in development mode
"""
import os

# Force development mode
os.environ['FLASK_ENV'] = 'development'

from app import create_app

# Create app with development config
app = create_app('development')

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting VapeCrib Dashboard - Development Server")
    print("=" * 60)
    print(f"📍 Server running on: http://127.0.0.1:5000")
    print(f"🔧 Debug Mode: {app.debug}")
    print(f"💾 Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print("=" * 60)
    print("\n✨ Press Ctrl+C to stop the server\n")
    
    # Get socketio instance from app after it's been created
    from app import socketio
    # Run with SocketIO support
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, allow_unsafe_werkzeug=True)

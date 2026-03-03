import os
from app import create_app, socketio
from whitenoise import WhiteNoise

app = create_app('production')

# Serve static files via WhiteNoise: compressed + long-lived browser cache
app.wsgi_app = WhiteNoise(
    app.wsgi_app,
    root=os.path.join(os.path.dirname(__file__), 'static'),
    prefix='static',
    max_age=86400,          # 1 day browser cache for static assets
    autorefresh=False,
)

# Bind to PORT environment variable that Render provides
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)

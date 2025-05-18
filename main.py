import os
import logging
from app import app
from routes.auth import auth_bp
from routes.games import games_bp
from routes.main import main_bp
from routes.mining import mining_bp

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(games_bp)
app.register_blueprint(main_bp)
app.register_blueprint(mining_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

#!/usr/bin/env python
"""
Main py script for application creation and execution.
"""
import os

from duck.settings import SETTINGS

# Modify debug settings in place for fast deployment and testing
# DEPLOYMENT SETTINGS (Heroku compatible)
DEBUG = bool(os.getenv('DEBUG', True))
PORT = int(os.getenv("PORT") or 8000)
DOMAIN = os.getenv('DOMAIN') or "localhost"
SERVER_URL = os.getenv('SERVER_URL')

SETTINGS['ENABLE_HTTPS'] = 0
SETTINGS['DEBUG'] = DEBUG
SETTINGS['USE_DJANGO'] = 0 if DEBUG else 1
SETTINGS['LOG_TO_FILE'] = 1 if DEBUG else 0
SETTINGS['EXTRA_HEADERS'] = {"cache-control": "no-cache"} if DEBUG else {}
SETTINGS['ALLOWED_HOSTS'] = [DOMAIN, f"*.{DOMAIN}"] if not DEBUG else ["*"]
SETTINGS['ASYNC_HANDLING'] = 1
SETTINGS['ASYNC_LOOP'] = "uvloop" if not DEBUG else "asyncio"


from duck.app import App


app = App(
    port=PORT,
    addr="0.0.0.0",
    domain=DOMAIN,
    workers=5,
    server_url=SERVER_URL,
)

 
if __name__ == "__main__":
    # Run the application
    app.run()

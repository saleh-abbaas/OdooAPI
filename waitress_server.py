# waitress_server.py

import logging
from logging.handlers import RotatingFileHandler
from OdooAPI import create_app

# Set up logging
handler = RotatingFileHandler('waitress.log', maxBytes=10*1024*1024, backupCount=5)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)

# Get the root logger and add the handler
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

app = create_app()

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)

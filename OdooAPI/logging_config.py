import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    # Application logger
    handler = RotatingFileHandler(app.config['LOG_FILE'], maxBytes=10*1024*1024, backupCount=5)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Audit logger
    audit_logger = logging.getLogger('audit')
    audit_handler = RotatingFileHandler(app.config['AUDIT_LOG_FILE'], maxBytes=10*1024*1024, backupCount=5)
    audit_handler.setLevel(logging.INFO)
    audit_formatter = logging.Formatter('%(asctime)s %(message)s')
    audit_handler.setFormatter(audit_formatter)
    audit_logger.addHandler(audit_handler)

import os

class Config:
    # Odoo connection parameters
    ODOO_URL = 'http://localhost:8069'
    ODOO_DB = 'marafeqdemo'
    ODOO_USERNAME = 'esadad@marafeqserv.com'
    ODOO_PASSWORD = 'iiok6HCLPiS4CfX'  # Get password from environment variable
    # SSL Verification
    ODOO_SSL_VERIFY = False  # Set to True if using a valid SSL certificate

    # Logging configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_FILE = os.path.join(BASE_DIR, 'app.log')
    AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit.log')

    # MySQL configuration (adjust as needed)
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'example'
    MYSQL_DB = 'audit_db'
    MYSQL_CHARSET = 'utf8mb4'

    # SQLAlchemy Database URL
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}?charset={MYSQL_CHARSET}"

# OdooAPI/config.py

import os

class Config:
    # Odoo connection parameters
    # ODOO_URL = 'https://erp.marafeqserv.com'
    # ODOO_DB = 'marafeq'
    # ODOO_USERNAME = 'esadad@marafeqserv.com'
    # ODOO_PASSWORD = 'iiok6HCLPiS4CfX'  # Get password from environment variable
    # ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD')  # Get password from environment variable

    # Marafeq Demo 
    ODOO_URL = 'https://erp.marafeqserv.com'
    ODOO_DB = 'marafeqdemo'
    ODOO_USERNAME = 'esadad@marafeqserv.com'
    ODOO_PASSWORD = 'iiok6HCLPiS4CfX'  # Get password from environment variable
    # SSL Verification
    ODOO_SSL_VERIFY = False  # Set to True if using a valid SSL certificate
    
    # Logging configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_FILE = os.path.join(BASE_DIR, 'app.log')
    AUDIT_LOG_FILE = os.path.join(BASE_DIR, 'audit.log')

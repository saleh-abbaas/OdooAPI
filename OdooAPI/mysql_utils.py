import mysql.connector
from mysql.connector import Error
from flask import current_app
import logging

def get_mysql_connection():
    """Establish a connection to the MySQL database using credentials from config."""
    try:
        config = current_app.config
        connection = mysql.connector.connect(
            host=config['MYSQL_HOST'],
            user=config['MYSQL_USER'],
            password=config['MYSQL_PASSWORD'],
            database=config['MYSQL_DB']
        )
        return connection
    except Error as e:
        logging.error(f"MySQL connection error: {e}", exc_info=True)
        raise

def check_guid_exists(guid):
    """Check if the given GUID already exists in audit logs."""
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id FROM payment_audit WHERE guid = %s LIMIT 1"
        cursor.execute(query, (guid,))
        row = cursor.fetchone()
        return row is not None
    except Error as e:
        logging.error(f"MySQL error checking GUID: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def insert_guid_record(guid, customer_id, total_amount, source):
    """Insert initial record for this GUID to prevent duplicates."""
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO payment_audit (guid, customer_id, total_amount, source, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (guid, customer_id, total_amount, source))
        conn.commit()
    except Error as e:
        logging.error(f"MySQL insert GUID record error: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

def log_invoices_state(guid, stage, invoices):
    """Log the state of invoices before or after processing payment.
       stage: 'before' or 'after'"""
    if not invoices:
        return
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO invoice_state_log (guid, invoice_id, amount_residual, amount_total, state, log_stage, logged_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        for inv in invoices:
            invoice_id = inv.get('id')
            amount_residual = inv.get('amount_residual', 0.0)
            amount_total = inv.get('amount_total', 0.0)
            invoice_state = inv.get('state', 'unknown')
            cursor.execute(query, (guid, invoice_id, amount_residual, amount_total, invoice_state, stage))
        conn.commit()
    except Error as e:
        logging.error(f"MySQL invoice state logging error: {e}", exc_info=True)
        raise
    finally:
        cursor.close()
        conn.close()

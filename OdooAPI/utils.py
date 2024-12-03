# OdooAPI/utils.py

from flask import request
from datetime import datetime
import logging

def create_json_response(message, code, datetime_value, query_number, query_table, status_of_query, status, query_status):
    response = {
        'message': message,
        'code': code,
        'datetime': datetime_value.strftime('%Y-%m-%d %H:%M:%S'),
        'queryNumber': query_number,
        'queryTable': query_table,
        'status_of_query': str(status_of_query).lower(),
        'status': status,
        'query_status': str(query_status)
    }
    return response

def audit_request(audit_logger, endpoint, request_data, source):
    try:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        audit_data = {
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'endpoint': endpoint,
            'source': source,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'request_data': request_data
        }
        audit_logger.info(audit_data)
    except Exception as e:
        logging.error("Audit logging failed", exc_info=True)

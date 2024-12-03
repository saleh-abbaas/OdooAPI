# OdooAPI/routes.py

from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
import logging

from .utils import create_json_response, audit_request
from .odoo_client import OdooClient

bp = Blueprint('main', __name__)

def get_odoo_client():
    config = current_app.config
    return OdooClient(
        url=config['ODOO_URL'],
        db=config['ODOO_DB'],
        username=config['ODOO_USERNAME'],
        password=config['ODOO_PASSWORD'],
        ssl_verify=config['ODOO_SSL_VERIFY']
    )

@bp.route('/check_customer', methods=['POST'])
def check_customer():
    logging.info("Received request at /check_customer")
    query_number = str(uuid.uuid4())
    query_table = 'check_customer'

    try:
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data.")

        mobile_number = data.get('mobile_number')
        source = data.get('source')

        if not mobile_number:
            raise ValueError("Mobile number is required.")
        if not source:
            raise ValueError("Source is required.")

        mobile_number = mobile_number.strip()
        source = source.strip().lower()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/check_customer', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source.")

        # Get Odoo client
        odoo_client = get_odoo_client()

        # Search for partners by mobile number
        try:
            partners = odoo_client.get_partners_by_mobile(mobile_number)
        except Exception as e:
            logging.error(f"Odoo connection error: {e}", exc_info=True)
            return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

        if not partners:
            # message = f"No customer found for mobile number {mobile_number}."
            message = f"Invalid Billing Number"
            code = '408'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Check customer failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for mobile number {mobile_number}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Check customer failed: {message}")
            return jsonify(response_data), 400
        else:
            # Exactly one customer found
            message = f"Customer found for mobile number {mobile_number}: {partners[0]['name']}."
            code = '200'
            status_of_query = True
            status_str = 'successful'
            query_status = 1
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.info(f"Check customer success: {message}")
            return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in /check_customer endpoint: {e}", exc_info=True)
        error_message = f"Error: {str(e)}"
        code = '500'
        status_of_query = False
        status_str = 'failed'
        query_status = 0
        response_data = create_json_response(
            error_message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
        response_data['invoice_list'] = []
        return jsonify(response_data), 500

@bp.route('/total_amount', methods=['POST'])
def get_total_amount():
    logging.info("Received request at /total_amount")
    query_number = str(uuid.uuid4())
    query_table = 'total_amount'

    try:
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data.")

        mobile_number = data.get('mobile_number')
        source = data.get('source')

        if not mobile_number:
            raise ValueError("Mobile number is required.")
        if not source:
            raise ValueError("Source is required.")

        mobile_number = mobile_number.strip()
        source = source.strip().lower()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/total_amount', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source. Accepted values are 'demo' or 'esadad'.")

        # Get Odoo client
        odoo_client = get_odoo_client()

        # Search for partners by mobile number
        try:
            partners = odoo_client.get_partners_by_mobile(mobile_number)
        except Exception as e:
            logging.error(f"Odoo connection error: {e}", exc_info=True)
            return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

        if not partners:
            message = f"Invalid Billing Number"
            # No customer found for mobile number {mobile_number}.
            code = '408'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Total amount failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for mobile number {mobile_number}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Total amount failed: {message}")
            return jsonify(response_data), 400
        else:
            try:
                invoices = odoo_client.get_unpaid_invoices_by_mobile(mobile_number)
            except Exception as e:
                logging.error(f"Odoo connection error: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            if not invoices:
                total_amount=0.0
                message = f"No unpaid invoices found for mobile number {mobile_number}."
                code = '200'
                status_of_query = True
                status_str = 'successful'
                query_status = 0
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['total_amount'] = total_amount
                response_data['invoice_list'] = []
                logging.info(f"Total amount failed: {message}")
                return jsonify(response_data), 200
            else:
                total_amount = sum(invoice['amount_residual'] for invoice in invoices)
                invoice_list = [{'id':p['id'],'amount':p['amount_residual']} for p in invoices]
                message = f"Total unpaid amount for mobile number {mobile_number} is {total_amount}."
                code = '200'
                status_of_query = True
                status_str = 'successful'
                query_status = 1
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['invoice_list'] = invoice_list
                response_data['total_amount'] = total_amount  # Include total amount in response
                logging.info(f"Total amount success: {message}")
                return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in /total_amount endpoint: {e}", exc_info=True)
        error_message = f"Error: {str(e)}"
        code = '500'
        status_of_query = False
        status_str = 'failed'
        query_status = 0
        response_data = create_json_response(
            error_message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
        response_data['invoice_list'] = []
        return jsonify(response_data), 500

@bp.route('/pay_invoices', methods=['POST'])
def pay_all_invoices():
    logging.info("Received request at /pay_invoices")
    query_number = str(uuid.uuid4())
    query_table = 'pay_invoices'

    try:
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data.")

        mobile_number = data.get('mobile_number')
        total_amount = data.get('total_amount')
        payment_date = data.get('date')
        source = data.get('source')

        if not mobile_number:
            raise ValueError("Mobile number is required.")
        if not total_amount:
            raise ValueError("Total amount is required.")
        if not payment_date:
            raise ValueError("Date is required.")
        if not source:
            raise ValueError("Source is required.")

        mobile_number = mobile_number.strip()
        total_amount = float(total_amount)
        payment_date = payment_date.strip()
        source = source.strip().lower()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/pay_invoices', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source. Accepted values are 'demo' or 'esadad'.")

        # Get Odoo client
        odoo_client = get_odoo_client()

        # Search for partners by mobile number
        try:
            partners = odoo_client.get_partners_by_mobile(mobile_number)
        except Exception as e:
            logging.error(f"Odoo connection error: {e}", exc_info=True)
            return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

        if not partners:
            message = "Invalid Billing Number"
            code = '408'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Pay invoices failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for mobile number {mobile_number}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = []
            logging.error(f"Pay invoices failed: {message}")
            return jsonify(response_data), 400
        else:
            # Validate the total amount using '/total_amount'
            try:
                invoices = odoo_client.get_unpaid_invoices_by_mobile(mobile_number)
            except Exception as e:
                logging.error(f"Odoo connection error: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            if not invoices:
                total_unpaid_amount = 0.0
                message = f"No unpaid invoices found for mobile number {mobile_number}."
                code = '303'
                status_of_query = False
                status_str = 'failed'
                query_status = 0
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['invoice_list'] = []
                response_data['total_amount'] = total_unpaid_amount
                logging.error(f"Pay invoices failed: {message}")
                return jsonify(response_data), 303

            total_unpaid_amount = sum(invoice['amount_residual'] for invoice in invoices)

            # Check if the inputted total_amount matches the calculated total_unpaid_amount
            if round(total_unpaid_amount, 2) != round(total_amount, 2):
                message = "Provided total amount does not match the total unpaid amount."
                code = '303'
                status_of_query = False
                status_str = 'failed'
                query_status = 0
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['invoice_list'] = []
                response_data['expected_total_amount'] = total_unpaid_amount
                logging.error(f"Pay invoices failed: {message}")
                return jsonify(response_data), 303

            # Proceed to register payments
            try:
                payment_results = odoo_client.register_payment_for_invoices(invoices, payment_date)
            except Exception as e:
                logging.error(f"Odoo connection error: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            # Convert payment results to string for the message
            payments_info = '; '.join(
                [f"Invoice ID {p['invoice_id']}: {p['status']}" for p in payment_results])
            invoice_list = [ {'invoice_id':p['invoice_id'],'status' : p['status']} for p in payment_results]
            message = f"Payment process completed. Details: {payments_info}."
            code = '200'
            status_of_query = True
            status_str = 'successful'
            query_status = 1
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            response_data['invoice_list'] = invoice_list
            logging.info(f"Pay invoices success: {message}")
            return jsonify(response_data)

    except Exception as e:
        logging.error(f"Error in /pay_invoices endpoint: {e}", exc_info=True)
        error_message = f"Error: {str(e)}"
        code = '500'
        status_of_query = False
        status_str = 'failed'
        query_status = 0
        response_data = create_json_response(
            error_message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
        response_data['invoice_list'] = []
        return jsonify(response_data), 500

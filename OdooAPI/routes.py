from flask import Blueprint, request, jsonify, current_app
import uuid
from datetime import datetime
import logging

from .utils import create_json_response, audit_request
from .odoo_client import OdooClient
from .models import PaymentRequest, InvoiceStateLog, PaymentInvoiceResult, get_session

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

def check_guid_exists(session, guid):
    """Check if the given GUID already exists in the payment requests table."""
    return session.query(PaymentRequest).filter_by(requestGUID=guid).first() is not None

def insert_guid_record(session, guid, customer_id, total_amount, source):
    """Insert initial record for this GUID."""
    new_record = PaymentRequest(
        requestGUID=guid,
        customer_id=customer_id,
        total_amount=total_amount,
        source=source
    )
    session.add(new_record)
    session.commit()

def log_invoices_state(session, guid, stage, invoices):
    """Log the state of invoices before or after processing payment."""
    if not invoices:
        return
    logs = []
    for inv in invoices:
        logs.append(InvoiceStateLog(
            guid=guid,
            invoice_id=inv.get('id'),
            amount_residual=inv.get('amount_residual', 0.0),
            amount_total=inv.get('amount_total', 0.0),
            state=inv.get('state', 'unknown'),
            log_stage=stage
        ))
    session.add_all(logs)
    session.commit()

def log_payment_results(session, guid, invoice_list):
    """Log the final payment results (amount_paid, amount_remaining, etc.) for each invoice."""
    results = []
    for inv in invoice_list:
        results.append(PaymentInvoiceResult(
            guid=guid,
            invoice_id=inv['invoice_id'],
            amount_paid=inv['amount_paid'],
            amount_remaining=inv['amount_remaining'],
            invoice_total_amount=inv['invoice_total_amount'],
            status=inv['status']
        ))
    session.add_all(results)
    session.commit()


@bp.route('/check_customer', methods=['POST'])
def check_customer():
    logging.info("Received request at /check_customer")
    query_number = str(uuid.uuid4())
    query_table = 'check_customer'

    try:
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data.")

        customer_id = data.get('customer_id')
        source = data.get('source')

        if not customer_id:
            raise ValueError("Customer ID is required.")
        if not source:
            raise ValueError("Source is required.")

        customer_id = customer_id.strip()
        source = source.strip().lower()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/check_customer', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source.")

        odoo_client = get_odoo_client()

        # Search for partners by customer id
        try:
            partners = odoo_client.get_partners_by_mobile(customer_id)
        except Exception as e:
            logging.error(f"Odoo connection error: {e}", exc_info=True)
            return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

        if not partners:
            message = f"Invalid Billing Number"
            code = '408'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            logging.error(f"Check customer failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for customer id {customer_id}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            logging.error(f"Check customer failed: {message}")
            return jsonify(response_data), 400
        else:
            message = f"Customer found for customer id {customer_id}: {partners[0]['name']}."
            code = '200'
            status_of_query = True
            status_str = 'successful'
            query_status = 1
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
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

        customer_id = data.get('customer_id')
        source = data.get('source')

        if not customer_id:
            raise ValueError("Customer ID is required.")
        if not source:
            raise ValueError("Source is required.")

        customer_id = customer_id.strip()
        source = source.strip().lower()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/total_amount', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source. Accepted values are 'demo' or 'esadad'.")

        odoo_client = get_odoo_client()

        # Search for partners by customer id
        try:
            partners = odoo_client.get_partners_by_mobile(customer_id)
        except Exception as e:
            logging.error(f"Odoo connection error: {e}", exc_info=True)
            return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

        if not partners:
            message = f"Invalid Billing Number"
            code = '408'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            logging.error(f"Total amount failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for customer id {customer_id}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            logging.error(f"Total amount failed: {message}")
            return jsonify(response_data), 400
        else:
            try:
                invoices = odoo_client.get_unpaid_invoices_by_mobile(customer_id)
            except Exception as e:
                logging.error(f"Odoo connection error: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            if not invoices:
                total_amount=0.0
                message = f"No unpaid invoices found for customer id {customer_id}."
                code = '200'
                status_of_query = True
                status_str = 'successful'
                query_status = 0
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['total_amount'] = total_amount
                logging.info(f"Total amount success: {message}")
                return jsonify(response_data), 200
            else:
                total_amount = sum(invoice['amount_residual'] for invoice in invoices)
                message = f"Total unpaid amount for customer id {customer_id} is {total_amount}."
                code = '200'
                status_of_query = True
                status_str = 'successful'
                query_status = 1
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['total_amount'] = total_amount
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
        return jsonify(response_data), 500


@bp.route('/pay_invoices', methods=['POST'])
def pay_all_invoices():
    logging.info("Received request at /pay_invoices")
    query_number = str(uuid.uuid4())
    query_table = 'pay_invoices'

    session = get_session()
    try:
        data = request.get_json()
        if not data:
            raise ValueError("Invalid JSON data.")

        customer_id = data.get('customer_id')
        total_amount = data.get('total_amount')
        payment_date = data.get('date')
        source = data.get('source')
        guid = data.get('guid')  # New field for GUID

        if not customer_id:
            raise ValueError("Customer ID is required.")
        if total_amount is None:
            raise ValueError("Total amount is required.")
        if not payment_date:
            raise ValueError("Date is required.")
        if not source:
            raise ValueError("Source is required.")
        if not guid:
            raise ValueError("GUID is required.")

        customer_id = customer_id.strip()
        total_amount = float(total_amount)
        payment_date = payment_date.strip()
        source = source.strip().lower()
        guid = guid.strip()

        # Audit the request
        audit_logger = logging.getLogger('audit')
        audit_request(audit_logger, '/pay_invoices', data, source)

        # Validate source
        if source not in ['demo', 'esadad']:
            raise ValueError("Invalid source. Accepted values are 'demo' or 'esadad'.")

        # Check if GUID already used to prevent duplicate payments
        if check_guid_exists(session, guid):
            message = "Duplicate payment attempt detected."
            code = '409'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table,
                status_of_query, status_str, query_status
            )
            logging.error(message)
            return jsonify(response_data), 409

        # Insert a record for this GUID
        insert_guid_record(session, guid, customer_id, total_amount, source)

        odoo_client = get_odoo_client()

        # Search for partners by customer id
        try:
            partners = odoo_client.get_partners_by_mobile(customer_id)
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
            logging.error(f"Pay invoices failed: {message}")
            return jsonify(response_data), 408
        elif len(partners) > 1:
            partner_names = ', '.join(partner['name'] for partner in partners)
            message = f"Multiple customers found for customer id {customer_id}: {partner_names}."
            code = '400'
            status_of_query = False
            status_str = 'failed'
            query_status = 0
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
            logging.error(f"Pay invoices failed: {message}")
            return jsonify(response_data), 400
        else:
            # Fetch unpaid invoices
            try:
                invoices = odoo_client.get_unpaid_invoices_by_mobile(customer_id)
            except Exception as e:
                logging.error(f"Odoo connection error: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            if not invoices:
                total_unpaid_amount = 0.0
                message = f"No unpaid invoices found for customer id {customer_id}."
                code = '303'
                status_of_query = False
                status_str = 'failed'
                query_status = 0
                response_data = create_json_response(
                    message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
                response_data['total_amount'] = total_unpaid_amount
                logging.error(f"Pay invoices failed: {message}")
                return jsonify(response_data), 303

            # Log invoice states before payment
            log_invoices_state(session, guid, 'before', invoices)

            # Proceed to register payments with the given total_amount and GUID
            try:
                payment_results = odoo_client.register_payment_for_invoices(invoices, payment_date, total_amount, guid=guid)
            except Exception as e:
                logging.error(f"Odoo connection error during payment registration: {e}", exc_info=True)
                return jsonify({'message': 'Service temporarily unavailable. Please try again later.'}), 503

            # Re-fetch invoices to log their state after payment
            try:
                updated_invoices = odoo_client.get_unpaid_invoices_by_mobile(customer_id)
            except Exception as e:
                logging.error(f"Odoo connection error on re-fetch: {e}", exc_info=True)
                updated_invoices = []  # If unable to fetch, leave empty

            # Log invoice states after payment
            log_invoices_state(session, guid, 'after', updated_invoices)

            # Log the final payment results for each invoice into the database
            log_payment_results(session, guid, payment_results)

            # Prepare invoice list for response
   

            payments_info = '; '.join(
                [f"Invoice ID {p['invoice_id']}: {p['status']}" for p in payment_results])
            message = f"Payment process completed. Details: {payments_info}."
            code = '200'
            status_of_query = True
            status_str = 'successful'
            query_status = 1
            response_data = create_json_response(
                message, code, datetime.now(), query_number, query_table, status_of_query, status_str, query_status)
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
            error_message, code, datetime.now(), query_number, query_table,
            status_of_query, status_str, query_status
        )
        return jsonify(response_data), 500
    finally:
        session.close()

# OdooAPI/odoo_client.py

import xmlrpc.client
import ssl
import logging
import time

class OdooClient:
    def __init__(self, url, db, username, password, ssl_verify=False):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.ssl_verify = ssl_verify
        self.uid = None

        if not ssl_verify:
            context = ssl._create_unverified_context()
            self.transport = xmlrpc.client.SafeTransport(context=context)
        else:
            self.transport = None  # Use default SSL context

        self.common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common', transport=self.transport)
        self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object', transport=self.transport)
        self.authenticate()

    def authenticate(self):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                uid = self.common.authenticate(self.db, self.username, self.password, {})
                if not uid:
                    logging.error("Authentication failed")
                    self.uid = None
                    return
                self.uid = uid
                return
            except Exception as e:
                logging.error(f"Odoo authentication failed on attempt {attempt+1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    self.uid = None
                    return

    def execute_kw(self, model, method, args, kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.uid is None:
                    self.authenticate()
                    if self.uid is None:
                        raise Exception("Unable to authenticate with Odoo.")
                return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)
            except Exception as e:
                logging.error(f"Odoo execution failed on attempt {attempt+1}/{max_retries} for {model}.{method}: {e}")
                self.uid = None
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    raise

    # Odoo interaction methods

    def get_bank_journal_id(self):
        bank_journal = self.execute_kw(
            'account.journal', 'search_read',
            [[['name', '=', 'Bank']]],
            {'fields': ['id', 'name']}
        )
        if bank_journal:
            return bank_journal[0]['id']
        else:
            return None

    def get_partners_by_mobile(self, mobile_number):
        partners = self.execute_kw(
            'res.partner', 'search_read',
            [[['mobile', '=', mobile_number]]],
            {'fields': ['id', 'name']}
        )
        return partners

    def get_unpaid_invoices_by_mobile(self, mobile_number):
        partners = self.get_partners_by_mobile(mobile_number)
        if not partners or len(partners) != 1:
            return None
        partner_id = partners[0]['id']
        invoices = self.execute_kw(
            'account.move', 'search_read',
            [[
                ['partner_id', '=', partner_id],
                ['state', '=', 'posted'],
                ['move_type', '=', 'out_invoice'],
                ['amount_residual', '>', 0]
            ]],
            {'fields': ['id', 'amount_residual', 'currency_id', 'partner_id']}
        )
        if not invoices:
            return None
        return invoices

    def register_payment_for_invoices(self, invoices, payment_date):
        payments_made = []
        bank_journal_id = self.get_bank_journal_id()
        if not bank_journal_id:
            return [{"message": "Bank journal not found."}]

        for invoice in invoices:
            try:
                invoice_id = invoice['id']
                # Fetch the invoice details
                invoice_record = self.execute_kw(
                    'account.move', 'read',
                    [invoice_id],
                    {'fields': ['amount_residual', 'state', 'partner_id']}
                )
                if not invoice_record or invoice_record[0]['state'] != 'posted':
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'status': 'Invoice not posted or not found.'
                    })
                    continue
                if invoice_record[0]['amount_residual'] <= 0:
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'status': 'Invoice already paid or no balance remaining.'
                    })
                    continue

                # Step 1: Call 'action_register_payment' on the invoice
                action = self.execute_kw(
                    'account.move', 'action_register_payment',
                    [[invoice_id]],
                    {}
                )

                # Get the context from the action
                context = action.get('context', {})
                context.update(
                    {'active_ids': [invoice_id], 'active_model': 'account.move', 'active_id': invoice_id})

                # Step 2: Create the payment register wizard with the context
                payment_register_id = self.execute_kw(
                    'account.payment.register', 'create',
                    [{
                        'journal_id': bank_journal_id,
                        'payment_date': payment_date,
                        'amount': invoice_record[0]['amount_residual'],
                    }],
                    {'context': context}
                )

                # Step 3: Read 'available_payment_method_line_ids' from the wizard
                payment_register = self.execute_kw(
                    'account.payment.register', 'read',
                    [payment_register_id],
                    {'fields': ['available_payment_method_line_ids'], 'context': context}
                )
                available_payment_method_line_ids = payment_register[0]['available_payment_method_line_ids']

                if not available_payment_method_line_ids:
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'status': 'No available payment methods.'
                    })
                    continue

                # Step 4: Select a payment method line
                payment_method_line_id = available_payment_method_line_ids[0]  # Select the first available method

                # Step 5: Write the 'payment_method_line_id' back to the wizard
                self.execute_kw(
                    'account.payment.register', 'write',
                    [[payment_register_id], {
                        'payment_method_line_id': payment_method_line_id
                    }],
                    {'context': context}
                )

                # Step 6: Call 'action_create_payments' on the wizard to create the payment
                self.execute_kw(
                    'account.payment.register', 'action_create_payments',
                    [[payment_register_id]],
                    {'context': context}
                )

                payments_made.append({
                    'invoice_id': invoice_id,
                    'payment_register_id': payment_register_id,
                    'status': 'Payment Completed'
                })

            except Exception as e:
                logging.error(f"Payment registration failed for invoice {invoice_id}: {e}", exc_info=True)
                payments_made.append({
                    'invoice_id': invoice_id,
                    'status': f'Payment Registration Failed: {str(e)}'
                })

        return payments_made

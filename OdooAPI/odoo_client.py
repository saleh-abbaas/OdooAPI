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
            [[['name', '=', 'Arab Islamic bank-ILS']]],
            {'fields': ['id', 'name']}
        )
        if bank_journal:
            return bank_journal[0]['id']
        else:
            return None

    def get_partners_by_mobile(self, mobile_number):
        partners = self.execute_kw(
            'res.partner', 'search_read',
            [[['vat', '=', mobile_number]]],
            {'fields': ['id', 'name','vat']}
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
            {'fields': ['id', 'amount_residual', 'currency_id', 'partner_id', 'invoice_date', 'amount_total', 'state']}
        )
        if not invoices:
            return None
        return invoices

    def register_payment_for_invoices(self, invoices, payment_date, total_amount, guid=None):
        payments_made = []
        bank_journal_id = self.get_bank_journal_id()

        if not bank_journal_id:
            logging.error("Bank journal not found.")
            return [{"message": "Bank journal not found."}]

        invoices_sorted = sorted(invoices, key=lambda x: x.get('invoice_date', ''))

        for invoice in invoices_sorted:
            try:
                if 'id' not in invoice or 'amount_total' not in invoice or 'amount_residual' not in invoice:
                    payments_made.append({
                        'invoice_id': invoice.get('id', 'Unknown'),
                        'invoice_total_amount': invoice.get('amount_total', 0.0),
                        'amount_paid': 0.0,
                        'amount_remaining': invoice.get('amount_residual', 0.0),
                        'status': 'Invalid invoice structure.'
                    })
                    continue

                invoice_id = invoice['id']
                invoice_amount_total = invoice['amount_total']
                invoice_amount_residual = invoice['amount_residual']
                if total_amount <= 0:
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'invoice_total_amount': invoice_amount_total,
                        'amount_paid': 0.0,
                        'amount_remaining': invoice_amount_residual,
                        'status': 'Payment not applied: Insufficient funds.'
                    })
                    continue

                amount_to_pay = min(invoice_amount_residual, total_amount)
                if amount_to_pay <= 0:
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'invoice_total_amount': invoice_amount_total,
                        'amount_paid': 0.0,
                        'amount_remaining': invoice_amount_residual,
                        'status': 'Invoice already paid or no balance remaining.'
                    })
                    continue

                # Step 1: Call 'action_register_payment' on the invoice
                action = self.execute_kw(
                    'account.move', 'action_register_payment',
                    [[invoice_id]],
                    {}
                )
                context = action.get('context', {})
                context.update({'active_ids': [invoice_id], 'active_model': 'account.move', 'active_id': invoice_id})

                # Step 2: Create the payment register wizard with GUID in 'communication'
                payment_register_id = self.execute_kw(
                    'account.payment.register', 'create',
                    [{
                        'journal_id': bank_journal_id,
                        'payment_date': payment_date,
                        'amount': amount_to_pay,
                        'communication': f"GUID={guid}" if guid else ''
                    }],
                    {'context': context}
                )

                # Step 3: Read 'available_payment_method_line_ids' from the wizard
                payment_register = self.execute_kw(
                    'account.payment.register', 'read',
                    [payment_register_id],
                    {'fields': ['available_payment_method_line_ids'], 'context': context}
                )
                available_payment_method_line_ids = payment_register[0].get('available_payment_method_line_ids', [])

                if not available_payment_method_line_ids:
                    payments_made.append({
                        'invoice_id': invoice_id,
                        'invoice_total_amount': invoice_amount_total,
                        'amount_paid': 0.0,
                        'amount_remaining': invoice_amount_residual,
                        'status': 'No available payment methods.'
                    })
                    continue

                payment_method_line_id = available_payment_method_line_ids[0]

                # Step 5: Write the 'payment_method_line_id' and 'amount' back to the wizard
                self.execute_kw(
                    'account.payment.register', 'write',
                    [[payment_register_id], {
                        'payment_method_line_id': payment_method_line_id,
                        'amount': amount_to_pay,
                    }],
                    {'context': context}
                )

                # Step 6: Call 'action_create_payments' on the wizard to create the payment
                self.execute_kw(
                    'account.payment.register', 'action_create_payments',
                    [[payment_register_id]],
                    {'context': context}
                )

                total_amount -= amount_to_pay

                # Fetch updated invoice residual amount
                invoice_updated = self.execute_kw(
                    'account.move', 'read',
                    [invoice_id],
                    {'fields': ['amount_residual'], 'context': context}
                )
                amount_remaining = invoice_updated[0].get('amount_residual', 0.0)

                payments_made.append({
                    'invoice_id': invoice_id,
                    'invoice_total_amount': invoice_amount_total,
                    'amount_paid': amount_to_pay,
                    'amount_remaining': amount_remaining,
                    'status': 'Payment Completed'
                })

            except Exception as e:
                logging.error(f"Payment registration failed for invoice {invoice.get('id', 'Unknown')}: {e}", exc_info=True)
                payments_made.append({
                    'invoice_id': invoice.get('id', 'Unknown'),
                    'invoice_total_amount': invoice.get('amount_total', 0.0),
                    'amount_paid': 0.0,
                    'amount_remaining': invoice.get('amount_residual', 0.0),
                    'status': f'Payment Registration Failed: {str(e)}'
                })

        return payments_made

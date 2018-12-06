# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp.tools.translate import _
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp


class customer_situation(models.TransientModel):

    _name = "customer.situation"
    _description = "Customer Situation"

    start_date = fields.Date('Date Debut')
    end_date = fields.Date('Date Fin')

    def _get_invoices_voucher(self, voucher_ids, invoice_id):
        invoices = []
        for voucher in voucher_ids:
            for line in voucher.line_cr_ids:
                if line.move_line_id.invoice.id == invoice_id:
                    invoices.append(line)
        return invoices

    def _get_total_vouchers_encaissed(self, payment_ids):
        payment_ids = sorted(payment_ids._ids)
        total = 0
        payments = self.env['account.move.line'].browse(payment_ids)
        for payment in payments:
            if payment.move_id.voucher_id.state == 'encaissed':
                total += payment.credit
        return total

    def _get_vouchers_transferred_to_bank(self, payment_ids):
        payment_ids = sorted(payment_ids._ids)
        vouchers = []
        payments = self.env['account.move.line'].browse(payment_ids)
        now = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
        for payment in payments:
            if payment.move_id.voucher_id.state == 'bank_transfert':
                vouchers.append(payment)
        return vouchers

    def _get_vouchers_not_overdue(self, payment_ids):
        payment_ids = sorted(payment_ids._ids)
        vouchers = []
        payments = self.env['account.move.line'].browse(payment_ids)
        now = datetime.strptime(datetime.now().strftime("%d/%m/%Y"), "%d/%m/%Y")
        for payment in payments:
            if payment.move_id.voucher_id.deadline_date:
                deadline_date = datetime.strptime(payment.move_id.voucher_id.deadline_date, "%Y-%m-%d")
                if payment.move_id.voucher_id.state == 'posted' and deadline_date >= now:
                    vouchers.append(payment)
        return vouchers

    def _print_customer_situation(self):
        partner_ids = self._context.get('active_ids', False)
        tab_situation = []
        for partner in self.env['res.partner'].browse(partner_ids) :
            invoices = self.env['account.invoice'].search([('type','=','out_invoice'),('partner_id','=',partner.id),('date_invoice','>=',self.start_date),('date_invoice','<=',self.end_date),('state','in',('open','paid'))])
            for invoice in invoices:
                if invoice.state == 'open':
                    if invoice.payment_ids and not partner.unpaid_aml_ids:
                        vouchers_transferred_to_bank = self._get_vouchers_transferred_to_bank(invoice.payment_ids)
                        vouchers_not_overdue = _get_vouchers_not_overdue(invoice.payment_ids)
                        total_vouchers_encaissed = self._get_total_vouchers_encaissed(invoice.payment_ids)
                        if vouchers_transferred_to_bank:
                            for payment in vouchers_transferred_to_bank:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement remis en banque'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
                        if vouchers_not_overdue:
                            for payment in vouchers_not_overdue:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement non échue'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
                    elif not invoice.payment_ids and partner.unpaid_aml_ids:
                        invoices_unpaid = self._get_invoices_voucher(partner.voucher_ids, invoice.id)
                        if invoices_unpaid:
                            for aml in invoices_unpaid:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': aml.voucher_id.number,
                                    'amount_voucher': -aml.move_line_id.debit,
                                    'amount_to_paid': invoice.amount_total,
                                    'description': 'Paiement impayé'
                                }
                                tab_situation.append(record)
                    elif invoice.payment_ids and partner.unpaid_aml_ids:
                        vouchers_transferred_to_bank = self._get_vouchers_transferred_to_bank(invoice.payment_ids)
                        vouchers_not_overdue = _get_vouchers_not_overdue(invoice.payment_ids)
                        invoices_unpaid = self._get_invoices_voucher(partner.voucher_ids, invoice.id)
                        total_vouchers_encaissed = self._get_total_vouchers_encaissed(invoice.payment_ids)
                        if vouchers_transferred_to_bank:
                            for payment in vouchers_transferred_to_bank:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement remis en banque'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
                        if vouchers_not_overdue:
                            for payment in vouchers_not_overdue:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement non échue'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
                        if invoices_unpaid:
                            for aml in invoices_unpaid:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': aml.voucher_id.number,
                                    'amount_voucher': -aml.move_line_id.debit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed,
                                    'description': 'Paiement impayé'
                                }
                                tab_situation.append(record)
                    else:
                        record = {
                            'customer': partner.name,
                            'invoice': invoice.number,
                            'amount_invoice': invoice.amount_total,
                            'reglement': '-',
                            'amount_voucher': '-',
                            'amount_to_paid': invoice.amount_total
                        }

                        tab_situation.append(record)
                else:
                    if invoice.payment_ids:
                        vouchers_transferred_to_bank = self._get_vouchers_transferred_to_bank(invoice.payment_ids)
                        vouchers_not_overdue = self._get_vouchers_not_overdue(invoice.payment_ids)
                        total_vouchers_encaissed = self._get_total_vouchers_encaissed(invoice.payment_ids)
                        if vouchers_transferred_to_bank:
                            for payment in vouchers_transferred_to_bank:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement remis en banque'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
                        if vouchers_not_overdue:
                            for payment in vouchers_not_overdue:
                                record = {
                                    'customer': partner.name,
                                    'invoice': invoice.number,
                                    'amount_invoice': invoice.amount_total,
                                    'reglement': payment.move_id.voucher_id.number,
                                    'amount_voucher': payment.credit,
                                    'amount_to_paid': invoice.amount_total - total_vouchers_encaissed - payment.credit,
                                    'description': 'Paiement non échue'
                                }
                                tab_situation.append(record)
                                total_vouchers_encaissed += payment.credit
        return tab_situation

    @api.multi
    def print_report(self):
        situation = self._print_customer_situation()
        data = {}
        data['model'] = 'customer.situation'
        data['user'] = self.env.user.name
        data['lang'] = self.env.user.lang
        data['form'] = {}
        data['form']['start_date'] = self.start_date
        data['form']['end_date'] = self.end_date
        data['form']['situation'] = situation
        return self.env['report'].get_action(self, 'account_invoice_payment.customer_situation', data=data)

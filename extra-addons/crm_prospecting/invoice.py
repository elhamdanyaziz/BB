# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import itertools
from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from dateutil.relativedelta import relativedelta
from datetime import datetime

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('with_deposit','with_guaranty','deposit_number', 'guaranty_number','invoice_line.price_subtotal','tax_line.amount')
    def _compute_amount(self):

        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line)
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax
        self.amount_iat = self.amount_total
        self.deposit_number_prc = str(self.deposit_number*100)+'%'
        self.guaranty_number_prc = str(self.guaranty_number*100)+'%'
        self.discount_prc = str(self.discount_number*100)+'%'

        if self.with_discount :
            self.discount_amount_untaxed = self.amount_untaxed
            self.amount_untaxed = self.amount_untaxed-self.amount_untaxed*self.discount_number
            #self.amount_tax = self.amount_tax-self.amount_tax*self.discount_number
            self.discount_amount = self.discount_amount_untaxed * self.discount_number
            #self.amount_total = self.amount_total-self.discount_amount
            self.amount_total = self.amount_untaxed + self.amount_tax
            self.amount_iat = self.amount_total
        else :
            self.discount_amount_untaxed = 0
            self.discount_amount = 0

        if self.inv_species :
            self.timbre_amount = self.amount_total*0.0025
            self.amount_total = self.amount_total+self.timbre_amount
        else :
            self.timbre_amount = 0
            self.amount_total = self.amount_total

        if self.with_guaranty:
            self.amount_guaranty = self.amount_total * self.guaranty_number
        else:
            self.amount_guaranty = 0
        if self.with_deposit:
            self.amount_deposit = self.amount_total * self.deposit_number
        else:
            self.amount_deposit = 0
        self.amount_total = self.amount_total - (self.amount_guaranty + self.amount_deposit)

    @api.multi
    def _get_period(self):
        currentMonth = datetime.now().month
        currentYear = datetime.now().year
        if 1 <= currentMonth <=9 :
            period_code = '0'+str(currentMonth)+'/'+str(currentYear)
        else :
            period_code = str(currentMonth)+'/'+str(currentYear)
        period = self.env['account.period'].search([('code','=',period_code)])
        return period.id or False

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line.price_subtotal',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        # Fixes the fact that move_id.line_id.amount_residual, being not stored and old API, doesn't trigger recomputation
        'move_id.line_id.reconcile_id',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
        'timbre_amount','amount_guaranty'
    )
    # An invoice's residual amount is the sum of its unreconciled move lines and,
    # for partially reconciled move lines, their residual amount divided by the
    # number of times this reconciliation is used in an invoice (so we split
    # the residual amount between all invoice)
    def _compute_residual(self):
        self.residual = 0.0
        # Each partial reconciliation is considered only once for each invoice it appears into,
        # and its residual amount is divided by this number of invoices
        partial_reconciliations_done = []
        for line in self.sudo().move_id.line_id:
            if line.account_id.type not in ('receivable', 'payable'):
                continue
            if line.reconcile_partial_id and line.reconcile_partial_id.id in partial_reconciliations_done:
                continue
            # Get the correct line residual amount
            if line.currency_id == self.currency_id:
                line_amount = line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                from_currency = line.company_id.currency_id.with_context(date=line.date)
                line_amount = from_currency.compute(line.amount_residual, self.currency_id)

            # For partially reconciled lines, split the residual amount
            if line.reconcile_partial_id:
                partial_reconciliation_invoices = set()
                for pline in line.reconcile_partial_id.line_partial_ids:
                    if pline.invoice and self.type == pline.invoice.type:
                        partial_reconciliation_invoices.update([pline.invoice.id])
                line_amount = self.currency_id.round(line_amount / len(partial_reconciliation_invoices))

                partial_reconciliations_done.append(line.reconcile_partial_id.id)
            self.residual += line_amount
            if self.state != 'paid':
                self.residual = self.residual + self.timbre_amount - self.amount_guaranty
            else :
                self.residual = self.residual
        self.residual = max(self.residual, 0.0)


    period_id = fields.Many2one('account.period', string='Force Period',domain=[('state', '!=', 'done')],default=_get_period, copy=False,help="Keep empty to use the period of the validation(invoice) date.",readonly=True, states={'draft': [('readonly', False)]})
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    order_id = fields.Many2one('sale.order', 'Bon de commande')
    with_deposit = fields.Boolean('Avec Acompte ?', default=False)
    with_discount = fields.Boolean('Avec Remise ?', default=False)
    deposit_number = fields.Float('Restitution d\'acompte',default=0)
    inv_guaranty = fields.Boolean('Facture de Garantie ?', default=False)
    inv_species = fields.Boolean('Paiement Espéce ?', default=False)
    with_guaranty = fields.Boolean('Avec Garantie ?', default=False)
    guaranty_number = fields.Float('Retenue de garantie',default=0)
    discount_number = fields.Float('Pourcentage de la Remise', default=0)
    is_deposit_inv = fields.Boolean('Acompte', default=False)
    amount_guaranty = fields.Float(string='Retenue de Garantie', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_deposit = fields.Float(string='Restitution d\'Accompte', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    timbre_amount = fields.Float(string='Timbre', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    discount_amount = fields.Float(string='Remise', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    discount_amount_untaxed = fields.Float(string='Total HT', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_iat = fields.Float(string='Montant TTC', digits=dp.get_precision('Account'),store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    deposit_number_prc = fields.Char('Pourcentage de l\'Acompte',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    guaranty_number_prc = fields.Char('Pourcentage de la Garantie',store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    discount_prc = fields.Char('Pourcentage de la Remise',store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.multi
    def button_reset_taxes(self):
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()
            partner = invoice.partner_id
            if partner.lang:
                ctx['lang'] = partner.lang
            for taxe in account_invoice_tax.compute(invoice.with_context(ctx)).values():
                if invoice.with_discount :
                    taxe['base_amount'] = invoice.amount_untaxed
                    taxe['base'] = invoice.amount_untaxed
                    taxe['amount'] = invoice.amount_untaxed*0.2
                    taxe['tax_amount'] = invoice.amount_untaxed * 0.2
                account_invoice_tax.create(taxe)
        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line': []})

    @api.multi
    def check_tax_lines(self, compute_taxes):
        account_invoice_tax = self.env['account.invoice.tax']
        company_currency = self.company_id.currency_id
        if not self.tax_line:
            for tax in compute_taxes.values():
                account_invoice_tax.create(tax)
        else:
            tax_key = []
            precision = self.env['decimal.precision'].precision_get('Account')
            for tax in self.tax_line:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                tax_key.append(key)
                if key not in compute_taxes:
                    raise except_orm(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if self.with_discount:
                    base = self.amount_untaxed
                if float_compare(abs(base - tax.base), company_currency.rounding, precision_digits=precision) == 1:
                    raise except_orm(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise except_orm(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))


    @api.multi
    def action_number(self):
        # TODO: not correct fix but required a fresh values before reading it.
        for inv in self:
            inv.write({'internal_number': inv.number})

            if inv.type in ('in_invoice', 'in_refund'):
                if not inv.reference:
                    ref = inv.number
                else:
                    ref = inv.reference
            else:
                ref = inv.number
            if inv.opp_id :
                self._cr.execute(""" UPDATE account_move SET ref=%s,opp_id=%s,order_id=%s
                               WHERE id=%s AND (ref IS NULL OR ref = '')""",
                                 (ref, inv.move_id.id,inv.opp_id.id,inv.order_id.id))
            self._cr.execute(""" UPDATE account_move_line SET ref=%s
                           WHERE move_id=%s AND (ref IS NULL OR ref = '')""",
                             (ref, inv.move_id.id))
            if inv.inv_guaranty:
                self._cr.execute(""" UPDATE account_move_line SET name=%s
                               WHERE move_id=%s""",
                                 (inv.partner_id.name+' '+inv.number+' '+'reprise Retenue Garantie', inv.move_id.id))
            self._cr.execute(""" UPDATE account_analytic_line SET ref=%s
                           FROM account_move_line
                           WHERE account_move_line.move_id = %s AND
                                 account_analytic_line.move_id = account_move_line.id""",
                             (ref, inv.move_id.id))
            if inv.type == 'out_invoice':
                SIGN = {'out_invoice': -1, 'in_invoice': 1, 'out_refund': 1, 'in_refund': -1}
                direction = SIGN[self.type]
                date = self._context.get('date_p') or fields.Date.context_today(self)
                if self._context.get('amount_currency') and self._context.get('currency_id'):
                    amount_currency = self._context['amount_currency']
                    currency_id = self._context['currency_id']
                else:
                    amount_currency = False
                    currency_id = False

                self._cr.execute(""" UPDATE account_move_line SET name=%s
                               WHERE move_id=%s and description_updated_ok=%s""",
                                 (inv.partner_id.name + ' ' + inv.number, inv.move_id.id, False))


                    # if inv.currency_id:
                #     self._cr.execute(""" UPDATE account_move_line SET currency_id=%s
                #                    WHERE move_id=%s""",
                #                      (inv.currency_id.id, inv.move_id.id))

            self.invalidate_cache()
        return True

    @api.model
    def line_get_convert(self, line, part, date):
        return {
            'date_maturity': line.get('date_maturity', False),
            'partner_id': part,
            'name': line['name'][:64],
            'date': date,
            'debit': line['price']>0 and line['price'],
            'credit': line['price']<0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price']>0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'tax_code_id': line.get('tax_code_id', False),
            'tax_amount': line.get('tax_amount', False),
            'ref': line.get('ref', False),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
            'description_updated_ok': True if 'description_updated_ok' in line.keys() else False,
            'guaranty_ok':True if 'guaranty_ok' in line.keys() else False
        }

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            company_currency = inv.company_id.currency_id
            if not inv.date_invoice:
                # FORWARD-PORT UP TO SAAS-6
                if inv.currency_id != company_currency and inv.tax_line:
                    raise except_orm(
                        _('Warning!'),
                        _('No invoice date!'
                            '\nThe invoice currency is not the same than the company currency.'
                            ' An invoice date is required to determine the exchange rate to apply. Do not forget to update the taxes!'
                        )
                    )
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv.with_context(lang=inv.partner_id.lang))
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            if self.env.user.has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # Force recomputation of tax_amount, since the rate potentially changed between creation
            # and validation of the invoice
            inv._recompute_tax_amount()
            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number
            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)
            if inv.with_discount and inv.type == 'out_invoice' and not inv.with_deposit :
                total = inv.amount_total-inv.timbre_amount
            if inv.with_deposit and inv.type == 'out_invoice' :
                #total = total - total*inv.deposit_number
                total = inv.amount_total
                current_year = datetime.today().year
                if 1 <= inv.journal_id.sequence_id.number_next_actual <= 9 :
                    sequence = '000'+str(inv.journal_id.sequence_id.number_next_actual)
                elif 10 <= inv.journal_id.sequence_id.number_next_actual <= 99:
                    sequence = '00'+str(inv.journal_id.sequence_id.number_next_actual)
                elif 100 <= inv.journal_id.sequence_id.number_next_actual <= 999:
                    sequence = '0'+str(inv.journal_id.sequence_id.number_next_actual)
                else :
                    sequence = str(inv.journal_id.sequence_id.number_next_actual)
                account_acompte = self.env['account.account'].search([('code', '=', 4421000000)])
                iml.append({
                    'type': 'dest',
                    'name': inv.partner_id.name+' '+inv.journal_id.code+'/'+str(current_year)+'/'+sequence,
                    'price': inv.amount_deposit,
                    'account_id': account_acompte.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref,
                    'description_updated_ok':True
                })
            if inv.with_guaranty and inv.type == 'out_invoice':
                total = inv.amount_total+inv.amount_guaranty
                current_year = datetime.today().year
                if 1 <= inv.journal_id.sequence_id.number_next_actual <= 9 :
                    sequence = '000'+str(inv.journal_id.sequence_id.number_next_actual)
                elif 10 <= inv.journal_id.sequence_id.number_next_actual <= 99:
                    sequence = '00'+str(inv.journal_id.sequence_id.number_next_actual)
                elif 100 <= inv.journal_id.sequence_id.number_next_actual <= 999:
                    sequence = '0'+str(inv.journal_id.sequence_id.number_next_actual)
                else :
                    sequence = str(inv.journal_id.sequence_id.number_next_actual)
                month = inv.period_id.name[:2]
                account_code = '3423'+month+'0000'
                account_guaranty = self.env['account.account'].search([('code', '=', account_code)])
                iml.append({
                    'type': 'dest',
                    'name': inv.partner_id.name+' '+inv.journal_id.code+'/'+str(current_year)+'/'+sequence+' Retenue Garantie',
                    'price': inv.amount_guaranty,
                    'account_id': account_guaranty.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref,
                    'description_updated_ok': True
                })
                iml.append({
                    'type': 'dest',
                    'name': inv.partner_id.name+' '+inv.journal_id.code+'/'+str(current_year)+'/'+sequence+' Retenue Garantie',
                    'price': -inv.amount_guaranty,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref,
                    'description_updated_ok': True,
                    'guaranty_ok':True
                })

            # if inv.inv_species and inv.type == 'out_invoice':
            #     current_year = datetime.today().year
            #     if 1 <= inv.journal_id.sequence_id.number_next_actual <= 9 :
            #         sequence = '000'+str(inv.journal_id.sequence_id.number_next_actual)
            #     elif 10 <= inv.journal_id.sequence_id.number_next_actual <= 99:
            #         sequence = '00'+str(inv.journal_id.sequence_id.number_next_actual)
            #     elif 100 <= inv.journal_id.sequence_id.number_next_actual <= 999:
            #         sequence = '0'+str(inv.journal_id.sequence_id.number_next_actual)
            #     else :
            #         sequence = str(inv.journal_id.sequence_id.number_next_actual)
            #     account_timbre = self.env['account.account'].search([('code', '=', 5161000000)])
            #     iml.append({
            #         'type': 'dest',
            #         'name': 'timbre'+'/'+inv.journal_id.code+'/'+str(current_year)+'/'+sequence,
            #         'price': inv.timbre_amount,
            #         'account_id': account_timbre.id,
            #         'date_maturity': inv.date_due,
            #         'amount_currency': diff_currency and total_currency,
            #         'currency_id': diff_currency and inv.currency_id.id,
            #         'ref': ref,
            #         'description_updated_ok': True
            #     })
            #     account_payable = self.env['account.account'].search([('code', '=', 4458000000)])
            #
            #     iml.append({
            #         'type': 'dest',
            #         'name': 'etat autres comptes crediteurs',
            #         'price': -inv.timbre_amount,
            #         'account_id': account_payable.id,
            #         'date_maturity': inv.date_due,
            #         'amount_currency': diff_currency and total_currency,
            #         'currency_id': diff_currency and inv.currency_id.id,
            #         'ref': ref,
            #         'description_updated_ok': True,
            #     })
            name = inv.supplier_invoice_number or inv.name or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref,
                })
            date = date_invoice
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            if inv.type == 'in_invoice' :
                if inv.type_service != 'service' :
                    line = inv.group_lines(iml, line)
            else :
                line = inv.group_lines(iml, line)
            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)
            if inv.with_discount and inv.type == 'out_invoice':
                for l in line :
                    if l[2]['product_id'] :
                        l[2]['credit'] = (l[2]['credit']-l[2]['credit']*inv.discount_number)
            move_vals = {
                'ref': inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            ############################Lettrage Partiel dans le cas garantie######################################
            if inv.with_guaranty and inv.type == 'out_invoice':
                move_lines = self.env['account.move.line'].search([('account_id','=',inv.account_id.id),('move_id','=',move.id)])
                reconcile = self.pool.get('account.move.line').reconcile_partial(self._cr, self._uid,move_lines._ids,writeoff_acc_id=False,writeoff_period_id=inv.period_id.id,writeoff_journal_id=inv.journal_id.id)
            #######################################################################################################
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        if invoice_line.get('product_id', 'False') and invoice_line['account_id'] :
            return "%s" % (invoice_line['account_id'],)
        elif invoice_line.get('guaranty_ok', 'False') :
            return "%s-%s" % (
                invoice_line['account_id'],
                invoice_line.get('guaranty_ok', 'False'),
            )
        else :
            return "%s-%s-%s-%s-%s" % (
                invoice_line['account_id'],
                invoice_line.get('tax_code_id', 'False'),
                invoice_line.get('product_id', 'False'),
                invoice_line.get('analytic_account_id', 'False'),
                invoice_line.get('date_maturity', 'False'),
            )


class account_move(models.Model):
    _inherit = 'account.move'

    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    order_id = fields.Many2one('sale.order', 'Bon de commande')

class account_move_line(models.Model):

    _inherit = 'account.move.line'

    description_updated_ok = fields.Boolean('À Mettre à jour la description',default=False)
    guaranty_ok = fields.Boolean('Ligne de garantie', default=False)

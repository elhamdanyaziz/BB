# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp import models, fields, api, _
import time
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import workflow
from openerp.tools import float_compare


class account_voucher(models.Model):

    _inherit = "account.voucher"

    deadline_date = fields.Date(string='Date d\'échéance')
    transfert_date = fields.Date(string='Date de remise')
    state = fields.Selection(
            [('draft','Draft'),
             ('cancel','Cancelled'),
             ('proforma','Pro-forma'),
             ('posted','Validé'),
             ('bank_transfert', 'remis en banque'),
             ('unpaid', 'impayé'),
             ('encaissed','Encaissé')
            ], 'Statut', readonly=True, track_visibility='onchange', copy=False)
    bank_id = fields.Many2one('account.journal', string='Banque', required=False)
    voucher_action = fields.Selection([('noprocessed', 'Non Traité'), ('processed', 'Traité')], 'Type Action',default='noprocessed')
    unpaid_ids = fields.Many2many('account.voucher','voucher_unpaid_rel','voucher_id','unpaid_id',string='Imapyés')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=True,states={'draft': [('readonly', False)]},default=120)

    @api.model
    def create(self,vals):
        print "vals create",vals
        res = super(account_voucher,self).create(vals)
        return res

    @api.multi
    def write(self,vals):
        print "vals write",vals
        res = super(account_voucher,self).write(vals)
        return res

    @api.multi
    def proforma_voucher(self):
        voucher = self
        reconcile = False
        if voucher.journal_id.is_species :
            rec_ids = []
            seq_obj = self.env['ir.sequence']
            if voucher.number:
                name = voucher.number
            elif voucher.journal_id.sequence_id:
                name = seq_obj.next_by_id(voucher.journal_id.sequence_id.id)
            account_move = {
                'name':name,
                'journal_id':voucher.journal_id.id,
                'ref':voucher.number,
                'period_id':voucher.period_id.id,
                'narration': voucher.narration,
                'date': voucher.date,
                'voucher_id':voucher.id,
            }
            account_move = self.env['account.move'].create(account_move)
            for line in voucher.line_ids :
                rec_ids.append(line.move_line_id.id)
                if line.reconcile :
                    reconcile = True
                move_line_cach_vals = {
                    'name': 'encais especes /'+line.move_line_id.invoice.number,
                    'quantity': 1,
                    'debit': line.move_line_id.invoice.amount_total-line.move_line_id.invoice.timbre_amount,
                    'credit': 0,
                    'account_id': voucher.journal_id.default_debit_account_id.id,
                    'partner_id': voucher.partner_id.id,
                    'ref': line.move_line_id.invoice.number,
                    'currency_id': line.move_line_id.currency_id.id,
                    'company_id': line.move_line_id.invoice.company_id.id,
                    'move_id': account_move.id,
                    'period_id': voucher.period_id.id,
                    'journal_id': voucher.journal_id.id,
                    'date': voucher.date,
                }
                self.env['account.move.line'].create(move_line_cach_vals)
                move_line_cach_timbre_vals = {
                    'name': 'timbre/'+line.move_line_id.invoice.number,
                    'quantity': 1,
                    'debit': line.move_line_id.invoice.timbre_amount,
                    'credit': 0,
                    'account_id': voucher.journal_id.default_debit_account_id.id,
                    'partner_id': voucher.partner_id.id,
                    'ref': line.move_line_id.invoice.number,
                    'currency_id': line.move_line_id.currency_id.id,
                    'company_id': line.move_line_id.invoice.company_id.id,
                    'move_id': account_move.id,
                    'period_id': voucher.period_id.id,
                    'journal_id': voucher.journal_id.id,
                    'date': voucher.date,
                }
                self.env['account.move.line'].create(move_line_cach_timbre_vals)
                move_line_partner_vals = {
                    'name': 'encais especes /'+line.move_line_id.invoice.number,
                    'quantity': 1,
                    'debit': 0,
                    'credit': line.move_line_id.invoice.amount_total-line.move_line_id.invoice.timbre_amount,
                    'account_id': voucher.partner_id.property_account_receivable.id,
                    'partner_id': voucher.partner_id.id,
                    'ref': line.move_line_id.invoice.number,
                    'currency_id': line.move_line_id.currency_id.id,
                    'company_id': line.move_line_id.invoice.company_id.id,
                    'move_id': account_move.id,
                    'period_id': voucher.period_id.id,
                    'journal_id': voucher.journal_id.id,
                    'date': voucher.date,
                }
                account_move_line = self.env['account.move.line'].create(move_line_partner_vals)
                rec_ids.append(account_move_line.id)
                account_timbre = self.env['account.account'].search([('code', '=', 6167100000)])
                move_line_timbre_vals = {
                    'name': 'encaissement timbre/'+line.move_line_id.invoice.number,
                    'quantity': 1,
                    'debit': 0,
                    'credit': line.move_line_id.invoice.timbre_amount,
                    'account_id': account_timbre.id,
                    'partner_id': voucher.partner_id.id,
                    'ref': line.move_line_id.invoice.number,
                    'currency_id': line.move_line_id.currency_id.id,
                    'company_id': line.move_line_id.invoice.company_id.id,
                    'move_id': account_move.id,
                    'period_id': voucher.period_id.id,
                    'journal_id': voucher.journal_id.id,
                    'date': voucher.date,
                }
                self.env['account.move.line'].create(move_line_timbre_vals)
            self.write({'state':'encaissed','move_id':account_move.id,'name':account_move.name})
            if voucher.journal_id.entry_posted:
                account_move.post()
            if reconcile:
                reconcile = self.pool.get('account.move.line').reconcile(self._cr,self._uid,rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
            else :
                reconcile = self.pool.get('account.move.line').reconcile_partial(self._cr, self._uid, rec_ids,writeoff_acc_id=voucher.writeoff_acc_id.id,writeoff_period_id=voucher.period_id.id,writeoff_journal_id=voucher.journal_id.id)
        else :
            self.action_move_line_create()
        return True

    @api.multi
    def action_move_line_create(self):
        '''
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        res = super(account_voucher,self).action_move_line_create()
        voucher = self
        journal = self.env['account.journal'].search([('code', '=', 'JIMP')])
        if voucher.unpaid_ids :
            for v in voucher.unpaid_ids :
                moves = self.env['account.move'].search([('voucher_id','=',v.id),('journal_id','=',journal.id)])
                if moves :
                    for mv in moves :
                        for line in mv.line_id :
                            line.write({'state_action':'processed'})
        return res


    @api.v7
    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        move_obj = self.pool.get('account.move')
        move_obj.write(cr,uid,[move_id],{'voucher_id':voucher_id})

        date = self.read(cr, uid, [voucher_id], ['date'], context=context)[0]['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore."))
                sign = line.type =='dr' and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            account_id = line.account_id.id
            if voucher.journal_id.is_jboe :
                month = voucher.period_id.name[:2]
                account_code = '3425'+month+'0000'
                account_boe_id = self.pool.get('account.account').search(cr,uid,[('code','=',account_code)])
                if account_boe_id :
                    account_id = account_boe_id[0]
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': account_id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    foreign_currency_diff = line.move_line_id.amount_residual_currency - abs(amount_currency)

            move_line['amount_currency'] = amount_currency
            voucher_line = move_line_obj.create(cr, uid, move_line)
            rec_ids = [voucher_line, line.move_line_id.id]

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                new_id = move_line_obj.create(cr, uid, exch_lines[0],context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': (-1 if line.type == 'cr' else 1) * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)

    @api.v7
    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        """
        Returns a dict that contains new values and context

        @param partner_id: latest value from user input for field partner_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        def _remove_noise_in_o2m():
            """if the line is partially reconciled, then we must pay attention to display it only once and
                in the good o2m.
                This function returns True if the line is considered as noise and should not be displayed
            """
            if line.reconcile_partial_id:
                if currency_id == line.currency_id.id:
                    if line.amount_residual_currency <= 0:
                        return True
                else:
                    if line.amount_residual <= 0:
                        return True
            return False

        if context is None:
            context = {}
        context_multi_currency = context.copy()

        currency_pool = self.pool.get('res.currency')
        move_line_pool = self.pool.get('account.move.line')
        partner_pool = self.pool.get('res.partner')
        journal_pool = self.pool.get('account.journal')
        line_pool = self.pool.get('account.voucher.line')

        #set default values
        default = {
            'value': {'line_dr_ids': [], 'line_cr_ids': [], 'pre_line': False},
        }

        # drop existing lines
        line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
        for line in line_pool.browse(cr, uid, line_ids, context=context):
            if line.type == 'cr':
                default['value']['line_cr_ids'].append((2, line.id))
            else:
                default['value']['line_dr_ids'].append((2, line.id))

        if not partner_id or not journal_id:
            return default

        journal = journal_pool.browse(cr, uid, journal_id, context=context)
        partner = partner_pool.browse(cr, uid, partner_id, context=context)
        currency_id = currency_id or journal.company_id.currency_id.id

        total_credit = 0.0
        total_debit = 0.0
        account_type = None
        if context.get('account_id'):
            account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
        if ttype == 'payment':
            if not account_type:
                account_type = 'payable'
            total_debit = price or 0.0
        else:
            total_credit = price or 0.0
            if not account_type:
                account_type = 'receivable'

        if not context.get('move_line_ids', False):
            ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id), ('move_line_type', '=', 'basic'), ('voucher_state', '=', ('open','unpaid'))], context=context)
        else:
            ids = context['move_line_ids']
        invoice_id = context.get('invoice_id', False)
        company_currency = journal.company_id.currency_id.id
        move_lines_found = []

        #order the lines by most old first
        ids.reverse()
        account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

        #compute the total debit/credit and look for a matching open amount or invoice
        for line in account_move_lines:
            if _remove_noise_in_o2m():
                continue

            if invoice_id:
                if line.invoice.id == invoice_id:
                    #if the invoice linked to the voucher line is equal to the invoice_id in context
                    #then we assign the amount on that line, whatever the other voucher lines
                    move_lines_found.append(line.id)
            elif currency_id == company_currency:
                #otherwise treatments is the same but with other field names
                if line.amount_residual == price:
                    #if the amount residual is equal the amount voucher, we assign it to that voucher
                    #line, whatever the other voucher lines
                    move_lines_found.append(line.id)
                    break
                #otherwise we will split the voucher amount on each line (by most old first)
                total_credit += line.credit and line.amount_residual or 0.0
                total_debit += line.debit and line.amount_residual or 0.0

                # tttimbre = line.invoice.timbre_amount
                # ttguaranty = line.invoice.amount_guaranty
                # total_credit += line.credit and line.amount_residual+tttimbre-ttguaranty or 0.0
                # total_debit  += line.debit and line.amount_residual+tttimbre-ttguaranty or 0.0

            elif currency_id == line.currency_id.id:
                if line.amount_residual_currency == price:
                    move_lines_found.append(line.id)
                    break
                line_residual = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual), context=context_multi_currency)
                total_credit += line.credit and line_residual or 0.0
                total_debit += line.debit and line_residual or 0.0

                # total_credit += line.credit and line_residual+tttimbre-ttguaranty or 0.0
                # total_debit  += line.debit and line_residual+tttimbre-ttguaranty or 0.0


        remaining_amount = price
        #voucher line creation
        for line in account_move_lines:

            # tttimbre = line.invoice.timbre_amount
            # ttguaranty = line.invoice.amount_guaranty

            if _remove_noise_in_o2m():
                continue

            if line.currency_id and currency_id == line.currency_id.id:
                amount_original = abs(line.amount_currency)
                amount_unreconciled = abs(line.amount_residual_currency)

                # amount_original = amount_original + tttimbre - ttguaranty
                # amount_unreconciled = amount_unreconciled + tttimbre - ttguaranty
            else:
                #always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0, context=context_multi_currency)
                amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual), context=context_multi_currency)

                # amount_original = amount_original + tttimbre - ttguaranty
                # amount_unreconciled = amount_unreconciled + tttimbre - ttguaranty
            line_currency_id = line.currency_id and line.currency_id.id or company_currency
            rs = {
                'name':line.move_id.name,
                'type': line.credit and 'dr' or 'cr',
                'move_line_id':line.id,
                'account_id':line.account_id.id,
                'amount_original': amount_original,
                'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
                'date_original':line.date,
                'date_due':line.date_maturity,
                'amount_unreconciled': amount_unreconciled,
                'currency_id': line_currency_id,
            }
            remaining_amount -= rs['amount']
            #in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
            #on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
            if not move_lines_found:
                if currency_id == line_currency_id:
                    if line.credit:
                        amount = min(amount_unreconciled, abs(total_debit))
                        rs['amount'] = amount
                        total_debit -= amount
                    else:
                        amount = min(amount_unreconciled, abs(total_credit))
                        rs['amount'] = amount
                        total_credit -= amount
            if rs['amount_unreconciled'] == rs['amount']:
                rs['reconcile'] = True

            if rs['type'] == 'cr':
                default['value']['line_cr_ids'].append(rs)
            else:
                default['value']['line_dr_ids'].append(rs)

            if len(default['value']['line_cr_ids']) > 0:
                default['value']['pre_line'] = 1
            elif len(default['value']['line_dr_ids']) > 0:
                default['value']['pre_line'] = 1
            default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
        return default

class account_move(models.Model):

    _inherit = "account.move"

    voucher_id = fields.Many2one('account.voucher', string='voucher')

class account_move_line(models.Model):

    _inherit = "account.move.line"

    voucher_state = fields.Selection(
            [('open','Validé'),
             ('unpaid', 'impayé'),
             ('encaissed','Encaissé')
            ], 'Statut de paiement', readonly=True,default='open')

    move_line_type = fields.Selection(
            [('basic','de base'),
             ('to_sedof', 'Vers Sédof')
            ], 'Type Écriture', readonly=True,default='basic')



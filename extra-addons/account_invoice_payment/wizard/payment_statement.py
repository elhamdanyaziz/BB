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

import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp.tools.translate import _
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

class payment_statement(models.TransientModel):
    
    _name = "account.payment.statement"
    _description = "Constat Paiement"


    act_id = fields.Selection([('unpaid','Impayé'),('encaissed','Encaissé'),],'Action à Appliquer',required=True)


    @api.multi
    def create_payment_statement(self):
        voucher_ids = self._context.get('active_ids')
        voucher_obj = self.env['account.voucher']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        reconcile_obj = self.env['account.move.reconcile']
        seq_obj = self.env['ir.sequence']
        journal_obj = self.env['account.journal']
        journal = journal_obj.search([('code','=','JIMP')])
        ctx = dict(self._context)
        if self.act_id == 'encaissed' :
            for voucher in voucher_obj.browse(voucher_ids):
                voucher.write({'state': 'encaissed','voucher_action': 'processed'})
                if voucher.move_ids :
                    for line in voucher.move_ids :
                        line.write({'voucher_state': 'encaissed'})
                for line in voucher.line_ids :
                    line.move_line_id.write({'voucher_state':'encaissed'})
                if voucher.line_dr_ids :
                    for line in voucher.line_dr_ids:
                        line.move_line_id.write({'voucher_state': 'encaissed'})
        if self.act_id == 'unpaid':
            for voucher in voucher_obj.browse(voucher_ids) :
                voucher.refresh()
                for line in voucher.line_ids :
                    line.move_line_id.write({'voucher_state':'unpaid'})
                ctx.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
                name = seq_obj.next_by_id(journal.sequence_id.id, context=ctx)
                if not voucher.reference:
                    ref = name.replace('/', '')
                else:
                    ref = voucher.reference

                move_record = {
                    'name': name,
                    'journal_id': journal.id,
                    'date': time.strftime('%Y-%m-%d'),
                    'ref': ref,
                    'period_id': voucher.period_id.id,
                    'voucher_id': voucher.id,
                }
                move_id = move_obj.create(move_record)
                move_line_record = {
                    'journal_id': voucher.bank_id.id,
                    'period_id': voucher.period_id.id,
                    'name': 'Retour Impayé du réglement de référence '+ref+' de la banque '+voucher.bank_id.name,
                    'account_id': voucher.bank_id.default_debit_account_id.id,
                    'move_id': move_id.id,
                    'partner_id': voucher.partner_id.id,
                    'quantity': 1,
                    'credit': voucher.amount,
                    'debit': 0,
                    'date': time.strftime('%Y-%m-%d'),
                    'move_line_type':'to_sedof'
                }
                move_line_obj.create(move_line_record)
                move_line_record = {
                    'journal_id': journal.id,
                    'period_id': voucher.period_id.id,
                    'name': 'Retour Impayé du réglement de référence '+ref+' de la banque '+voucher.bank_id.name,
                    'account_id': voucher.partner_id.property_account_receivable.id,
                    'move_id': move_id.id,
                    'partner_id': voucher.partner_id.id,
                    'quantity': 1,
                    'credit': 0,
                    'debit': voucher.amount,
                    'date': time.strftime('%Y-%m-%d'),
                    'move_line_type': 'to_sedof'
                }
                move_line_obj.create(move_line_record)
                for line in voucher.move_ids:
                    line.refresh()
                    line.write({'voucher_state':'unpaid'})
                    if line.reconcile_id:
                        move_lines = [move_line.id for move_line in line.reconcile_id.line_id]
                        move_lines.remove(line.id)
                        line.reconcile_id.unlink()
                        if len(move_lines) >= 2:
                            #move_line_obj.reconcile_partial(move_lines)
                            self.pool.get('account.move.line').reconcile_partial(self._cr, self._uid, move_lines,'auto',context=ctx)
                    if line.reconcile_partial_id:
                        move_lines = [move_line.id for move_line in line.reconcile_partial_id.line_partial_ids]
                        move_lines.remove(line.id)
                        line.reconcile_partial_id.unlink()
                        if len(move_lines) >= 2:
                            #move_line_obj.reconcile_partial(move_lines)
                            self.pool.get('account.move.line').reconcile_partial(self._cr, self._uid, move_lines,'auto',context=ctx)
                if voucher.move_id:
                    voucher.move_id.button_cancel()
                    #voucher.move_id.unlink()
                voucher.write({'state': 'unpaid','move_id':False})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

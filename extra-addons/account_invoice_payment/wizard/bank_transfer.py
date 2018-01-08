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

class bank_transfer(models.TransientModel):
    
    _name = "account.bank.transfer"
    _description = "Remise en banque"


    journal_id = fields.Many2one('account.journal', string='Banque',required=True)

    @api.multi
    def create_bank_transfer(self):
        voucher_ids = self._context.get('active_ids')
        voucher_obj = self.env['account.voucher']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        seq_obj = self.env['ir.sequence']
        ctx = dict(self._context)
        for voucher in voucher_obj.browse(voucher_ids) :
            voucher.write({'state':'bank_transfert','transfert_date':time.strftime('%Y-%m-%d'),'bank_id':self.journal_id.id})
            ctx.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
            name = seq_obj.next_by_id(self.journal_id.sequence_id.id, context=ctx)
            if not voucher.reference:
                ref = name.replace('/', '')
            else:
                ref = voucher.reference

            move_record = {
                'name': name,
                'journal_id': self.journal_id.id,
                'date': time.strftime('%Y-%m-%d'),
                'ref': ref,
                'period_id': voucher.period_id.id,
            }
            move_id = move_obj.create(move_record)
            move_line_record = {
                'journal_id': self.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': 'trasfert bancaire vers la banque '+self.journal_id.name,
                'account_id': self.journal_id.default_debit_account_id.id,
                'move_id': move_id.id,
                'partner_id': voucher.partner_id.id,
                'quantity': 1,
                'credit': 0.0,
                'debit': voucher.amount,
                'date': time.strftime('%Y-%m-%d'),
                'move_line_type':'to_sedof'
            }
            move_line_obj.create(move_line_record)
            move_line_record = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': 'trasfert bancaire vers la banque '+self.journal_id.name,
                'account_id': voucher.journal_id.default_debit_account_id.id,
                'move_id': move_id.id,
                'partner_id': voucher.partner_id.id,
                'quantity': 1,
                'credit': voucher.amount,
                'debit': 0,
                'date': time.strftime('%Y-%m-%d'),
                'move_line_type': 'to_sedof'
            }
            move_line_obj.create(move_line_record)
            if voucher.unpaid_ids :
                for unpaid in voucher.unpaid_ids :
                    unpaid.write({'voucher_action':'processed'})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

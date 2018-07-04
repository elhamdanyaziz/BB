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
    type = fields.Selection([('check','Remise Chèques'),('effect','Remise Effets'),],'Type',readonly=False,default='check', copy=False)


    @api.multi
    def create_bank_transfer(self):
        voucher_ids = self._context.get('active_ids')
        voucher_obj = self.env['account.voucher']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        bank_obj = self.env['res.partner.bank']
        bank_deposit_obj = self.env['account.bank.deposit']
        seq_obj = self.env['ir.sequence']
        ctx = dict(self._context)
        total_amount = 0
        depositines = []
        for voucher in voucher_obj.browse(voucher_ids) :
            if self.type == 'effect' and not voucher.journal_id.is_jboe:
                raise except_orm(_('Attention!'), _('Il y a un paiement de type chèque sélectionné !'))
            if self.type == 'check' and voucher.journal_id.is_jboe:
                raise except_orm(_('Attention!'), _('Il y a un paiement de type effet sélectionné !'))
            total_amount+=total_amount+voucher.amount
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
                'voucher_id': voucher.id,
            }
            move_id = move_obj.create(move_record)
            move_line_record = {
                'journal_id': self.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': 'trasfert bancaire vers la banque '+self.journal_id.name,
                #'account_id': self.journal_id.default_debit_account_id.id,
                'move_id': move_id.id,
                'partner_id': voucher.partner_id.id,
                'quantity': 1,
                'credit': 0.0,
                'debit': voucher.amount,
                'date': time.strftime('%Y-%m-%d'),
                'move_line_type':'to_sedof'
            }
            if self.type == 'effect':
                mv = move_obj.search([('journal_id','=',voucher.journal_id.id),('voucher_id','=',voucher.id)])
                mvline = move_line_obj.search([('journal_id', '=', voucher.journal_id.id), ('move_id', '=', mv.id),('account_id', '!=', voucher.partber_id.property_account_receivable.id)])
                move_line_record['account_id'] = mvline.account_id.id
            else :
                move_line_record['account_id'] =self.journal_id.default_debit_account_id.id
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

            deposit_line = {
                'partner_id': voucher.partner_id.id,
                'bank': voucher.customer_bank,
                'city': voucher.city_customer_bank,
                'amount': voucher.amount,
                'type': self.type,
            }
            if self.type == 'check' :
                deposit_line['ref_check'] = voucher.reference
            if self.type == 'effect' :
                deposit_line['ref_lcn'] = voucher.reference
                deposit_line['deadline_date'] = voucher.deadline_date
            depositines.append((0, 0, deposit_line))

        bank = bank_obj.search([('journal_id','=',self.journal_id.id)])
        record_deposit = {
            'bank_agency_code':bank.bank_bic,
            'bank_agency_name':bank.bank_name,
            'account_number':bank.acc_number,
            'amount_total':total_amount,
            'type': self.type,
            'customer_name':self.env.user.company_id.name,
            'user_id':self.env.user.id,
            'line_ids':depositines
        }
        if self.type == 'check':
            record_deposit['number_check'] = len(voucher_ids)
            record_deposit['line_check_ids'] = depositines
        if self.type == 'effect':
            record_deposit['number_lcn'] = len(voucher_ids)
            record_deposit['line_lcn_ids'] = depositines
        bank_deposit_obj.create(record_deposit)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

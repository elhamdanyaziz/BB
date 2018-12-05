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
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp

class stock_invoice_onshipping(models.TransientModel):

    _inherit = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"

    @api.multi
    def _get_date_shipping(self):
        picking_id = self._context.get('active_id', [])
        picking_obj = self.env['stock.picking']
        picking = picking_obj.browse(picking_id)
        return picking.date_done


    invoice_date = fields.Date('Invoice Date',default=_get_date_shipping)

    @api.multi
    def open_invoice(self):
        if self._context is None:
            self._context = {}
        picking_obj=self.env['stock.picking']
        invoice_obj = self.env['account.invoice']
        invoice_ids = self.create_invoice()
        if not invoice_ids:
            raise except_orm(_('Error!'), _("No invoice created!"))

        picking = picking_obj.browse(self._context.get('active_id',False))

        invoice = invoice_obj.browse(invoice_ids[0])
        if picking.opp_id :
            invoice.write({'opp_id':picking.opp_id.id})
        if picking.order_id:
            invoice.write({'payment_term': picking.order_id.payment_term.id,'payment_condition': picking.order_id.payment_condition.id,'order_id': picking.order_id.id,'with_deposit': picking.order_id.with_deposit,'deposit_number': picking.order_id.deposit_number,'with_guaranty': picking.order_id.with_guaranty,'guaranty_number': picking.order_id.guaranty_number,'user_id':picking.order_id.user_id.id})
            if picking.order_id.amount_discount_ongoing != 0 :
                invoice.write({'with_discount': True,'discount_number':picking.order_id.amount_discount_ongoing/100})
        invoice.button_reset_taxes()
        action_model = False
        action = {}

        journal2type = {'sale': 'out_invoice', 'purchase': 'in_invoice', 'sale_refund': 'out_refund','purchase_refund': 'in_refund'}
        inv_type = journal2type.get(self.journal_type) or 'out_invoice'
        data_pool = self.env['ir.model.data']
        if inv_type == "out_invoice":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree1')
        elif inv_type == "in_invoice":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree2')
            invoice.write({'type_service': 'purchase_goods'})
        elif inv_type == "out_refund":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree3')
        elif inv_type == "in_refund":
            action_id = data_pool.xmlid_to_res_id('account.action_invoice_tree4')

        if action_id:
            action_pool = self.pool['ir.actions.act_window']
            action = action_pool.read(self._cr,self._uid, action_id, context=self._context)
            action['domain'] = "[('id','in', [" + ','.join(map(str, invoice_ids)) + "])]"
            return action
        return True


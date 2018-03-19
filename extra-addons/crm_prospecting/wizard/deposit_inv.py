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


class deposit_inv(models.TransientModel):
    _name = "deposit.inv"
    _description = "Acompte"

    @api.multi
    def _get_accompte_product(self):
        try:
            product = self.env['ir.model.data'].get_object('sale', 'advance_product_0')
        except ValueError:
            # a ValueError is returned if the xml id given is not found in the table ir_model_data
            return False
        return product.id

    advance_payment_method = fields.Selection([('percentage', 'Pourcentage'), ('fixed', 'Prix fixe (depot)')], 'Méthode Acompte', required=True,
        help="""
                Utilisez Pourcentage pour facturer un pourcentage du montant total.
                Utilisez Prix fixe pour facturer en avance un montant spécifique.
                """, default='percentage')
    qtty = fields.Float('Quantité', digits=(16, 2), required=True, default=1.0)
    product_id = fields.Many2one('product.product', 'Produit Acompte', domain=[('type', '=', 'service')])
    amount = fields.Float('Montant Acompte', digits_compute=dp.get_precision('Account'),help="le montant à facturer dans l'acompte.")
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    tax_id = fields.Many2one('account.tax', 'Taxe', domain=[('type_tax_use', '=', 'sale')])
    order_id = fields.Many2one('sale.order', string='Bon de commande')

    @api.model
    def default_get(self, fields):
        if self._context is None: self._context = {}
        res = super(deposit_inv, self).default_get(fields)
        order_id = self._context.get('active_id', [])
        order = self.env['sale.order'].browse(order_id)
        res.update(opp_id=order.opp_id.id,order_id=order_id)
        return res

    @api.multi
    def onchange_method(self, advance_payment_method, order_id, product_id=False):

        if advance_payment_method == 'percentage':
            if order_id:
                order = self.env['sale.order'].browse(order_id)
                amount = order.deposit_number
                return {'value': {'amount': amount, 'product_id': False}}
        # if product_id:
        #     product = self.env['product.product'].browse(product_id)
        #     return {'value': {'amount': product.list_price}}
        return {'value': {'amount': 0}}

    @api.multi
    def _prepare_advance_invoice_vals(self):
        if self._context is None:
            self._context = {}
        fiscal_obj = self.env['account.fiscal.position']
        inv_line_obj = self.env['account.invoice.line']
        order_id = self._context.get('active_id', [])
        result = []
        order = self.env['sale.order'].browse(order_id)
        res = {}
        # determine and check income account
        if not self.product_id :
            #prop = ir_property_obj.get('property_account_income_categ', 'product.category', 'product.category,1')
            # prop_id = prop and prop.id or False
            # print "prop_id",prop_id
            # account_id = fiscal_obj.map_account(prop_id)
            # if not account_id:
            #     raise Warning(_('Erreur de Configuration!'),
            #             _('Pas de compte définit pour cette propriété.'))
            account_accompte_id = self.env['account.account'].search([('code', '=', 4421000000)])
            res['account_id'] = account_accompte_id.id
        if not res.get('account_id'):
            raise Warning(_('Erreur de Configuration!'),_('Pas de compte définit pour l\'acompte'))

        # determine invoice amount
        if self.amount <= 0.00:
            raise Warning(_('Donnée n\'est pas correct'),_('Montant Acompte doit etre positif.'))
        if self.advance_payment_method == 'percentage':
            # inv_amount = order.amount_untaxed * self.amount
            inv_amount = order.amount_total * self.amount
            if not res.get('name'):
                res['name'] = _("Acompte %s %%") % (self.amount * 100)
        else:
            # inv_amount = self.amount_untaxed
            inv_amount = self.amount_total
            if not res.get('name'):
                # TODO: should find a way to call formatLang() from rml_parse
                symbol = order.currency_id.symbol
                if order.currency_id.position == 'after':
                    res['name'] = _("Acompte  %s %s") % (inv_amount, symbol)
                else:
                    res['name'] = _("Acompte  %s %s") % (symbol, inv_amount)

        # determine taxes
        # if res.get('invoice_line_tax_id'):
        #     res['invoice_line_tax_id'] = [(6, 0, res.get('invoice_line_tax_id'))]
        # else:
        #     res['invoice_line_tax_id'] = False

        # create the invoice
        inv_line_values = {
            'name': res.get('name'),
            'origin': order.name,
            'account_id': res['account_id'],
            'price_unit': inv_amount,
            'quantity': self.qtty or 1.0,
            'discount': False,
            'uos_id': res.get('uos_id', False),
            #'product_id': self.product_id.id,
            # 'invoice_line_tax_id': [(6, 0, [self.tax_id.id])],
            'invoice_line_tax_id': False,
            # 'account_analytic_id': self.project_id.id or False,
        }
        inv_values = {
            'name': order.name,
            'origin': order.name,
            'type': 'out_invoice',
            'reference': False,
            'account_id': order.partner_id.property_account_receivable.id,
            # 'partner_id': order.partner_invoice_id.id if order.partner_invoice_id else order.partner_id.id,
            'partner_id': order.partner_id.id,
            'invoice_line': [(0, 0, inv_line_values)],
            'currency_id': order.currency_id.id,
            'comment': '',
            # 'payment_term': order.payment_term.id,
            'fiscal_position': order.partner_id.property_account_position.id if order.partner_id.property_account_position else False,
            'opp_id': self.opp_id.id,
            'order_id': order.id,
            'is_deposit_inv':True
        }
        result.append((order.id, inv_values))
        return result

    @api.multi
    def _create_invoices(self, inv_values, order_id):
        inv_obj = self.env['account.invoice']
        inv_id = inv_obj.create(inv_values)
        inv_id.button_reset_taxes()
        order = self.env['sale.order'].browse(order_id)
        # add the invoice to the sales order's invoices
        order.write({'invoice_ids': [(4, inv_id.id)]})
        return inv_id.id

    @api.multi
    def create_invoices(self):
        """ create invoices for the active sales orders """
        act_window = self.env['ir.actions.act_window']
        order_id = self._context.get('active_id', [])
        order = self.env['sale.order'].browse(order_id)
        order.write({'is_deposit': True})
        assert self.advance_payment_method in ('fixed', 'percentage')

        inv_ids = []
        for order_id, inv_values in self._prepare_advance_invoice_vals():
            inv_ids.append(self._create_invoices(inv_values, order_id))

        if self._context.get('open_invoices', False):
            return self.open_invoices(inv_ids)
        return {}

    def open_invoices(self, invoice_ids):

        def get_view_id(xid, name):
            try:
                return self.env['ir.model.data'].xmlid_to_res_id('account.' + xid, raise_if_not_found=True)
            except ValueError:
                try:
                    return self.env['ir.ui.view'].search([('name', '=', name)], limit=1).id
                except Exception:
                    return False  # view not found

        """ open a view on one of the given invoice_ids """
        form_id = get_view_id('invoice_form', 'account.invoice.form')
        tree_id = get_view_id('invoice_tree', 'account.invoice.tree')
        # form_res = ir_model_data.get_object_reference(cr, uid, 'account', 'form_res')
        # form_id = form_res and form_res[1] or False
        # tree_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
        # tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Facture Acompte'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': invoice_ids[0],
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{'type': 'out_invoice'}",
            'type': 'ir.actions.act_window',
        }
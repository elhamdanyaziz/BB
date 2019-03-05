
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
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from lxml import etree


class sale_order(models.Model):

    _inherit = 'sale.order'

    quotation_id = fields.Many2one('sale.order', string='Devis',default=False)
    is_quotation = fields.Boolean('Devis ?',default=False)
    is_order = fields.Boolean('Bon de commande ?')
    state = fields.Selection([
        ('draft', 'BC Reçu'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé'),
        ('approved', 'Approuvé'),
        ('archived', 'Archivé'),
        ('sent', 'Quotation Sent'),

        #('received', 'BC Reçu'),
        ('cancel', 'Cancelled'),
        ('waiting_date', 'Waiting Schedule'),
        ('progress', 'Sales Order'),
        ('manual', 'Sale to Invoice'),
        ('shipping_except', 'Shipping Exception'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Done'),
    ], 'Statut', readonly=True, copy=False, select=True)
    state1 = fields.Selection([
        ('draft', 'Devis brouillon'),
        ('confirmed', 'Confirmé'),
        ('validated', 'Validé'),
        ('approved', 'Approuvé'),
        ('archived', 'Archivé'),
        ('sent', 'Devis envoyé'),
    ], 'Statut', readonly=True, copy=False, select=True,default='draft')
    partner_invoice = fields.Char(string='Adresse de facturation')
    partner_shipping = fields.Char(string='Adresse de livraison')
    partner_code = fields.Char(string='Code Client')
    quotation_ids = fields.One2many('sale.order', 'quotation_id', 'Bons de Commande',readonly=True,domain=[('is_order','=',True)])
    order_policy = fields.Selection([('manual', 'On Demand'),('picking', 'On Delivery Order'),('prepaid', 'Before Delivery'),], 'Create Invoice', required=True, readonly=True,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},default='picking',help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered.""")
    is_solded = fields.Boolean('Devis Soldé',default=False)

    @api.multi
    def action_shipped_quotation(self):
        for order in self :
            order.write({'is_solded':True})
        return True

    @api.multi
    def action_revised(self):
        if self.quotation_ids :
            raise except_orm(_('Attention!'), _('Vous pouvez pas faire cette opération.'))
        self.write({'state1':'archived','state':'archived'})
        lines = []
        quotations = self.search([('is_quotation', '=', True),('quotation_id', '=', self.id),('state', '=','archived')])
        for line in self.order_line :
            line = (0,0, {'order_id':self.id,'product_id' : line.product_id.id,'name' : line.name,'price_unit' : line.price_unit,'product_uom_qty' : line.product_uom_qty,'product_uom':line.product_uom.id,'purchase_price' :line.purchase_price,'cost_price' :line.cost_price,'line_discount' :line.line_discount,'picking_delay' :line.picking_delay,'state':'draft'})
            lines.append(line)

        return {
            'name': 'Devis',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.ui.view'].search([('name', '=', 'sale.order.form')])[0].id,
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',

            'context': {
                'default_name': self.name+'/REV'+str(len(quotations)+1),
                'default_opp_id': self.opp_id.id,
                'default_payment_condition': self.payment_condition.id,
                'default_quotation_id': self.id,
                'default_state': 'draft',
                'default_is_quotation': True,
                'default_is_order': False,
                'default_user_id': self.user_id.id,
                'default_partner_id': self.partner_id.id,
                'default_pricelist_id': self.pricelist_id.id,
                'default_company_id': self.company_id.id,
                'default_amount_discount_ongoing': self.amount_discount_ongoing,
                'default_order_line': lines,
                'default_payment_term': self.payment_term.id,
                'default_partner_code': self.partner_code,
                'default_partner_invoice': self.partner_invoice,
                'default_partner_shipping': self.partner_shipping,
                'default_validity_offer': self.validity_offer,
                'default_client_order_ref': self.client_order_ref,
            }
        }

    @api.multi
    def action_create_sale_order(self):
        lines = []
        orders = self.search([('is_order', '=', True), ('quotation_id', '=', self.id)])
        for line in self.order_line :
            order_lines = self.env['sale.order.line'].search([('product_id', '=', line.product_id.id),('order_id', 'in', orders._ids)])
            if order_lines :
                qty_solded = sum(ol.product_uom_qty for ol in order_lines)
                qty_avalaible = line.product_uom_qty - qty_solded
            else :
                qty_avalaible = line.product_uom_qty
            #line = (0,0, {'order_id':self.id,'product_id' : line.product_id.id,'name' : line.name,'product_uom_qty' : line.product_uom_qty,'product_uom':line.product_uom.id,'purchase_price' : line.purchase_price,'tax_id': [0,0,line.tax_id._ids]})
            line = (0,0, {'product_available_qty':line.product_available_qty,'line_discount':line.line_discount,'order_id':self.id,'product_id' : line.product_id.id,'name' : line.name,'price_unit' : line.price_unit,'product_uom_qty' : qty_avalaible,'product_uom':line.product_uom.id,'purchase_price' : line.purchase_price,'cost_price':line.cost_price,'state':line.state})
            lines.append(line)

        return {
            'name': 'Bon de Commande',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.ui.view'].search([('name', '=', 'crm.sale.order.form.inherit1')])[0].id,
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',

            'context': {
                'default_name': self.name+'/'+str(len(orders)+1),
                'default_partner_id': self.partner_id.id,
                'default_opp_id': self.opp_id.id,
                'default_payment_condition': self.payment_condition.id,
                'default_quotation_id': self.id,
                'default_state': 'draft',
                'default_is_quotation': False,
                'default_is_order': True,
                'default_user_id': self.user_id.id,
                'default_pricelist_id': self.pricelist_id.id,
                'default_company_id': self.company_id.id,
                'default_amount_discount_ongoing': self.amount_discount_ongoing,
                'default_order_line': lines,
                'default_payment_term': self.payment_term.id,
                'default_partner_shipping': self.partner_shipping,
            }
        }

    @api.multi
    def action_button_confirmed(self):
        self.signal_workflow('wait_confirmed_quotation')
        return True


    @api.multi
    def action_wait_confirmed_quotation(self):
        return True

    @api.multi
    def action_confirmed(self):
        self.state = 'confirmed'
        self.state1 = 'confirmed'
        return True

    @api.multi
    def action_button_validate(self):
        self.signal_workflow('wait_validated_quotation')
        return True

    @api.multi
    def action_wait_validated_quotation(self):
        return True

    @api.multi
    def action_validated(self):
        self.state = 'validated'
        self.state1 = 'validated'
        return True

    @api.multi
    def action_approved(self):
        self.state = 'approved'
        self.state1 = 'approved'
        return True

    @api.multi
    def action_sent(self):
        self.state = 'sent'
        self.state1 = 'sent'
        return True

    @api.v7
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        if not part:
            return {'value': {'partner_invoice': False,'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

        part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        invoice_part = self.pool.get('res.partner').browse(cr, uid, addr['invoice'], context=context)
        payment_term = invoice_part.property_payment_term and invoice_part.property_payment_term.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        val = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            # 'payment_term': payment_term,
            'user_id': dedicated_salesman,
            'partner_code': part.customer_code,
            'partner_invoice': part.street,
            'amount_discount':part.customer_discount,
            #'user_id':part.user_id.id,
            'section_id': part.section_id.id,
            # 'payment_condition': part.payment_condition.id
        }
        quotation_default_values = self.default_get(cr, uid, ['is_quotation','quotation_id'], context=context)

        if quotation_default_values['is_quotation'] :
            val['payment_condition'] =  part.payment_condition.id
            val['payment_term'] = payment_term
        else:
            if not quotation_default_values['quotation_id'] :
                val['payment_condition'] = part.payment_condition.id
                val['payment_term'] = payment_term
        delivery_onchange = self.onchange_delivery_id(cr, uid, ids, False, part.id, addr['delivery'], False,  context=context)
        val.update(delivery_onchange['value'])
        if pricelist:
            val['pricelist_id'] = pricelist
        if not self._get_default_section_id(cr, uid, context=context) and part.section_id:
            val['section_id'] = part.section_id.id
        sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
        if sale_note: val.update({'note': sale_note})
        return {'value': val}

class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        context = self._context or {}
        if context.get('default_model') == 'sale.order' and context.get('default_res_id') and context.get('mark_so_as_sent'):
            context = dict(context, mail_post_autofollow=True)
            order = self.env['sale.order'].browse(context['default_res_id'])
            order.signal_workflow('quotation_sent')
            order.write({'state':'sent','state1':'sent'})
        return super(mail_compose_message, self).send_mail()

class sale_config_settings(models.TransientModel):

    _inherit = 'sale.config.settings'

    module_sale_validation = fields.Boolean('Validation BC')
    limit_amount_cd = fields.Integer('Montant nécessite une validation DC', required=True, default=5000)
    limit_amount_gm = fields.Integer('Montant nécessite une validation DG', required=True, default=10000)

    @api.multi
    def set_limit_amount(self):
        ir_model_data = self.env['ir.model.data']
        draft_confirmed = ir_model_data.get_object('sale_firm', 'trans_wait_confirmed_quotation_confirmed')
        draft_confirmed.write({'condition': 'amount_untaxed >= %s' % self.limit_amount_cd})
        draft_approved = ir_model_data.get_object('sale_firm', 'trans_wait_confirmed_quotation_approved')
        draft_approved.write({'condition': 'amount_untaxed < %s' % self.limit_amount_cd})
        confirmed_validated = ir_model_data.get_object('sale_firm', 'trans_wait_validated_quotation_validated')
        confirmed_validated.write({'condition': 'amount_untaxed >= %s' % self.limit_amount_gm})
        confirmed_approved = ir_model_data.get_object('sale_firm', 'trans_wait_validated_quotation_approved')
        confirmed_approved.write({'condition': 'amount_untaxed < %s' % self.limit_amount_gm})

class product_category(models.Model):

    _inherit = 'product.category'

    description = fields.Text(string='Description')
    english_description = fields.Text(string='Description en Anglais')

class res_partner(models.Model):

    _inherit = 'res.partner'

    sale_quotation_count = fields.Integer(string='# de Devis', readonly=False, compute='_compute_count', store=True)
    sale_order_2_count = fields.Integer(string='# des Bons de Commande', readonly=False, compute='_compute_count',store=True)
    sale_quotation_ids = fields.One2many('sale.order', 'partner_id', 'Devis', domain=[('is_quotation', '=', True)])
    sale_order_ids = fields.One2many('sale.order', 'partner_id', 'Bons de Commande', domain=[('is_order', '=', True)])

    @api.one
    @api.depends('sale_quotation_ids', 'sale_order_ids')
    def _compute_count(self):
        for partner in self:
            if partner.sale_quotation_ids:
                self.sale_quotation_count = len(partner.sale_quotation_ids)
            else :
                self.sale_quotation_count = 0
            if partner.sale_order_ids:
                self.sale_order_2_count = len(partner.sale_order_ids)
            else :
                self.sale_order_2_count = 0

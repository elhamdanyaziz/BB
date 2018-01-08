
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
from openerp import tools



class sale_order(models.Model):

    _inherit = 'sale.order'

    opp_id = fields.Many2one('crm.lead',string='Opportunité',domain=[('type','=','opportunity')])
    percentage_margin = fields.Float('Marge en Pourcentage', compute='_compute_percentage_margin', readonly=True)
    amount_untaxed = fields.Float('Montant HT', compute='_compute_amount',digits=dp.get_precision('Quotation Amount'), readonly=True,store=True)
    amount_tax = fields.Float('Taxes', compute='_compute_amount', digits=dp.get_precision('Quotation Amount'),readonly=True,store=True)
    amount_total = fields.Float('Montant TTC', compute='_compute_amount', digits=dp.get_precision('Quotation Amount'),readonly=True,store=True)
    global_discount = fields.Float('Remise', compute='_compute_amount', digits=dp.get_precision('Quotation Amount'),readonly=True, store=True)
    amount_discount = fields.Float('Remise(%)', degits=2, default=0,digits=dp.get_precision('Quotation Amount'))
    amount_discount_ongoing = fields.Float('Remise(%)', degits=2, default=0,digits=dp.get_precision('Quotation Amount'))
    carrier_id = fields.Many2one('sale.carrier', string='Transporteur')
    tel = fields.Char('Tél Société')
    driver = fields.Char('Chauffeur')
    driver_tel = fields.Char('Tél de Chauffeur')
    whith_reservation = fields.Boolean('Avec Réservation ?')
    with_deposit = fields.Boolean('Avec Acompte ?', default=False)
    deposit_number = fields.Float('Restitution d\'acompte',default=0.1)
    is_deposit = fields.Boolean('Acompte', default=False)
    with_guaranty = fields.Boolean('Avec Retenue de garantie ?', default=False)
    guaranty_number = fields.Float('Retenue de garantie',default=0.1)
    move_lines = fields.One2many('stock.move', 'sale_order_id', 'Livraisons',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    margin = fields.Float('Marge', compute='_compute_margin', readonly=True, store=True)
    situation_product_ids = fields.One2many('sale.order.situation', 'sale_order_id', 'Situation',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    picking_ids = fields.One2many('stock.picking', 'order_id','BLs',domain=[('picking_type_id', '=', 2)])
    deliverie_ids = fields.One2many('stock.picking', 'order_id', 'BLs', domain=[('picking_type_id', '=', 2)])
    whith_manifacture = fields.Boolean('Avec Production ?')
    amount_untaxed_with_discount = fields.Float('Montant HT', compute='_compute_amount',digits=dp.get_precision('Quotation Amount'), readonly=True,store=True)
    payment_condition = fields.Many2one('res.partner.payment.condition', string='Condition de paiement')
    validity_offer = fields.Char('Validité de l’offre')
    reel_margin = fields.Float('Marge Réelle', compute='_compute_margin', readonly=True, store=True)
    reel_percentage_margin = fields.Float('Marge Réelle en Pourcentage', compute='_compute_reel_percentage_margin', readonly=True)


    @api.multi
    def arrondi(self,x):
        nb = str(x).split('.')
        if int(nb[1][0]) >=0 and int(nb[1][0]) < 3 :
            decimal = float(nb[0])
        elif int(nb[1][0]) >=3 and int(nb[1][0]) < 7:
            decimal = float(nb[0]+'.5')
        else :
            decimal = float(nb[0])+1
        return decimal

    @api.multi
    def is_line_discount(self,lines):
        for line in lines:
            if line.line_discount !=0 :
                return True
        return False

    @api.depends('global_discount','order_line.margin_line')
    def _compute_margin(self):
        for order in self:
            is_margin_line = self.is_line_discount(order.order_line)
            #margin = sum(line.margin_line for line in order.order_line)
            #margin_order = (margin-order.global_discount) if not is_margin_line else margin
            sum_cost = sum(line.purchase_price * line.product_uom_qty for line in order.order_line)
            sum_reel_cost = sum(line.cost_price * line.product_uom_qty for line in order.order_line)
            margin_order = order.amount_untaxed - (order.global_discount+sum_cost)
            order.margin = margin_order
            #reel_margin = sum(line.reel_margin_line for line in order.order_line)
            #reel_margin_order = (reel_margin-order.global_discount) if not is_margin_line else reel_margin
            reel_margin_order = order.amount_untaxed - (order.global_discount+sum_reel_cost)
            order.reel_margin = reel_margin_order


    @api.depends('margin','amount_untaxed')
    def _compute_percentage_margin(self):
        for order in self :
            percentage_margin = (order.margin/(order.amount_untaxed-order.global_discount))*100 if order.amount_untaxed !=0 else 0
            #print "percentage_margin",percentage_margin
            #order.write({'percentage_margin':percentage_margin})
            order.percentage_margin = percentage_margin

    @api.depends('reel_margin','amount_untaxed')
    def _compute_reel_percentage_margin(self):
        for order in self :
            percentage_margin = (order.reel_margin/(order.amount_untaxed-order.global_discount))*100 if order.amount_untaxed !=0 else 0
            order.reel_percentage_margin = percentage_margin


    @api.one
    @api.depends('order_line.price_subtotal', 'order_line.tax_id')
    def _compute_amount(self):

        self.amount_untaxed = sum(line.price_subtotal for line in self.order_line)
        amount_tax = sum(self._amount_line_tax(line) for line in self.order_line)
        sum_discount_subtotal = sum(line.discount_subtotal for line in self.order_line)
        sum_line_discount = sum(line.line_discount for line in self.order_line)
        if sum_line_discount > 0 :
            amount_discount_ongoing = (sum_discount_subtotal/self.amount_untaxed)*100
            self.amount_discount_ongoing = self.arrondi(amount_discount_ongoing)
        self.amount_untaxed_with_discount = self.amount_untaxed-self.amount_untaxed*(self.amount_discount_ongoing/100)
        self.amount_tax = (amount_tax-amount_tax*(self.amount_discount_ongoing/100)) if self.amount_discount_ongoing !=0 else amount_tax
        self.global_discount = self.amount_untaxed*(self.amount_discount_ongoing/100) if self.amount_discount_ongoing !=0 else sum_discount_subtotal
        self.amount_total = (self.amount_untaxed + self.amount_tax)-self.global_discount

    @api.multi
    def action_sale_global_discount(self):
        #self.global_discount = self.amount_untaxed*(self.amount_discount/100)
        self.amount_discount_ongoing = self.amount_discount
        #self._compute_amount()
        for line in self.order_line :
            line.write({'line_discount':0,'discount_subtotal':0})
        self._compute_amount()
        self.amount_discount = 0

    @api.onchange('carrier_id')
    def _compute_carrier_id(self):
        if self.carrier_id:
            self.tel = self.carrier_id.tel
            self.driver = self.carrier_id.driver
            self.driver_tel = self.carrier_id.driver_tel

    # @api.onchange('partner_id')
    # def _onchange_partner_id(self):
    #     if self.partner_id:
    #         self.user_id = self.partner_id.user_id.id
    #         self.amount_discount = self.partner_id.customer_discount

    @api.multi
    def action_create_removal_order(self):
        if self.partner_id.blocking_ok and not self.env.user.force_picking_out_ok:
            raise except_orm(_('Blockage!'),_('Ce client est bloqué,vous pouvez pas générer des bons d\'enlevement.'))
        lines = []
        date_expected = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        location_dest_id = self.section_id.location_id.id
        opp_id = False
        if self.opp_id :
            opp_id = self.opp_id.id
        if not self.whith_reservation :
            location_dest_id = self.warehouse_id.delivery_location_id.id
        for line in self.order_line :
            qty = line.product_uom_qty - line.qty_available
            line = (0,0, {'invoice_state':'2binvoiced','date_expected':date_expected,'opp_id':opp_id,'sale_order_id':self.id,'price_unit':line.product_id.cost_price,'price_unit_sale':line.price_unit,'sale_order_line_id':line.id,'product_id' : line.product_id.id,'name' : line.name,'product_uom_qty' : qty,'product_uom':line.product_uom.id,'location_id' : self.warehouse_id.location_id.id,'location_dest_id': location_dest_id})
            lines.append(line)
        return {
            'name': 'BE',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.ui.view'].search([('name', '=', 'stock.removal.form')])[0].id,
            'res_model': 'stock.removal',
            'type': 'ir.actions.act_window',

            'context': {
                'default_type': 'removal',
                'default_origin': self.name,
                'default_section_id': self.section_id.id,
                'default_sale_order_id': self.id,
                'default_opp_id': self.opp_id.id,
                'default_user_id': self.user_id.id,
                'default_partner_id': self.partner_id.id,
                'default_location_id': self.warehouse_id.location_id.id,
                'default_location_dest_id': location_dest_id,
                'default_company_id': self.company_id.id,
                'default_move_lines': lines,
                'default_whith_reservation':self.whith_reservation,
            }
        }

    @api.multi
    def action_button_confirm(self):
        # if self.whith_manifacture :
        #     res = super(sale_order, self).action_button_confirm()
        #     return res
        # else :
        ####################################################################"
        self.write({'state': 'progress', 'date_confirm': datetime.today()})
        stage = self.env['crm.case.stage'].search([('name', '=', 'Gagnée')])
        if self.opp_id :
            self.opp_id.write({'stage_id': stage.id})
        for line in self.order_line :
            line.button_confirm()
            ##################creation situation####################
            record_situation = {
                'product_id':line.product_id.id,
                'qty_ordered':line.product_uom_qty,
                'sale_order_id':self.id

            }
            self.env['sale.order.situation'].create(record_situation)
        ########################################################
        ##########################bloc de controle##################################
        domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'draft')]
        draft_invoices = self.env['account.invoice'].search(domain)
        draft_invoices_amount = sum([x.amount_untaxed for x in draft_invoices])

        available_credit = self.partner_id.credit_limit - (self.partner_id.credit + draft_invoices_amount)  # a rajouter les factures qui ne sont pas encaissé
        # available_credit = self.partner_id.credit_limit - (self.partner_id.credit + none_invoiced_amount + draft_invoices_amount) # arajouter les factures qui ne sont pas encaissé
        if self.amount_total > available_credit:
            assert len(self) == 1, 'This option should only be used for a single id at a time.'
            template = self.env.ref('crm_prospecting.email_template_control_limit_credit_sale', False)
            compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            ctx = dict(
                default_model='sale.order',
                default_res_id=self.id,
                default_use_template=bool(template),
                default_template_id=template.id,
                default_composition_mode='comment',
                #mark_so_as_sent=True,
            )
            return {
                'name': _('Envoi mail controle plafond'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    @api.multi
    def action_wait(self):
        res = super(sale_order, self).action_wait()
        stage = self.env['crm.case.stage'].search([('name','=','Gagnée')])
        if self.opp_id :
            self.opp_id.write({'stage_id':stage.id})
        return True

    @api.multi
    def check_limit(self):
        # if self.order_policy == 'prepaid':
        #     return True
        #
        # # We sum from all the sale orders that are aproved, the sale order
        # # lines that are not yet invoiced
        # domain = [('order_id.partner_id', '=', self.partner_id.id),('invoiced', '=', False),('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
        # order_lines = self.env['sale.order.line'].search(domain)
        # none_invoiced_amount = sum([x.price_subtotal for x in order_lines])
        #
        # # We sum from all the invoices that are in draft the total amount
        # domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'draft')]
        # draft_invoices = self.env['account.invoice'].search(domain)
        # draft_invoices_amount = sum([x.amount_total for x in draft_invoices])

        # We sum from all the invoices that are in draft the total amount
        domain = [('partner_id', '=', self.partner_id.id), ('state', '=', 'draft')]
        draft_invoices = self.env['account.invoice'].search(domain)
        draft_invoices_amount = sum([x.amount_untaxed for x in draft_invoices])

        available_credit = self.partner_id.credit_limit - (self.partner_id.credit + draft_invoices_amount)  # a rajouter les factures qui ne sont pas encaissé
        # available_credit = self.partner_id.credit_limit - (self.partner_id.credit + none_invoiced_amount + draft_invoices_amount) # arajouter les factures qui ne sont pas encaissé
        if self.amount_total > available_credit:
            assert len(self) == 1, 'This option should only be used for a single id at a time.'
            template = self.env.ref('crm_prospecting.email_template_control_limit_credit_sale', False)
            compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            ctx = dict(
                default_model='sale.order',
                default_res_id=self.id,
                default_use_template=bool(template),
                default_template_id=template.id,
                default_composition_mode='comment',
                mark_so_as_sent=True,
            )
            return {
                'name': _('Envoi mail controle plafond'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }



class sale_order_line(models.Model):

    _inherit = 'sale.order.line'

    line_discount = fields.Float('% Remise',degits=2,default=0)
    price_subtotal = fields.Float('Sous-total', compute='_amount_line', readonly=True, store=True)
    discount_subtotal = fields.Float('Remise', compute='_compute_discount_subtotal', readonly=True, store=True)
    margin_line = fields.Float('MRG', compute='_compute_margin_line', readonly=True,store=True)
    qty_available = fields.Float('Quantité Restante',default=0)
    product_available_qty = fields.Float('Dispo', digits=dp.get_precision('Product UoS'), required=False,readonly=True)
    picking_delay =  fields.Float('Délai(semaine)', required=False)
    reel_margin_line = fields.Float('MRG R', compute='_compute_margin_line', readonly=True, store=True)
    cost_price = fields.Float('PRR', required=False)

    @api.v7
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            #raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
            raise except_orm(_('No Customer Defined!'),_('Before choosing a product,\n select a customer in the sales form.'))

        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = context.copy()
        context_partner.update({'lang': lang, 'partner_id': partner_id})

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)
        result['product_available_qty'] = product_obj.qty_available
        result['purchase_price'] = product_obj.standard_price
        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)

        #if uid == SUPERUSER_ID and context.get('company_id'):
        if context.get('company_id'):
            taxes = product_obj.taxes_id.filtered(lambda r: r.company_id.id == context['company_id'])
        else:
            taxes = product_obj.taxes_id
        result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes, context=context)

        # if not flag:
        #     result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
        #     if product_obj.description_sale:
        #         result['name'] += '\n'+product_obj.description_sale

        result['name'] = product_obj.categ_id.description
        result['cost_price'] = product_obj.cost_price

        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            ctx = dict(
                context,
                uom=uom or result.get('product_uom'),
                date=date_order,
            )
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, ctx)[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                price = self.pool['account.tax']._fix_tax_included_price(cr, uid, price, taxes, result['tax_id'])
                result.update({'price_unit': price})
                if context.get('uom_qty_change', False):
                    values = {'price_unit': price}
                    if result.get('product_uos_qty'):
                        values['product_uos_qty'] = result['product_uos_qty']
                    return {'value': values, 'domain': {}, 'warning': False}
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}


    # @api.v7
    # def _calc_line_base_price(self, cr, uid, line, context=None):
    #     return line.price_unit * (1 - (line.line_discount or 0.0) / 100.0)


    @api.one
    @api.depends('price_unit', 'product_uom_qty')
    def _amount_line(self):
        self.price_subtotal = (self.price_unit*self.product_uom_qty)

    @api.one
    @api.depends('price_subtotal')
    def _compute_discount_subtotal(self):
        self.discount_subtotal = self.price_subtotal*(self.line_discount/100.0)

    @api.one
    @api.depends('price_unit', 'product_uom_qty','purchase_price','discount_subtotal')
    def _compute_margin_line(self):
        #self.price_subtotal = (self.price_unit * self.product_uom_qty)
        self.margin_line = ((self.price_unit-self.purchase_price)*self.product_uom_qty)-self.discount_subtotal
        #self.reel_margin_line = ((self.price_unit-self.product_id.product_tmpl_id.cost_price)*self.product_uom_qty)-self.discount_subtotal
        self.reel_margin_line = ((self.price_unit-self.product_id.cost_price) * self.product_uom_qty) - self.discount_subtotal
        #self.discount_subtotal = self.price_subtotal * (self.line_discount / 100)
        # if (self.discount_subtotal/self.product_uom_qty) > self.purchase_price:
        #     raise except_orm('Attention', 'Le montant de la remise est superieur du prix de revient du produit %s' % (self.product_id.name))

    @api.onchange('line_discount','product_uom_qty')
    def _onchange_line_discount(self):
        if self.line_discount != 0 :
            self.discount_subtotal = self.price_subtotal*(self.line_discount/100)
            #global_discount = global_discount+self.discount_subtotal
            #self.order_id.write({'amount_discount_ongoing': 0})
            #self._cr.execute('update sale_order set amount_discount_ongoing=%s',(0,))
            if self.discount_subtotal > self.purchase_price*self.product_uom_qty :
                raise except_orm('Attention','Le montant de la remise est superieur du prix de revient du produit %s' % (self.product_id.name))

class sale_order_situation(models.Model):

    _name = 'sale.order.situation'

    product_id = fields.Many2one('product.product', string='Article')
    qty_ordered = fields.Float('Quantité Commandé', default=0)
    qty_canceled = fields.Float('Quantité Annulée', default=0)
    qty_shipped = fields.Float('Quantité Livrée', default=0)
    qty_remaining_deliver = fields.Float('Quantité Restante à livrer', compute='_compute_qty',store=True)
    sale_order_id = fields.Many2one('sale.order', string='Bon de Commande')

    @api.one
    @api.depends('qty_ordered','qty_canceled','qty_shipped')
    def _compute_qty(self):
        # cancellations = self.env['stock.cancellation'].search([('sale_order_id','=',self.sale_order_id.id),('state','=','validated')])
        # qty = 0
        # qty_removal = 0
        # if cancellations :
        #     for cancellation in cancellations :
        #         cancellation_line = self.env['stock.cancellation.line'].search([('cancellation_id', '=', cancellation.id),('product_id', '=', self.product_id.id)])
        #         qty = qty + cancellation_line.product_qty
        # self.qty_canceled = qty
        # print "self.sale_order_id.id",self.sale_order_id.id
        # removals = self.env['stock.removal'].search([('sale_order_id', '=', self.sale_order_id.id), ('state', '=', 'done')])
        # for removal in removals:
        #     removal_line = self.env['stock.move'].search([('removal_id', '=', removal.id), ('product_id', '=', self.product_id.id)])
        #     qty_removal = qty_removal + removal_line.product_uom_qty
        # self.qty_shipped = qty_removal
        self.qty_remaining_deliver = (self.qty_ordered-(self.qty_canceled+self.qty_shipped))

class sale_carrier(models.Model):

    _name = 'sale.carrier'

    name = fields.Char('Société')
    tel = fields.Char('Tél Société')
    driver = fields.Char('Chauffeur')
    driver_tel = fields.Char('Tél de Chauffeur')

class stock_removal(models.Model):

    _name = "stock.removal"
    _inherit = ['mail.thread']
    _description = "Removal List"
    _order = "delivery_date desc, date asc, id desc"

    name =  fields.Char('Référence',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},default='/')
    origin = fields.Char('Document d\'origine',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},help="Reference of the document")
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validé'),('approuved', 'Approuvé'),('in_preparation', 'En préparation'),('end_preparation', 'Préparation Terminée'),('ready_to_deliver', 'Prêt à livrer'),('done', 'Livré')],'Statut',required=True,default='draft')
    state_preparation = fields.Selection([('draft', 'En Préparation'),('end_preparation', 'Préparation Terminée')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    delivery_date = fields.Datetime('Date de livraison',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},required=True)
    move_lines = fields.One2many('stock.move', 'removal_id', 'Articles',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    partner_id = fields.Many2one('res.partner', 'Client',states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one('res.company', 'Société', required=False,states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda self: self.env.user.company_id.id)
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True,states={'done': [('readonly', True)]},default=12)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True, states={'done': [('readonly', True)]})
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM',default=lambda self: self.env.user)
    type = fields.Selection([('removal', 'Bon d\'enlévement'), ('preparation', 'Bon de préparation')],'Type de l\'opération',required=True)
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')
    last_removal = fields.Boolean('Est Dernier ?')
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    amount_untaxed = fields.Float('Montant HT', compute='_compute_amount', readonly=True,store=True)
    whith_reservation = fields.Boolean('Avec Réservation ?',default=False)
    #amount_tax = fields.Float('Taxes', compute='_compute_amount', readonly=True,store=True)
    #amount_total = fields.Float('Montant TTC', compute='_compute_amount', readonly=True,store=True)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id and self.user_id.default_section_id:
            self.section_id = self.user_id.default_section_id.id

    @api.onchange('section_id','whith_reservation')
    def _onchange_section_id(self):
        if self.section_id:
            if self.whith_reservation :
                self.location_dest_id = self.section_id.location_id.id
            else :
                self.location_dest_id = 9

    @api.one
    @api.depends('sale_order_id','move_lines.sale_order_line_id')
    def _compute_amount(self):
        if self.sale_order_id :
            #amount_untaxed = sum(line.product_id.lst_price*line.product_uom_qty for line in self.move_lines)
            amount_untaxed = sum(line.price_unit_sale*line.product_uom_qty for line in self.move_lines)
            self.amount_untaxed = amount_untaxed-(self.sale_order_id.amount_discount_ongoing*amount_untaxed/100)
        #self.amount_tax = sum(self._amount_line_tax(line) for line in self.move_lines)
        #self.amount_total = self.amount_untaxed

    @api.model
    def create(self, values):
        if values.get('sale_order_id') :
            removals = self.search([('sale_order_id', '=', values.get('sale_order_id'))])
            if values.get('move_lines') :
                for move in values.get('move_lines') :
                    moves = self.env['stock.move'].search([('removal_id', 'in', removals._ids),('sale_order_line_id','=',move[2]['sale_order_line_id'])])
                    sum_qty = sum(line.product_uom_qty for line in moves)
                    sale_order_line = self.env['sale.order.line'].search([('id', '=',move[2]['sale_order_line_id'])])
                    if sum_qty + move[2]['product_uom_qty'] > sale_order_line.product_uom_qty:
                        raise except_orm('Attention', 'Le quatité à planifier est superieur à la quantité vendue %s' % (sale_order_line.product_uom_qty))
                    else :
                        sale_order_line.write({'qty_available': sum_qty + move[2]['product_uom_qty']})
                    move[2]['date_expected'] = values.get('delivery_date')
        else :
            if values.get('move_lines') :
                for move in values.get('move_lines') :
                    move[2]['date_expected'] = values.get('delivery_date')
                    move[2]['invoice_state'] = '2binvoiced'
        return super(stock_removal, self).create(values)

    @api.multi
    def write(self, values):
        if self.sale_order_id :
            if values.get('delivery_date'):
                if values.get('move_lines'):
                    for move in values.get('move_lines'):
                        if move[2] and move[0] != 2:
                            move_line = self.env['stock.move'].browse(move[1])
                            moves = self.env['stock.move'].search([('removal_id', '=',self.id),('sale_order_line_id','=',move_line.sale_order_line_id.id),('id','=',move_line.id)])
                            if moves :
                                sum_qty = sum(line.product_uom_qty for line in moves)
                                if sum_qty+move[2]['product_uom_qty'] > move_line.sale_order_line_id.product_uom_qty :
                                    raise except_orm('Attention','Le quatité à planifier est superieur à la quantité vendue %s' %(move_line.sale_order_line_id.product_uom_qty))
                                else :
                                    sale_order_line.write({'qty_available': sum_qty + move[2]['product_uom_qty']})
                            move[2]['delivery_date'] = values.get('delivery_date')
                else :
                    for move in self.move_lines:
                        move.write({'date_expected': values.get('delivery_date')})
        return super(stock_removal, self).write(values)

    @api.multi
    def action_validated(self):
        self.state = 'validated'
        removals = self.search([('sale_order_id','=',self.sale_order_id.id),('id','!=',self.id),('state','!=','draft')])
        if len(removals) == 0 :
            self.name = self.sale_order_id.name+'BE001'
        elif 1 <= len(removals) < 9 :
            self.name = self.sale_order_id.name+'BE00'+str(len(removals)+1)
        elif 9 <= len(removals) < 99 :
            self.name = self.sale_order_id.name+'BE0'+str(len(removals)+1)
        else :
            self.name = self.sale_order_id.name+'BE'+ str(len(removals)+1)
        record_reservation = {
                'origin': self.name,
                'section_id': self.section_id.id,
                'partner_id': self.partner_id.id,
                'sale_order_id': self.sale_order_id.id,
                'delivery_date':self.delivery_date,
                'user_id': self.user_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'company_id': self.company_id.id,
                'removal_id':self.id
        }

        reservation = self.env['stock.normal.reservation'].create(record_reservation)

        for move in self.move_lines :
            if move.product_id.qty_available < move.product_uom_qty :
                raise except_orm(_('Attention !!'), _("Le stock n'est pas disponible,Merci de la planifier soit sur arrivage ou bien sur un achat"))
            reservation_line = {
                'sale_order_line_id':move.sale_order_line_id.id,
                'product_id' : move.product_id.id,
                'name' : move.name,
                'product_qty' : move.product_uom_qty,
                'product_uom_id': move.product_uom.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'delivery_date': self.delivery_date,
                'reservation_id':reservation.id,
                'partner_id':self.partner_id.id,
                'section_id': self.section_id.id,
                'user_id':self.user_id.id,
                'removal_id':self.id,
                'move_id':move.id
            }
            self.env['stock.normal.reservation.line'].create(reservation_line)
            move.action_confirm()
        return True

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
        normal_reservation = self.env['stock.normal.reservation'].search([('removal_id', '=', self.id)])
        shipping_reservation = self.env['stock.shipping.reservation'].search([('removal_id', '=', self.id)])
        purchase_reservation = self.env['stock.purchase.reservation'].search([('removal_id', '=', self.id)])
        if normal_reservation :
            normal_reservation.action_cancel()
        if shipping_reservation :
            shipping_reservation.action_cancel()
        if purchase_reservation :
            purchase_reservation.action_cancel()
            purchase_request = self.env['purchase.request'].search([('removal_id', '=', self.id)])
            purchase_request.button_rejected()
        for move in self.move_lines :
            move.action_cancel()
        return True

    @api.multi
    def action_create_preparation(self):
        self.state = 'in_preparation'
        self.state_preparation = 'draft'
        record_preparation = {
                'type': 'preparation',
                'origin': self.name,
                'section_id': self.section_id.id,
                'partner_id': self.partner_id.id,
                'sale_order_id': self.sale_order_id.id,
                'delivery_date':self.delivery_date,
                'user_id': self.user_id.id,
                'location_id': self.location_dest_id.id,
                'location_dest_id': self.sale_order_id.warehouse_id.preparation_location_id.id,
                'company_id': self.company_id.id,
                'removal_id':self.id
        }
        preparation_order = self.create(record_preparation)
        for move in self.move_lines :
            move.action_assign()
            move.action_done()
            if move.move_src_id :
                if move.move_src_id.state != 'done' :
                    #move.write({'state':'waiting'})
                    raise except_orm(_('Attention !!'), _("Le stock n'est pas disponible"))
            if move.state != 'done' :
                raise except_orm(_('Attention !!'),_("Le stock n'est pas disponible"))
            preparation_order_line = {
                'sale_order_line_id':move.sale_order_line_id.id,
                'product_id' : move.product_id.id,
                'name' : move.name,
                'product_uom_qty' : move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'location_id' : preparation_order.location_id.id,
                'location_dest_id': preparation_order.location_dest_id.id,
                'date_expected': self.delivery_date,
                'removal_id':preparation_order.id
                #'opp_id':self.opp_id.id
            }
            self.env['stock.move'].create(preparation_order_line)
        return True

    @api.multi
    def action_create_picking_out(self):
        if self.partner_id.blocking_ok and not self.env.user.force_picking_out_ok:
            raise except_orm(_('Blockage!'),_('Ce client est bloqué,vous pouvez pas générer des bons de livraison.'))
        self.state = 'ready_to_deliver'
        # self.state_preparation = 'end_preparation'
        # self.removal_id.write({'state':'ready_to_deliver'})
        picking_type = self.env['stock.picking.type'].browse(2)
        picking_move = {}
        if self.whith_reservation:
            for move in self.move_lines:
                if move.move_src_id:
                    if move.move_src_id.state != 'done':
                        # move.write({'state':'waiting'})
                        raise except_orm(_('Attention !!'), _("Le stock n'est pas disponible"))
                if move.state != 'done':
                    raise except_orm(_('Attention !!'), _("Le stock n'est pas disponible"))
                picking_move = {
                    'sale_order_line_id': move.sale_order_line_id.id,
                    'sale_order_id': self.sale_order_id.id,
                    'picking_type_id': picking_type.id,
                    'product_id': move.product_id.id,
                    'name': move.name,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': self.sale_order_id.warehouse_id.delivery_location_id.id,
                    'date_expected': self.delivery_date,
                    #'picking_id':picking.id,
                    'preparation_order_id':self.id,
                    'origin': self.name,
                    'product_uos_qty': move.product_uom_qty,
                    'warehouse_id':1,
                    'user_id':self._uid,
                    'section_id':self.section_id.id,
                    'customer_id':self.partner_id.id,
                    'price_unit_sale':move.sale_order_line_id.price_unit,
                    'price_unit':move.product_id.cost_price,
                    'invoice_state': '2binvoiced'
                    #'removal_id': self.id
                }
                if self.opp_id:
                    picking_move['opp_id'] = self.opp_id.id
                # self.env['stock.move'].create(picking_move)
                # move.action_confirm()
                # move.action_assign()
                # move.action_done()
        else :
            for move in self.move_lines:
                picking_move = {
                    'picking_type_id': picking_type.id,
                    'name': move.name,
                    #'picking_id':picking.id,
                    'origin': self.name,
                    'product_uos_qty': move.product_uom_qty,
                    'warehouse_id':1,
                    'user_id':self._uid,
                    'section_id':self.section_id.id,
                    'customer_id':self.partner_id.id,
                    'price_unit_sale':move.sale_order_line_id.price_unit,
                    'price_unit':move.product_id.cost_price
                }
                # move.write(picking_move)
                # move.action_confirm()
                # move.action_assign()
                #move.action_done()
        record_picking = {
            'picking_type_id': picking_type.id,
            'origin': self.name,
            'removal_id': self.id,
            'name':self.env['ir.sequence'].next_by_id(picking_type.sequence_id.id),
            'move_type':'direct',
            'invoice_state':'2binvoiced',
            'recompute_pack_op':False,
            'min_date': self.delivery_date,
            'company_id': self.company_id.id,
            'move_lines':[(0, 0,picking_move)],
            'state':'draft',
            'location_id': self.location_id.id,
            'location_dest_id':9,
        }
        if self.partner_id :
            record_picking['partner_id'] = self.partner_id.id
        if self.opp_id:
            record_picking['opp_id'] = self.opp_id.id
        if self.sale_order_id:
            record_picking['order_id'] = self.sale_order_id.id
        picking = self.env['stock.picking'].create(record_picking)
        picking.action_confirm()
        picking.action_assign()
        #picking.write({'invoice_state':'2binvoiced'})
        return True


class stock_move(models.Model):

    _inherit = 'stock.move'

    removal_id = fields.Many2one('stock.removal',string='Bon d\'Enlévement')
    sale_order_id = fields.Many2one('sale.order', string='Bon de Commande')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Ligne Bon de Commande')
    preparation_order_id = fields.Many2one('stock.removal', string='Bon de préparation')
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    purchase_request_id = fields.Many2one('purchase.request', string='Demande Achat')
    purchase_request_line_id = fields.Many2one('purchase.request.line', string='Ligne Demande Achat')
    move_src_id = fields.Many2one('stock.move', string='Mouvement')
    supplier_id = fields.Many2one(related='picking_id.partner_id', comodel_name='res.partner',string='Fournisseur', store=True, readonly=True)
    customer_id = fields.Many2one('res.partner', string='Client')

    @api.v7
    def get_price_unit(self, cr, uid, move, context=None):
        """ Returns the unit price to store on the quant """
        return move.product_id.cost_price



    # @api.onchange('product_id','location_id','location_dest_id','partner_id')
    # def onchange_product_id(self):
    #     if self.product_id:
    #         self.product_uom = self.product_id.uom_id.id
    #         self.name = self.product_id.name
    #         self.product_uos = self.product_id.uos_id.id or False
    #         self.invoice_state = '2binvoiced'
    #         self.location_id =  12
    #         self.location_dest_id = 9
    #         self.date_expected = datetime.today()


class stock_removal_move(models.Model):
    _name = 'stock.removal.move'
    _auto = False
    _order = 'delivery_date asc'


    removal_id = fields.Many2one('stock.removal',string='Bon d\'Enlévement')
    sale_order_id = fields.Many2one('sale.order', string='Bon de Commande')
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    partner_id = fields.Many2one('res.partner', string='Client')
    product_id = fields.Many2one('product.product', string='Article')
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validé'),('approuved', 'Approuvé'),('in_preparation', 'En préparation'),('end_preparation', 'Préparation Terminée'),('ready_to_deliver', 'Prêt à livrer')],'Statut',required=True,default='draft')
    delivery_date = fields.Datetime('Date de livraison')
    product_uom_qty = fields.Float('Quantité', degits=2)


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_removal_move')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_removal_move AS (
              SELECT
                removal.id as id,
                move.removal_id,
                removal.sale_order_id,
                removal.section_id,
                removal.user_id,
                removal.opp_id,
                removal.partner_id,
                move.product_id,
                removal.state,
                removal.delivery_date,
                move.product_uom_qty
                FROM
                    stock_removal removal,stock_move move
                WHERE removal.id=move.removal_id AND removal.state not in ('cancel', 'done')
                GROUP BY removal.id,move.removal_id,removal.sale_order_id,removal.section_id,removal.user_id,removal.opp_id,removal.partner_id,move.product_id,removal.state,removal.delivery_date,move.product_uom_qty
            )""")


class stock_warehouse(models.Model):

    _inherit = 'stock.warehouse'

    location_id = fields.Many2one('stock.location',string='Emplacement source par défaut',domain=[('usage','=','internal')])
    preparation_location_id = fields.Many2one('stock.location', string='Emplacement de préparation par défaut',domain=[('usage', '=', 'internal')])
    delivery_location_id = fields.Many2one('stock.location', string='Emplacement de sortie par défaut',domain=[('usage', '=', 'customer')])


class stock_normal_reservation(models.Model):

    _name = "stock.normal.reservation"
    _inherit = ['mail.thread']
    _description = "Reservation List"
    _order = "delivery_date desc, date asc, id desc"

    name =  fields.Char('Référence',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default='/')
    origin = fields.Char('Document d\'origine',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},help="Reference of the document")
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validée')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    delivery_date = fields.Datetime('Date de livraison',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},required=True)
    reservation_lines = fields.One2many('stock.normal.reservation.line', 'reservation_id', 'Articles',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    partner_id = fields.Many2one('res.partner', 'Client',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one('res.company', 'Société', required=False,states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True,states={'validated': [('readonly', True)]})
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True, states={'validated': [('readonly', True)]})
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')

    @api.multi
    def action_validated(self):
        self.state = 'validated'
        self.removal_id.write({'state':'approuved'})
        for line in self.reservation_lines :
            line.move_id.action_assign()
            line.move_id.action_done()
        return True

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
        return True



class stock_normal_reservation_line(models.Model):

    _name = "stock.normal.reservation.line"
    _inherit = ['mail.thread']
    _description = "Resrevation List"

    name =  fields.Char('Description')
    product_id = fields.Many2one('product.product', string='Article')
    product_qty= fields.Float('Quantité', degits=2, default=0)
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    move_id = fields.Many2one('stock.move', string='Mouvement')
    delivery_date = fields.Datetime('Date de livraison')
    partner_id = fields.Many2one('res.partner', 'Client')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True)
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')
    reservation_id = fields.Many2one('stock.normal.reservation', string='Réservation')

class stock_shipping_reservation(models.Model):

    _name = "stock.shipping.reservation"
    _inherit = ['mail.thread']
    _description = "Reservation List"
    _order = "delivery_date desc, date asc, id desc"

    name =  fields.Char('Référence',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default='/')
    origin = fields.Char('Document d\'origine',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},help="Reference of the document")
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validée')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    delivery_date = fields.Datetime('Date de livraison',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},required=True)
    reservation_lines = fields.One2many('stock.shipping.reservation.line', 'reservation_id', 'Articles',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    partner_id = fields.Many2one('res.partner', 'Client',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one('res.company', 'Société', required=False,states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True,states={'validated': [('readonly', True)]})
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True, states={'validated': [('readonly', True)]})
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')

    @api.multi
    def action_validated(self):
        self.state = 'validated'
        self.removal_id.write({'state': 'approuved'})
        for line in self.reservation_lines :
            line.move_id.write({'move_dest_id': line.move_dest_id.id})
            line.move_dest_id.write({'move_src_id': line.move_id.id,'state':'waiting'})
            # line.move_dest_id.action_assign()
            # line.move_dest_id.action_done()
        return True

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
        return True


class stock_shipping_reservation_line(models.Model):

    _name = "stock.shipping.reservation.line"
    _inherit = ['mail.thread']
    _description = "Resrevation List"

    name =  fields.Char('Description')
    product_id = fields.Many2one('product.product', string='Article')
    product_qty= fields.Float('Quantité', degits=2, default=0)
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    move_id = fields.Many2one('stock.move', string='Mouvement Source')
    move_dest_id = fields.Many2one('stock.move', string='Mouvement Destination')
    delivery_date = fields.Datetime('Date de livraison')
    partner_id = fields.Many2one('res.partner', 'Client')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True)
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')
    reservation_id = fields.Many2one('stock.shipping.reservation', string='Réservation')

class stock_picking(models.Model):

    _inherit = 'stock.picking'

    removal_id = fields.Many2one('stock.removal', string='Bon de préparation')
    opp_id = fields.Many2one('crm.lead', string='Opportunité', domain=[('type', '=', 'opportunity')])
    order_id = fields.Many2one('sale.order', string='Bon de commande')

    @api.multi
    def do_transfer(self) :
        res = super(stock_picking, self).do_transfer()
        picking_id = self._context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        shipping_reservation_line_obj = self.env['stock.shipping.reservation.line']
        purchase_reservation_line_obj = self.env['stock.purchase.reservation.line']

        if picking.picking_type_id.id == 1 :
            if picking.import_id :
                picking.import_id.write({'entry_date':picking.date_done})
            for move in picking.move_lines :
                shipping_reservation_lines = shipping_reservation_line_obj.search([('move_id', '=', move.id)])
                if shipping_reservation_lines :
                    for line in shipping_reservation_lines :
                        line.move_dest_id.action_assign()
                        line.move_dest_id.action_done()
                purchase_reservation_lines = purchase_reservation_line_obj.search([('move_id', '=', move.id)])
                if purchase_reservation_lines:
                    for line in purchase_reservation_lines:
                        line.move_dest_id.action_assign()
                        line.move_dest_id.action_done()
                                # if line.reservation_id.state == 'validated' :
                        #     line.move_dest_id.action_assign()
                        #     line.move_dest_id.action_done()
                        #     line.reservation_id.removal_id.write({'state':'approuved'})
        if picking.picking_type_id.id == 2 :
            if self.partner_id.blocking_ok and not self.env.user.force_picking_out_ok:
                raise except_orm(_('Blockage!'),_('Ce client est bloqué,vous pouvez pas faire cette opération.'))

            amount = 0
            if picking.removal_id.sale_order_id :
                picking.write({'order_id':picking.removal_id.sale_order_id.id})
                for move in picking.move_lines :
                    situation = self.env['sale.order.situation'].search([('sale_order_id','=',picking.removal_id.sale_order_id.id),('product_id','=',move.product_id.id)])
                    situation.write({'qty_shipped':situation.qty_shipped+move.product_uom_qty})
            if picking.removal_id.opp_id:
                picking.write({'opp_id':picking.removal_id.opp_id.id})
            if picking.removal_id :
                picking.removal_id.write({'state':'done'})
                if picking.removal_id.sale_order_id :
                    #amount = sum(line.sale_order_line_id.price_unit*(1-(line.sale_order_line_id.line_discount / 100))*line.product_uom_qty for line in picking.move_lines)
                    amount = sum(line.price_unit_sale * line.product_uom_qty for line in picking.move_lines)
                    amount = amount-(picking.removal_id.sale_order_id.amount_discount_ongoing*amount/100)
                else :
                    amount = sum(line.price_unit_sale*line.product_uom_qty for line in picking.move_lines)
                available_credit = self.check_limit(picking.partner_id)
                if (amount > available_credit) and not self.env.user.force_picking_out_ok :
                    raise except_orm(_('Deppassement du plafond défini !!'),_("Le montant de la livraison dépasse l'encours %s du client %s") % (picking.partner_id.credit_limit,picking.partner_id.name,))
                if picking.removal_id.last_removal and picking.removal_id.sale_order_id :
                    # for line in self.env['sale.order'].browse(picking.removal_id.removal_id.sale_order_id.id).order_line :
                    #     moves = self.env['stock.move'].search([('sale_order_line_id','=',line.id),('removal_id','=',picking.removal_id.removal_id.id)])
                    #     if moves :
                    #         qty = sum(move.product_uom_qty for move in moves)
                    #         line.write({'product_uom_qty':qty,'state':'done'})
                    picking.removal_id.sale_order_id.write({'state':'done','shipped':True})
        return res

    @api.multi
    def check_limit(self,partner):

        #domain = [('order_id.partner_id', '=', partner.id),('invoiced', '=', False),('order_id.state', 'not in', ['draft', 'cancel', 'sent'])]
        #order_lines = self.env['sale.order.line'].search(domain)
        #none_invoiced_amount = sum([x.price_subtotal for x in order_lines])

        # We sum from all the invoices that are in draft the total amount
        domain = [('partner_id', '=', partner.id), ('state', '=', 'draft')]
        draft_invoices = self.env['account.invoice'].search(domain)
        draft_invoices_amount = sum([x.amount_untaxed for x in draft_invoices])

        available_credit = partner.credit_limit - (partner.credit + draft_invoices_amount) # a rajouter les factures qui ne sont pas encaissé

        return available_credit

# class stock_move(models.Model):
#
#     _inherit = "stock.move"
#
#     supplier_id = fields.Many2one(related='picking_id.partner_id', comodel_name='res.partner',string='Fournisseur', store=True, readonly=True)
#     customer_id = fields.Many2one('res.partner', string='Client')



class stock_purchase_reservation(models.Model):

    _name = "stock.purchase.reservation"
    _inherit = ['mail.thread']
    _description = "Reservation List"
    _order = "delivery_date desc, date asc, id desc"

    name =  fields.Char('Référence',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default='/')
    origin = fields.Char('Document d\'origine',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},help="Reference of the document")
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validée')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    delivery_date = fields.Datetime('Date de livraison',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},required=True)
    reservation_lines = fields.One2many('stock.purchase.reservation.line', 'reservation_id', 'Articles',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    partner_id = fields.Many2one('res.partner', 'Client',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    company_id = fields.Many2one('res.company', 'Société', required=False,states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True,states={'validated': [('readonly', True)]})
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True, states={'validated': [('readonly', True)]})
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')

    @api.multi
    def action_validated(self):
        for line in self.reservation_lines :
            stock_move = self.env['stock.move'].search([('product_id','=',line.product_id.id),('purchase_request_id','=',line.purchase_request_id.id),('purchase_request_line_id','=',line.purchase_request_line_id.id)])
            if stock_move :
                line.write({'move_id':stock_move.id})
                stock_move.write({'move_dest_id':line.move_dest_id.id})
                line.move_dest_id.write({'move_src_id': stock_move.id,'state':'waiting'})
            else :
                raise except_orm('Attention','La demande d\'achat pour l\'article %s pas encore traité ou bien son bon de commande est encours de traitement' % (line.product_id.name))
        self.state = 'validated'
        self.removal_id.write({'state': 'approuved'})
        # for line in self.reservation_lines :
        #     line.move_dest_id.action_assign()
        #     line.move_dest_id.action_done()
        return True

    @api.multi
    def action_cancel(self):
        self.state = 'cancel'
        return True


class stock_purchase_reservation_line(models.Model):

    _name = "stock.purchase.reservation.line"
    _inherit = ['mail.thread']
    _description = "Resrevation List"

    name =  fields.Char('Description')
    product_id = fields.Many2one('product.product', string='Article')
    product_qty= fields.Float('Quantité', degits=2, default=0)
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    move_id = fields.Many2one('stock.move', string='Mouvement Source')
    move_dest_id = fields.Many2one('stock.move', string='Mouvement Destination')
    delivery_date = fields.Datetime('Date de livraison')
    partner_id = fields.Many2one('res.partner', 'Client')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True)
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')
    reservation_id = fields.Many2one('stock.purchase.reservation', string='Réservation')
    purchase_request_id = fields.Many2one('purchase.request', string='Demande Achat')
    purchase_request_line_id = fields.Many2one('purchase.request.line', string='Ligne Demande Achat')


class purchase_order(models.Model):

    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one('purchase.request', string='Demande Achat')

    @api.v7
    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
        product_uom = self.pool.get('product.uom')
        price_unit = order_line.price_unit
        if order_line.taxes_id:
            taxes = self.pool['account.tax'].compute_all(cr, uid, order_line.taxes_id, price_unit, 1.0,
                                                             order_line.product_id, order.partner_id)
            price_unit = taxes['total']
        if order_line.product_uom.id != order_line.product_id.uom_id.id:
            price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
        if order.currency_id.id != order.company_id.currency_id.id:
            #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
            price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
        res = []
        if order.location_id.usage == 'customer':
            name = order_line.product_id.with_context(dict(context or {}, lang=order.dest_address_id.lang)).display_name
        else:
            name = order_line.name or ''
        move_template = {
            'name': name,
            'product_id': order_line.product_id.id,
            'product_uom': order_line.product_uom.id,
            'product_uos': order_line.product_uom.id,
            'date': order.date_order,
            'date_expected': order_line.date_planned,
            'location_id': order.partner_id.property_stock_supplier.id,
            'location_dest_id': order.location_id.id,
            'picking_id': picking_id,
            'partner_id': order.dest_address_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': order_line.id,
            'company_id': order.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': order.picking_type_id.id,
            'group_id': group_id,
            'procurement_id': False,
            'origin': order.name,
            'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id':order.picking_type_id.warehouse_id.id,
            'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
        }
        if order_line.purchase_request_id :
            move_template['purchase_request_id'] = order_line.purchase_request_id.id
        if order_line.purchase_request_line_id:
            move_template['purchase_request_line_id'] = order_line.purchase_request_line_id.id
        diff_quantity = order_line.product_qty
        for procurement in order_line.procurement_ids:
            procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
            tmp = move_template.copy()
            tmp.update({
                'product_uom_qty': min(procurement_qty, diff_quantity),
                'product_uos_qty': min(procurement_qty, diff_quantity),
                'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
                'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
                'procurement_id': procurement.id,
                'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
                'propagate': procurement.rule_id.propagate,
            })
            diff_quantity -= min(procurement_qty, diff_quantity)
            res.append(tmp)
        #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
        #split the future stock move in two because the route followed may be different.
        if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
            move_template['product_uom_qty'] = diff_quantity
            move_template['product_uos_qty'] = diff_quantity
            res.append(move_template)
        return res


class purchase_order_line(models.Model):

    _inherit = 'purchase.order.line'

    purchase_request_id = fields.Many2one('purchase.request', string='Demande Achat')
    purchase_request_line_id = fields.Many2one('purchase.request.line', string='Ligne Demande Achat')


class stock_cancellation(models.Model):

    _name = "stock.cancellation"
    _inherit = ['mail.thread']

    name =  fields.Char('Code',default='/')
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validée')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    validate_date = fields.Datetime('Date de validation')
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    line_ids = fields.One2many('stock.cancellation.line', 'cancellation_id', 'Articles')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=False,states={'validated': [('readonly', True)]})
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=False, states={'validated': [('readonly', True)]})
    section_id = fields.Many2one('crm.case.section', string='BU')
    user_id = fields.Many2one('res.users', string='KAM')
    note = fields.Text('Notes')

    @api.onchange('sale_order_id')
    def onchange_sale_order_id(self):
        if self.sale_order_id:
            self.user_id = self.sale_order_id.user_id.id
            self.section_id = self.sale_order_id.section_id.id
            self.location_id = self.sale_order_id.section_id.location_id.id

    @api.multi
    def action_validated(self):
        cancellations = self.search([('state','=','validated')])
        nbr_cancellation = len(cancellations)
        code = self.sale_order_id.name+str(nbr_cancellation+1)
        self.write({'name':code})
        for line in self.line_ids :
            # if line.removal_id.state == 'draft' :
            #     move = self.env['stock.move'].search([('removal_id','=',line.removal_id.id),('product_id','=',line.product_id.id)])
            #     move.write({'product_uom_qty':move.product_uom_qty-line.product_qty})
            #     situation = self.env['sale.order.situation'].search([('sale_order_id','=',self.sale_order_id.id),('product_id','=',line.product_id.id)])
            #     situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
            if line.removal_id.state == 'validated':
                move = self.env['stock.move'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                move.write({'product_uom_qty': move.product_uom_qty - line.product_qty})
                # situation = self.env['sale.order.situation'].search([('sale_order_id','=',self.sale_order_id.id),('product_id','=',line.product_id.id)])
                # situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
                line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_normal_reservation :
                    if line_normal_reservation.reservation_id.state == 'draft' :
                        line_normal_reservation.write({'product_qty': move.product_qty})
                line_shipping_reservation = self.env['stock.shipping.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_shipping_reservation:
                    if line_shipping_reservation.reservation_id.state == 'draft':
                        line_shipping_reservation.write({'product_qty': move.product_qty})
                line_purchase_reservation = self.env['stock.purchase.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_purchase_reservation:
                    if line_purchase_reservation.reservation_id.state == 'draft':
                        line_purchase_reservation.write({'product_qty': move.product_qty})
                order_line = self.env['sale.order.line'].search([('order_id', '=', self.sale_order_id.id), ('product_id', '=', line.product_id.id)])
                order_line.write({'qty_available':order_line.qty_available+line.product_qty})
                situation = self.env['sale.order.situation'].search([('sale_order_id','=',self.sale_order_id.id),('product_id','=',line.product_id.id)])
                situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
            if line.removal_id.state == 'approuved':
                move = self.env['stock.move'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                move.write({'product_uom_qty': move.product_uom_qty - line.product_qty})
                line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_normal_reservation:
                    record_move = {
                        'product_id':line.product_id.id,
                        'product_uom_qty':line.product_qty,
                        'product_uom': line.product_id.uom_id.id,
                        'name': line.product_id.name,
                        'invoice_state':'none',
                        'location_id': line.cancellation_id.location_id.id,
                        'location_dest_id': line.cancellation_id.location_dest_id.id,
                        'date_expected': datetime.today()
                    }
                    move = self.env['stock.move'].create(record_move)
                    move.action_confirm()
                    move.action_assign()
                    move.action_done()

                line_shipping_reservation = self.env['stock.shipping.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_shipping_reservation:
                    # if line_shipping_reservation.move_id.state != 'done':
                    #     line_shipping_reservation.move_dest_id.write({'product_uom_qty': line_shipping_reservation.move_dest_id.product_uom_qty - line.product_qty})
                    # else :
                    if line_shipping_reservation.move_id.state == 'done':
                        record_move = {
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_id.uom_id.id,
                            'name': line.product_id.name,
                            'invoice_state': 'none',
                            'location_id': line.cancellation_id.location_id.id,
                            'location_dest_id': line.cancellation_id.location_dest_id.id,
                            'date_expected': datetime.today()
                        }
                        move = self.env['stock.move'].create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()

                line_purchase_reservation = self.env['stock.purchase.reservation.line'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                if line_purchase_reservation:
                    # if line_purchase_reservation.move_id.state != 'done':
                    #     line_purchase_reservation.move_dest_id.write({'product_uom_qty': line_purchase_reservation.move_dest_id.product_uom_qty - line.product_qty})
                    # else :
                    if line_purchase_reservation.move_id.state == 'done':
                        record_move = {
                            'product_id': line.product_id.id,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_id.uom_id.id,
                            'name': line.product_id.name,
                            'invoice_state': 'none',
                            'location_id': line.cancellation_id.location_id.id,
                            'location_dest_id': line.cancellation_id.location_dest_id.id,
                            'date_expected': datetime.today()
                        }
                        move = self.env['stock.move'].create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                order_line = self.env['sale.order.line'].search([('order_id', '=', self.sale_order_id.id), ('product_id', '=', line.product_id.id)])
                order_line.write({'qty_available':order_line.qty_available+line.product_qty})
                situation = self.env['sale.order.situation'].search([('sale_order_id','=',self.sale_order_id.id),('product_id','=',line.product_id.id)])
                situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
            if line.removal_id.state == 'ready_to_deliver' :
                move = self.env['stock.move'].search([('removal_id', '=', line.removal_id.id), ('product_id', '=', line.product_id.id)])
                move.write({'product_uom_qty': move.product_uom_qty - line.product_qty})
                record_move = {
                    'product_id':line.product_id.id,
                    'product_uom_qty':line.product_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'name': line.product_id.name,
                    'invoice_state':'none',
                    'location_id': line.cancellation_id.location_id.id,
                    'location_dest_id': line.cancellation_id.location_dest_id.id,
                    'date_expected': datetime.today()
                }
                move = self.env['stock.move'].create(record_move)
                move.action_confirm()
                move.action_assign()
                move.action_done()
                picking = self.env['stock.picking'].search([('removal_id', '=', line.removal_id.id)])
                move_picking = self.env['stock.move'].search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                move_picking.write({'product_uom_qty': move_picking.product_uom_qty - line.product_qty})
                picking.do_unreserve()
                picking.action_confirm()
                picking.action_assign()
                order_line = self.env['sale.order.line'].search([('order_id', '=', self.sale_order_id.id), ('product_id', '=', line.product_id.id)])
                order_line.write({'qty_available':order_line.qty_available+line.product_qty})
                situation = self.env['sale.order.situation'].search([('sale_order_id','=',self.sale_order_id.id),('product_id','=',line.product_id.id)])
                situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
        self.write({'state':'validated'})
        return True



class stock_cancellation_line(models.Model):

    _name = "stock.cancellation.line"
    _inherit = ['mail.thread']

    product_id = fields.Many2one('product.product', string='Article',required=True)
    product_qty= fields.Float('Quantité', degits=2, default=0)
    removal_id = fields.Many2one('stock.removal', string='Enlévement',required=True)
    cancellation_id = fields.Many2one('stock.cancellation', string='Annulation')

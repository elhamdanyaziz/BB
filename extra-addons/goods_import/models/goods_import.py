
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
from openerp import SUPERUSER_ID, workflow
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar



class goods_import(models.Model):

    _name = 'goods.import'

    name =  fields.Char('N° entrée',default='/')
    note = fields.Text('Notes')
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé')],'Statut',required=True,default='draft')
    date = fields.Datetime('Date de création',states={'validated': [('readonly', True)]},default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    entry_date = fields.Datetime('Date d’entrée',states={'validated': [('readonly', True)]},required=True,default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    partner_id = fields.Many2one('res.partner', 'Fournisseur',states={'validated': [('readonly', True)]},domain=[('supplier','=',True)])
    import_engagement = fields.Char('N° Engagement d’Importation')
    export_declaration = fields.Char('N° DUM')
    date_export_declaration = fields.Datetime('Date DUM',states={'validated': [('readonly', True)]},required=True)
    currency_rate = fields.Float('Cours de devise de la DUM',default=1,digits=dp.get_precision('Currency Rate'))
    currency_id = fields.Many2one('res.currency', string='Devise',default=113)
    certificate_marine_insurance_number = fields.Char('Numéro certificat d’assurance maritime')
    company_id = fields.Many2one('res.company', string='Société', required=False,states={'validated': [('readonly', True)]},default=1)
    user_id = fields.Many2one('res.users', string='Responsable',default=lambda self: self.env.user)
    purchase_ids = fields.One2many('purchase.order', 'import_id', 'Achats',states={'validated': [('readonly', True)]})
    picking_ids = fields.One2many('stock.picking', 'import_id', 'Achats', states={'validated': [('readonly', True)]},domain=[('picking_type_id','=',1)])
    invoice_ids = fields.One2many('account.invoice', 'import_id', 'Factures Fournisseur', states={'validated': [('readonly', True)]},domain=[('type','=','in_invoice')])
    import_amount = fields.Float('Valeur d\'importation', compute='_compute_amount', readonly=True,store=True)
    amount_import_charges = fields.Float('Charges sur l’importation', compute='_compute_amount', readonly=True, store=True)
    amount_customs_charges = fields.Float('Charges douanière', compute='_compute_amount', readonly=True,store=True)
    amount_total = fields.Float('Total do dossier', compute='_compute_amount', readonly=True,store=True)
    import_coef = fields.Float('coefficient d\'importation', readonly=True)
    year = fields.Char(string='Année', default=lambda self: datetime.today().year, size=4, readonly=True)
    receipt_number = fields.Char('N° de quittance')
    domiciliation_number = fields.Char('N° de domiciliation')
    product_coef_ids = fields.One2many('goods.import.product.coef', 'import_id', 'coefficients d\'Import',states={'validated': [('readonly', True)]})
    amount_bank_charges = fields.Float('Montant Frais Bancaire',default=0)
    amount_import_charges_without_bank_charges = fields.Float('Charges sur l’importation', compute='_compute_amount', readonly=True,store=True)

    @api.one
    @api.depends('invoice_ids.amount_untaxed','currency_rate','amount_bank_charges')
    def _compute_amount(self):
        self.import_amount = 0
        self.amount_import_charges = 0
        for invoice in self.invoice_ids :
            if invoice.type_service == 'purchase_goods' :
                self.import_amount += invoice.amount_untaxed*invoice.currency_rate
            elif invoice.type_service == 'customs' :
                self.amount_customs_charges += invoice.amount_untaxed * invoice.currency_rate
            else :
                self.amount_import_charges_without_bank_charges += invoice.amount_untaxed*invoice.currency_rate
        self.amount_import_charges = self.amount_import_charges_without_bank_charges + self.amount_bank_charges
        self.amount_total = self.import_amount + self.amount_import_charges+self.amount_customs_charges


    # @api.multi
    # def action_validated(self):
    #     self.state = 'validated'
    #     for invoice in self.invoice_ids:
    #         if invoice.type_service == 'purchase_goods':
    #             import_coef = 0
    #             for line in invoice.invoice_line :
    #                 line.product_id.write({'cost_purchase':line.price_unit})
    #                 price_unit = line.price_unit*invoice.currency_rate
    #                 amount_total = price_unit*line.quantity
    #                 prorata_import = amount_total/self.import_amount
    #                 prorata_import_charges = prorata_import*self.amount_import_charges
    #                 product_cost_price = (amount_total+prorata_import_charges)/line.quantity
    #                 import_coef = (amount_total+prorata_import_charges)/(line.price_unit*line.quantity)
    #                 #line.product_id.product_tmpl_id.write({'cost_price':product_cost_price})
    #                 moves = self.env['stock.move'].search([('product_id','=',line.product_id.id),('picking_id','in',self.picking_ids._ids)])
    #                 total_qty = sum(move.product_uom_qty for move in moves)
    #                 if line.product_id.qty_available != 0:
    #                     product_cump_cost = ((line.product_id.qty_available-total_qty)*line.product_id.cost_price+total_qty*product_cost_price)/(line.product_id.qty_available)
    #                 else :
    #                     product_cump_cost = product_cost_price
    #                 line.product_id.write({'cost_price': product_cump_cost})
    #                 for move in moves :
    #                     move.write({'price_unit':product_cump_cost})
    #                     for quant in move.quant_ids :
    #                         quant.write({'cost': product_cump_cost})
    #     self.import_coef = import_coef
    #     return True



    @api.multi
    def _get_sum_line_supplier_invoice_whith_product_customs_coefficient(self,invoice_line):
        sum_line_supplier_invoice_whith_product_customs_coefficient = 0
        for line in invoice_line:
            if line.product_id.customs_coefficient != 0:
                sum_line_supplier_invoice_whith_product_customs_coefficient+=line.quantity*line.price_unit*self.currency_rate
        return sum_line_supplier_invoice_whith_product_customs_coefficient

    @api.multi
    def _get_sum_customs_whith_product_customs_coefficient(self,invoice_line):
        sum_customs_whith_product_customs_coefficient = 0
        for line in invoice_line:
            if line.product_id.customs_coefficient != 0 :
                sum_customs_whith_product_customs_coefficient+=line.quantity*line.price_unit*self.currency_rate*line.product_id.customs_coefficient
        return sum_customs_whith_product_customs_coefficient

    @api.multi
    def action_validated(self):
        self.state = 'validated'
        for invoice in self.invoice_ids:
            if invoice.type_service == 'purchase_goods':
                import_coef = 0
                product_cost_price = 0
                sum_customs = self._get_sum_customs_whith_product_customs_coefficient(invoice.invoice_line)
                sum_line_supplier_invoice = self._get_sum_line_supplier_invoice_whith_product_customs_coefficient(invoice.invoice_line)
                for line in invoice.invoice_line :
                    line.product_id.write({'cost_purchase': line.price_unit})
                    if line.product_id.customs_coefficient != 0:
                        price_unit = line.price_unit*invoice.currency_rate
                        amount_total = price_unit*line.quantity
                        customs_charges = amount_total*line.product_id.customs_coefficient
                        prorata_import = amount_total/self.import_amount
                        prorata_import_charges = prorata_import*self.amount_import_charges
                        product_cost_price = (amount_total+customs_charges+prorata_import_charges)/line.quantity
                        import_coef = product_cost_price/line.price_unit
                        product_cost = line.price_unit*import_coef
                        product_coef_vals = {
                            'product_id':line.product_id.id,
                            'import_coef': import_coef,
                            'product_cost': product_cost,
                            'import_id': self.id,
                        }
                        self.env['goods.import.product.coef'].create(product_coef_vals)
                    else :
                        remaining_customs_charges = self.amount_customs_charges-sum_customs
                        remaining_amount_import = self.import_amount - sum_line_supplier_invoice
                        total_charges = remaining_customs_charges+self.amount_import_charges
                        price_unit = line.price_unit*invoice.currency_rate
                        amount_total = price_unit*line.quantity
                        prorata_import = amount_total/remaining_amount_import
                        prorata_import_charges = prorata_import*total_charges
                        product_cost_price = (amount_total+prorata_import_charges)/line.quantity
                        import_coef = product_cost_price/line.price_unit
                        product_coef_vals = {
                            'product_id':line.product_id.id,
                            'import_coef': import_coef,
                            'import_id': self.id,
                        }
                        self.env['goods.import.product.coef'].create(product_coef_vals)
                    moves = self.env['stock.move'].search([('product_id','=',line.product_id.id),('picking_id','in',self.picking_ids._ids)])
                    total_qty = sum(move.product_uom_qty for move in moves)
                    if line.product_id.qty_available != 0:
                        product_cump_cost = ((line.product_id.qty_available-total_qty)*line.product_id.cost_price+total_qty*product_cost_price)/(line.product_id.qty_available)
                    else :
                        product_cump_cost = product_cost_price
                    line.product_id.write({'cost_price': product_cump_cost})
                    for move in moves :
                        move.write({'price_unit':product_cump_cost})
                        for quant in move.quant_ids :
                            quant.write({'cost': product_cump_cost})
        return True

    @api.model
    def create(self, values):
        current_year = datetime.today().year
        current_month = datetime.today().month
        gois = self.search([('year', '=', current_year)])
        if len(gois) == 0 :
            values['name'] = 'DI-'+str(current_year)+'-'+str(current_month)+'-'+'001'
        elif 1 <= len(gois) < 9 :
            values['name'] = 'DI-'+str(current_year)+'-'+str(current_month)+'-'+'00'+str(len(gois)+1)
        elif 9 <= len(gois) < 99 :
            values['name'] = 'DI-'+str(current_year)+'-'+str(current_month)+'-'+'00'+str(len(gois)+1)
        else :
            values['name'] = 'DI-'+str(current_year)+'-'+ str(current_month)+'-'+str(len(gois)+1)
        return super(goods_import, self).create(values)

class goods_import_product_coef(models.Model):

    _name = 'goods.import.product.coef'

    product_id = fields.Many2one('product.product', 'Article',readonly=True)
    import_coef = fields.Float('coefficient d\'importation', readonly=True)
    product_cost = fields.Float('PR Import', readonly=True)
    import_id = fields.Many2one('goods.import', 'Dossier')

class purchase_order(models.Model):

    _inherit = 'purchase.order'

    import_id = fields.Many2one('goods.import', string='Dossier d\'import')
    settlement_date = fields.Datetime('date de règlement prévisionnelle',states={'validated': [('readonly', True)]},required=False,default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    #customer_id = fields.Many2one('res.partner', 'Client', states={'validated': [('readonly', True)]},domain=[('customer', '=', True)])

    # @api.v7
    # def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
    #     ''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
    #     product_uom = self.pool.get('product.uom')
    #     price_unit = order_line.price_unit
    #     if order_line.taxes_id:
    #         taxes = self.pool['account.tax'].compute_all(cr, uid, order_line.taxes_id, price_unit, 1.0,
    #                                                          order_line.product_id, order.partner_id)
    #         price_unit = taxes['total']
    #     if order_line.product_uom.id != order_line.product_id.uom_id.id:
    #         price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
    #     if order.currency_id.id != order.company_id.currency_id.id:
    #         #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
    #         price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
    #     res = []
    #     if order.location_id.usage == 'customer':
    #         name = order_line.product_id.with_context(dict(context or {}, lang=order.dest_address_id.lang)).display_name
    #     else:
    #         name = order_line.name or ''
    #     move_template = {
    #         'name': name,
    #         'product_id': order_line.product_id.id,
    #         'product_uom': order_line.product_uom.id,
    #         'product_uos': order_line.product_uom.id,
    #         'date': order.date_order,
    #         'date_expected': fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
    #         'location_id': order.partner_id.property_stock_supplier.id,
    #         'location_dest_id': order.location_id.id,
    #         'picking_id': picking_id,
    #         'partner_id': order.dest_address_id.id,
    #         'move_dest_id': False,
    #         'state': 'draft',
    #         'purchase_line_id': order_line.id,
    #         'company_id': order.company_id.id,
    #         'price_unit': price_unit,
    #         'picking_type_id': order.picking_type_id.id,
    #         'group_id': group_id,
    #         'procurement_id': False,
    #         'origin': order.name,
    #         'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
    #         'warehouse_id':order.picking_type_id.warehouse_id.id,
    #         'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
    #     }
    #     if order_line.customer_id:
    #         move_template['customer_id'] = order_line.customer_id.id
    #     if order_line.purchase_request_line_id:
    #         move_template['user_id'] = order_line.purchase_request_line_id.request_id.requested_by.id
    #     if order_line.purchase_request_line_id:
    #         move_template['section_id'] = order_line.purchase_request_line_id.request_id.section_id.id
    #     if order_line.purchase_request_line_id and order_line.purchase_request_line_id.request_id.removal_id and order_line.purchase_request_line_id.request_id.removal_id.opp_id:
    #         move_template['opp_id'] = order_line.purchase_request_line_id.request_id.removal_id.opp_id.id
    #
    #     print "move_template",move_template
    #     diff_quantity = order_line.product_qty
    #     for procurement in order_line.procurement_ids:
    #         procurement_qty = product_uom._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, to_uom_id=order_line.product_uom.id)
    #         tmp = move_template.copy()
    #         tmp.update({
    #             'product_uom_qty': min(procurement_qty, diff_quantity),
    #             'product_uos_qty': min(procurement_qty, diff_quantity),
    #             'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
    #             'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
    #             'procurement_id': procurement.id,
    #             'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
    #             'propagate': procurement.rule_id.propagate,
    #         })
    #         diff_quantity -= min(procurement_qty, diff_quantity)
    #         res.append(tmp)
    #     #if the order line has a bigger quantity than the procurement it was for (manually changed or minimal quantity), then
    #     #split the future stock move in two because the route followed may be different.
    #     if float_compare(diff_quantity, 0.0, precision_rounding=order_line.product_uom.rounding) > 0:
    #         move_template['product_uom_qty'] = diff_quantity
    #         move_template['product_uos_qty'] = diff_quantity
    #         res.append(move_template)
    #     return res

    # @api.multi
    # def _prepare_order_line_move(self,order, order_line, picking_id, group_id):
    #     res = super(purchase_order, self)._prepare_order_line_move(order, order_line, picking_id, group_id)
    #     print "my result her",res
    #     if order_line.customer_id:
    #         res['customer_id'] = order_line.customer_id.id
    #     if order_line.purchase_request_line_id:
    #         res['user_id'] = order_line.purchase_request_line_id.request_id.requested_by.id
    #     if order_line.purchase_request_line_id:
    #         res['section_id'] = order_line.purchase_request_line_id.request_id.section_id.id
    #     if order_line.purchase_request_line_id and order_line.purchase_request_line_id.request_id.removal_id and order_line.purchase_request_line_id.request_id.removal_id.opp_id:
    #         res['opp_id'] = order_line.purchase_request_line_id.request_id.removal_id.opp_id.id
    #     return res

    @api.v7
    def _create_stock_moves(self, cr, uid, order, order_lines, picking_id=False, context=None):
        """Creates appropriate stock moves for given order lines, whose can optionally create a
        picking if none is given or no suitable is found, then confirms the moves, makes them
        available, and confirms the pickings.

        If ``picking_id`` is provided, the stock moves will be added to it, otherwise a standard
        incoming picking will be created to wrap the stock moves (default behavior of the stock.move)

        Modules that wish to customize the procurements or partition the stock moves over
        multiple stock pickings may override this method and call ``super()`` with
        different subsets of ``order_lines`` and/or preset ``picking_id`` values.

        :param browse_record order: purchase order to which the order lines belong
        :param list(browse_record) order_lines: purchase order line records for which picking
                                                and moves should be created.
        :param int picking_id: optional ID of a stock picking to which the created stock moves
                               will be added. A new picking will be created if omitted.
        :return: None
        """
        stock_move = self.pool.get('stock.move')
        todo_moves = []
        new_group = self.pool.get("procurement.group").create(cr, uid, {'name': order.name, 'partner_id': order.partner_id.id}, context=context)
        for order_line in order_lines:
            if order_line.state == 'cancel':
                continue
            if not order_line.product_id:
                continue

            if order_line.product_id.type in ('product', 'consu'):
                for vals in self._prepare_order_line_move(cr, uid, order, order_line, picking_id, new_group, context=context):
                    if order_line.customer_id:
                        vals['customer_id'] = order_line.customer_id.id
                    if order_line.purchase_request_line_id:
                        vals['user_id'] = order_line.purchase_request_line_id.request_id.requested_by.id
                    if order_line.purchase_request_line_id:
                        vals['section_id'] = order_line.purchase_request_line_id.request_id.section_id.id
                    if order_line.purchase_request_line_id and order_line.purchase_request_line_id.request_id.removal_id and order_line.purchase_request_line_id.request_id.removal_id.opp_id:
                        vals['opp_id'] = order_line.purchase_request_line_id.request_id.removal_id.opp_id.id
                    vals['price_unit'] = order_line.product_id.cost_price
                    move = stock_move.create(cr, uid, vals, context=context)
                    todo_moves.append(move)

        todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
        stock_move.force_assign(cr, uid, todo_moves)


class purchase_order_line(models.Model):

    _inherit = 'purchase.order.line'

    customer_id = fields.Many2one('res.partner', 'Client', states={'validated': [('readonly', True)]},domain=[('customer', '=', True)])

    @api.v7
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        """
        onchange handler of product_id.
        """
        if context is None:
            context = {}

        res = {'value': {'price_unit': price_unit or 0.0, 'name': name or '', 'product_uom' : uom_id or False}}
        if not product_id:
            if not uom_id:
                uom_id = self.default_get(cr, uid, ['product_uom'], context=context).get('product_uom', False)
                res['value']['product_uom'] = uom_id
            return res

        product_product = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')
        res_partner = self.pool.get('res.partner')
        product_pricelist = self.pool.get('product.pricelist')
        account_fiscal_position = self.pool.get('account.fiscal.position')
        account_tax = self.pool.get('account.tax')

        # - check for the presence of partner_id and pricelist_id
        #if not partner_id:
        #    raise osv.except_osv(_('No Partner!'), _('Select a partner in purchase order to choose a product.'))
        #if not pricelist_id:
        #    raise osv.except_osv(_('No Pricelist !'), _('Select a price list in the purchase order form before choosing a product.'))

        # - determine name and notes based on product in partner lang.
        context_partner = context.copy()
        if partner_id:
            lang = res_partner.browse(cr, uid, partner_id).lang
            context_partner.update( {'lang': lang, 'partner_id': partner_id} )
        product = product_product.browse(cr, uid, product_id, context=context_partner)
        #call name_get() with partner in the context to eventually match name and description in the seller_ids field
        if not name or not uom_id:
            # The 'or not uom_id' part of the above condition can be removed in master. See commit message of the rev. introducing this line.
            dummy, name = product_product.name_get(cr, uid, product_id, context=context_partner)[0]
            if product.description_purchase:
                name += '\n' + product.description_purchase
            res['value'].update({'name': name})

        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}

        # - check that uom and product uom belong to the same category
        product_uom_po_id = product.uom_po_id.id
        if not uom_id:
            uom_id = product_uom_po_id

        if product.uom_id.category_id.id != product_uom.browse(cr, uid, uom_id, context=context).category_id.id:
            if context.get('purchase_uom_check') and self._check_product_uom_group(cr, uid, context=context):
                res['warning'] = {'title': _('Warning!'), 'message': _('Selected Unit of Measure does not belong to the same category as the product Unit of Measure.')}
            uom_id = product_uom_po_id

        res['value'].update({'product_uom': uom_id})

        # - determine product_qty and date_planned based on seller info
        if not date_order:
            date_order = fields.datetime.now()


        supplierinfo = False
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Unit of Measure')
        for supplier in product.seller_ids:
            if partner_id and (supplier.name.id == partner_id):
                supplierinfo = supplier
                if supplierinfo.product_uom.id != uom_id:
                    res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier only sells this product by %s') % supplierinfo.product_uom.name }
                min_qty = product_uom._compute_qty(cr, uid, supplierinfo.product_uom.id, supplierinfo.min_qty, to_uom_id=uom_id)
                if float_compare(min_qty , qty, precision_digits=precision) == 1: # If the supplier quantity is greater than entered from user, set minimal.
                    if qty:
                        res['warning'] = {'title': _('Warning!'), 'message': _('The selected supplier has a minimal quantity set to %s %s, you should not purchase less.') % (supplierinfo.min_qty, supplierinfo.product_uom.name)}
                    qty = min_qty
        dt = self._get_date_planned(cr, uid, supplierinfo, date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        qty = qty or 1.0
        res['value'].update({'date_planned': date_planned or dt})
        if qty:
            res['value'].update({'product_qty': qty})

        price = price_unit
        if price_unit is False or price_unit is None:
            # - determine price_unit and taxes_id
            if pricelist_id:
                date_order_str = datetime.strptime(date_order, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                price = product_pricelist.price_get(cr, uid, [pricelist_id],
                        product.id, qty or 1.0, partner_id or False, {'uom': uom_id, 'date': date_order_str})[pricelist_id]
            else:
                price = product.standard_price

        if uid == SUPERUSER_ID:
            company_id = self.pool['res.users'].browse(cr, uid, [uid]).company_id.id
            taxes = product.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id)
        else:
            taxes = product.supplier_taxes_id
        fpos = fiscal_position_id and account_fiscal_position.browse(cr, uid, fiscal_position_id, context=context) or False
        #taxes_ids = account_fiscal_position.map_tax(cr, uid, fpos, taxes, context=context)
        partner = res_partner.browse(cr,uid,partner_id,context=context)
        taxes_ids = [taxe.id for taxe in partner.taxe_ids]
        #price = self.pool['account.tax']._fix_tax_included_price(cr, uid, price, product.supplier_taxes_id, taxes_ids)
        price = product.cost_purchase
        res['value'].update({'price_unit': price, 'taxes_id': taxes_ids})

        return res


class stock_picking(models.Model):

    _inherit = 'stock.picking'

    import_id = fields.Many2one('goods.import', string='Dossier d\'import')

    @api.v7
    def action_invoice_create(self, cr, uid, ids, journal_id, group=False, type='out_invoice', context=None):
        """ Creates invoice based on the invoice state selected for picking.
        @param journal_id: Id of journal
        @param group: Whether to create a group invoice or not
        @param type: Type invoice to be created
        @return: Ids of created invoices for the pickings
        """
        context = context or {}
        todo = {}
        products = []
        for picking in self.browse(cr, uid, ids, context=context):
            partner = self._get_partner_to_invoice(cr, uid, picking, dict(context, type=type))
            #grouping is based on the invoiced partner
            if group:
                key = partner
            else:
                key = picking.id
            for move in picking.move_lines:
                if move.invoice_state == '2binvoiced':
                    if (move.state != 'cancel') and not move.scrapped:
                        todo.setdefault(key, [])
                        if move.product_id.id not in products :
                            products.append(move.product_id.id)
                            todo[key].append(move)
                        else :
                            for mv in todo[key] :
                                if mv.product_id.id == move.product_id.id :
                                    cr.execute('update stock_move set qty_group=%s where id = %s',(move.product_uom_qty,mv.id,))
                                    cr.execute('update stock_move set invoice_state=%s where id = %s',('invoiced',move.id,))
                                    cr.execute('update stock_picking set invoice_state=%s where id = %s',('invoiced', move.picking_id.id,))
                                    if move.purchase_line_id :
                                        cr.execute('update purchase_order_line set invoiced=%s,state=%s where id = %s',(True,'done', move.purchase_line_id.id))
                                        cr.execute('update purchase_order set state=%s where id = %s',('done', move.purchase_line_id.order_id.id))
        invoices = []
        for moves in todo.values():
            invoices += self._invoice_create_line(cr, uid, moves, journal_id, type, context=context)
        return invoices

    @api.v7
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move,context=context)
        if move.picking_id and move.picking_id.import_id:
            inv_vals.update({
                'import_id': move.picking_id.import_id.id,
            })
        return inv_vals


class stock_move(models.Model):

    _inherit = "stock.move"

    #supplier_id = fields.Many2one(related='picking_id.partner_id', comodel_name='res.partner',string='Fournisseur', store=True, readonly=True)
    #customer_id = fields.Many2one(related='purchase_line_id.order_id.customer_id', comodel_name='res.partner',string='Client', store=True, readonly=True)
    #customer_id = fields.Many2one('res.partner', string='Client')
    price_unit_sale = fields.Float('Prix de Vente')
    amount_total = fields.Float('Total HT', compute='_compute_amount', readonly=True, store=True)
    qty_group = fields.Float('Qté de groupement',default=0)

    @api.one
    @api.depends('price_unit','price_unit_sale','product_uom_qty','picking_type_id')
    def _compute_amount(self):
        if self.picking_type_id.id == 1 :
            self.amount_total = self.price_unit*self.product_uom_qty
        if self.picking_type_id.id == 2:
            self.amount_total = self.price_unit_sale*self.product_uom_qty

    @api.v7
    def _get_invoice_line_vals(self, cr, uid, move, partner, inv_type, context=None):
        inv_line_vals = super(stock_move, self)._get_invoice_line_vals(cr, uid, move, partner, inv_type,context=context)
        inv_line_vals.update({
            'quantity': inv_line_vals['quantity']+move.qty_group,
        })
        return inv_line_vals




class account_invoice(models.Model):

    _inherit = 'account.invoice'

    import_id = fields.Many2one('goods.import', string='Dossier d\'import')
    currency_rate = fields.Float('Cours de devise de la DUM', default=1)
    #type_service = fields.Selection([('purchase_goods', 'Achat de marchandise'),('freight', 'Fret'), ('freight_forwarder', 'Transit'), ('shopping', 'Magasinage'), ('demurrage', 'Surestarie'), ('customs', 'Douane'), ('insurance', 'Assurances'), ('truck_transport', 'Transport routier')],'Type de prestation',required=False)
    type_service = fields.Selection([('purchase_goods', 'Achat de marchandise'),('service', 'Service'),('customs', 'Douane')],'Type de prestation',required=False,default='service')

    @api.multi
    def action_cancel(self):
        res = super(account_invoice, self).action_cancel()
        for inv in self :
            if inv.type == 'in_invoice' :
                inv.internal_number = False
        return res

    @api.onchange('import_id')
    def _onchange_import_id(self):
        if self.import_id :
            if self.currency_id != self.import_id.currency_id:
                self.currency_rate = self.import_id.currency_rate

    @api.multi
    def invoice_validate(self):
        res = super(account_invoice, self).invoice_validate()
        if self.type == 'in_invoice' and self.type_service == 'purchase_goods' :
            for line in self.invoice_line :
                record_price_history = {
                    'product_id':line.product_id.id,
                    'product_qty':line.quantity,
                    'product_uom_id': line.uos_id.id,
                    'invoice_id': self.id,
                    'partner_id': self.partner_id.id,
                    'price': line.price_unit,
                    'date': line.date_invoice,
                }
                self.env['price.history'].create(record_price_history)
        return res


    @api.multi
    def compute_invoice_totals(self, company_currency, ref, invoice_move_lines):
        total = 0
        total_currency = 0
        for line in invoice_move_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = currency.round(line['price'])
                #line['price'] = currency.compute(line['price'], company_currency)
                line['price'] = self.currency_id.round(line['price']*self.currency_rate)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
            line['ref'] = ref
            if self.type in ('out_invoice','in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, invoice_move_lines

class account_invoice_line(models.Model):

    _inherit = 'account.invoice.line'

    type_product = fields.Selection([('service', 'Service'),('other','Autre')],'Type Article', required=False)

    @api.model
    def default_get(self,fields):
        # Compute simple values
        account_invoice = self.env['account.invoice']
        data = super(account_invoice_line, self).default_get(fields)
        if self._context.get('invoice_line'):
            for invoice_line_dict in account_invoice.resolve_2many_commands('invoice_line', self._context.get('invoice_line')):
                data['name'] = data.get('name') or invoice_line_dict.get('name')
                data['type_product'] = data.get('type_product') or invoice_line_dict.get('type_product')
        return data

    @api.onchange('type_product')
    def _onchange_type_product(self):
        if self.type_product :
            current_year = datetime.today().year
            if 1 <= self.invoice_id.journal_id.sequence_id.number_next_actual <= 9:
                sequence = '000' + str(self.invoice_id.journal_id.sequence_id.number_next_actual)
            elif 10 <= self.invoice_id.journal_id.sequence_id.number_next_actual <= 99:
                sequence = '00' + str(self.invoice_id.journal_id.sequence_id.number_next_actual)
            elif 100 <= self.invoice_id.journal_id.sequence_id.number_next_actual <= 999:
                sequence = '0' + str(self.invoice_id.journal_id.sequence_id.number_next_actual)
            else:
                sequence = str(self.invoice_id.journal_id.sequence_id.number_next_actual)
            desc = self.invoice_id.partner_id.name+'/'+self.invoice_id.journal_id.code+'/'+str(current_year)+'/'+sequence
            if self.type_product == 'service' :
                if self.invoice_id.import_id :
                    name = desc+'/'+self.invoice_id.import_id.name
                else :
                    name = desc
                if not self._context.get('invoice_line'):
                    self.name = name
                return {'domain': {'product_id': [('type', '=','service')]}}
            if self.type_product == 'other' :
                return {'domain': {'product_id': [('type', '!=','service')]}}

    @api.multi
    def product_id_change(self, product, uom_id, qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)
        if not partner_id:
            raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value': {}, 'domain': {'uos_id': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'uos_id': []}}

        values = {}

        part = self.env['res.partner'].browse(partner_id)
        fpos = self.env['account.fiscal.position'].browse(fposition_id)

        if part.lang:
            self = self.with_context(lang=part.lang)
        product = self.env['product.product'].browse(product)

        if not name :
            values['name'] = product.partner_ref

        if type in ('out_invoice', 'out_refund'):
            account = product.property_account_income or product.categ_id.property_account_income_categ
        else:
            account = product.property_account_expense or product.categ_id.property_account_expense_categ
        account = fpos.map_account(account)
        # if account:
        #     values['account_id'] = account.id

        if account and type == 'in_invoice':
            values['account_id'] = part.property_account_expense.id
        if account and type == 'out_invoice':
            values['account_id'] = account.id

        if type in ('out_invoice', 'out_refund'):
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale
        else:
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase

        fp_taxes = fpos.map_tax(taxes)
        #values['invoice_line_tax_id'] = fp_taxes.ids

        if type == 'in_invoice':
            values['invoice_line_tax_id'] = part.taxe_ids._ids
        if type == 'out_invoice':
            values['invoice_line_tax_id'] = fp_taxes.ids

        if type in ('in_invoice', 'in_refund'):
            if price_unit and price_unit != product.standard_price:
                values['price_unit'] = price_unit
            else:
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.standard_price, taxes, fp_taxes.ids)
        else:
            values['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.lst_price, taxes, fp_taxes.ids)

        values['uos_id'] = product.uom_id.id
        if uom_id:
            uom = self.env['product.uom'].browse(uom_id)
            if product.uom_id.category_id.id == uom.category_id.id:
                values['uos_id'] = uom_id

        domain = {'uos_id': [('category_id', '=', product.uom_id.category_id.id)]}

        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)

        if company and currency:
            if company.currency_id != currency:
                values['price_unit'] = values['price_unit'] * currency.rate

            if values['uos_id'] and values['uos_id'] != product.uom_id.id:
                values['price_unit'] = self.env['product.uom']._compute_price(
                    product.uom_id.id, values['price_unit'], values['uos_id'])

        return {'value': values, 'domain': domain}

class account_invoice_tax(models.Model):

    _inherit = 'account.invoice.tax'

    @api.model
    def default_get(self,fields):
        # Compute simple values
        account_invoice = self.env['account.invoice']
        data = super(account_invoice_tax, self).default_get(fields)
        if self._context.get('invoice_line'):
            for invoice_line_dict in account_invoice.resolve_2many_commands('invoice_line', self._context.get('invoice_line')):
                data['name'] = data.get('name') or invoice_line_dict.get('name')
        return data

class product_template(models.Model):

    _inherit = 'product.template'

    @api.multi
    def _compute_qty_reservation(self):

        section_obj = self.env['crm.case.section']

        sum_qty_reservation = 0

        for product in self:
            if product.type == 'product' :
                sections = section_obj.search([])
                for section in sections :
                    if section.location_id :
                        if section.location_id.id != 12 and section.location_id.id != 9 :
                            stock_historys = self.env['stock.history'].search([('location_id','=',section.location_id.id),('product_id','=',product.id)])
                            sum_qty_reservation = sum(histo.quantity for histo in stock_historys)
            product.total_reservation_qty = sum_qty_reservation

    cost_price = fields.Float('Prix de revient calculé', default=0)
    cost_purchase = fields.Float('Prix d\'Achat', default=0)
    customs_coefficient = fields.Float('Coefficient douanier', default=0.00)
    total_reservation_qty = fields.Float('Résa BU',compute='_compute_qty_reservation')

    # @api.multi
    # def action_res_by_section(self):
    #     ctx = dict(
    #         search_default_group_by_section='product.template',
    #         search_default_group_by_partner=True,
    #         search_default_group_by_product=True,
    #         search_default_product_id = self.id,
    #     )
    #     return {
    #         'name': _('Analyse des Reservations sur Stock'),
    #         'view_type': 'form',
    #         'view_mode': 'tree,graph',
    #         'res_model': 'stock.normal.reservation.history',
    #         'type': 'ir.actions.act_window',
    #         'context': ctx,
    #         'domain':[('state','in',('approuved','ready_to_deliver'))]
    #     }

    @api.multi
    def action_res_by_section(self):
        ctx = dict(
            search_default_group_by_section=True,
            search_default_group_by_partner=True,
            search_default_group_by_product=True,
            search_default_product_id = self.id,
        )
        return {
            'name': _('Analyse des Reservations'),
            'view_type': 'form',
            'view_mode': 'tree,graph',
            'res_model': 'stock.removal.reservation',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    @api.v7
    def create(self, cr, uid, vals, context=None):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
        if not context or "create_product_product" not in context:
            self.create_variant_ids(cr, uid, [product_template_id],context=context)
        self._set_standard_price(cr, uid, product_template_id, vals.get('cost_price', 0.0),context=context)

        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related_vals = {}
        if vals.get('ean13'):
            related_vals['ean13'] = vals['ean13']
        if vals.get('default_code'):
            related_vals['default_code'] = vals['default_code']
        if related_vals:
            self.write(cr, uid, product_template_id, related_vals, context=context)

        return product_template_id

    @api.v7
    def write(self, cr, uid, ids, vals, context=None):
        ''' Store the standard price change in order to be able to retrieve the cost of a product template for a given date'''
        if isinstance(ids, (int, long)):
            ids = [ids]
        if 'uom_po_id' in vals:
            new_uom = self.pool.get('product.uom').browse(cr, uid, vals['uom_po_id'], context=context)
            for product in self.browse(cr, uid, ids, context=context):
                old_uom = product.uom_po_id
                if old_uom.category_id.id != new_uom.category_id.id:
                    raise except_orm(_('Unit of Measure categories Mismatch!'), _("New Unit of Measure '%s' must belong to same Unit of Measure category '%s' as of old Unit of Measure '%s'. If you need to change the unit of measure, you may deactivate this product from the 'Procurements' tab and create a new one.") % (new_uom.name, old_uom.category_id.name, old_uom.name,))
        if 'cost_price' in vals:
            for prod_template_id in ids:
                self._set_standard_price(cr, uid, prod_template_id, vals['cost_price'], context=context)
        res = super(product_template, self).write(cr, uid, ids, vals, context=context)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids(cr, uid, ids, context=context)
        if 'active' in vals and not vals.get('active'):
            ctx = context and context.copy() or {}
            ctx.update(active_test=False)
            product_ids = []
            for product in self.browse(cr, uid, ids, context=ctx):
                product_ids += map(int, product.product_variant_ids)
            self.pool.get("product.product").write(cr, uid, product_ids, {'active': vals.get('active')}, context=ctx)
        return res


class price_history(models.Model):

    _name = 'price.history'

    product_id = fields.Many2one('product.product', string='Article')
    product_qty = fields.Float('Quantité')
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    invoice_id = fields.Many2one('account.invoice', string='Facture')
    partner_id = fields.Many2one('res.partner', 'Fournisseur',domain=[('supplier', '=', True)])
    price = fields.Float('Prix unitaire')
    date = fields.Datetime('Date')


class stock_history(models.Model):

    _inherit = 'stock.history'

    inventory_value = fields.Float('Inventory Value', compute='_compute_inventory_value',readonly=True)

    @api.one
    @api.depends('price_unit_on_quant','quantity')
    def _compute_inventory_value(self):
        self.inventory_value = self.quantity*self.price_unit_on_quant

    @api.v7
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        res = super(stock_history, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if context is None:
            context = {}
        date = context.get('history_date', datetime.now())
        if 'inventory_value' in fields:
            group_lines = {}
            for line in res:
                domain = line.get('__domain', domain)
                group_lines.setdefault(str(domain), self.search(cr, uid, domain, context=context))
            line_ids = set()
            for ids in group_lines.values():
                for product_id in ids:
                    line_ids.add(product_id)
            line_ids = list(line_ids)
            lines_rec = {}
            if line_ids:
                cr.execute('SELECT id, product_id, price_unit_on_quant, company_id, quantity FROM stock_history WHERE id in %s', (tuple(line_ids),))
                lines_rec = cr.dictfetchall()
            lines_dict = dict((line['id'], line) for line in lines_rec)
            product_ids = list(set(line_rec['product_id'] for line_rec in lines_rec))
            products_rec = self.pool['product.product'].read(cr, uid, product_ids, ['cost_method', 'product_tmpl_id'], context=context)
            products_dict = dict((product['id'], product) for product in products_rec)
            cost_method_product_tmpl_ids = list(set(product['product_tmpl_id'][0] for product in products_rec if product['cost_method'] != 'real'))
            histories = []
            if cost_method_product_tmpl_ids:
                cr.execute('SELECT DISTINCT ON (product_template_id, company_id) product_template_id, company_id, cost FROM product_price_history WHERE product_template_id in %s AND datetime <= %s ORDER BY product_template_id, company_id, datetime DESC', (tuple(cost_method_product_tmpl_ids), date))
                histories = cr.dictfetchall()
            histories_dict = {}
            for history in histories:
                histories_dict[(history['product_template_id'], history['company_id'])] = history['cost']
            for line in res:
                inv_value = 0.0
                lines = group_lines.get(str(line.get('__domain', domain)))
                for line_id in lines:
                    line_rec = lines_dict[line_id]
                    product = products_dict[line_rec['product_id']]
                    price = line_rec['price_unit_on_quant']
                    # if product['cost_method'] == 'real':
                    #     price = line_rec['price_unit_on_quant']
                    # else:
                    #     price = histories_dict.get((product['product_tmpl_id'][0], line_rec['company_id']), 0.0)
                    inv_value += price * line_rec['quantity']
                line['inventory_value'] = inv_value
        return res

class stock_quant(models.Model):

    _inherit = 'stock.quant'

    inventory_value = fields.Float('Inventory Value', compute='_compute_inventory_value',readonly=True)

    @api.one
    @api.depends('cost','qty')
    def _compute_inventory_value(self):
        self.inventory_value = self.cost*self.qty

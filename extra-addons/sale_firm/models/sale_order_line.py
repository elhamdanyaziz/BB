
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
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv

class sale_order(osv.Model):

    _inherit = 'sale.order'

    _columns = {
        'order_line': fields.one2many('sale.order.line', 'order_id', 'Order Lines', readonly=True,
                                  states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'received': [('readonly', False)]}, copy=True),

    }


class sale_order_line(osv.Model):

    _inherit = 'sale.order.line'


    _columns = {
        'order_id': fields.many2one('sale.order', 'Order Reference', required=True, ondelete='cascade', select=True,
                                    readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'name': fields.text('Description', required=True, readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok', '=', True)], change_default=True,
                                      readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}, ondelete='restrict'),
        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'),
                                   readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'tax_id': fields.many2many('account.tax', 'sale_order_tax', 'order_line_id', 'tax_id', 'Taxes', readonly=True,
                                   states={'draft': [('readonly', False)], 'received': [('readonly', False)]},
                                   domain=['|', ('active', '=', False), ('active', '=', True)]),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoS'), required=True,
                                        readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure ', required=True, readonly=True,
                                       states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'product_uos_qty': fields.float('Quantity (UoS)', digits_compute=dp.get_precision('Product UoS'), readonly=True,
                                        states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'discount': fields.float('Discount (%)', digits_compute=dp.get_precision('Discount'), readonly=True,
                                 states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
        'th_weight': fields.float('Weight', readonly=True, states={'draft': [('readonly', False)],'received': [('readonly', False)]},
                                  digits_compute=dp.get_precision('Stock Weight')),
        'delay': fields.float('Delivery Lead Time', required=True,
                              help="Number of days between the order confirmation and the shipping of the products to the customer",
                              readonly=True, states={'draft': [('readonly', False)], 'received': [('readonly', False)]}),
    }

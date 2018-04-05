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

class stock_removal_cancel(models.TransientModel):
    
    _name = "stock.removal.cancel"
    _description = "Annulation BE"

    type_action = fields.Selection([('partial_cancellation', 'Annulation Partielle'),('total_cancellation', 'Annulation Totale')], 'Opération', required=True)
    action1 = fields.Selection([('customer_request', 'Demande client'),('internal_request', 'Demande Interne')], 'Qualification de l\'Annulation', required=False)
    action2 = fields.Selection([('customer_request', 'Demande client'),('internal_request', 'Demande Interne'),('product_not_available','Article non disponible en stock'),('defective_product','Article défectueux'),('product_to_repair','Article à réparer')], 'Qualification de l\'Annulation', required=False)
    filter = fields.Selection([('approuved', 'Approuvé'),('ready_to_deliver', 'Prêt à livrer')],'Statut',required=False)
    note = fields.Text('Notes')
    line_ids = fields.One2many('stock.removal.cancel.line','cancel_id', 'Annulations', required=False)


    @api.multi
    def create_removal_cancellation(self):
        removal_id = self._context.get('active_id')
        move_obj = self.env['stock.move']
        removal_obj = self.env['stock.removal']
        situation_obj = self.env['sale.order.situation']
        inventory_obj = self.env['stock.inventory']
        location_obj = self.env['stock.location']
        picking_obj = self.env['stock.picking']
        request_obj = self.env['purchase.request']
        request_line_obj = self.env['purchase.request.line']

        removal = removal_obj.browse(removal_id)
        if self.type_action == 'total_cancellation' :
            if removal.state == 'draft':
                removal.action_cancel()
                for line in self.line_ids :
                    line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-line.product_qty})
            if removal.state == 'validated':
                removal.action_cancel()
                for line in self.line_ids :
                    line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
            elif removal.state == 'approuved' :
                if self.action1 == 'customer_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        situation = situation_obj.search([('sale_order_id','=',line.removal_id.sale_order_id.id),('product_id','=',line.product_id.id)])
                        situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
                    removal.action_cancel()
                elif self.action1 == 'internal_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                          'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
                    removal.action_cancel()
            elif removal.state == 'ready_to_deliver' :
                if self.action2 == 'customer_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        situation = situation_obj.search([('sale_order_id','=',line.removal_id.sale_order_id.id),('product_id','=',line.product_id.id)])
                        situation.write({'qty_canceled':situation.qty_canceled+line.product_qty})
                    removal.action_cancel()
                    picking_type = self.env['stock.picking.type'].browse(2)
                    picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                    picking.action_cancel()
                elif self.action2 == 'internal_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
                    removal.action_cancel()
                    picking_type = self.env['stock.picking.type'].browse(2)
                    picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                    picking.action_cancel()

                elif self.action2 == 'product_not_available' :
                    inventory_lines = []
                    for line in self.line_ids :
                        record_inventory_line = {
                         'product_id': line.product_id.id,
                         'product_qty': line.product_qty,
                         'product_uom_id': line.product_uom_id.id,
                         'location_id': removal.location_id.id,
                         }
                        inventory_lines.append((0, 0, record_inventory_line))
                        line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
                    record_inventory = {
                        'name': 'Inventaire le '+str(datetime.today()),
                        'date': datetime.today(),
                        'location_id': removal.location_id.id,
                        'filter': 'partial',
                        'line_ids': inventory_lines
                    }
                    inventory = inventory_obj.create(record_inventory)
                    inventory.action_done()
                    removal.action_cancel()
                    picking_type = self.env['stock.picking.type'].browse(2)
                    picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                    picking.action_cancel()

                elif self.action2 == 'defective_product':
                    location = location_obj.search([('name','=','Stock rebut')])
                    for line in self.line_ids:
                        record_move = {
                            'invoice_state': 'none',
                            'date_expected': datetime.today(),
                            'price_unit': line.move_id.price_unit,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'location_id': removal.location_dest_id.id,
                            'location_dest_id': location.id,
                            'note': self.note
                        }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
                    removal.action_cancel()
                    picking_type = self.env['stock.picking.type'].browse(2)
                    picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                    picking.action_cancel()
                elif self.action2 == 'product_to_repair':
                    location = location_obj.search([('name','=','Stock réparation')])
                    for line in self.line_ids:
                        record_move = {
                            'invoice_state': 'none',
                            'date_expected': datetime.today(),
                            'price_unit': line.move_id.price_unit,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'location_id': removal.location_dest_id.id,
                            'location_dest_id': location.id,
                            'note': self.note
                        }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available':line.move_id.sale_order_line_id.qty_available-line.product_qty})
                    removal.action_cancel()
                    picking_type = self.env['stock.picking.type'].browse(2)
                    picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                    picking.action_cancel()
        else :
            if removal.state == 'draft':
                for line in self.line_ids:
                    line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                    line.move_id.write({'product_uom_qty':line.product_qty})
            elif removal.state == 'validated':
                for line in self.line_ids:
                    line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                    line.move_id.write({'product_uom_qty': line.product_qty})
                    line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                    if line_normal_reservation:
                        line_normal_reservation.write({'product_qty': line.product_qty})
                    line_shipping_reservation = self.env['stock.shipping.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                    if line_shipping_reservation:
                        line_shipping_reservation.write({'product_qty': line.product_qty})
                        line_shipping_reservation.move_id.write({'product_uom_qty': line.product_qty})
                    line_purchase_reservation = self.env['stock.purchase.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                    if line_purchase_reservation :
                        line_purchase_reservation.write({'product_qty': line.product_qty})
                        request = request_obj.search([('removal_id','=',removal.id)])
                        request_line = request_line_obj.search([('request_id','=',request.id),('product_id', '=', line.product_id.id)])
                        stock_move = self.env['stock.move'].search([('product_id', '=', line.product_id.id),('purchase_request_id', '=', request.id), ('purchase_request_line_id', '=',request_line.id)])
                        if stock_move :
                            stock_move.write({'product_uom_qty': line.product_qty})
            elif removal.state == 'approuved' :
                if self.action1 == 'customer_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        situation = situation_obj.search([('sale_order_id','=',line.removal_id.sale_order_id.id),('product_id','=',line.product_id.id)])
                        situation.write({'qty_canceled':situation.qty_canceled+(line.move_id.product_uom_qty - line.product_qty)})
                        if line.product_qty < line.move_id.product_uom_qty :
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else :
                            line.move_id.action_cancel()
                elif self.action1 == 'internal_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                          'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                        if line.product_qty < line.move_id.product_uom_qty :
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else :
                            line.move_id.action_cancel()
            elif removal.state == 'ready_to_deliver' :
                if self.action2 == 'customer_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        situation = situation_obj.search([('sale_order_id','=',line.removal_id.sale_order_id.id),('product_id','=',line.product_id.id)])
                        situation.write({'qty_canceled':situation.qty_canceled+(line.move_id.product_uom_qty - line.product_qty)})
                        picking_type = self.env['stock.picking.type'].browse(2)
                        picking = picking_obj.search([('removal_id','=',removal.id),('picking_type_id','=',picking_type.id)])
                        move_picking = move_obj.search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                        if line.product_qty < line.move_id.product_uom_qty :
                            move_picking.write({'product_uom_qty': line.product_qty})
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else :
                            move_picking.action_cancel()
                            line.move_id.action_cancel()
                elif self.action2 == 'internal_request' :
                    for line in self.line_ids :
                        record_move = {
                         'invoice_state': 'none',
                         'date_expected': datetime.today(),
                         'price_unit': line.move_id.price_unit,
                         'product_id': line.product_id.id,
                         'name': line.product_id.name,
                         'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                         'product_uom': line.product_uom_id.id,
                         'location_id': removal.location_dest_id.id,
                         'location_dest_id': removal.location_id.id,
                         'note': self.note
                         }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                        picking_type = self.env['stock.picking.type'].browse(2)
                        picking = picking_obj.search([('removal_id', '=', removal.id), ('picking_type_id', '=', picking_type.id)])
                        move_picking = move_obj.search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                        if line.product_qty < line.move_id.product_uom_qty:
                            move_picking.write({'product_uom_qty': line.product_qty})
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else:
                            move_picking.action_cancel()
                            line.move_id.action_cancel()
                elif self.action2 == 'product_not_available' :
                    inventory_lines = []
                    for line in self.line_ids :
                        record_inventory_line = {
                         'product_id': line.product_id.id,
                         'product_qty': line.move_id.product_uom_qty-line.product_qty,
                         'product_uom_id': line.product_uom_id.id,
                         'location_id': removal.location_id.id,
                         }
                        inventory_lines.append((0, 0, record_inventory_line))
                        line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                        picking_type = self.env['stock.picking.type'].browse(2)
                        picking = picking_obj.search([('removal_id', '=', removal.id), ('picking_type_id', '=', picking_type.id)])
                        move_picking = move_obj.search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                        if line.product_qty < line.move_id.product_uom_qty:
                            move_picking.write({'product_uom_qty': line.product_qty})
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            picking.do_unreserve()
                            picking.action_confirm()
                            picking.action_assign()
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else:
                            move_picking.action_cancel()
                            line.move_id.action_cancel()
                    record_inventory = {
                        'name': 'Inventaire le '+str(datetime.today()),
                        'date': datetime.today(),
                        'location_id': removal.location_id.id,
                        'filter': 'partial',
                        'line_ids':inventory_lines
                    }
                    inventory = inventory_obj.create(record_inventory)
                    inventory.action_done()
                elif self.action2 == 'defective_product':
                    location = location_obj.search([('name','=','Stock rebut')])
                    for line in self.line_ids:
                        record_move = {
                            'invoice_state': 'none',
                            'date_expected': datetime.today(),
                            'price_unit': line.move_id.price_unit,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'location_id': removal.location_dest_id.id,
                            'location_dest_id': location.id,
                            'note': self.note
                        }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                        picking_type = self.env['stock.picking.type'].browse(2)
                        picking = picking_obj.search([('removal_id', '=', removal.id), ('picking_type_id', '=', picking_type.id)])
                        move_picking = move_obj.search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                        if line.product_qty < line.move_id.product_uom_qty:
                            move_picking.write({'product_uom_qty': line.product_qty})
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else:
                            move_picking.action_cancel()
                            line.move_id.action_cancel()
                elif self.action2 == 'product_to_repair':
                    location = location_obj.search([('name','=','Stock réparation')])
                    for line in self.line_ids:
                        record_move = {
                            'invoice_state': 'none',
                            'date_expected': datetime.today(),
                            'price_unit': line.move_id.price_unit,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.move_id.product_uom_qty-line.product_qty,
                            'product_uom': line.product_uom_id.id,
                            'location_id': removal.location_dest_id.id,
                            'location_dest_id': location.id,
                            'note': self.note
                        }
                        move = move_obj.create(record_move)
                        move.action_confirm()
                        move.action_assign()
                        move.action_done()
                        line.move_id.sale_order_line_id.write({'qty_available': line.move_id.sale_order_line_id.qty_available-(line.move_id.product_uom_qty - line.product_qty)})
                        picking_type = self.env['stock.picking.type'].browse(2)
                        picking = picking_obj.search([('removal_id', '=', removal.id), ('picking_type_id', '=', picking_type.id)])
                        move_picking = move_obj.search([('picking_id', '=', picking.id), ('product_id', '=', line.product_id.id)])
                        if line.product_qty < line.move_id.product_uom_qty:
                            move_picking.write({'product_uom_qty': line.product_qty})
                            line.move_id.write({'product_uom_qty': line.product_qty})
                            line_normal_reservation = self.env['stock.normal.reservation.line'].search([('removal_id', '=', removal.id), ('product_id', '=', line.product_id.id)])
                            if line_normal_reservation:
                                line_normal_reservation.write({'product_qty': line.product_qty})
                        else:
                            move_picking.action_cancel()
                            line.move_id.action_cancel()
        return True

class stock_removal_cancel_line(models.TransientModel):

    _name = "stock.removal.cancel.line"

    product_id = fields.Many2one('product.product', 'Produit')
    product_qty = fields.Float('Quantité', degits=2, default=0)
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    move_id = fields.Many2one('stock.move', string='Mouvement')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=False)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=False)
    cancel_id = fields.Many2one('stock.removal.cancel', 'Annulation', ondelete='cascade')
    removal_id = fields.Many2one('stock.removal', 'BE', required=False)
    opp_id = fields.Many2one('crm.lead', 'Opp', required=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

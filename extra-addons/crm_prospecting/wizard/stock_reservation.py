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


class stock_reservation(models.TransientModel):
    _name = "stock.reservation"
    _description = "Reservation"


    # reservation_method = fields.Selection([('stock', 'Réservation sur Stock'), ('shipping', 'Reservation sur Arrivage'), ('purchase', 'Reservation sur Demande Achat'),('none', 'Sans Réservation'),], 'Méthode de Réservation', required=True, default='stock')
    reservation_method = fields.Selection([('stock', 'Réservation sur Stock'), ('shipping', 'Reservation sur Arrivage'),('none', 'Sans Réservation'),], 'Méthode de Réservation', required=True, default='stock')


    @api.multi
    def create_shipping_reservation(self, removal, moves):
        # move_ids = self._context.get('active_ids')
        move_obj = self.env['stock.move']
        shipping_reservation_obj = self.env['stock.shipping.reservation']
        shipping_reservation_line_obj = self.env['stock.shipping.reservation.line']
        res = {}
        record_reservation = {
                'origin': removal.name,
                'section_id': removal.section_id.id,
                'partner_id': removal.partner_id.id,
                'sale_order_id': removal.sale_order_id.id,
                'delivery_date':removal.delivery_date,
                'user_id': removal.user_id.id,
                'location_id': removal.location_id.id,
                'location_dest_id': removal.location_dest_id.id,
                'company_id': removal.company_id.id,
                'removal_id':removal.id
        }

        reservation = shipping_reservation_obj.create(record_reservation)

        for move in moves :
            if move.customer_id :
                raise except_orm('Attention', 'Vous pouvez pas réserver sur cette arrivage concernant une commande spéciale,merci de contacter service achat ')
            qty = 0
            removal_move = move_obj.search([('removal_id','=',removal.id),('product_id','=',move.product_id.id)])
            #reservation_lines = shipping_reservation_line_obj.search([('section_id','=',removal_move.section_id.id),('move_id','=',move.id)]) # rajouter un traitement pour annuler les reservation encours
            reservation_lines = shipping_reservation_line_obj.search([('move_id','=',move.id),('state', '!=', 'cancel')]) # rajouter un traitement pour annuler les reservation encours
            if reservation_lines :
                qty = sum(resv.product_qty for resv in reservation_lines)
                if qty > move.product_uom_qty :
                    raise except_orm('Attention','Le stock d\'arrivage est consomé totalement')
                else :
                    if (move.product_uom_qty-qty) < removal_move.product_uom_qty :
                        raise except_orm('Attention', 'Le stock d\'arrivage ne peut pas couvrir cette réservation')
            else :
                if move.product_uom_qty < removal_move.product_uom_qty:
                    raise except_orm('Attention', 'Le stock d\'arrivage ne peut pas couvrir cette réservation')

            reservation_line = {
                'sale_order_line_id':removal_move.sale_order_line_id.id,
                'product_id' : removal_move.product_id.id,
                'name' : removal_move.name,
                'product_qty' : removal_move.product_uom_qty,
                'product_uom_id': removal_move.product_uom.id,
                'location_id': removal_move.location_id.id,
                'location_dest_id': removal_move.location_dest_id.id,
                'delivery_date': removal.delivery_date,
                'reservation_id':reservation.id,
                'partner_id':removal_move.partner_id.id,
                'section_id': removal_move.section_id.id,
                'user_id':removal.user_id.id,
                'removal_id':removal.id,
                'move_id':move.id,
                'move_dest_id':removal_move.id,
            }
            move.write({'move_dest_id':removal_move.id})
            shipping_reservation_line_obj.create(reservation_line)
            removal.write({'state': 'validated'})
        return True

    @api.multi
    def create_resetvation(self):
        moves = []
        lines = []
        if self.reservation_method == 'stock' :
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if not removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement sans réservation ')
            removal.action_validated()
            removal.write({'reservation_method':'stock'})
        elif self.reservation_method == 'shipping' :
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if not removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement sans réservation ')
            for move in removal.move_lines :
                stock_moves = self.env['stock.move'].search([('product_id','=',move.product_id.id),('picking_type_id','=',1),('state','=','assigned')])
                if stock_moves :
                    # for stock_move in stock_moves :
                    #     moves.append(stock_move.id)
                # domain = "[('id','in',%s)]"%moves
                #removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id)])
                    self.create_shipping_reservation(removal, stock_moves)
                    removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
                    if len(removals) == 0:
                        removal.write({'name':removal.sale_order_id.name+'BE001'})
                    elif 1 <= len(removals) < 9:
                        removal.write({'name': removal.sale_order_id.name+'BE00'+str(len(removals)+1)})
                    elif 9 <= len(removals) < 99:
                        removal.write({'name': removal.sale_order_id.name+'BE0'+str(len(removals)+1)})
                    else:
                        removal.write({'name': removal.sale_order_id.name+'BE'+str(len(removals)+1)})
                else:
                    raise except_orm('Attention', 'Aucun Arrivage ni planifié ')
            removal.write({'reservation_method': 'shipping'})
            # return {
            #     'name': 'Arrivages',
            #     'view_type': 'form',
            #     'view_mode': 'tree',
            #     'view_id': self.env['ir.ui.view'].search([('name', '=', 'stock.move.shipping.tree')])[0].id,
            #     'res_model': 'stock.move',
            #     'type': 'ir.actions.act_window',
            #     'domain': domain,
            # }
        # elif self.reservation_method == 'purchase':
        #     removal_id = self._context.get('active_id',False)
        #     removal = self.env['stock.removal'].browse(removal_id)
        #     if not removal.whith_reservation :
        #         raise except_orm('Attention', 'Bon d\'enlévement sans réservation ')
        #     self.state = 'validated'
        #     #removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id)])
        #     removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
        #     if len(removals) == 0:
        #         removal.write({'state':'validated','name':removal.sale_order_id.name+'BE001'})
        #     elif 1 <= len(removals) < 9:
        #         removal.write({'state': 'validated', 'name': removal.sale_order_id.name+'BE00'+str(len(removals)+1)})
        #     elif 9 <= len(removals) < 99:
        #         removal.write({'name': removal.sale_order_id.name+'BE0'+str(len(removals)+1)})
        #     else:
        #         removal.write({'state': 'validated', 'name': removal.sale_order_id.name+'BE'+str(len(removals)+1)})
        #     for move in removal.move_lines:
        #         line = (0, 0,{'partner_id':removal.partner_id.id,'removal_move_id':move.id,'sale_order_line_id':move.sale_order_line_id.id,'product_id': move.product_id.id,'name': move.name, 'product_qty': move.product_uom_qty, 'product_uom_id': move.product_uom.id})
        #         lines.append(line)
        #     removal.write({'reservation_method': 'purchase'})
        #     return {
        #         'name': 'Demande Achat',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'view_id': self.env['ir.ui.view'].search([('name', '=', 'purchase.request.form')])[0].id,
        #         'res_model': 'purchase.request',
        #         'type': 'ir.actions.act_window',
        #
        #         'context': {
        #             'default_origin': removal.name,
        #             'default_section_id': removal.section_id.id,
        #             'default_removal_id': removal.id,
        #             'default_partner_id': removal.partner_id.id,
        #             #'default_sale_order_id': self.id,
        #             #'default_opp_id': self.opp_id.id,
        #             'default_requested_by': removal.user_id.id,
        #             #'default_partner_id': self.partner_id.id,
        #             #'default_location_id': self.warehouse_id.location_id.id,
        #             #'default_location_dest_id': self.section_id.location_id.id,
        #             'default_company_id': removal.company_id.id,
        #             'default_line_ids': lines,
        #         }
        #     }
        else :
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement avec réservation ')
            removal.write({'reservation_method': 'none'})
            #removals = self.env['stock.removal'].search([('sale_order_id', '=', False), ('id', '!=', removal.id)])
            if removal.sale_order_id.id :
                removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
                if len(removals) == 0:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE01'})
                elif 0 < len(removals) < 9:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE0' + str(len(removals) + 1)})
                else:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE' + str(len(removals) + 1)})
                removal.action_create_picking_out()
            else :
                removals = self.env['stock.removal'].search([('sale_order_id', '=', False), ('id', '!=', removal.id)])
                if len(removals) == 0:
                    removal.write({'state':'approuved','name':'BE01'})
                elif 0 < len(removals) < 9:
                    removal.write({'state': 'approuved', 'name':'BE0'+str(len(removals)+1)})
                else:
                    removal.write({'state': 'approuved', 'name':'BE'+str(len(removals)+1)})
                removal.action_create_picking_out()
            for move in removal.move_lines:
                move.write({'removal_id': False})
                move.action_cancel()

            picking = self.env['stock.picking'].search([('order_id', '=', removal.sale_order_id.id), ('removal_id', '=', removal_id)])
            for move in picking.move_lines:
                move.write({'removal_id': removal_id})



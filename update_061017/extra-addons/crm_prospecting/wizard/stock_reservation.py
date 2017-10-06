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


    reservation_method = fields.Selection([('stock', 'Réservation sur Stock'), ('shipping', 'Reservation sur Arrivage'), ('purchase', 'Reservation sur Demande Achat'),('none', 'Sans Réservation'),], 'Méthode de Réservation', required=True, default='stock')

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
        elif self.reservation_method == 'shipping' :
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if not removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement sans réservation ')
            for move in removal.move_lines :
                stock_moves = self.env['stock.move'].search([('product_id','=',move.product_id.id),('picking_type_id','=',1),('state','=','assigned')])
                if stock_moves :
                    for stock_move in stock_moves :
                        moves.append(stock_move.id)
            domain = "[('id','in',%s)]"%moves
            #removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id)])
            removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
            if len(removals) == 0:
                removal.write({'name':removal.sale_order_id.name+'BE001'})
            elif 1 <= len(removals) < 9:
                removal.write({'name': removal.sale_order_id.name+'BE00'+str(len(removals)+1)})
            elif 9 <= len(removals) < 99:
                removal.write({'name': removal.sale_order_id.name+'BE0'+str(len(removals)+1)})
            else:
                removal.write({'name': removal.sale_order_id.name+'BE'+str(len(removals)+1)})

            return {
                'name': 'Arrivages',
                'view_type': 'form',
                'view_mode': 'tree',
                'view_id': self.env['ir.ui.view'].search([('name', '=', 'stock.move.shipping.tree')])[0].id,
                'res_model': 'stock.move',
                'type': 'ir.actions.act_window',
                'domain': domain,
            }
        elif self.reservation_method == 'purchase':
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if not removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement sans réservation ')
            self.state = 'validated'
            #removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id)])
            removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
            if len(removals) == 0:
                removal.write({'state':'validated','name':removal.sale_order_id.name+'BE001'})
            elif 1 <= len(removals) < 9:
                removal.write({'state': 'validated', 'name': removal.sale_order_id.name+'BE00'+str(len(removals)+1)})
            elif 9 <= len(removals) < 99:
                removal.write({'name': removal.sale_order_id.name+'BE0'+str(len(removals)+1)})
            else:
                removal.write({'state': 'validated', 'name': removal.sale_order_id.name+'BE'+str(len(removals)+1)})
            for move in removal.move_lines:
                line = (0, 0,{'partner_id':removal.partner_id.id,'removal_move_id':move.id,'sale_order_line_id':move.sale_order_line_id.id,'product_id': move.product_id.id,'name': move.name, 'product_qty': move.product_uom_qty, 'product_uom_id': move.product_uom.id})
                lines.append(line)
            return {
                'name': 'Demande Achat',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env['ir.ui.view'].search([('name', '=', 'purchase.request.form')])[0].id,
                'res_model': 'purchase.request',
                'type': 'ir.actions.act_window',

                'context': {
                    'default_origin': removal.name,
                    'default_section_id': removal.section_id.id,
                    'default_removal_id': removal.id,
                    #'default_sale_order_id': self.id,
                    #'default_opp_id': self.opp_id.id,
                    'default_requested_by': removal.user_id.id,
                    #'default_partner_id': self.partner_id.id,
                    #'default_location_id': self.warehouse_id.location_id.id,
                    #'default_location_dest_id': self.section_id.location_id.id,
                    'default_company_id': removal.company_id.id,
                    'default_line_ids': lines,
                }
            }
        else :
            removal_id = self._context.get('active_id',False)
            removal = self.env['stock.removal'].browse(removal_id)
            if removal.whith_reservation :
                raise except_orm('Attention', 'Bon d\'enlévement avec réservation ')
            #removals = self.env['stock.removal'].search([('sale_order_id', '=', False), ('id', '!=', removal.id)])
            if removal.sale_order_id.id :
                removals = self.env['stock.removal'].search([('sale_order_id', '=', removal.sale_order_id.id), ('id', '!=', removal.id), ('state', '!=', 'draft')])
                if len(removals) == 0:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE01'})
                elif 0 < len(removals) < 9:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE0' + str(len(removals) + 1)})
                else:
                    removal.write({'state':'approuved','name': removal.sale_order_id.name + 'BE' + str(len(removals) + 1)})
            else :
                removals = self.env['stock.removal'].search([('sale_order_id', '=', False), ('id', '!=', removal.id)])
                if len(removals) == 0:
                    removal.write({'state':'approuved','name':'BE01'})
                elif 0 < len(removals) < 9:
                    removal.write({'state': 'approuved', 'name':'BE0'+str(len(removals)+1)})
                else:
                    removal.write({'state': 'approuved', 'name':'BE'+str(len(removals)+1)})



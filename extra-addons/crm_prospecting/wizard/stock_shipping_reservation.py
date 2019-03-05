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

class stock_shipping_reservation(models.TransientModel):
    
    _name = "shipping.reservation"
    _description = "Reservation"

    # @api.model
    # def _get_domain_user(self):
    #     user = self.env['res.users'].browse(self._uid)
    #     users = self.env['res.users'].search([('default_section_id','=',user.default_section_id.id)])
    #     user_ids = users._ids
    #     domain =  [('id', 'in', user_ids)]
    #     return domain

    @api.model
    def _get_domain_removal(self):
        # removal_ids = []
        # normal_reservations = self.env['stock.normal.reservation'].search([('state','=','cancel')])
        # for reserv in normal_reservations :
        #     if reserv.removal_id.id not in removal_ids :
        #         removal_ids.append(reserv.removal_id.id)
        user = self.env['res.users'].browse(self._uid)
        #domain = [('type', '=', 'removal'),('section_id', '=', user.default_section_id.id),('state', '=', 'validated'),('id','in',removal_ids),('user_id', '=', user.id)]
        #domain = [('type', '=', 'removal'),('section_id', '=', user.default_section_id.id),('state', '=', 'validated'),('user_id', '=', user.id)]
        #domain = [('type', '=', 'removal'), ('section_id', '=', user.default_section_id.id)]
        domain = [('type', '=', 'removal'), ('user_id', '=', user.id), ('state', '=', 'draft')]
        return domain

    @api.model
    def _get_default_user(self):
        return self._uid

    @api.model
    def _get_default_section(self):
        user = self.env['res.users'].browse(self._uid)
        return user.default_section_id.id

    removal_id = fields.Many2one('stock.removal', string='Enlévement',domain=_get_domain_removal)
    section_id = fields.Many2one('crm.case.section', string='Département',readonly=True,default=_get_default_section)
    #user_id = fields.Many2one('res.users', string='KAM',domain=_get_domain_user,default=_get_default_user)
    user_id = fields.Many2one('res.users', string='KAM',default=_get_default_user)
    #line_ids = fields.One2many('shipping.reservation.line','reservation_id', 'Lignes de réservation', required=False)

    @api.onchange('user_id')
    def _compute_removal_id(self):
        # removal_ids = []
        # normal_reservations = self.env['stock.normal.reservation'].search([('state','=','cancel')])
        # for reserv in normal_reservations :
        #     if reserv.removal_id.id not in removal_ids :
        #         removal_ids.append(reserv.removal_id.id)
        if self.user_id :
            #removals = self.env['stock.removal'].search([('type', '=', 'removal'),('section_id', '=', self.user_id.default_section_id.id),('state', '=', 'validated'),('id','in',removal_ids),('user_id', '=', self.user_id.id)])
            #removals = self.env['stock.removal'].search([('type', '=', 'removal'),('section_id', '=', self.user_id.default_section_id.id),('state', '=', 'validated'),('user_id', '=', self.user_id.id)])
            removals = self.env['stock.removal'].search([('type', '=', 'removal'),('user_id', '=', self.user_id.id)])
            if removals :
                removal_ids = removals._ids
                self.removal_id = removal_ids[0]
                return {'domain': {'removal_id': [('id', 'in', list(removal_ids))]}}
        return {'domain': {'removal_id': [('id', 'in', list([]))]}}

    @api.multi
    def create_shipping_reservation(self):
        move_ids = self._context.get('active_ids')
        move_obj = self.env['stock.move']
        shipping_reservation_obj = self.env['stock.shipping.reservation']
        shipping_reservation_line_obj = self.env['stock.shipping.reservation.line']
        res = {}
        record_reservation = {
                'origin': self.removal_id.name,
                #'section_id': self.section_id.id,
                'section_id': self.removal_id.section_id.id,
                'partner_id': self.removal_id.partner_id.id,
                'sale_order_id': self.removal_id.sale_order_id.id,
                'delivery_date':self.removal_id.delivery_date,
                'user_id': self.user_id.id,
                'location_id': self.removal_id.location_id.id,
                'location_dest_id': self.removal_id.location_dest_id.id,
                'company_id': self.removal_id.company_id.id,
                'removal_id':self.removal_id.id
        }

        reservation = shipping_reservation_obj.create(record_reservation)

        for move in move_obj.browse(move_ids) :
            if move.customer_id :
                raise except_orm('Attention', 'Vous pouvez pas réserver sur cette arrivage concernant une commande spéciale,merci de contacter service achat ')
            qty = 0
            removal_move = move_obj.search([('removal_id','=',self.removal_id.id),('product_id','=',move.product_id.id)])
            #reservation_lines = shipping_reservation_line_obj.search([('section_id','=',removal_move.section_id.id),('move_id','=',move.id)]) # rajouter un traitement pour annuler les reservation encours
            reservation_lines = shipping_reservation_line_obj.search([('move_id','=',move.id)]) # rajouter un traitement pour annuler les reservation encours
            if reservation_lines :
                qty = sum(resv.product_qty for resv in reservation_lines)
                if qty > move.product_uom_qty :
                    raise except_orm('Attention','Le stock d\'arrivage est consomée totalement')
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
                'delivery_date': self.removal_id.delivery_date,
                'reservation_id':reservation.id,
                'partner_id':removal_move.partner_id.id,
                'section_id': removal_move.section_id.id,
                'user_id':self.user_id.id,
                'removal_id':self.removal_id.id,
                'move_id':move.id,
                'move_dest_id':removal_move.id,
            }
            move.write({'move_dest_id':removal_move.id})
            shipping_reservation_line_obj.create(reservation_line)
        self.removal_id.write({'state': 'validated'})
        return True

# class stock_shipping_reservation_line(models.TransientModel):
#
#     _name = "shipping.reservation.line"
#     _order = "scale desc"
#
#     product_id = fields.Many2one('product.product', 'Produit')
#     product_qty = fields.Float('Quantité', degits=2, default=0)
#     product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
#     move_id = fields.Many2one('stock.move', string='Mouvement')
#     delivery_date = fields.Datetime('Date de livraison')
#     location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True)
#     location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True)
#     section_id = fields.Many2one('crm.case.section', string='Département')
#     user_id = fields.Many2one('res.users', string='KAM')
#     sale_order_line_id = fields.Many2one('sale.order.line', string='Bon de commande')
#     removal_id = fields.Many2one('stock.removal', string='Enlévement')
#     reservation_id = fields.Many2one('shipping.reservation', 'Réservation', ondelete='cascade')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

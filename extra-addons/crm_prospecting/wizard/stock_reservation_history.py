
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


class wizard_normal_reservation_history(models.TransientModel):

    _name = 'wizard.stock.normal.reservation.history'

    choose_date = fields.Boolean('Avec Date ?',default=False)
    start_date = fields.Date('Date Début', required=False)
    end_date = fields.Date('Date Fin', required=False)

    @api.multi
    def open_table(self):
        ctx = {}
        ctx['search_default_group_by_section'] = True
        ctx['search_default_group_by_partner'] = True
        ctx['search_default_group_by_product'] = True
        if not self.start_date and not self.end_date :
            return {
                #'domain': "[('date', '<=', '" + data['date'] + "')]",
                'name': _('Analyse des Reservations sur Stock'),
                'view_type': 'form',
                'view_mode': 'tree,graph',
                'res_model': 'stock.normal.reservation.history',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        elif self.start_date and not self.end_date :
            return {
                'domain': "[('delivery_date', '>=', '" + self.start_date + "')]",
                'name': _('Analyse des Reservations sur Stock'),
                'view_type': 'form',
                'view_mode': 'tree,graph',
                'res_model': 'stock.normal.reservation.history',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        elif not self.start_date and self.end_date :
            return {
                'domain': "[('delivery_date', '<=', '" + self.end_date + "')]",
                'name': _('Analyse des Reservations sur Stock'),
                'view_type': 'form',
                'view_mode': 'tree,graph',
                'res_model': 'stock.normal.reservation.history',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        else :
            return {
                'domain': "[('delivery_date', '>=', '" + self.start_date + "'),('delivery_date', '<=', '" + self.end_date + "')]",
                'name': _('Analyse des Reservations sur Stock'),
                'view_type': 'form',
                'view_mode': 'tree,graph',
                'res_model': 'stock.normal.reservation.history',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }


class stock_normal_reservation_history(models.Model):
    _name = 'stock.normal.reservation.history'
    _auto = False
    _order = 'delivery_date asc'


    name =  fields.Char('Description')
    product_id = fields.Many2one('product.product', string='Article')
    product_qty= fields.Float('Quantité', degits=2, default=0)
    product_uom_id = fields.Many2one('product.uom', string='Unité de mésure')
    move_id = fields.Many2one('stock.move', string='Mouvement')
    partner_id = fields.Many2one('res.partner', 'Client')
    location_id = fields.Many2one('stock.location', 'Emplacement Source', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Emplacement Destination', required=True)
    section_id = fields.Many2one('crm.case.section', string='BU')
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande')
    user_id = fields.Many2one('res.users', string='KAM')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Bon de commande')
    removal_id = fields.Many2one('stock.removal', string='Enlévement')
    reservation_id = fields.Many2one('stock.normal.reservation', string='Réservation')
    delivery_date = fields.Datetime('Date de livraison',states={'validated': [('readonly', True)], 'cancel': [('readonly', True)]},required=True)
    state = fields.Selection([('draft', 'Brouillon'), ('cancel', 'Annulé'), ('validated', 'Validé'),('approuved', 'Approuvé'),('ready_to_deliver', 'Prêt à livrer')],'Statut',required=True,default='draft')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_normal_reservation_history')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_normal_reservation_history AS (
              SELECT
                snr.id as id,
                sr.state,
                sr.name,

                snr.delivery_date,
                snr.partner_id,
                snr.location_id,
                snr.location_dest_id,
                snr.section_id,
                snr.user_id,
                snr.sale_order_id,
                snr.removal_id,

                snrl.product_id,
                snrl.product_qty,
                snrl.product_uom_id,
                snrl.move_id,
                snrl.sale_order_line_id
                FROM
                    stock_removal sr,stock_normal_reservation snr,stock_normal_reservation_line snrl
                WHERE sr.id=snr.removal_id AND sr.state != 'done' AND snr.id=snrl.reservation_id
                GROUP BY snr.id,sr.state,sr.name,snr.delivery_date, snr.partner_id,snr.location_id,snr.location_dest_id,snr.section_id,snr.user_id,snr.sale_order_id,snr.removal_id,snrl.product_id,snrl.product_qty,snrl.product_uom_id,snrl.move_id,snrl.sale_order_line_id
            )""")

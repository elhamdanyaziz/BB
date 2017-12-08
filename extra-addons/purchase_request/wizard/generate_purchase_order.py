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


class generate_purchase(models.TransientModel):

    _name = "purchase.generate.order"
    _description = "Purchase Order"

    @api.multi
    def create_purchase_order(self):
        lines = []
        request_line_ids = self._context.get('active_ids',False)
        request_lines = self.env['purchase.request.line'].browse(request_line_ids)
        new_date = datetime.now().strftime("%Y-%m-%d")
        for line in request_lines:
            line = (0, 0,{'customer_id':line.partner_id.id if line.partner_id else False,'taxes_id':line.product_id.taxes_id._ids,'date_planned':new_date,'state':'draft','purchase_request_id':line.request_id.id,'purchase_request_line_id':line.id,'product_id': line.product_id.id,'name': line.name, 'product_qty': line.product_qty, 'product_uom': line.product_uom_id.id,'price_unit': line.product_id.lst_price})
            lines.append(line)
        return {
            'name': 'Achat',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.ui.view'].search([('name', '=', 'purchase.order.form')])[0].id,
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': {
                'default_order_line': lines,
            }
        }


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

from openerp import api
from openerp.osv import fields, osv
from lxml import etree
from openerp.tools.translate import _
from datetime import datetime


class res_partner(osv.osv):

    _inherit = "res.partner"

    _columns = {
        'unreconciled_aml_ids':fields.one2many('account.move.line', 'partner_id', domain=['&',('date_maturity', '<=', datetime.now().strftime("%Y-%m-%d")),'&', ('reconcile_id', '=', False), '&',
                            ('account_id.active','=', True), '&', ('account_id.type', '=', 'receivable'), ('state', '!=', 'draft'), '&',('voucher_state', '=', 'open'),'&',('move_line_type', '=', 'basic')]),
        'unpaid_aml_ids': fields.one2many('account.move.line', 'partner_id', domain=['&', ('reconcile_id', '=', False), '&',
                                                                                           ('account_id.active', '=',True), '&', ('account_id.type', '=','receivable'),('state', '!=', 'draft'), '&',('voucher_state', '=', 'open'),'&',('move_line_type', '=', 'to_sedof'),'&',('state_action', '=', 'noprocessed')]),

    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

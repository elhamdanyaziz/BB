# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
{
    "name": "Sale QUotation",
    'version': '8.0.0.0.0',
    'category': 'Sales Management',
    'sequence': 14,
    'author':  'SMAPS',
    'website': 'www.smartapsconseil.com',
    'license': 'AGPL-3',
    'summary': '',
    "description": """
Sale Global Discount
====================
defference beetwen quotation and order sale
    """,
    "depends": [
        "sale","stock_account"
    ],
    'external_dependencies': {
    },
    "data": [
        #'wizard/sale_global_discount_wizard_view.xml',
        'views/sale_order_view.xml',
        'views/report_saleorder.xml',
        'views/report_salequotation.xml',
        'views/ir_qweb.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

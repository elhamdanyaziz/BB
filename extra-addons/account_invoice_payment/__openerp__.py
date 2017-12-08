# -*- coding: utf-8 -*-
#/#############################################################################
#
#
#    Copyright (C) 20015-TODAY
#    Author : ABDELLATOF BENZBIRIA
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
#/#############################################################################
{
    'name': 'Bill of exchange payment',
    'version': '1.0',
    'category': 'Accounting/Payment method',
    'description': """
        Allow to manage payment by bill of exchange
    """,
    'author': 'SMAPS',
    'depends': ["account","account_voucher"],
    'init_xml': [],
    'data': [
              'views/account_voucher_view.xml',
              'views/account_journal_view.xml',
              #'wizard/payment_view.xml',
              'wizard/bank_transfer_view.xml',
              'wizard/payment_statement_view.xml'
    ],
    'installable': True,
    'auto_install': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

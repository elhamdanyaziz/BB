
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

{
    "name": "Gestion des opportunités ",
    'website': '',
    "version": "1.0",
    "depends": ['base','account_followup','crm','sale','sales_team','sale_crm','stock','sale_margin','sale_firm','purchase_request'],
    "author": "SMAPS",
    "category": "SALES",
    "description": """
        Ce module permet de :
         - enrichir la fiche CRM
         - Catégoriser les opportunités
    """,
    "init_xml": [],
    'update_xml': [
        'security/crm_security.xml',
        'security/res.groups.csv',
        'crm_lead_view.xml',
        'crm_partner_view.xml',
        'wizard/deposit_inv_view.xml',
        'wizard/stock_reservation_view.xml',
        'crm_sale_view.xml',
        'wizard/stock_shipping_reservation_view.xml',
        'sale_order_limit_credit_control_template_email.xml',
        'wizard/stock_reservation_history_view.xml',
        'report/stock_report.xml',
        'report/report_stockpreparation.xml',
        'report/account_report.xml',
        'report/report_invoice.xml'

    ],
    'data': [],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

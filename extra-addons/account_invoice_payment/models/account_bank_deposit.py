# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp import models, fields, api, _
import time
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import workflow
from openerp.tools import float_compare


class account_bank_deposit(models.Model):

    _name = "account.bank.deposit"

    name = fields.Char(string='Numéro de Remise',size=7)
    transfert_date = fields.Date(string='Date de Remise')
    state = fields.Selection(
            [('draft','Draft'),
             ('validated','Validé'),
             ('sent','Envoyé')
            ], 'Statut', readonly=True, track_visibility='onchange',default='draft', copy=False)
    ref_customer = fields.Char(string='Référence Client',size=12)
    bank_agency_code = fields.Char(string='Code Agence',size=3)
    bank_agency_name = fields.Char(string='Nom Agence')
    account_number = fields.Char(string='Numéro de Compte',size=9)
    amount_total = fields.Float('Montant')
    number_lcn = fields.Integer('Nombre de LCN')
    number_check = fields.Integer('Nombre de Chèques')
    customer_name = fields.Char(string='Nom du Client')
    note = fields.Text(string='Description')
    type = fields.Selection(
            [('check','Remise Chèques'),
             ('effect','Remise Effets'),
            ], 'Type', readonly=True, track_visibility='onchange',default='check', copy=False)
    line_ids = fields.One2many('account.bank.deposit.line', 'deposit_id', 'Détails',readonly=False)
    line_lcn_ids = fields.One2many('account.bank.deposit.line', 'deposit_id', 'Détails', readonly=False)
    line_check_ids = fields.One2many('account.bank.deposit.line', 'deposit_id', 'Détails', readonly=False)
    user_id = fields.Many2one('res.users', string='Utilisateur')

    @api.multi
    def action_validate(self):
        self.state = 'validated'
        return True

    @api.multi
    def action_deposit(self):
        self.state = 'sent'
        self.transfert_date = time.strftime('%Y-%m-%d')
        return True



class account_bank_deposit_line(models.Model):

    _name = "account.bank.deposit.line"


    partner_id = fields.Many2one('res.partner',string='TIRÉ/TIREUR')
    bank = fields.Char(string='Banque')
    city = fields.Char(string='Ville')
    ref_lcn = fields.Char('N° LCN')
    ref_check = fields.Char('N° du Chèque')
    amount = fields.Float('Montant')
    deadline_date = fields.Date(string='Échéance')
    deposit_id = fields.Many2one('account.bank.deposit', string='Remise')
    type = fields.Selection(related='deposit_id.type', store=True, readonly=True, copy=False)


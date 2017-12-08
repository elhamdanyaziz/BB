
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
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
# from openerp.osv.orm import setup_modifiers
# from lxml import etree


class mail_compose_message(models.TransientModel):

    _inherit = 'mail.compose.message'

    @api.v7
    def send_mail(self, cr, uid, ids, context=None):
        res = super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)
        active_model = context.get('active_model',False)
        partner_id = context.get('active_id', False)
        type = context.get('type', False)
        wizard = self.browse(cr, uid, ids, context=context)
        if active_model == 'res.partner' :
            partner = self.pool.get('res.partner').browse(cr,uid,partner_id)
            if type == 'invoice' :
                followup = partner.action_done()
                followup.write({'email_note':wizard.body})
            if type == 'unpaid' :
                followup = partner.unpaid_action_done()
                followup.write({'email_note':wizard.body})
        return res

class res_partner(models.Model):

    _inherit = 'res.partner'

    # @api.model
    # def _get_domain_aml(self):
    #     new_date = datetime.now().strftime("%Y-%m-%d")
    #     domain = ['&',('date_maturity', '<=', new_date),'&', ('reconcile_id', '=', False), '&', ('account_id.active', '=', True), '&',('account_id.type', '=', 'receivable'), ('state', '!=', 'draft')]
    #     print "my domain",new_date,domain
    #     return domain

    @api.one
    def _compute_readonly_accounting(self):
        self.accounting_readonly = self.env.user.accounting_readonly


    owner = fields.Boolean("Maître d'ouvrage",default=False)
    office_study = fields.Boolean("Bureau d'Étude",default=False)
    customer_class = fields.Selection([('a','A'),('b','B'),('c','C')],'Classe',select=True, readonly=False)
    categ_id = fields.Many2one('res.partner.category',string='Catégorie')
    customer_code = fields.Char("Code Client",default="/")
    customer_discount = fields.Float('Remise(%)', degits=2, default=0)
    garanty = fields.Selection([('ct', '001'), ('cqs', '002'), ('cqp', '003')], 'Garantie')
    amount_garanty = fields.Float('Montant Garantie', degits=2, default=0)
    deadline_garanty = fields.Date(string='Date Échéance',readonly=False,index=True)
    classification_id = fields.Many2one('res.partner.classification', string='Classification')
    litigation = fields.Text("Contentieux")
    due_date = fields.Date(string='Date Échéance',readonly=False,compute='_compute_due_date',store=True)
    deadline_ok = fields.Boolean('Garantie Payé',default=False)
    blocking_ok = fields.Boolean('Client bloqué ?', default=False)
    blocking_id = fields.Many2one('res.partner.blocking.pattern', string='Motif de blockage')
    city_id = fields.Many2one('crm.city', string='Ville')
    tax_identification = fields.Char("Identifiant Fiscal")
    payment_condition = fields.Many2one('res.partner.payment.condition', string='Condition de paiement')
    provider_foreign_ok = fields.Boolean('Fournisseur Étranger ?', default=False)
    local_ok = fields.Boolean('Fournisseur Locale ?', default=False)
    voucher_ids = fields.One2many('account.voucher', 'partner_id', 'Impayés',domain=[('state','=','unpaid')])
    unpaid_responsible_id = fields.Many2one('res.users', string='Responsable')
    unpaid_note = fields.Text('Promesse de paiement client', help="Notes", track_visibility="onchange")
    unpaid_next_action = fields.Text('Action suivante', copy=False)
    unpaid_next_action_date = fields.Date('Date Action suivante', copy=False)
    unpaid_amount_due = fields.Float(string='Montant dû', readonly=False, compute='_compute_unpaid_amount_due', store=True)
    date = fields.Date('Date', select=1,readonly=True,default=lambda *a: time.strftime('%Y-%m-%d'))
    property_account_expense = fields.Many2one('account.account', string='Compte de charge',domain=[('type','not in',('view','consolidation'))])
    taxe_ids = fields.Many2many('account.tax', 'res_partner_account_tax', 'partner_id', 'tax_id', string='Taxes fournisseurs')
    total_invoiced = fields.Float(string="Facturé",groups='account.group_account_invoice',compute='_compute_invoice_total')
    invoice_ids = fields.One2many('account.invoice', 'partner_id', 'Factures',domain=[('state','not in',('draft','cancel'))])
    blocking_ok_related = fields.Boolean(related='blocking_ok', store=True, readonly=True, copy=False)
    blocking_id_related = fields.Many2one(related='blocking_id', store=True, readonly=True, copy=False)
    customer_related = fields.Boolean(related='customer', store=True, readonly=True, copy=False)
    supplier_related = fields.Boolean(related='supplier', store=True, readonly=True, copy=False)
    accounting_readonly = fields.Boolean(compute='_compute_readonly_accounting')

    @api.multi
    def action_garanty_payed(self):
        self.deadline_ok = True

    @api.one
    @api.depends('deadline_garanty')
    def _compute_due_date(self):
        if self.deadline_garanty :
            due_date = (datetime.strptime(self.deadline_garanty,'%Y-%m-%d')-relativedelta(months=3)).strftime('%Y-%m-%d')
            self.due_date = due_date

    @api.one
    @api.depends('invoice_ids')
    def _compute_invoice_total(self):
        if self.invoice_ids :
            self.total_invoiced = sum([inv.amount_untaxed for inv in self.invoice_ids])
        else :
            self.total_invoiced = 0

    @api.one
    @api.depends('unpaid_aml_ids', 'unpaid_aml_ids.result')
    def _compute_unpaid_amount_due(self):
        for partner in self :
            if partner.unpaid_aml_ids :
                unpaid_amount_due = sum([x.result for x in partner.unpaid_aml_ids])
                self.unpaid_amount_due = unpaid_amount_due

    # @api.model
    # def create(self, values):
    #     if 'supplier' in values.keys() :
    #         if values['supplier']:
    #             if 'customer' in values.keys():
    #                 customer_indice = ''
    #                 if values['customer'] :
    #                     partners = self.search([('customer','=',True)])
    #                     nbr_partner = len(partners)
    #                     if 0 <= nbr_partner < 9 :
    #                         code = ('0'+values['name'][0]+'00'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     elif 9 <= nbr_partner < 99 :
    #                         code = ('0'+values['name'][0]+'0'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     else :
    #                         code = ('0'+values['name'][0]+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #             else :
    #                 if values['provider_foreign_ok']:
    #                     partners = self.search([('supplier','=',True),('provider_foreign_ok','=',True)])
    #                     nbr_partner = len(partners)
    #                     if 0 <= nbr_partner < 9 :
    #                         code = ('E'+values['name'][0]+'00'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     elif 9 <= nbr_partner < 99 :
    #                         code = ('E'+values['name'][0]+'0'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     else :
    #                         code = ('E'+values['name'][0]+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                 else :
    #                     partners = self.search([('supplier', '=', True), ('provider_foreign_ok', '=', False)])
    #                     nbr_partner = len(partners)
    #                     if 0 <= nbr_partner < 9 :
    #                         code = ('L'+values['name'][0]+'00'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     elif 9 <= nbr_partner < 99 :
    #                         code = ('L'+values['name'][0]+'0'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     else :
    #                         code = ('L'+values['name'][0]+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #         else :
    #             if 'customer' in values.keys():
    #                 if values['customer'] :
    #                     partners = self.search([('customer','=',True)])
    #                     nbr_partner = len(partners)
    #                     if 0 <= nbr_partner < 9 :
    #                         code = ('0'+values['name'][0]+'00'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     elif 9 <= nbr_partner < 99 :
    #                         code = ('0'+values['name'][0]+'0'+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #                     else :
    #                         code = ('0'+values['name'][0]+str(nbr_partner + 1)).upper()
    #                         values['customer_code'] = code
    #     return super(res_partner, self).create(values)

    @api.model
    def create(self, values):
        partner_code = self.env['res.partner.code'].search([('name', '=', (values['name'][0]).upper())])
        if not partner_code:
            raise except_orm(_('Attention!'), _('la Lettre %s n\'as pas d\'entrée dans la matrice des lettres;Merci de la créer !.' % ((values['name'][0]).upper())))
        if 'supplier' in values.keys() :
            if values['supplier']:
                if 'customer' in values.keys():
                    customer_indice = ''
                    if values['customer'] :
                        #################verify dans la mertice####################
                        customer_indice = partner_code.customer_indice
                        ###########################################################
                        if 0 <= customer_indice < 9 :
                            code = ('0'+values['name'][0]+'00'+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        elif 9 <= customer_indice < 99 :
                            code = ('0'+values['name'][0]+'0'+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        else :
                            code = ('0'+values['name'][0]+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        partner_code.write({'customer_indice':customer_indice+1})
                        record_account = {
                            'name':values['name'],
                            'code':'3421'+code+'00',
                            'parent_id':11608,
                            'type':'receivable',
                            'user_type':23,
                            'reconcile':True
                        }
                        account = self.env['account.account'].create(record_account)
                        # values['property_account_receivable'] = account.id
                        # record_account = {
                        #     'name': values['name'],
                        #     'code': '4411'+code,
                        #     'parent_id': 15901,
                        #     'type': 'payable',
                        #     'user_type': 23,
                        #     'reconcile': True
                        # }
                        # account = self.env['account.account'].create(record_account)
                        # values['property_account_payable'] = account.id
                    else :
                        if values['provider_foreign_ok']:
                            customer_indice = partner_code.supplier_indice_provider_foreign
                            if 0 <= customer_indice < 9 :
                                code = ('E'+values['name'][0]+'000'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 9 <= customer_indice < 99 :
                                code = ('E'+values['name'][0]+'00'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 99 <= customer_indice < 999 :
                                code = ('E'+values['name'][0]+'0'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            else :
                                code = ('E'+values['name'][0]+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            partner_code.write({'supplier_indice_provider_foreign': customer_indice + 1})
                            record_account = {
                                'name':values['name'],
                                'code':'4411'+code,
                                'parent_id':15901,
                                'type':'payable',
                                'user_type':23,
                                'reconcile':True
                            }
                            account = self.env['account.account'].create(record_account)
                            values['property_account_payable'] = account.id
                        elif values['local_ok']:
                            customer_indice = partner_code.supplier_indice_local
                            if 0 <= customer_indice < 9 :
                                code = ('L'+values['name'][0]+'000'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 9 <= customer_indice < 99 :
                                code = ('L'+values['name'][0]+'00'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 99 <= customer_indice < 999 :
                                code = ('E'+values['name'][0]+'0'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            else :
                                code = ('L'+values['name'][0]+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            partner_code.write({'supplier_indice_local': customer_indice + 1})
                            record_account = {
                                'name':values['name'],
                                'code':'4411'+code,
                                'parent_id':15901,
                                'type':'payable',
                                'user_type':23,
                                'reconcile':True
                            }
                            account = self.env['account.account'].create(record_account)
                            values['property_account_payable'] = account.id
                        else :
                            customer_indice = partner_code.supplier_indice_several
                            if 0 <= customer_indice < 9 :
                                code = ('D'+values['name'][0]+'000'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 9 <= customer_indice < 99 :
                                code = ('D'+values['name'][0]+'00'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            elif 99 <= customer_indice < 999 :
                                code = ('E'+values['name'][0]+'0'+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            else :
                                code = ('D'+values['name'][0]+str(customer_indice + 1)).upper()
                                values['customer_code'] = code
                            partner_code.write({'supplier_indice_several': customer_indice + 1})
                            record_account = {
                                'name':values['name'],
                                'code':'4411'+code,
                                'parent_id':15901,
                                'type':'payable',
                                'user_type':23,
                                'reconcile':True
                            }
                            account = self.env['account.account'].create(record_account)
                            values['property_account_payable'] = account.id
            else :
                if 'customer' in values.keys():
                    if values['customer'] :
                        customer_indice = partner_code.customer_indice
                        if 0 <= customer_indice < 9 :
                            code = ('0'+values['name'][0]+'00'+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        elif 9 <= customer_indice < 99 :
                            code = ('0'+values['name'][0]+'0'+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        else :
                            code = ('0'+values['name'][0]+str(customer_indice + 1)).upper()
                            values['customer_code'] = code
                        partner_code.write({'customer_indice': customer_indice + 1})
                        record_account = {
                            'name':values['name'],
                            'code':'3421'+code+'00',
                            'parent_id':11608,
                            'type':'receivable',
                            'user_type':23,
                            'reconcile':True
                        }
                        account = self.env['account.account'].create(record_account)
                        values['property_account_receivable'] = account.id
        return super(res_partner, self).create(values)

    @api.multi
    def action_done(self):
        #res = super(res_partner, self).action_done()
        #partner = self.browse(self.id)
        self.write({'payment_next_action_date': False, 'payment_next_action': '', 'payment_responsible_id': False})
        new_date = datetime.now().strftime("%Y-%m-%d")
        record_history_followup = {
            'partner_id':self.id,
            'followup_date':new_date,
            'followup_amount':self.payment_amount_due,
            'note':self.payment_next_action,
            'payment_note':self.payment_note
        }
        history_followup = self.env['account.followup.history'].create(record_history_followup)
        for invoice in self.unreconciled_aml_ids :
            record_history_followup_line = {
                'followup_id':history_followup.id,
                'invoice_date':invoice.date,
                'number':invoice.move_id.name,
                'deadline_date':invoice.date_maturity,
                'deadline_delay': invoice.deadline_delay,
                'invoice_amount':invoice.result,
                'note': invoice.note
            }
            self.env['account.followup.history.line'].create(record_history_followup_line)
        return history_followup

    @api.multi
    def unpaid_action_done(self):
        partner = self.browse(self._uid)
        partner.write({'payment_next_action_date': False, 'payment_next_action': '', 'payment_responsible_id': False})
        new_date = datetime.now().strftime("%Y-%m-%d")
        record_history_followup = {
            'partner_id':self.id,
            'followup_date':new_date,
            'followup_amount':self.unpaid_amount_due,
            'note':self.unpaid_next_action,
            'payment_note':self.unpaid_note
        }
        history_followup = self.env['account.followup.history'].create(record_history_followup)
        for invoice in self.unpaid_aml_ids :
            record_history_followup_line = {
                'followup_id':history_followup.id,
                'invoice_date':invoice.date,
                'number':invoice.move_id.name,
                #'deadline_date':invoice.date_maturity,
                #'deadline_delay': invoice.deadline_delay,
                'invoice_amount':invoice.result,
                'note': invoice.note
            }
            self.env['account.followup.history.line'].create(record_history_followup_line)
        return history_followup

    def invoice_action_followup_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        template_id = False
        # try:
        #     template_id = ir_model_data.get_object_reference(cr, uid, 'sale', 'email_template_edi_sale')[1]
        # except ValueError:
        #     template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'res.partner',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'type':'invoice'
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def unpaid_action_followup_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        template_id = False
        # try:
        #     template_id = ir_model_data.get_object_reference(cr, uid, 'sale', 'email_template_edi_sale')[1]
        # except ValueError:
        #     template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'res.partner',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'type':'unpaid'
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.v7
    def compute_deadline_delay(self, cr, uid, ids=False, context=None):
        partner_ids = self.search(cr, uid, [('customer','=',True)],context=context)
        for partner in self.browse(cr,uid,partner_ids,context=context) :
            if partner.unreconciled_aml_ids :
                for line in partner.unreconciled_aml_ids :
                    if line.date_maturity and line.date_maturity < datetime.now().strftime("%Y-%m-%d") :
                        deadline_delay = abs((datetime.strptime(datetime.now().strftime("%Y-%m-%d"),'%Y-%m-%d')-datetime.strptime(line.date_maturity, '%Y-%m-%d')).days)
                        line.write({'deadline_delay':deadline_delay})
                    else:
                        deadline_delay = 0
                        line.write({'deadline_delay': deadline_delay})
        return True

    # @api.model
    # def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
    #     context = self._context
    #     res = super(res_partner, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=False)
    #     user = self.env['res.users'].browse(self._uid)
    #     doc = etree.XML(res['arch'])
    #     if user.accounting_readonly :
    #         for field in ['property_account_position','property_account_receivable','payment_condition','property_payment_term','credit_limit','garanty','amount_garanty','deadline_garanty','last_reconciliation_date','bank_ids']:
    #             nodes = doc.xpath("//field[@name=%s]"%field)
    #             for node in nodes:
    #                 node.set('readonly', '1')
    #                 setup_modifiers(node, res['fields'][field])
    #         res['arch'] = etree.tostring(doc)
    #     return res


class res_partner_code(models.Model):

    _name = 'res.partner.code'

    name = fields.Char("Lettre")
    customer_indice = fields.Integer("Compteur Client",default=1)
    supplier_indice = fields.Integer("Compteur Fournisseur",default=1)
    supplier_indice_provider_foreign = fields.Integer("Compteur Fournisseur Etranger", default=1)
    supplier_indice_local = fields.Integer("Compteur Fournisseur Locaux", default=1)
    supplier_indice_several = fields.Integer("Compteur Fournisseur Divers", default=1)

class res_partner_blocking_pattern(models.Model):

    _name = 'res.partner.blocking.pattern'

    name = fields.Char("Motif")


class res_partner_classification(models.Model):

    _name = 'res.partner.classification'

    name = fields.Char("Nom Classification")
    code = fields.Char("Code Classification")

class res_partner_payment_condition(models.Model):

    _name = 'res.partner.payment.condition'

    name = fields.Char("Condition de paiement")


class history_account_followup(models.Model):

    _name = 'account.followup.history'

    partner_id = fields.Many2one('res.partner', string='Client')
    followup_date = fields.Datetime('Date de relance')
    followup_amount = fields.Float('Montant')
    note = fields.Text('Actions')
    payment_note = fields.Text('Promesses')
    line_ids = fields.One2many('account.followup.history.line', 'followup_id', 'Factures')
    email_note = fields.Html('Mail')


class history_account_followup_line(models.Model):

    _name = 'account.followup.history.line'

    followup_id = fields.Many2one('account.followup.history', string='Relance')
    invoice_date = fields.Datetime('Date de relance')
    number = fields.Char('Némuro de facture')
    deadline_date = fields.Datetime('Date échéance')
    invoice_amount = fields.Float('Montant')
    deadline_delay = fields.Integer('Nombre de jours de retard')
    note = fields.Text('Notes')

class account_move_line(models.Model):

    _inherit = 'account.move.line'

    #deadline_delay_1 = fields.Integer('Nombre de jours de retard', compute='_compute_deadline_delay', readonly=True, store=True)
    deadline_delay = fields.Integer('Nombre de jours de retard',readonly=True)
    note = fields.Text('Notes')
    state_action = fields.Selection([('noprocessed', 'Non Traité'), ('processed', 'Traité')], 'Type Action',default='noprocessed')


    ##########a rendre dans le schiduler#####
    # @api.one
    # def _compute_deadline_delay_1(self):
    #     for partner in self :
    #         if partner.unreconciled_aml_ids :
    #             for line in partner.unreconciled_aml_ids :
    #                 if line.date_maturity and line.date_maturity < datetime.now().strftime("%Y-%m-%d") :
    #                     deadline_delay = abs(( datetime.strptime(datetime.now().strftime("%Y-%m-%d"), '%Y-%m-%d') - datetime.strptime(line.date_maturity, '%Y-%m-%d')).days)
    #                     line.write({'deadline_delay':deadline_delay})
    #                 else:
    #                     deadline_delay = 0
    #                     line.write({'deadline_delay': deadline_delay})

class res_partner_bank(models.Model):

    _inherit = 'res.partner.bank'

    bank_tel = fields.Char("Tél Banque")

class res_users(models.Model):

    _inherit = 'res.users'

    force_picking_out_ok = fields.Boolean("Forcer la livraison ?")
    accounting_readonly = fields.Boolean('Comptabilité en lecture', default=False)
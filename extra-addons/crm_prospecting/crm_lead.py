
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


class crm_lead(models.Model):

    _inherit = 'crm.lead'

    # @api.model
    # @api.depends('quotations_ids')
    # def _get_domain_quotation(self):
    #     domain = [('state', 'in', ('draft', 'sent')), ('opp_id', 'in', self.quotations_ids._ids)]
    #     return domain
    #
    # @api.model
    # def _get_domain_order(self):
    #     print "ffffff",self.id,self
    #     domain = [('is_quotation','=',True),('opp_id', '=', self.id)]
    #     print "my dommmmm",domain
    #     return domain


    lead_type_id = fields.Many2one('crm.lead.type', 'Type d\'Opprtunité')
    spinneret_id = fields.Many2one('crm.spinneret', 'Filière')
    job_id = fields.Many2one('crm.job', 'Métier')
    city = fields.Char('Ville')
    city_id = fields.Many2one('crm.city', 'Ville')
    owner_id = fields.Many2one('res.partner', 'Maître d\'ouvrage',domain=[('owner','=',1)])
    office_study_id = fields.Many2one('res.partner', 'Bureau d\'étude', domain=[('office_study', '=', 1)])
    tender_number = fields.Char('Numéro d\'appel d\'offre')
    market_number = fields.Char('Numéro du marché')
    quotations_ids = fields.One2many('sale.order','opp_id',string='Devis',domain=[('is_quotation','=',True)])
    order_ids = fields.One2many('sale.order', 'opp_id', string='Bons de commande',domain=[('is_order','=',True)])
    quotation_id = fields.Many2one('sale.order', 'Devis Favori')
    quotation_amount = fields.Float('Montant devis favori', readonly=True)
    max_quotations = fields.Float('Max des devis', compute='_compute_max_quotations', readonly=True)
    total_orders = fields.Float('Total des bons de commande', compute='_compute_total_orders', readonly=True)
    move_lines = fields.One2many('stock.move', 'opp_id', 'Livraisons',readonly=1)
    code = fields.Char('Code')
    date = fields.Date('Date de création', readonly=True, index=True, copy=False,default=lambda *a: time.strftime('%Y-%m-%d'))
    stage_id = fields.Many2one('crm.case.stage', 'Étape', select=True)
    state = fields.Many2one('crm.case.stage', 'Statut', select=True)
    picking_ids = fields.One2many('stock.picking', 'opp_id', 'BLs', domain=[('picking_type_id', '=', 2)])


    @api.depends('quotations_ids')
    def _compute_max_quotations(self):
        total = 0
        if self.quotations_ids :
            for quotation in self.quotations_ids:
                if quotation.amount_untaxed_with_discount >= total :
                    total = quotation.amount_untaxed_with_discount
        self.max_quotations = total

    @api.depends('order_ids')
    def _compute_total_orders(self):
        total = 0
        if self.order_ids :
            for order in self.order_ids:
                total = total+order.amount_untaxed
        self.total_orders = total


    # @api.onchange('section_id')
    # def _compute_job_id(self):
    #     if self.section_id :
    #         jobs = self.env['crm.job'].search([('crm_case_section_id','=',self.section_id.id)])
    #         if jobs :
    #             job_ids = jobs._ids
    #             self.job_id = job_ids[0]
    #             return {'domain': {'job_id': [('id', 'in', list(job_ids))]}}
    #     return {'domain': {'job_id': [('id', 'in', list([]))]}}
    @api.onchange('lead_type_id')
    def _onchange_lead_type_id(self):
        if self.lead_type_id :
            if self.lead_type_id.state_ids :
                self.state = self.lead_type_id.state_ids._ids[0]
                return {'domain': {'state': [('id', 'in', list(self.lead_type_id.state_ids._ids))]}}
            else :
                return {'domain': {'state': [('id', 'in', list([]))]}}
        return {'domain': {'state': [('id', 'in', list([]))]}}

    @api.onchange('id')
    def _onchange_opp_id(self):
        if self.id :
            quotations = self.env['sale.order'].search([('is_quotation','=',True),('opp_id','=',self.id)])
            if quotations :
                self.quotation_id = quotations._ids[0]
                return {'domain': {'quotation_id': [('id', 'in', list([quotations._ids]))]}}
            else :
                return {'domain': {'quotation_id': [('id', 'in', list([]))]}}
        return {'domain': {'quotation_id': [('id', 'in', list([]))]}}


    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id and self.user_id.default_section_id:
            self.section_id = self.user_id.default_section_id.id

    @api.onchange('quotation_id')
    def _onchange_quotation_id(self):
        if self.quotation_id :
            self.partner_id = self.quotation_id.partner_id.id
            self.quotation_amount = self.quotation_id.amount_untaxed_with_discount


    @api.model
    def create(self, values):
        if values.get('section_id'):
            section_id = values.get('section_id')
            section = self.env['crm.case.section'].browse(section_id)
            opps = self.search([('section_id','=',section_id)])
            if 0 <= len(opps) < 9:
                values['code'] = section.code+'_000'+str(len(opps)+1)+'_'+str(datetime.today().month)+'_'+str(datetime.today().year)
            elif 9 <= len(opps) < 99:
                values['code'] = section.code+'_00'+str(len(opps)+1)+'_'+str(datetime.today().month)+'_'+str(datetime.today().year)
            elif 99 <= len(opps) < 999:
                values['code'] = section.code+'_0'+str(len(opps)+1)+'_'+str(datetime.today().month)+'_'+str(datetime.today().year)
            else :
                values['code'] = section.code+'_'+str(len(opps)+1)+'_'+str(datetime.today().month)+'_'+str(datetime.today().year)
        return super(crm_lead, self).create(values)

    @api.onchange('section_id')
    def _onchange_section_id(self):
        if self.section_id :
            if self.section_id.spinneret_ids :
                self.spinneret_id = self.section_id.spinneret_ids._ids[0]
                return {'domain': {'spinneret_id': [('id', 'in', list(self.section_id.spinneret_ids._ids))]}}
            else :
                return {'domain': {'spinneret_id': [('id', 'in', list([]))]}}
        return {'domain': {'spinneret_id': [('id', 'in', list([]))]}}


    @api.onchange('spinneret_id')
    def _onchange_spinneret_id(self):
        if self.spinneret_id :
            if self.spinneret_id.job_ids :
                self.job_id = self.spinneret_id.job_ids._ids[0]
                return {'domain': {'job_id': [('id', 'in', list(self.spinneret_id.job_ids._ids))]}}
            else :
                return {'domain': {'job_id': [('id', 'in', list([]))]}}
        return {'domain': {'job_id': [('id', 'in', list([]))]}}



class crm_lead_type(models.Model):

    _name = 'crm.lead.type'

    name = fields.Char("Type d'Opprtunuité",size=16384)
    state_ids = fields.Many2many('crm.case.stage', 'crm_lead_stage', 'crm_lead_id', 'stage_id', string='Statuts')


class crm_job(models.Model):

    _name = 'crm.job'

    name = fields.Char("Métier",size=16384)
    #crm_case_section_id = fields.Many2one('crm.case.section', 'Département')

class crm_spinneret(models.Model):
    _name = 'crm.spinneret'

    name = fields.Char("Filière", size=16384)
    job_ids = fields.Many2many('crm.job', 'crm_spinneret_job', 'crm_spinneret_id', 'job_id', string='Métiers')


class crm_case_section(models.Model):

    _inherit = 'crm.case.section'

    location_id = fields.Many2one('stock.location', 'Emplacement du Stock')
    spinneret_ids = fields.Many2many('crm.spinneret', 'crm_case_section_spinneret', 'section_id', 'spinneret_id', string='Filières')
    total_invoiced = fields.Float(string="Facturé",compute='_compute_invoice_total')
    invoice_ids = fields.One2many('account.invoice', 'section_id', 'Factures',domain=[('state','not in',('draft','cancel'))])

    @api.one
    @api.depends('invoice_ids')
    def _compute_invoice_total(self):
        if self.invoice_ids :
            self.total_invoiced = sum([inv.amount_untaxed for inv in self.invoice_ids])
        else :
            self.total_invoiced = 0


class crm_city(models.Model):

    _name = 'crm.city'

    name = fields.Char("Ville",size=16384)
    province = fields.Char("Province", size=16384)
    region = fields.Char("Région", size=16384)
    zip_code = fields.Char("Code Postale", size=16384)


# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp import models, fields


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    notes = fields.Html()

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        result = super(SaleOrder, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        result['bom_id'] = line.bom_id and line.bom_id.id or False
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # def has_bom_ids(self, cr, uid, ids, field_name, arg, context=None):
    #     for order_line in self.browse(cr,uid,ids,context):
    #         bom_ids=self.pool.get('mrp.bom').search(cr,uid,[('product_tmpl_id','=',order_line.product)])
    #         if bom_ids :
    #     return True

    bom_id = fields.Many2one(comodel_name="mrp.bom", string="Nomenclature", required=False)
    #has_bom_ids = fields.Boolean(string="Posséde une nomenclature",compute=has_bom_ids)

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        res = super(SaleOrderLine, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        if product:
            bom_ids=self.pool.get('mrp.bom').search(cr,uid,[('product_tmpl_id','=',product)])
            if bom_ids :
                domain=[('id','in',bom_ids)]
                res['domain'].update({'bom_id': domain})
        res['value'].update({'bom_id': False})
        return res








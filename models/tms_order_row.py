from odoo import api, fields, models, _

class TmtrExchangeTmsOrderRow(models.Model):
    _inherit = ['tms.order.row']

    counterparty_id = fields.Many2one('tmtr.exchange.1c.counterparty', 'Client')

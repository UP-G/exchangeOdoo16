from odoo import api, fields, models, _

class TmtrExchangeTmsDeliveryRow(models.Model):
    _inherit = ['tms.delivery.row']

    counterparty_id = fields.Many2one('tmtr.exchange.1c.counterparty', string='Client')

    # def get_counterparty(self, ref_key):
    #     client = self.env['tmtr.exchange.1c.counterparty'].search([('ref_key', '=', ref_key)])
    #     return client

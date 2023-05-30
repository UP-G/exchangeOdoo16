from odoo import api, fields, models, _

class TmtrExchangeOneCInteraction(models.Model):
    _name = 'tmtr.exchange.1c.interaction'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)

    def test_button(self):
        return
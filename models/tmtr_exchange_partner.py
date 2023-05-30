from odoo import api, fields, models, _

class TmtrExchangeOneCPartner(models.Model):
    _name = 'tmtr.exchange.1c.partner'

    partner_id = fields.Many2one('res.partner', string='Partner')

    def test_button(self):
        return
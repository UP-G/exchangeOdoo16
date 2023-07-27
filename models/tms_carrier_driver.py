from odoo import api, fields, models, _

class TmtrExchangeTmsCarrierDriver(models.Model):
    _inherit = ['tms.carrier.driver']

    ref_key = fields.Char(string='ref_key')

    def get_carrier_driver(self, ref_key):
        driver = self.search([('ref_key', '=', ref_key)])
        if not driver:
            driver = self.env['tmtr.exchange.1c.individual'].get_individual(ref_key)
        return driver
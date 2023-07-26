from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCTransportCompany(models.Model):
    _name = 'tmtr.exchange.1c.company.route'
    _description = '1C routes of company'

    ref_key = fields.Char(string='ref_key')
    full_name = fields.Char(string="route name")
    driver_key = fields.Char(string="dirver key")
    tc_key=fields.Char(string="transport company key")

    carrier_route_id = fields.Many2one('tms.carrier.route', string='carrier route id')
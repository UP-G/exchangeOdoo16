from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCCompanyRoute(models.Model):
    _name = 'tmtr.exchange.1c.company.route'
    _description = '1C routes of company'

    ref_key = fields.Char(string='ref_key')
    driver_key = fields.Char(string="dirver key")
    tc_key=fields.Char(string="transport company key")

    name = fields.Char(string="route name")

    carrier_route_id = fields.Many2one('tms.carrier.route', string='carrier route id')
    individual_id = fields.Many2one('tmtr.exchange.1c.individual', string='carrier driver id')
    company_id = fields.Many2one('tmtr.exchange.1c.transport.company', string='transport company id')
    route_id = fields.Many2one('tms.route', string='route id')

    def create_company_route(self, data):
        for impl in data['Реализации']:
            routes = self.search([('ref_key', '=', impl['Маршрут_Key'])])
            if not routes:
                self.create_new_entry(data, impl)
            else:
                tc_keys = [r.tc_key for r in routes]
                if not impl['ТК'] in tc_keys:
                    self.create_new_route(data)
        self.create_tms_carrier_route()

    def create_new_entry(self, data, impl):
        route_tms = self.env['tms.route'].search([('route_1c_key','=',impl['Маршрут_Key'])])
        individual = self.env['tmtr.exchange.1c.individual'].search([('ref_key','=',data['Водитель_Key'])])
        company = self.env['tmtr.exchange.1c.transport.company'].search([('ref_key','=', impl['ТК'])])
        self.create({
            'ref_key': impl['Маршрут_Key'],
            'driver_key': data['Водитель_Key'],
            'tc_key': impl['ТК'],
            'name': data['МаршрутыДоставки'],
            'individual_id': individual.id,
            'company_id': company.id,
            'route_id': route_tms.id,
        })

    def create_tms_carrier_route(self):
        routes = self.search(['&',('individual_id', '!=', None),('company_id', '!=', None)])
        if not routes:
            return
        for route in routes:
                carrier_route = self.create_new_tms_route_entry(route)
                route.carrier_route_id = carrier_route.id

    def create_new_tms_route_entry(self,obj):
        self.env['tms.carrier.route'].create({
            'name': obj.name,
            'carrier_id': obj.company_id.carrier_id,
            'driver_id': obj.individual_id.carrier_driver_id,
            'route_id': obj.route_id,
        })
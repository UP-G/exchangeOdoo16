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
    #individual_id = fields.Many2one('tmtr.exchange.1c.individual', string='carrier driver id')
    driver_id = fields.Many2one('tms.carrier.driver', string='carrier driver id')
    company_id = fields.Many2one('tmtr.exchange.1c.transport.company', string='transport company id')
    route_id = fields.Many2one('tms.route', string='route id')

    def create_company_route(self, data):
        cnt= 0
        for impl in data['Реализации']:
            routes = self.search([('ref_key', '=', impl['Маршрут_Key'])])
            
            if not routes:
                new_entry = self.create_new_entry(data, impl)
                cnt+=1
            else:
                tc_keys = [r.tc_key for r in routes]
                if not impl['ТК'] in tc_keys:
                    new_entry = self.create_new_entry(data, impl)
                    cnt+=1
                else:
                    _logger.info(f'can not create entry for {impl}')
                    continue
        if cnt != 0:
            self.create_tms_carrier_route()

    def create_new_entry(self, data, impl):
        route_tms = self.env['tms.route'].search([('route_1c_key','=',impl['Маршрут_Key'])])
        driver = self.env['tms.carrier.driver'].search([('ref_key','=',data['Водитель_Key'])])
        company = self.env['tmtr.exchange.1c.transport.company'].search([('ref_key','=', impl['ТК'])])
        if not route_tms or not driver or not company:
            _logger.info(f"NOT tmtr route created Маршрут_Key: {impl['Маршрут_Key']}, driver_key: {data['Водитель_Key']}, company_key: {impl['ТК']}")
            return False
        new_entry = self.create({
            'ref_key': impl['Маршрут_Key'],
            'driver_key': data['Водитель_Key'],
            'tc_key': impl['ТК'],
            'name': data['МаршрутыДоставки'],
            'driver_id': driver.id,
            'company_id': company.id,
            'route_id': route_tms.id,
        })
        _logger.info('tmtr route created')
        return new_entry

    def create_tms_carrier_route(self):
        routes = self.search(['&',('driver_id', '!=', None),
                              ('company_id', '!=', None)])
        carrier_route = self.env['tms.carrier.route'].search([])
        carrier_route_list = [r.id for r in carrier_route]
        print(routes)
        if not routes:
            return
        for route in routes:
                if route.carrier_route_id.id in carrier_route_list:
                    continue
                carrier_route = self.create_new_tms_route_entry(route)
                route.carrier_route_id = carrier_route.id

    def create_new_tms_route_entry(self, obj):
        new_carrier_route = self.env['tms.carrier.route'].create({
            'name': obj.name,
            'carrier_id': obj.company_id.carrier_id.id,
            'driver_id': obj.driver_id.id,
            'route_id': obj.route_id.id,
        })
        return new_carrier_route
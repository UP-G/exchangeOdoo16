from odoo import api, fields, models, _
from datetime import datetime, timedelta
import json

class TmtrExchangeOneCRoute(models.Model):
    _name = 'tmtr.exchange.1c.route'
    _description = '1C Route'

    ref_key = fields.Char(string='Ref key')
    route_key = fields.Char(string='Route key')
    store_key = fields.Char(string='Склад key')
    type_route_key = fields.Char(string='Тип маршрута key')
    car_out = fields.Char(string='Время выезда')
    description = fields.Char(string='description')
    order_id = fields.Many2one('tmtr.exchange.1c.purchase.order', string='Заказ id')

    # def update_routes(self, top, skip):
    #     tms_route_data = self.env['odata.1c.route'].get_by_route(
    #         "1c_ut/get_routes/", 
    #         {
    #         "top": top,
    #         "skip": skip,
    #         })['value']
    
    #     for json_data in tms_route_data:
    #         if json_data['DeletionMark'] == True:
    #             continue
    #         route = self.env['tmtr.exchange.1c.route'].search([("route_key", "=", json_data['Ref_Key'])])
    #     #     # if not order:>
    #     #     #     order = self.env['tmtr.exchange.1c.purchase.order'].create({
    #     #     #             'ref_key' : json_data['Ref_Key'],
    #     #     #             'date_car_out' : json_data['ДатаВыездаМашины'],
    #     #     #             'date' : json_data['Date'],
    #     #     #             'responsible_key' : json_data['Ответственный_Key'],
    #     #     #             'store_key' : json_data['Склад_Key'],
    #     #     #             'note': json_data['Примичание'],
    #     #     #             'is_load': json_data['ЗаказОтгружен'],
    #     #     #             'number': json_data['Number'],
                    
    #     #     #         })
    #         if route:
    #             route.description = json_data['Description']
    #             route.car_out = json_data['ВыездМашины']
    #             # route.date_out = json_data['ДатаВыездаМашины']
    #             # route.end_time = json_data['ДатаОкончания']

    def upload_new_routes(self, top = 100, skip = 0):
        routes_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_routes/", 
            {
                "top": top,
                "skip": skip
                })['value']
        # ref_ids = [r['Ref_Key'] for r in routes_data if r['DeletionMark'] != True]

        # route_exists = dict((r.ref, r.ref) for r in self.search([("Ref_Key", "in", ref_ids)]))
        for item in routes_data:
            route = self.env['tmtr.exchange.1c.route'].search([("route_key", "=", item['Ref_Key'])])
            if route:
                route.ref_key = item['Ref_Key']
                route.store_key = item['СкладМаршрута_Key']
                route.type_route_key = item['ТипМаршрута_Key']
                route.car_out = item['ВыездМашины']
                route.description = item['Description']
        return

    # def update_new_routes(self, json_date):
    #     self.env['tmtr.exchange.1c.route'].create({
    #         'ref_key' : json_date['Ref_Key'],
    #         'store_key' : json_date['СкладМаршрута_Key'],
    #         'type_route_key': json_date['ТипМаршрута_Key'],
    #         'car_out' : json_date['ВыездМашины'],
    #         'description': json_date['Description']
    #         })
    #     return         

            
            
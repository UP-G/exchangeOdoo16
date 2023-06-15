from odoo import api, fields, models, _

import json

class TmtrExchangeOneCRoute(models.Model):
    _name = 'tmtr.exchange.1c.route'
    _description = '1C Route'

    ref_key = fields.Char(string='Ref key')
    driver_key = fields.Char(string='Водитель key')
    route_key = fields.Char(string='Маршрут key')
    car_out = fields.Char(string='Время выезда')
    date_out = fields.Char(string='Дата выезда')
    start_time = fields.Char(string='start_time')
    end_time = fields.Char(string='end_time')
    description = fields.Char(string='description')

    order_id = fields.Many2one('tmtr.exchange.1c.purchase.order', string='Заказ id')

    def update_routes(self, top, skip):
        tms_route_data = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_route2/", 
            {
            "top": top,
            "skip": skip,
            })['value']
    
        for json_data in tms_route_data:
            if json_data['DeletionMark'] == True:
                continue
            route = self.env['tmtr.exchange.1c.route'].search([("route_key", "=", json_data['Ref_Key'])])
        #     # if not order:
        #     #     order = self.env['tmtr.exchange.1c.purchase.order'].create({
        #     #             'ref_key' : json_data['Ref_Key'],
        #     #             'date_car_out' : json_data['ДатаВыездаМашины'],
        #     #             'date' : json_data['Date'],
        #     #             'responsible_key' : json_data['Ответственный_Key'],
        #     #             'store_key' : json_data['Склад_Key'],
        #     #             'note': json_data['Примичание'],
        #     #             'is_load': json_data['ЗаказОтгружен'],
        #     #             'number': json_data['Number'],
                    
        #     #         })
            if route:
                route.description = json_data['Description']
                route.car_out = json_data['ВыездМашины']
                # route.date_out = json_data['ДатаВыездаМашины']
                # route.end_time = json_data['ДатаОкончания']
            
            
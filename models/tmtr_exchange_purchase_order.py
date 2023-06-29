from odoo import api, fields, models, _

import json

from datetime import datetime

class TmtrExchangeOneCPurchaseOrder(models.Model):
    _name = 'tmtr.exchange.1c.purchase.order'
    _description = '1C Deliver Order'

    ref_key = fields.Char(string='Ref key')
    date_car_out = fields.Char(string='Дата выезда машины')
    is_load = fields.Boolean(string='Заказ отгружен')
    date = fields.Char(string='Дата')
    responsible_key = fields.Char(string='Ответственный key')
    store_key = fields.Char(string='Склад key')
    number = fields.Char(string='Номер')
    note = fields.Char(string='Примечание')
    route_ids = fields.One2many('tmtr.exchange.1c.route', 'order_id', string = 'Routes')
    impl_ids = fields.One2many('tmtr.exchange.1c.implemention', 'order_id', string = 'Implementions')

    def upload_new_orders(self, top, skip):
    #url = "http://dcsrv-erpap-01:8080/StockTM_app/odata/standard.odata/Document_%D0%A9%D0%B5%D0%BF_%D0%97%D0%B0%D0%BA%D0%B0%D0%B7%D0%9D%D0%B0%D1%80%D1%8F%D0%B4?$format=json&$top=3&$skip=0&$orderby=Date desc"
        order_data = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_order/", 
            {
            "top": top,
            "skip": skip
            })['value']
    
        for json_data in order_data:
            if json_data['DeletionMark'] == True:
                continue
            order = self.env['tmtr.exchange.1c.purchase.order'].search([("ref_key", "=", json_data['Ref_Key'])])
            if not order:
                order = self.env['tmtr.exchange.1c.purchase.order'].create({
                        'ref_key' : json_data['Ref_Key'],
                        'date_car_out' : json_data['ДатаВыездаМашины'],
                        'date' : json_data['Date'],
                        'responsible_key' : json_data['Ответственный_Key'],
                        'store_key' : json_data['Склад_Key'],
                        'note': json_data['Примичание'],
                        'is_load': json_data['ЗаказОтгружен'],
                        'number': json_data['Number'],
                    
                    })
            routes_data= json_data['Маршруты']
            for route_data in routes_data:
                route = self.env['tmtr.exchange.1c.route'].search([('ref_key','=', route_data['Маршрут_Key'])])
                if not route:
                    route = self.env['tmtr.exchange.1c.route'].create({
                        'ref_key': route_data['Ref_Key'],
                        'route_key': route_data['Маршрут_Key'],
                        'car_out': route_data['ВремяВыезда'],
                        'description': json_data['МаршрутыДоставки'],
                    })        
                for impl_data in json_data['Реализации']:
                    implemention = self.env['tmtr.exchange.1c.implemention'].search([("ref_key", "=", impl_data['Ref_Key'])])
                    if not implemention:
                        new_implemention = self.env['tmtr.exchange.1c.implemention'].create({
                                'ref_key' : impl_data['Ref_Key'],
                                'route_id': route.id,
                                'impl_num': impl_data['Номер'],
                                'address': impl_data['АдресДоставки'],
                                'phone': impl_data['Телефон'],
                                'order_id': order.id,
                                'partner_key': self.update_partner(impl_data['Контрагент_Key']),
                            })            

    def update_order(self, ref_key):
        route = self.env['tmtr.exchange.1c.purchase.order'].search([("ref_key", "=", ref_key)])
        return route.id

    def update_partner(self, counterparty_key):
        counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("ref_key", "=", counterparty_key)])#заменить на модуль наследуемый от контрагента
        return counterparty.partner_id

    def check_route_in_order(self,ref_key):
        route = self.env['tmtr.exchange.1c.route'].search([("ref_key", "=", ref_key)])
        if route:
            return True
        else:
            return False       

    def update_tms(self):#учитывать в будующей версии множество реализаций на одну точку 
        orders = self.env['tmtr.exchange.1c.purchase.order'].search([])
        for order in orders:
            new_order_tms = self.env['tms.order'].create({
                'departed_on_route': order.date_car_out,
            })
            route = self.env['tmtr.exchange.1c.route'].search([('ref_key','=', order.ref_key)])
            new_route_tms = self.env['tms.route'].create({
                'name': route.description,
                'start_time': f"{order.date_car_out.date}T{route.car_out.time}",

            })
            order_rows = self.env['tmtr.exchange.1c.implemention'].search([('ref_key','=', order.ref_key)])
            # new_point = self.env['tms.route.point'].create({
                
            # })
            for order_row in order_rows:
                new_order_row = self.env['tms.order.row'].create({
                    # 'route_point_id': new_point.id,
                    'comment': str(order_row.phone) + ';' + str(order_row.address),
                    'impl_num': order_row.impl_num,
                    'order_id': new_order_tms.id,
                    'partner_key': order_row.partner_key.id,
                }) 
    # def update_tms(self):
    #     # routes = self.env['tmtr.exchange.1c.route'].search([], limit=3)
    #     # for route in routes:
    #     #     new_route_tms = self.env['tms.order'].create({
    #     #         'driver_id': 1,
    #     #         'route_id': 1,
    #     #         'order_num': order.number
    #     #     })

    #     routes = self.env['tmtr.exchange.1c.route'].search([])
    #     for route in routes:
    #         # route = self.env['tms.route'].search([("id", "=", partner_key)])
    #         if route.description:
    #             new_route_tms = self.env['tms.route'].create({
    #             'name': route.description,
    #             'start_time': datetime.strptime(route.order_id.date, '%Y-%m-%dT%H:%M:%S'),
    #             'end_time': datetime.strptime(route.order_id.date, '%Y-%m-%dT%H:%M:%S'),
    #             })
    #             new_order_tms = self.env['tms.order'].create({
    #                 'route_ids': new_route_tms.id,
    #                 'order_num': route.order_id.number,
    #             })
    #     order_rows = self.env['tmtr.exchange.1c.implemention'].search([])
    #     for row in order_rows:
    #         new_point = self.env['tms.route.point'].create({
                
    #         })
    #         new_order_row = self.env['tms.order.row'].create({
    #             'route_point_id': new_point.id,
    #             'comment': str(row.phone) + ';' + str(row.address),
    #             'impl_num': row.impl_num,
    #         })            



            

        


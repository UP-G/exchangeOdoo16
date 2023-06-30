from odoo import api, fields, models, _
import logging
import json
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)
class TmtrExchangeOneCDeliveryOrder(models.Model):
    _name = 'tmtr.exchange.1c.delivery.order'
    _description = '1C Deliver Order'

    ref_key = fields.Char(string='Ref key')
    date_car_out = fields.Char(string='Date car out')
    is_load = fields.Boolean(string='Order is loading')
    date = fields.Char(string='Date')
    responsible_key = fields.Char(string='Responsible key')
    store_key = fields.Char(string='Store key')
    number = fields.Char(string='Number')
    note = fields.Char(string='Note')
    route_ids = fields.One2many('tmtr.exchange.1c.route', 'order_id', string = 'Routes')
    impl_ids = fields.One2many('tmtr.exchange.1c.implemention', 'order_id', string = 'Implementions')

    def upload_new_orders(self, top = 50, skip = 0, from_date = None):
        from_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.last_order_date','2021-06-20T00:00:00')) if not from_date else from_date
        date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        date_till = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        finish_before = datetime.now() + timedelta(minutes=1)
        stop_import = False
        cnt = 0
        total_cnt = 0
        while datetime.now() < finish_before and not stop_import:
            order_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_order/", 
                {
                "top": top,
                "skip": skip,
                "date": date,
                })['value']
        
            for json_data in order_data:
                order = self.env['tmtr.exchange.1c.delivery.order'].search([("ref_key", "=", json_data['Ref_Key'])])
                if not order:
                    order = self.env['tmtr.exchange.1c.delivery.order'].create({
                            'ref_key' : json_data['Ref_Key'],
                            'date_car_out' : json_data['ДатаВыездаМашины'],
                            'date' : json_data['Date'],
                            'responsible_key' : json_data['Ответственный_Key'],
                            'store_key' : json_data['Склад_Key'],
                            'note': json_data['Примичание'],
                            'is_load': json_data['ЗаказОтгружен'],
                            'number': json_data['Number'],
                        })
                    cnt+=1
                routes_data= json_data['Маршруты']
                for route_data in routes_data:
                    route = self.env['tmtr.exchange.1c.route'].search([('route_key','=', route_data['Маршрут_Key'])])
                    if not route:
                        route = self.env['tmtr.exchange.1c.route'].create({
                            'ref_key': route_data['Ref_Key'],
                            'route_key': route_data['Маршрут_Key'],
                            'car_out': route_data['ВремяВыезда'],
                            'description': json_data['МаршрутыДоставки'],
                            'order_id': order.id,
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
            skip+=top
            total_cnt+=cnt
            if date < date_till and cnt == 0:
                # перейти к следующему дню, если он в прошлом
                from_date += timedelta(days=1)
                date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
                skip = 0
            elif date >= date_till and cnt == 0:
                # за текущий день больше не чего импортировать, прервать импорт
                stop_import = True
        # Сохранить день, на котором остановился импорт
        if date <= date_till:
            self.env['ir.config_parameter'].set_param('tmtr.exchange.last_order_date', from_date)
        return {'cnt': total_cnt, 'data': from_date}          


    def upload_order_by_number(self, order_number, date=None):
        document_filter = f"endswith(Number,%20%27{order_number}%27)%20eq%20true"
        orders_data = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_catalog/", 
            {
                "catalog_name": document_filter,
                "filter": f"endswith(Number,%20%27{order_number}%27)%20eq%20true",
            })['value']
        if not orders_data:
            _logger.info(f"order with number {order_number} not found")
            return
        for order_data in orders_data:
            route_tms = self.env['tms.route'].create({
                'name': order_data['МаршрутыДоставки'],
                'start_time': datetime.strptime(order_data['ДатаВыездаМашины'], "%Y-%m-%dT%H:%M:%S"),
            })
            order_tms = self.env['tms.order'].create({
                'route_id': route_tms.id,
                'order_num': order_data['Number'],
                'departed_on_route': f"{route_tms.start_time.date()} {datetime.strptime(order_data['Маршруты'][0]['ВремяВыезда'], '%Y-%m-%dT%H:%M:%S').time()}",
            })
            point_tms = self.env['tms.route.point'].create({})
            for impl in order_data['Реализации']:
                self.env['tms.order.row'].create({
                    'order_id': order_tms.id,
                    'route_point_id': point_tms.id,
                    'impl_num': impl['Номер'],
                    'comment': f"{impl['Телефон']};{impl['АдресДоставки']}",
                    'partner_key': self.update_partner(impl['Контрагент_Key']),
                })

    def update_order(self, ref_key):
        route = self.env['tmtr.exchange.1c.delivery.order'].search([("ref_key", "=", ref_key)])
        return route.id

    def update_partner(self, counterparty_key):
        counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("ref_key", "=", counterparty_key)])#заменить на модуль наследуемый от контрагента
        return counterparty.partner_id.id

    def check_route_in_order(self,ref_key):
        route = self.env['tmtr.exchange.1c.route'].search([("ref_key", "=", ref_key)])
        if route:
            return True
        else:
            return False       

    def update_tms(self):#учитывать в будующей версии множество реализаций на одну точку 
        orders = self.env['tmtr.exchange.1c.delivery.order'].search([])
        for order in orders:
            
            route = self.env['tmtr.exchange.1c.route'].search([('ref_key','=', order.ref_key)])
            new_route_tms = self.env['tms.route'].create({
                'name': route.description,
                'start_time': f"{order.date_car_out.date}T{route.car_out.time}",

            })
            new_order_tms = self.env['tms.order'].create({
                'departed_on_route': order.date_car_out,
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



            

        


from odoo import api, fields, models, _
import logging
import json
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)
class TmtrExchangeOneCPurchaseOrder(models.Model):
    _name = 'tmtr.exchange.1c.purchase.order'
    _description = '1C Deliver Order'

    ref_key = fields.Char(string='Ref key')
    date_car_out = fields.Char(string='Departure date of the car') #Дата выезда машины
    is_load = fields.Boolean(string='The order has been shipped') #Был ли отправлен заказ
    date = fields.Char(string='Date')
    responsible_key = fields.Char(string='Responsible key')
    store_key = fields.Char(string='Warehouse key') #Склад key
    number = fields.Char(string='Number')
    note = fields.Char(string='Note')
    route_ids = fields.One2many('tmtr.exchange.1c.route', 'order_id', string = 'Routes')
    impl_ids = fields.One2many('tmtr.exchange.1c.implemention', 'order_id', string = 'Implementions')

    def upload_new_orders(self, top = 50, skip = 0, from_date = None):
        if not from_date:
            from_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.last_order_date','2021-06-20T00:00:00'))
        date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        date_till = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        finish_before = datetime.now() + timedelta(minutes=1)
        stop_import = False
        total_cnt = 0

        while datetime.now() < finish_before and not stop_import:
            order_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_order/", 
                {
                "top": top,
                "skip": skip,
                "date": date,
                })['value']
            ref_key_ids = [r['Ref_Key'] for r in order_data if r['DeletionMark'] != True]
            order_exists = dict((r.ref_key, r.ref_key) for r in self.search([("ref_key", "in", ref_key_ids)]))
            cnt = 0
            for json_data in order_data:
                if json_data['Ref_Key'] in order_exists:
                    continue

                cnt += 1
                order = self.create_purchase_order(json_data)

                routes_data = json_data['Маршруты']
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

    def create_purchase_order(self, json_date):
        new_purchase_order = self.create({
                            'ref_key' : json_date['Ref_Key'],
                            'date_car_out' : json_date['ДатаВыездаМашины'],
                            'date' : json_date['Date'],
                            'responsible_key' : json_date['Ответственный_Key'],
                            'store_key' : json_date['Склад_Key'],
                            'note': json_date['Примичание'],
                            'is_load': json_date['ЗаказОтгружен'],
                            'number': json_date['Number'],
                        })
        return new_purchase_order


    def upload_order_by_number(self, order_numbers):
        cnt = 0
        for order_number in order_numbers:
            purchases_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_catalog/", 
                {
                    "catalog_name": "Document_Щеп_ЗаказНаряд",
                    "filter": f"endswith(Number,%20%27{order_number}%27)%20eq%20true",
                })['value']
            
            if not purchases_data:
                _logger.info(f"order with number {order_number} not found")
                return cnt
            
            for purchase_data in purchases_data:
                if  not self.env['tms.route'].have_stock(purchase_data):
                    _logger.info(f"order {purchase_data['Number']} dosent have a stock in DB")
                    continue

                cnt += 1
                #подождать до следующей версии
                #stock = self.env['tms.route'].upload_new_stock(purchase_data) 
                routes = self.env['tms.route'].upload_new_route(purchase_data)

                order_tms = self.env['tms.order'].search([('order_num','=',purchase_data['Number'])])
                if not order_tms and routes:
                    order_tms = self.upload_purchase_order(purchase_data, routes[0])

                if not order_tms.order_row_ids and (purchase_data['Реализации'] or purchase_data['ДопУслуги']):
                    if purchase_data['Реализации'] != []:
                        for item in purchase_data['Реализации']:
                            self.upload_order_row(item, order_tms)
                    if purchase_data['ДопУслуги'] != []:
                        for item in purchase_data['ДопУслуги']:
                            self.upload_returns_row(item, order_tms)

        return cnt

    def upload_purchase_order(self, json_value, route_tms):
        order = self.env['tms.order'].create({
                        'route_id': route_tms.id,
                            'order_num': json_value['Number'],
                            'notes': json_value['Примичание'],
                            #'departed_on_route': datetime.strptime(order_data['Date'], '%Y-%m-%dT%H:%M:%S'),
#                'departed_on_route': f"{route_tms.start_time.date()} {datetime.strptime(order_data['Маршруты'][0]['ВремяВыезда'], '%Y-%m-%dT%H:%M:%S').time()}",
                        })
        return order

    def create_delivery(self, json_value, route_tms):

        delivery = self.env['tms.delivery'].create({
                        'route_id': route_tms.id,
                            'name': json_value['Number'],
                            'order_num': json_value['Number'],
                            'notes': json_value['Примичание'],
                        })
        return delivery    
    
    def upload_returns_row(self, impl_json_value, order_tms):
        self.env['tms.order.row'].create({
                            'order_id': order_tms.id,
                            'note': impl_json_value['Комментарий'],
                    #'route_point_id': point_tms.id,
                            'order_row_type': 'return',
                            'impl_num': "Возврат {number}".format(number=impl_json_value['LineNumber']),
                            'comment': "{phone};{address}".format(phone='-',address=impl_json_value['Адрес']),
                            #'partner_key': self.update_partner_by_name(impl['Контрагент']),
                        })

    def create_returns_delivery(self, impl_json_value, tms_delivery):
        self.env['tms.delivery.row'].create({
                            'order_id': tms_delivery.id,
                            'selected_1c': impl_json_value['Выбрать'],
                            'order_row_type': 'return',
                            'impl_num': "Возврат {number}".format(number=impl_json_value['LineNumber']),
                            'comment': "{phone};{address}".format(phone='-',address=impl_json_value['Адрес']),
                        })

    def upload_order_row(self, impl_json_value, order_tms):
        self.env['tms.order.row'].create({
                                'order_id': order_tms.id,
                                'note': impl_json_value['Комментарий'],
                        #'route_point_id': point_tms.id,
                                'order_row_type': 'delivery',
                                'impl_num': impl_json_value['Номер'],
                                'comment': "{phone};{address}".format(phone=impl_json_value['Телефон'], address=impl_json_value['АдресДоставки']),
                                #'partner_key': self.update_partner(item['Контрагент_Key']),
                            })

    def create_delivery_row(self, impl_json_value, tms_delivery):
        self.env['tms.delivery.row'].create({
                                'delivery_id': tms_delivery.id,
                                'order_row_type': 'delivery',
                                'selected_1c': impl_json_value['Выбрать'],
                                'impl_num': impl_json_value['Номер'],
                                'comment': "{phone};{address}".format(phone=impl_json_value['Телефон'], address=impl_json_value['АдресДоставки']),
                            })

    def upload_order_by_number2(self, order_number):
        orders_data = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_catalog/", 
            {
                "catalog_name": "Document_Щеп_ЗаказНаряд",
                "filter": f"endswith(Number,%20%27{order_number}%27)%20eq%20true",
            })['value']
        cnt = 0
        if not orders_data:
            _logger.info(f"order with number {order_number} not found")
            return cnt
        for order_data in orders_data:
            cnt += 1
            order_tms = self.env['tms.order'].search([('order_num','=',order_data['Number'])])
            if not order_tms:
# Пока маршруты игнорируем
#            route_tms = self.env['tms.route'].create({
#                'name': order_data['МаршрутыДоставки'],
#                'start_time': datetime.strptime(order_data['ДатаВыездаМашины'], "%Y-%m-%dT%H:%M:%S"),
#            })
                order_tms = self.env['tms.order'].create({
#                'route_id': route_tms.id,
                    'order_num': order_data['Number'],
                    'departed_on_route': datetime.strptime(order_data['Date'], '%Y-%m-%dT%H:%M:%S'),
#                'departed_on_route': f"{route_tms.start_time.date()} {datetime.strptime(order_data['Маршруты'][0]['ВремяВыезда'], '%Y-%m-%dT%H:%M:%S').time()}",
                })
#            point_tms = self.env['tms.route.point'].create({})
            if not order_tms.order_row_ids and not order_data['Реализации']:
                for item in order_data['Реализации']:
                    self.env['tms.order.row'].create({
                        'order_id': order_tms.id,
                        #'route_point_id': point_tms.id,
                        'impl_num': item['Номер'],
                        'comment': "{phone};{address}".format(phone=item['Телефон'], address=item['АдресДоставки']),
                        'partner_key': self.update_partner(item['Контрагент_Key']),
                    })

    def update_order(self, ref_key):
        route = self.env['tmtr.exchange.1c.purchase.order'].search([("ref_key", "=", ref_key)])
        return route.id if route else False

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
        orders = self.env['tmtr.exchange.1c.purchase.order'].search([])
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
    # 
    def upload_update_order_stock_key(self, from_date=None, stock_upload=None, top=50, skip=0):

        key_ids = []
        total_cnt = 0
        date = None
        stock_not_upload = False

        stock_key = self.env['ir.config_parameter'].get_param('tmtr.exchange.1c_stock_not_upload') # Склады, которе не успели выгрузится
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой

        if stock_key: #Если есть не выгруженные маршруты по складам
            stock_key = json.loads(stock_key.replace("'", "\""))
            date = stock_key['date']
            stock_not_upload = True

        if not from_date and not date:
            from_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param('tmtr.exchange.1c_purchase_order_date','2023-07-11 00:00:00'))
            date = from_date.strftime("%Y-%m-%dT%H:%M:%S")

        date_till = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") # не искать дальше текущей даты

        if not stock_key:
            stock_key = self.env['tms.route'].search(["&", ("name", "=", 'upload'), "&", ("start_time", "=", None), 
                                                      "&", ("end_time", "=", None), "&", ("stock_id", "!=", None), 
                                                      "&", ("route_1c_key", "=", None), ("stock_1c_key", "!=", None)])
            
        key_ids = [r for r in stock_key['stock_1c_key']]

        copy_key_ids = key_ids[:]

        while datetime.now() < finish_before:
            cnt = 0
            if len(key_ids) == 0: #Если всё выгрузили
                if not date < date_till or stock_not_upload: #Если старая выгрузrа завершилось, то прерываем
                    break
                # перейти к следующему дню, если он в прошлом
                key_ids = copy_key_ids[:] # Запись маршрутов
                from_date += timedelta(days=1)
                date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
                skip = 0

            purchases_data = self.get_p_order_on_stock_key(date=date, stock_key=key_ids[0], top=top, skip=skip)

            if not purchases_data: #Если нет больше для склада маршрутов
                key_ids.remove(key_ids[0]) #Переход к следующему
                skip = 0
                continue # Возрат в начала while

            skip += top
                
            for purchase_data in purchases_data:
                if not self.env['tms.route'].have_stock(purchase_data):
                    _logger.info(f"order {purchase_data['Number']} dosent have a stock in DB")
                    continue

                routes = self.env['tms.route'].upload_new_route(purchase_data)

                order_tms = self.env['tms.order'].search([('order_num','=',purchase_data['Number'])])
                if not order_tms and routes:
                    order_tms = self.upload_purchase_order(purchase_data, routes[0])
                    cnt += 1

                if not order_tms.order_row_ids and (purchase_data['Реализации'] or purchase_data['ДопУслуги']):
                    if purchase_data['Реализации'] != []:
                        for item in purchase_data['Реализации']:
                            self.upload_order_row(item, order_tms)
                    if purchase_data['ДопУслуги'] != []:
                        for item in purchase_data['ДопУслуги']:
                            self.upload_returns_row(item, order_tms)
                
            total_cnt += cnt

        obj = {}    
        if key_ids != []: #Если не успели выгрузится все маршруты, то сохраняем до следующей выгрузки
            obj = {'stock_1c_key': [key  for key in key_ids], 'date': date}
            
            stock_key = self.env['ir.config_parameter'].set_param('tmtr.exchange.1c_stock_not_upload', obj)

        if date <= date_till and not stock_not_upload: #Еслы выгружали по прошлым складам, то дату не записываем, 
            self.env['ir.config_parameter'].sudo().set_param('tmtr.exchange.1c_purchase_order_date', from_date)
            
        return {
            'total_cnt': total_cnt,
            'not_upload': obj,
            }
            
    def get_p_order_on_stock_key(self, date, stock_key, top, skip):
        interaction_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_p_order_on_stock_key/", 
                {
                "date": date,
                "stock_key": stock_key,
                "top": top,
                "skip": skip
                })['value']
        return interaction_data
    
    def update_stock_id_route(self):
        stock_key = self.env['tms.route'].search(["&", ("name", "=", "upload"), "&", ("start_time", "=", None), 
                                                      "&", ("end_time", "=", None), "&", ("stock_id", "!=", None), 
                                                      "&", ("route_1c_key", "=", None), ("stock_1c_key", "!=", None)])

        for item in stock_key:
            route = self.env['tms.route'].search(["&", ("name", "!=", None), "&", ("stock_id", "=", None), 
                                                        "&", ("route_1c_key", "!=", None), ("stock_1c_key", "=", item['stock_1c_key'])])
            route.update({'stock_id': item['stock_id']})

    def upload_deliveries_by_stock_key(self, from_date=None, stock_upload=None, top=50, skip=0):
        key_ids = []
        total_cnt = 0
        date = None
        stock_not_upload = False

        stock_key = self.env['ir.config_parameter'].get_param('tmtr.exchange.1c_stock_not_upload') # Склады, которе не успели выгрузится
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой

        if stock_key: #Если есть не выгруженные маршруты по складам
            stock_key = json.loads(stock_key.replace("'", "\""))
            date = stock_key["date"]
            key_ids = [r for r in stock_key['stock_1c_key']]
            stock_not_upload = True

        if not from_date:
            from_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param('tmtr.exchange.1c_purchase_order_date','2023-07-11 00:00:00'))
        if not stock_not_upload:
            date = from_date.strftime("%Y-%m-%dT%H:%M:%S")

        date_till = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") # не искать дальше текущей даты

        if not stock_not_upload:
            stock_key = self.env['tms.route'].search(["&", ("name", "=", 'upload'), "&", ("start_time", "=", None), 
                                                      "&", ("end_time", "=", None), "&", ("stock_id", "!=", None), 
                                                      "&", ("route_1c_key", "=", None), ("stock_1c_key", "!=", None)])
            
            key_ids = [r['stock_1c_key'] for r in stock_key]

        copy_key_ids = key_ids[:]

        while datetime.now() < finish_before:
            cnt = 0
            if len(key_ids) == 0: #Если всё выгрузили
                if not date < date_till or stock_not_upload: #Если старая выгрузrа завершилось, то прерываем
                    break
                # перейти к следующему дню, если он в прошлом
                key_ids = copy_key_ids[:] # Запись маршрутов
                from_date += timedelta(days=1)
                date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
                skip = 0

            purchases_data = self.get_p_order_on_stock_key(date=date, stock_key=key_ids[0], top=top, skip=skip)

            if not purchases_data: #Если нет больше для склада маршрутов
                key_ids.remove(key_ids[0]) #Переход к следующему
                skip = 0
                continue # Возрат в начала while

            skip += top
                
            for purchase_data in purchases_data:
                if not self.env['tms.route'].have_stock(purchase_data):
                    _logger.info(f"order {purchase_data['Number']} dosent have a stock in DB")
                    continue
                
                routes = self.env['tms.route'].upload_new_route(purchase_data)
                driver = self.env['tmtr.exchange.1c.individual'].upload_new_individual(purchase_data['Водитель_Key'])#выгрузка водителей
                delivery_tms = self.env['tms.delivery'].search([('order_num','=',purchase_data['Number'])])
                if not delivery_tms and routes:
                    delivery_tms = self.create_delivery(purchase_data, routes[0])
                    cnt += 1

                if not delivery_tms.delivery_row_ids and (purchase_data['Реализации'] or purchase_data['ДопУслуги']):
                    if purchase_data['Реализации'] != []:
                        for item in purchase_data['Реализации']:
                            self.create_delivery_row(item, delivery_tms)
                    if purchase_data['ДопУслуги'] != []:
                        for item in purchase_data['ДопУслуги']:
                            self.create_returns_delivery(item, delivery_tms)
                
            total_cnt += cnt

        obj = {}    
        if key_ids != []: #Если не успели выгрузится все маршруты, то сохраняем до следующей выгрузки
            obj = {'stock_1c_key': [key for key in key_ids], 'date': date}
            
            stock_key = self.env['ir.config_parameter'].set_param('tmtr.exchange.1c_stock_not_upload', obj)

        if date <= date_till and not stock_not_upload: #Еслы выгружали по прошлым складам, то дату не записываем, 
            self.env['ir.config_parameter'].sudo().set_param('tmtr.exchange.1c_purchase_order_date', from_date)
            
        return {
            'total_cnt': total_cnt,
            'not_upload': obj,
            }
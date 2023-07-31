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


    def create_delivery(self, json_value, route_tms, driver_id):

        delivery = self.env['tms.delivery'].create({
                        'route_id': route_tms[0].id,
                            'name': json_value['Number'],
                            'order_num': json_value['Number'],
                            'notes': json_value['Примичание'],
                            'date_create_1c': self._parse_date(json_value['Date']),
                            'carrier_driver_id': driver_id,
                        })
        return delivery    
    
    def create_returns_delivery(self, impl_json_value, tms_delivery, name_client):
        self.env['tms.delivery.row'].create({
                            'delivery_id': tms_delivery.id,
                            'order_row_type': 'return',
                            'notes': impl_json_value['Комментарий'],
                            'client_name': name_client,
                            'impl_num': "Возврат {number}".format(number=impl_json_value['LineNumber']),
                            'comment': "{phone};{address}".format(phone='-',address=impl_json_value['Адрес']),
                        })

    def create_delivery_row(self, impl_json_value, tms_delivery, name_client):
        self.env['tms.delivery.row'].create({
                                'delivery_id': tms_delivery.id,
                                'order_row_type': 'delivery',
                                'selected_1c': impl_json_value['Выбрать'],
                                'impl_num': impl_json_value['Номер'],
                                'notes': impl_json_value['Комментарий'],
                                'client_name': name_client,
                                'comment': "{phone};{address}".format(phone=self._parse_contact_info(impl_json_value['Телефон']), address=self._parse_contact_info(impl_json_value['АдресДоставки'])),
                            })

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

        if len(copy_key_ids) == 0:
            _logger.info("There is no warehouse in the sample")
            return

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
            _logger.info(key_ids)
            purchases_data = self.get_p_order_on_stock_key(date=date, stock_key=key_ids[0], top=top, skip=skip)

            if not purchases_data: #Если нет больше для склада маршрутов
                key_ids.remove(key_ids[0]) #Переход к следующему
                skip = 0
                continue # Возрат в начала while

            skip += top

            clients = self.env['tmtr.exchange.1c.counterparty'].search([])
            cash_clients = dict([(r.ref_key, r.full_name) for r in clients])
                
            for purchase_data in purchases_data:
                # if not self.env['tms.route'].have_stock(purchase_data):
                #     _logger.info(f"order {purchase_data['Number']} dosent have a stock in DB")
                #     continue

                routes = self.env['tms.route'].upload_new_route(purchase_data)
                driver = self.env['tms.carrier.driver'].get_carrier_driver(purchase_data['Водитель_Key'])#выгрузка водителей
                _logger.info(purchase_data['Number'])
                delivery_tms = self.env['tms.delivery'].search([('order_num','=',purchase_data['Number'])])
                self.env['tmtr.exchange.1c.company.route'].create_company_route(purchase_data)

                if not delivery_tms and routes:
                    delivery_tms = self.create_delivery(purchase_data, routes, driver.id if driver else False)
                    cnt += 1

                tk_unique_key = self.get_unique_values_on_filed(purchase_data['Реализации'], 'ТК')
                transport_companys = self.get_transport_company_id(tk_unique_key)
                self.update_carrier_id(delivery_tms, transport_companys['carrier_ids'])

                # if driver:
                #     self.update_carrier_driver_id(delivery_tms, driver.carrier_driver_id)
                #     self.update_tk_driver(driver, transport_companys['tk_ids'])

                # tk_route = self.get_unique_values_on_filed(purchase_data['Маршруты'], 'Маршрут_Key')
                # route = self.get_route_id(tk_route)
                # self.update_route_tk(delivery_tms.carrier_ids, route['route_ids'])

                if not delivery_tms.delivery_row_ids and (purchase_data['Реализации'] or purchase_data['ДопУслуги']):
                    if purchase_data['Реализации'] != []:
                        for item in purchase_data['Реализации']:
                            name_client = cash_clients.get(item['Контрагент_Key'])
                            #delivery_tms.carrier_ids = self.get_transport_company_id(list(item['ТК']))['carrier_ids']
                            self.create_delivery_row(item, delivery_tms, name_client=name_client)
                    if purchase_data['ДопУслуги'] != []:
                        for item in purchase_data['ДопУслуги']:
                            name_client = cash_clients.get(item['Контрагент_Key'])
                            self.create_returns_delivery(item, delivery_tms, name_client=name_client)
                
            total_cnt += cnt

        obj = {}    
        if key_ids != []: #Если не успели выгрузится все маршруты, то сохраняем до следующей выгрузки
            obj = {'stock_1c_key': [key for key in key_ids], 'date': date}
        else:
            obj = ''
        
        stock_key = self.env['ir.config_parameter'].set_param('tmtr.exchange.1c_stock_not_upload', obj)

        if date <= date_till and not stock_not_upload: #Еслы выгружали по прошлым складам, то дату не записываем, 
            self.env['ir.config_parameter'].sudo().set_param('tmtr.exchange.1c_purchase_order_date', from_date)
            
        return {
            'total_cnt': total_cnt,
            'not_upload': obj,
            }
    
    def get_unique_values_on_filed(self, objects, name_field):
        unique_values = set(obj[name_field] for obj in objects)
        return list(unique_values)
    
    def update_carrier_id(self, obj, tk_keys):
        if tk_keys:
            obj.carrier_id = tk_keys[0]
        return
    
    def get_transport_company_id(self, tk_keys):
        transport_company_ids = self.env['tmtr.exchange.1c.transport.company'].search(['&',('ref_key', 'in', tk_keys),
                                                                             ('carrier_id', '!=', None)])
        carrier_ids = [r['id'] for r in transport_company_ids['carrier_id']]
        tk_ids = [r['id'] for r in transport_company_ids]
        _logger.info(f"tk_ids: {transport_company_ids}  carrer_ids: {carrier_ids}")
        return {
            'carrier_ids': carrier_ids,
            'tk_ids': tk_ids
                }
    
    def get_route_id(self, route_keys):
        route_ids = self.env['tms.route'].search([('route_1c_key', 'in', route_keys)])
        route_ids = [r['id'] for r in route_ids]
        return {
            'route_ids': route_ids
        }
    
    def update_carrier_driver_id(self, obj, carrier_driver_id):
        obj.carrier_driver_id = carrier_driver_id

    def update_tk_driver(self, obj, tk_list):
        tk_cur_list = [r['id'] for r in obj.transport_company_ids]
        tk_id_not_driver = list(set(tk_list) - set(tk_cur_list))
        if tk_id_not_driver != []:
            obj.transport_company_ids = [(4, new_tk_id) for new_tk_id in tk_id_not_driver]

    def update_route_tk(self, obj, route_list):
        for item in obj:
            self.env['tms.carrier.route'].create_carrier_route(item['id'], item['name'], route_list)
        return
    
    def _parse_date(self, str_date):
        date = datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S')
        return date - timedelta(hours=3) #Время по мск
    
    def _parse_contact_info(self, str_info):
        if ";" in str_info:
            str_info = str_info.replace(";", "")
        return str_info
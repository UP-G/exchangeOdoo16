from odoo import api, fields, models, _

import json

class TmtrExchangeOneCPurchaseOrder(models.Model):
    _name = 'tmtr.exchange.1c.purchase.order'
    _description = '1C Purchase Order'

    ref_key = fields.Char(string='Ref key')
    date_car_out = fields.Datetime(string='Дата выезда машины')
    is_load = fields.Boolean(string='Заказ отгружен')
    date = fields.Datetime(string='Дата')
    responsible_key = fields.Char(string='Ответственный key')
    store_key = fields.Char(string='Склад key')
    number = fields.Char(string='Номер')
    note = fields.Char(string='Примечание')

    def update_orders(self, top, skip):
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
                new_order = self.env['tmtr.exchange.1c.purchase.order'].create({
                        'ref_key' : json_data['ref_key'],
                        'date_car_out' : json_data['ДатаВыездаМашины'],
                        'date' : json_data['Date'],
                        'responsible_key' : json_data['Ответственный_Key'],
                        'store_key' : json_data['Склад_Key'],
                        'note': json_data['Примичание'],
                        'is_load': json_data['ЗаказОтгружен'],
                        'number': json_data['Number'],
                    })

        

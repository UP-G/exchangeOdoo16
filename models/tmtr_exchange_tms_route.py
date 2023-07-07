from odoo import api, fields, models, _

class TmtrExchangeTmsRoute(models.Model):
    _inherit = ['tms.route']

    stock_1c_key = fields.Char(string="stock key 1c")
    route_1c_key = fields.Char(string="route key 1c")

    def upload_new_stock(self, json_value):
        stock = self.search([('stock_1c_key','=',json_value['Склад_Key'])])
        if not stock:
            stock = self.create({
                'name': 'склад ' ,
                'stock_1c_key': json_value['Склад_Key'],
                'route_1c_key': 'False',
            })
        return stock


    def upload_new_route(self, json_value):
        new_routes = []
        for route_1c in json_value['Маршруты']:
            route_tms = self.search([('stock_1c_key','=', json_value['Склад_Key']), ('route_1c_key', '=', route_1c['Маршрут_Key'])])
            if not route_tms:
                route_tms = self.create({
                    'name': json_value['МаршрутыДоставки'],
                    'stock_1c_key': json_value['Склад_Key'],
                    'route_1c_key': route_1c['Маршрут_Key'],
                })
            new_routes.append(route_tms)

        return new_routes
            

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

    def have_stock(self, json_value):
        stock = self.search([('stock_1c_key','=',json_value['Склад_Key'])])
        result = True if stock else False
        return result

    def upload_new_route(self, json_value):
        new_routes = []
        name_route = json_value['МаршрутыДоставки'].split('/')
        i = 0
        for route_1c in json_value['Маршруты']:
            if name_route[i] == '':
                break
            route_tms = self.search([('stock_1c_key','=', json_value['Склад_Key']), ('route_1c_key', '=', route_1c['Маршрут_Key'])])
            if not route_tms and route_1c['Маршрут_Key'] != '00000000-0000-0000-0000-000000000000':
                route_tms = self.create({
                    'name': name_route[i],
                    'stock_1c_key': json_value['Склад_Key'],
                    'route_1c_key': route_1c['Маршрут_Key'],
                })
            new_routes.append(route_tms)
            i = i + 1

        return new_routes
            

from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCIntervals(models.Model):
    _name = 'tmtr.exchange.1c.intervals'
    _description = '1C intervals'

    route_key=fields.Char(string='route key')
    interval_from = fields.Datetime(string="interval from")
    interval_to = fields.Datetime(string="interval to")
    stock_key = fields.Char(string="stock key")
    tc_key = fields.Char(string="transport company key")
    delivery_terms= fields.Char(string="delivery terms")
    def upload_intervals(self, stock_key, route_key, top =100, skip=0,tc_key= None ):
        cnt = 0
        json_value = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_intervals_on_stock_key",
            {
                'top': top,
                'skip': skip,
                'stock_key': stock_key,
                'route_key': route_key,
            })['value']
        for data in json_value:
            if not tc_key:
                for tc in data['СписокТК']:
                    new_interval = self.create_interval(tc, data)
                    cnt+=1
            else:
                tc_keys = list([i['ТК_Key'] for i in data['СписокТК']])
                if tc_keys.count(tc_key) > 0:
                    tc_index = tc_keys.index(tc_key)
                    tc = data['СписокТК'][tc_index]
                    new_interval = self.create_interval(tc, data)
                else:
                    new_interval = False
        return new_interval

    def create_interval(self, tc, data):
        time_from= self._parse_date(tc['ИнтервалС'])
        time_to = self._parse_date(tc['ИнтервалПо'])
        if not time_from or not time_to:
            return False
        now = datetime.now() + timedelta(days=int(data['СрокДоставки']))
        interval_f = datetime(now.year, now.month, now.day,time_from.hour,time_from.minute,0)
        interval_t = datetime(now.year, now.month, now.day,time_to.hour,time_to.minute,0)
        new_interval = self.create({
            'interval_from': interval_f,
            'interval_to': interval_t,
            'stock_key': data['СкладМаршрута_Key'],
            'delivery_terms': data['СрокДоставки'],
            'tc_key': tc['ТК_Key'],
            'route_key': data['Ref_Key'],
        })
        return new_interval
    
    def get_intervals(self, route_key, stock_key, tc_key):
        interval = self.search(['&',('route_key','=', route_key),
                                '&', ('stock_key', '=', stock_key),
                                ('tc_key', '=', tc_key)], order='create_date desc', limit=1)
        if not interval:
            interval = self.upload_intervals(stock_key, route_key, top=1, skip=0, tc_key = tc_key)
        return interval
    
    def _parse_date(self, str_date):
        date = datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S')
        if date == datetime(1, 1, 1, 0, 0,0):
            return False
        return date - timedelta(hours=3) #Время по мск
    
    def _update_interval_for_tms_order(self):
        orders = self.env['tms.order'].search([])
        for order in orders:
            i = self.env['tmtr.exchange.1c.intervals'].search(['&',('route_key', '=', order.route_id.route_1c_key),
                                                       ('stock_key', '=', order.route_id.stock_1c_key),
                                                       '&', ('interval_from', '!=', None),
                                                       ('interval_to', '!=', None)], limit=1)
            date = order.car_departure_date + timedelta(days=int(i.delivery_terms)) if order.car_departure_date else (order.date_create_1c + timedelta(days=int(i.delivery_terms)) if order.date_create_1c else False)
            if not date or not i:
                continue
            interval_f = datetime(date.year, date.month, date.day,i.interval_from.hour,i.interval_from.minute,0)
            interval_t = datetime(date.year, date.month, date.day,i.interval_to.hour,i.interval_to.minute,0)         
            order.interval_from = interval_f
            order.interval_to = interval_t
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
    def upload_intervals(self, stock_key, top =100, skip=0 ):
        cnt = 0
        json_value = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_intervals_on_stock_key",
            {
                'top': top,
                'skip': skip,
                'stock_key': stock_key,
            })['value']
        for data in json_value:
            intervals = self.search([('stock_key','=',data['СкладМаршрута_Key'])])
            tc_keys = [i.tc_key for i in intervals]
            for tc in data['СписокТК']:
                if tc['ТК_Key'] in tc_keys:
                    continue
                self.create_interval(tc, data)
                cnt+=1

    def create_interval(self, tc, data):
        time_from= self._parse_date(tc['ИнтервалС'])
        time_to = self._parse_date(tc['ИнтервалПо'])
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
    
    def get_intervals(self, route_key):
        return self.search([('route_key','=', route_key)])
    
    def _parse_date(self, str_date):
        date = datetime.strptime(str_date, '%Y-%m-%dT%H:%M:%S')
        if date == datetime(1, 1, 1, 0, 0,0):
            return date
        return date - timedelta(hours=3) #Время по мск
    
    def _update_interval_for_tms_order(self):
        orders = self.env['tms.order'].search([])
        for order in orders:
            i = self.env['tmtr.exchange.1c.intervals'].search(['&',('route_key', '=', order.route_id.route_1c_key),('stock_key', '=', d.route_id.stock_1c_key)])
            date = order.car_departure_date + timedelta(days=int(i.delivery_terms)) if order.car_departure_date else order.date_create_1c + timedelta(days=int(i.delivery_terms))
            interval_f = datetime(date.year, date.month, date.day,i.interval_from.hour,i.interval_from.minute,0)
            interval_t = datetime(date.year, date.month, date.day,i.interval_to.hour,i.interval_to.minute,0)
            order.interval_from = interval_f
            order.interval_to = interval_t
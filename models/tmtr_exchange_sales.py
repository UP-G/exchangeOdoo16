from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta
from odoo import Command

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCCounterparty(models.Model):
    _name = 'tmtr.exchange.1c.sales'
    _description = '1C sales statistics'

    analytics_accounting_items_Key = fields.Char(string='АналитикаУчетаНоменклатуры_Key')
    customer_order = fields.Char(string='ЗаказКлиента')
    analytics_accounting_partners_Key= fields.Char(string="АналитикаУчетаПоПартнерам_Key")
    departament_key=fields.Char(string="Подразделение_Key")
    stock_type_key = fields.Char(string="ВидЗапасов_Key")
    tm_placement=fields.Char(string="ТМ_Помещение_Key")
    turnover_count= fields.Char(string="КоличествоTurnover")
    turnover_gain_summ=fields.Char(string="СуммаВыручкиTurnover")
    turnover_prime_cost=fields.Char(string="СебестоимостьTurnover")
    turnover_additional_cost=fields.Char(string="СуммаДополнительныхРасходовTurnover")
    turnover_prime_cost_regl=fields.Char(string="СебестоимостьРеглTurnover")
    turnover_gain_regl=fields.Char(string="СуммаВыручкиРеглTurnover")
    tm_turnover_prime_cost_sale=fields.Char(string="ТМ_СебестоимостьПродажиTurnover")
    date_sale = fields.Date(string="Дата регистрации продажи")
    def add_entry_cron(self, date):
        try:
            data = False
            while not data:
                date_str = date.strftime('%Y-%m-%d')
                data = self.env['odata.1c.route'].get_by_route("1c_ut/get_sales/", {"dateEnd": date_str,"dateStart":date_str})["value"]
                date = date - timedelta(days=1)
            
            for json_data in data:
                self.env['tmtr.exchange.1c.sales'].create({
                    'analytics_accounting_items_Key' : json_data['АналитикаУчетаНоменклатуры_Key'],
                    'customer_order' : json_data['ЗаказКлиента'],
                    'analytics_accounting_partners_Key' : json_data['АналитикаУчетаПоПартнерам_Key'],
                    'departament_key' : json_data['Подразделение_Key'],
                    'stock_type_key' : json_data['ВидЗапасов_Key'],
                    'tm_placement' : json_data['ТМ_Помещение_Key'],
                    'turnover_count' : json_data['КоличествоTurnover'],
                    'turnover_gain_summ' : json_data['СуммаВыручкиTurnover'],
                    'turnover_prime_cost' : json_data['СебестоимостьTurnover'],
                    'turnover_additional_cost' : json_data['СуммаДополнительныхРасходовTurnover'],
                    'turnover_prime_cost_regl' : json_data['СебестоимостьРеглTurnover'],
                    'turnover_gain_regl' : json_data['СуммаВыручкиРеглTurnover'],
                    'tm_turnover_prime_cost_sale' : json_data['ТМ_СебестоимостьПродажиTurnover'],
                    'date_sale' : date,
                    
                })
        except Exception as e:
            _logger.info(e)
            return

            
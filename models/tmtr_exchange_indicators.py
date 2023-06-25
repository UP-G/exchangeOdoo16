from odoo import api, fields, models, _
import logging
from datetime import datetime 
from odoo import Command

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCIndicators(models.Model):
    _name = 'tmtr.exchange.1c.indicators'
    _description = 'finance indicators from bitrix'

    partner_id = fields.Many2one('tmtr.exchange.1c.partner', string='Partner')
    plan = fields.Float(string='Plan for the current month') #План на текущий месяц
    prediction= fields.Float(string="Turnover forecast for the current month") #Прогноз выручки на текущий месяц
    turnover_this_mounth=fields.Float(string="Turnover for the current month") #Выручка текущего месяца
    turnover_previous_mounth = fields.Float(string="Turnover for the previous month") #Выручка предыдущего месяца
    turnover_last_3month = fields.Float(string="Turnover of last 3 month")
    turnover_last_30days = fields.Float(string="Turnover of last 30 days")
    debt=fields.Float(string="Debt amount") #Размер долга
    overdue_debt= fields.Float(string="Debt overdue")
    task_count = fields.Integer(string="Task count on client")
    company_ref_key = fields.Char(string= 'Ref key')
    origin_id = fields.Char(string='origin id from bitrix')
    identifier_ib = fields.Char(string="manager id")
    debs_percent = fields.Float(string="Interest rate on the debt") #Процент долга
    turnover_percent = fields.Float(string="Revenue percentage for 3 months") #процент выручки за 3 месяца
    in_work_date = fields.Date(string='Date of commencement') #дата передачи в работу
    

    def calculate_percent_new(self):
        valuesSumm = self.env['tmtr.exchange.1c.indicators'].read_group([],['identifier_ib',
                                                                            'debts:sum(overdue_debt)',
                                                                            'turnover:sum(turnover_last_3month)'], ['identifier_ib'])
        
        for values in valuesSumm:
            tasks = self.env['tmtr.exchange.1c.indicators'].search([('identifier_ib','=', values['identifier_ib'])], order='turnover_last_3month DESC')
            accamulative_percent_proceds = 0
            for task in tasks:
                accamulative_percent_proceds += 100 if values['turnover'] == 0 else task.turnover_last_3month / values['turnover']
                task.update({
                    'turnover_percent': accamulative_percent_proceds,
                })
        
        for values in valuesSumm:
            tasks = self.env['tmtr.exchange.1c.indicators'].search([('identifier_ib','=', values['identifier_ib'])], order='overdue_debt DESC')
            accamulative_percent_debt = 0
            for task in tasks:
                accamulative_percent_debt += 100 if values['debts'] == 0 else task.overdue_debt / values['debts']
                task.update({
                    'debs_percent':accamulative_percent_debt,
                })
    
    def get_best_one(self, json_data):
        try:
            identifier_ib = json_data['identifier_ib']
            exclude_client_ids = json_data['exclude_client_ids']
            best_task = self.env['tmtr.exchange.1c.indicators'].search([('identifier_ib', '=', identifier_ib), ('origin_id','not in', exclude_client_ids)],
                                                                       order='turnover_percent ASC', limit=1)
            if best_task.turnover_percent > 80:
                best_task = self.env['tmtr.exchange.1c.indicators'].search([('identifier_ib', '=', identifier_ib), ('origin_id','not in', exclude_client_ids)],
                                                                       order='debs_percent ASC', limit=1)
                if best_task.debs_percent > 80:
                    best_task = 0
            best_task.update({'in_work_date': datetime.now()})
            return best_task.origin_id
        except Exception as e:
                _logger.info(e)
                return 0


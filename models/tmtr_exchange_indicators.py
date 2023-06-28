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
    prediction = fields.Float(string="Turnover forecast for the current month") #Прогноз выручки на текущий месяц
    turnover_this_mounth=fields.Float(string="Turnover for the current month") #Выручка текущего месяца
    turnover_previous_mounth = fields.Float(string="Turnover for the previous month") #Выручка предыдущего месяца
    turnover_last_3month = fields.Float(string="Turnover of last 3 month")
    turnover_last_30days = fields.Float(string="Turnover of last 30 days")
    turnover_lacking = fields.Float('Lacking Turnover') # Недостающая выручка
    debt=fields.Float(string="Debt amount") #Размер долга
    overdue_debt= fields.Float(string="Debt overdue")
    task_count = fields.Integer(string="Task count on client")
    company_ref_key = fields.Char(string= 'Ref key')
    origin_id = fields.Char(string='origin id from bitrix')
    identifier_ib = fields.Char(string="manager id")
    debs_percent = fields.Float(string="Accumulated percent on Debts") # Накопленный процент просроченного долга
    turnover_percent = fields.Float(string="Accumulated percent of Turnover") # Накопленный процент выручки за 3 месяца
    turnover_lacking_percent = fields.Float('Accumulated percent on Lacking Turnover') # Накопленный процент недостающей выручки
    in_work_date = fields.Date(string='Date of commencement') #дата передачи в работу


    def calculate_percent_new(self):
        managers = self.read_group([],[
            'identifier_ib',
            'debts:sum(overdue_debt)',
            'turnover:sum(turnover_last_3month)',
            'turnover_lacking:sum(turnover_lacking)',
        ], ['identifier_ib'])
        for manager_total in managers:
            tasks = self.search([('identifier_ib','=', manager_total['identifier_ib'])], order='turnover_last_3month DESC')
            if manager_total['turnover'] == 0:
                tasks.update({
                    'turnover_percent': 1, # 100%
                })
            else:
                accumulative_turnover_percent = 0
                for task in tasks: # already sorted by order='turnover_last_3month DESC'
                    accumulative_turnover_percent += task.turnover_last_3month / manager_total['turnover']
                    task.update({
                        'turnover_percent': accumulative_turnover_percent,
                    })
            if manager_total['debts'] == 0:
                tasks.update({
                    'debs_percent': 1, # 100%
                })
            else:
                accumulative_debt_percent = 0
                for task in tasks.sorted('overdue_debt', reverse=True):
                    accumulative_debt_percent += task.overdue_debt / manager_total['debts']
                    task.update({
                        'debs_percent': accumulative_debt_percent,
                    })
            if manager_total['turnover_lacking'] == 0:
                tasks.update({
                    'turnover_lacking_percent': 1, # 100%
                })
            else:
                accumulative_lacking_percent = 0
                for task in tasks.sorted('turnover_lacking', reverse=True):
                    accumulative_lacking_percent += task.turnover_lacking / manager_total['turnover_lacking']
                    task.update({
                        'turnover_lacking_percent': accumulative_lacking_percent,
                    })
        return True

    def update_from_json(self, jsonValue):
        indicator = self.search([('origin_id', '=', jsonValue['origin_id'])], limit=1)
        plan = max([float(jsonValue['turnover_prevmonth']),(float(jsonValue['turnover_3month']/3))]) #(макс(среднее за предыдущий месяц; среднее за 3 месяца) * кол-во дней месяце)
        prediction = jsonValue['turnover_30days'] #Прогноз выручки на текущий месяц (среднее в день за 30 дней * количество дней в текущем месяце)
        turnover_lacking = plan - prediction if (plan - prediction) > 0 else 0
        item = {
                'plan': plan,
                'prediction': prediction, 
                'turnover_lacking': turnover_lacking,
                'turnover_this_mounth': jsonValue['turnover_thismonth'],
                'turnover_last_3month': jsonValue['turnover_3month'],
                'turnover_last_30days': jsonValue['turnover_30days'],
                'turnover_previous_mounth': jsonValue['turnover_prevmonth'],
                'overdue_debt': jsonValue['debt'],
                'task_count': jsonValue['task_count'],
                'origin_id': jsonValue['origin_id'],
                'identifier_ib': jsonValue['manager_id'],
                'debt': jsonValue['balance'],
        }
        if not indicator:
            _logger.info(jsonValue)
            indicator = http.request.env['tmtr.exchange.1c.indicators'].create(item)
        else:
            indicator.write(item)
        return indicator.id if indicator else 0

from odoo import fields, models, tools, api
import logging
from datetime import datetime, timedelta
from odoo import Command
import json

_logger = logging.getLogger(__name__)

class EfficiencySalerReport(models.Model):
    """ Efficiency Saler Analysis Hystory"""

    _name = "efficiency.saler.report_history"
    _description = "Efficiency Saler Report History"

    date = fields.Datetime('Date') # Дата версии отчета в часовом поясе Europe/Moscow
    manager_name = fields.Char('Manager Name') # ФИО менеджера
    manager_1c_id = fields.Char('Manager 1C ID') # 1С ИД безопасности
    type_client = fields.Selection([ # Тип клиента
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('2_new','New'), # Новые (появились в течение Y месяцев)
        ('3_old','Old'), # ХКБ (не было продаж предыдущих Х месяцев)
        ('4_main','Key'), # АКБ основные (80% выручки за Х месяцев)
        ('5_mean','Meaningful'), # АКБ значимые (следующие 10% выручки за Х месяцев)
        ('6_other','Active'), # АКБ прочие
        ], 'Type client')
    type_debts = fields.Selection([ # Тип клиента
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('4_main','Key'), # Должники ключевые (80% просроченного долга)
        ('5_mean','Meaningful'), # Должники значимые (следующие 10% долга)
        ('6_other','Overdued'), # Должники прочие
        ], 'Type debts')
    client_name = fields.Char('Client Name') # Клиент (+"не известный" в первой строке - все клиенты, чьи телефоны не найдены в контактах)
    client_1c_id = fields.Char('Client 1C ID') # origin_id
    business_type = fields.Char('Client Business Type') # ДИТ_ВидДеятельности_Key.Description
    price_level = fields.Char('Price Level') # DB Analisys
    requests_limit = fields.Integer(string='Daily requests limit') # ДИТ_МаксимальноеЧислоЗапросов

    team_id = fields.Many2one('crm.team', string="Sales Team")

    plan = fields.Float(string='Plan this month') # План на текущий месяц (макс(среднее в день за предыдущий месяц; среднее в день за 3 месяца) * кол-во дней в текущем месяце)
    # plan_percentage = fields.Float('Plan percantage') # Процент выполнения плана, поле долно быть вычисляемым, чтобы корректно работало при группировках
    prediction = fields.Float('Prediction') # Прогноз выручки на текущий месяц (среднее в день за 30 дней * количество дней в текущем месяце)
    plan_predicted_percentage = fields.Float('Plan prediction percantage', group_operator="avg") # >100% = Рост (зеленым)/ <100% = падение (красным) в % относительно плана
    turnover_lacking = fields.Float('Lacking Turnover') # Недостающая выручка
    turnover_this_mounth = fields.Float('Turnover this month') # Выручка текущего месяца
    turnover_previous_mounth = fields.Float('Turnover last month') # Выручка предыдущего месяца
    debt = fields.Float('Debt amount') # Размер долга
    overdue_debt = fields.Float('Overdue debt amount') # Просроченный долг
    turnover_lacking_percent = fields.Float('Accumulated percent on Lacking Turnover', group_operator="avg") # Размер долга
    task_count = fields.Float('Task count') # Задач по клиенту
    interaction_count = fields.Float('Interactions count') # Взаимодействий по клиенту
    interaction_last_date = fields.Datetime('Last Interaction Date') # Дата последнего Взаимодействия
    calls_in_count = fields.Float('Calls in count') # Вх.звонков (шт разных клиентов) из реч.аналитики
    calls_out_count = fields.Float('Calls out count') # исх.звонков (шт разных клиентов) из реч.аналитики
    calls_minute = fields.Float('Calls minutes') # Вх+исх.звонков (минут) из реч.аналитики
    sonder_calls_count = fields.Float('Sonder calls count') # Sonder (шт разных клиентов) из реч.аналитики
    calls_out_last_date = fields.Datetime('Last out call Date') # Дата последнего исходящего звонка

    capacity = fields.Float(string='Client capacity') # Емкость клиента в Евро
    capacity_percentage = fields.Float(string='Client capacity ratio', group_operator="avg") # Доля фактических отгрузок ТМ в емкости клиента
    our_share = fields.Float(string="Our share in client's purchases") # Доля ТМ в закупках клиентом запчастей
    capacity_lacking = fields.Float('Lacking Capacity Turnover') # Недостающая выручка до 30% доли
    type_capacity = fields.Selection([ # Тип клиента по емкости
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('4_main','Key'), # Ключевые по емкости (80% по емкости в рамках менеджера)
        ('5_mean','Meaningful'), # Значимые по емкости (следующие 15%)
        ('6_other','Other'), # Прочие по емкости
        ], 'Type capacity')

    @api.model
    def makeDayHistoryCron(self):
        field_names = [r for r in self.env['ir.model.fields'].search([('model_id.model','=',"efficiency.saler.report"),('readonly','=',False)]).mapped('name') if r not in ['date']]
        cnt = 0
        shot_date = fields.Datetime.now()
        # self.search([('date','=',shot_date)]).unlink() # delete old records for this day
        for rec in self.env["efficiency.saler.report"].search([]):
            src_data = dict((field_name, rec[field_name]) for field_name in field_names)
            src_data.update({'date': shot_date})
            shot = self.create(src_data)
            cnt += 1
        return cnt

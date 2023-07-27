from odoo import fields, models, tools, api
import logging
from datetime import datetime, timedelta
from odoo import Command
import json

_logger = logging.getLogger(__name__)

class EfficiencySalerReport(models.Model):
    """ Efficiency Saler Analysis """

    _name = "efficiency.saler.report"
    _auto = False#Обсудить False
    _description = "Efficiency Saler Report"
    _rec_name = 'id'

    date = fields.Datetime('Date') # Первый день месяца в часовом поясе Europe/Moscow
    manager_name = fields.Char('Manager Name') # ФИО менеджера
    manager_1c_id = fields.Char('Manager 1C ID') # 1С ИД безопасности
    type_client = fields.Selection([ # Тип клиента
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('2_new','New'), # Новые (появились в течение Y месяцев)
        ('3_old','Old'), # ХКБ (не было продаж предыдущих Х месяцев)
        ('4_main','Key'), # АКБ основные (80% выручки за Х месяцев)
        ('5_mean','Meaningful'), # АКБ значимые (следующие 15% выручки за Х месяцев)
        ('6_other','Active'), # АКБ прочие
        ], 'Type client')
    type_debts = fields.Selection([ # Тип клиента
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('4_main','Key'), # Должники ключевые (80% просроченного долга)
        ('5_mean','Meaningful'), # Должники значимые (следующие 15% долга)
        ('6_other','Overdued'), # Должники прочие
        ('7_ok','No debts'), # Нет просроченного долга
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
    turnover_lacking_percent = fields.Float('Accumulated percent on Lacking Turnover', group_operator="avg") # Накопленный процент упущенной выручки
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
    debts_to_limit_percentage = fields.Float(string='Detbs to credit_limit ration')

    indicator_id = fields.Many2one('tmtr.exchange.1c.indicators', string='Client Indicators', readonly=True) # Не дублировать поле в Истории, т.к. в Индикаторах хранится только последнее состояние

    def _select(self):
        return """
            SELECT
                max(indicators.id) as id,
                max(indicators.id) as indicator_id,
                timezone('Europe/Moscow',date_trunc('month',now())) as date,
                COALESCE(s1user.description, COALESCE(indicators.identifier_ib, 'Unknown manager')) as manager_name,
                COALESCE(indicators.identifier_ib, 'Unknown_ID') as manager_1c_id,
                COALESCE(indicators.origin_id, 'Unknown_ID') as client_1c_id,
                COALESCE(case
                    when min(indicators.turnover_percent) <= 0.8 then '4_main'
                    when min(indicators.turnover_percent) <= 0.95 then '5_mean'
                    else '6_other' end,'1_unknown') as type_client,
                COALESCE(case
                    when min(indicators.debs_percent) <= 0.8 then '4_main'
                    when min(indicators.debs_percent) <= 0.95 then '5_mean'
                    when min(indicators.debs_percent) = 0 then '7_ok'
                    else '6_other' end,'1_unknown') as type_debts,
                COALESCE(case
                    when min(indicators.capacity_percent) <= 0.8 then '4_main'
                    when min(indicators.capacity_percent) <= 0.95 then '5_mean'
                    else '6_other' end,'1_unknown') as type_capacity,
                COALESCE(client.full_name,'Unknown client') as client_name,
                COALESCE(business_type.name,'Unknown type') as business_type,
                COALESCE(indicators.level_code, '-') as price_level,
                COALESCE(client.requests_limit, 0) as requests_limit,
                indicators.team_id as team_id,

                max(indicators.target) as plan,
                max(indicators.prediction) as prediction,

                case when max(indicators.credit_limit) > 100 then max(indicators.debt) / max(indicators.credit_limit) else 0.99 end as debts_to_limit_percentage,

                sum(indicators.turnover_lacking_percent) as turnover_lacking_percent,
                case when max(indicators.target) > 0 then sum(indicators.prediction) / max(indicators.target) else 0 end as plan_predicted_percentage,
                case when max(indicators.target) - max(indicators.prediction) > 0 then max(indicators.target) - max(indicators.prediction) else 0 end as turnover_lacking,
                max(indicators.turnover_this_mounth) as turnover_this_mounth,
                max(indicators.turnover_previous_mounth) as turnover_previous_mounth,
                max(indicators.debt) as debt,
                max(indicators.overdue_debt) as overdue_debt,
                max(indicators.task_count) as task_count,
                sum(COALESCE(interaction.cnt, 0)) as interaction_count,
                timezone('Europe/Moscow',max(COALESCE(interaction.interaction_last_date, date_trunc('month',now() - '31 DAY'::INTERVAL)))) as interaction_last_date,
                sum(COALESCE(imot.calls_in_count, 0)) as calls_in_count,
                sum(COALESCE(imot.calls_out_count, 0)) as calls_out_count,
                sum(COALESCE(imot.calls_minute, 0)) as calls_minute,
                sum(COALESCE(imot.sonder_calls_count, 0)) as sonder_calls_count,
                timezone('Europe/Moscow',max(COALESCE(imot.calls_out_last_date, date_trunc('month',now() - '31 DAY'::INTERVAL)))) as calls_out_last_date,
                max(client.capacity) as capacity,
                case when (max(client.capacity)*0.3-max(indicators.prediction))>0 then max(client.capacity)*0.3-max(indicators.prediction) else 0 end as capacity_lacking,
                case when max(client.capacity) > 1 then max(indicators.prediction) / max(client.capacity) else 0 end as capacity_percentage,
                max(client.our_share / 100) as our_share
        """

    def _from(self):
        return """
            FROM (SELECT
                indicators.id,
                indicators.identifier_ib,
                indicators.origin_id,
                indicators.turnover_percent,
                indicators.turnover_previous_mounth,
                indicators.turnover_last_3month,
                indicators.turnover_last_30days,
                indicators.turnover_lacking_percent,
                indicators.turnover_this_mounth,
                indicators.capacity_percent,
                indicators.debs_percent,
                indicators.debt,
                indicators.overdue_debt,
                indicators.task_count,
                indicators.level_code,
                indicators.team_id,
                indicators.target,
                indicators.credit_limit,
                indicators.credit_days,
                GREATEST(
                    indicators.turnover_previous_mounth,
                    indicators.turnover_last_3month / 3,
                    indicators.turnover_last_30days
                ) as plan,
                case when extract(day from now()) < 16 then
                    indicators.turnover_last_30days else
                    indicators.turnover_this_mounth / (extract(day from now()) -1 ) * (DATE_PART('days', DATE_TRUNC('month', NOW())  + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL))
                end as prediction
                FROM tmtr_exchange_1c_indicators AS indicators) AS indicators
        """

    def _join(self):
        return """
            LEFT JOIN tmtr_exchange_1c_partner as client ON indicators.origin_id = client.code
            LEFT JOIN tmtr_exchange_1c_business_type as business_type ON business_type.ref = client.business_type_key
            LEFT JOIN (SELECT timot.client_origin_id, p2user.identifier_ib,
                sum(case when timot.type_call = 'Входящий'  then 1 else 0 end) as calls_in_count,
                sum(case when timot.type_call = 'Исходящий' then 1 when timot.type_call = 'Входящий' then 0 when COALESCE(timot.type_call, 'null') = 'null' then 1 else 0 end) as calls_out_count,
                sum(COALESCE(timot.duration,0)) / 60 as calls_minute,
                sum(case when timot.tags_rule_unique like '%Sonder%' then 1 else 0 end) as sonder_calls_count,
                max(case when timot.type_call = 'Исходящий' or COALESCE(timot.type_call, 'null') = 'null' then cast(to_timestamp(timot.call_time) as timestamp) 
                    else date_trunc('month',now() - '31 DAY'::INTERVAL) end) as calls_out_last_date
                FROM  voximplant_imot as timot
                LEFT JOIN voximplant_operator_phone p2user on timot.operator_phone = p2user.operator_phone
                WHERE date_trunc('month', cast(to_timestamp(timot.call_time) as timestamp)) = date_trunc('month',now())  and COALESCE(timot.duration,0) > 7
                GROUP BY timot.client_origin_id, p2user.identifier_ib
                ) as imot on imot.client_origin_id = indicators.origin_id and indicators.identifier_ib = imot.identifier_ib
            LEFT JOIN tmtr_exchange_1c_user as s1user ON s1user.identifier_ib = indicators.identifier_ib
            LEFT JOIN (SELECT tinteraction.onec_member_id, tinteraction.responsible_key, count(tinteraction.responsible_key) as cnt, max(tinteraction.date) as interaction_last_date
                FROM tmtr_exchange_1c_interaction as tinteraction
                WHERE date_trunc('month',tinteraction.date) = date_trunc('month',now())
                GROUP BY tinteraction.onec_member_id, tinteraction.responsible_key
                ) as interaction on client.id = interaction.onec_member_id and s1user.ref_key = interaction.responsible_key
        """

    def _where(self):
        return ''
        #### For DEBUG:
        return """
            WHERE indicators.origin_id = '00-00023608' and indicators.identifier_ib = '370515e0-f824-48f3-89ba-89db66b1d618'
        """

    def _group(self):
        return """
            GROUP BY manager_name, manager_1c_id, client_name, client_1c_id, business_type, price_level, requests_limit, indicators.team_id
        """

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
                %s
                %s
            )
        """ % (self._table, self._select(), self._from(), self._join(), self._where(), self._group())
        )

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.browse(docids)
        sorted_records = records
        #sorted_records = records.sorted(lambda r: r.overdue_debt, reverse=True)
        #_logger.info(sorted_records)
        return {
            'doc_ids' : docids,
            'doc_model' : 'efficiency.saler.report',
            'data' : data,
            'docs' : sorted_records,
        }

    @api.model
    def _render_html_by_manager(self, manager_1c_ids, data=None):
        docids = self.search([('manager_1c_id','in',manager_1c_ids)]).ids
        return self.env['ir.ui.view'].with_context(lang='ru_RU')._render_template('tmtr_exchange.efficiency_report_template',
            self._get_report_values(docids, data)
        )

    @api.model
    def _render_html_all(self, data=None):
        docids = self.search([]).ids
        return self.env['ir.ui.view'].with_context(lang='ru_RU')._render_template('tmtr_exchange.efficiency_report_template',
            self._get_report_values(docids, data)
        )

    @api.model
    def get_unknown_managers(self):
        manager_1c_ids = [r['manager_1c_id'] for r in self.group_read([('manager_name','ilike','-')],['manager_name','manager_1c_id'],['manager_name','manager_1c_id'])
            if r['manager_1c_id'] == ['manager_name']
        ]
        if manager_1c_ids:
            return self.env['tmtr.exchange.1c.user'].upload_by_sec_id(manager_1c_ids)
        else:
            return {'result': 'OK', 'message': 'nothing to upload'}

    @api.model
    def get_unknown_clients(self):
        client_1c_ids = [r['client_1c_id'] for r in self.group_read([('client_name','ilike','-')],['client_name','client_1c_id'],['client_name','client_1c_id'])
            if r['client_1c_id'] == ['client_name']
        ]
        if client_1c_ids:
            return self.env['tmtr.exchange.1c.partner'].get_partner_by_origin_id(client_1c_ids)
        else:
            return {'result': 'OK', 'message': 'nothing to upload'}

    def get_best_one(self, manager_1c_id, exclude_client_1c_ids):
        best_one_filters = json.loads(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.best_one_filters',json.dumps([
            {'days': '30', # 1. смотрим всех должников, нет коммуникаций за 30 дней
                'filter': [('type_debts','in',['4_main','5_mean','6_other']),('overdue_debt','>','0')],
                'order': 'overdue_debt DESC'},
            {'days': '30', # 2. смотрим среди всей АКБ отстающие на 20% и более
                'filter': [('type_client','in',['4_main','5_mean','6_other']),('plan_predicted_percentage','<','0.8'),('turnover_lacking_percent','<','0.95')],
                'order': 'turnover_lacking DESC'},
            {'days': '14', # 3. смотрим ключевых и значимых должников, нет коммуникаций за 14 дней
                'filter': [('type_debts','in',['4_main','5_mean']),('overdue_debt','>','0')],
                'order': 'overdue_debt DESC'},
            {'days': '14', # 4. смотрим среди ключевых и значимых отстающих на 10% и более от плана
                'filter': [('type_client','in',['4_main','5_mean']),('plan_predicted_percentage','<','0.95')],
                'order': 'turnover_lacking DESC'},
            {'days': '7',  # 5. смотрим ключевых должников, нет коммуникаций за 7 дней
                'filter': [('type_debts','in',['4_main']),('overdue_debt','>','0')],
                'order': 'overdue_debt DESC'},
            {'days': '7',  # 6. смотрим среди ключевых отстающих с максимальным отставанием продаж от плана
                'filter': [('type_client','in',['4_main']),('plan_predicted_percentage','<','1')],
                'order': 'turnover_lacking DESC'}, 
            {'days': '30', # 7. смотрим среди всей АКБ отстающие на 20% и более
                'filter': [('type_client','in',['4_main','5_mean','6_other']),('turnover_lacking_percent','<','0.95')],
                'order': 'turnover_lacking DESC'},
                           # 8. сообщаем об отсутствии задач
        ])))
        best_client_1c_id = ''
        step = 0
        for best_one_filter in best_one_filters:
            if not best_client_1c_id:
                step += 1
                before = datetime.now() + timedelta(days=int(best_one_filter.get('days','7')))
                best_task = self.search([
                    ('manager_1c_id', '=', manager_1c_id),
                    ('client_1c_id','not in', exclude_client_1c_ids),
                    ('interaction_last_date', '<', before),
                    ('calls_out_last_date', '<', before),
                    ] + best_one_filter.get('filter',[]),
                    order=best_one_filter.get('order','turnover_lacking DESC'))
                if best_task:
                    best_client_1c_id = best_task[0].client_1c_id
        return {'origin_id': best_client_1c_id, 'step': step, 'message': 'nothing to do' if not best_client_1c_id else '', 'manager_1c_id': manager_1c_id}


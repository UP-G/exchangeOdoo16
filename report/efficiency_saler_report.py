from odoo import fields, models, tools, api
import logging

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
        ('4_main','Main'), # АКБ основные (80% выручки за Х месяцев)
        ('5_mean','Meaningful'), # АКБ значимые (80-90% выручки за Х месяцев)
        ('6_other','Active'), # АКБ прочие
        ], 'Type client')
    type_debts = fields.Selection([ # Тип клиента
        ('1_unknown','Unknown'), # Не известен - не запонена связь
        ('4_main','Main'), # АКБ основные (80% просроченного долга)
        ('5_other','Overdued'), # АКБ прочие
        ], 'Type debts')
    client_name = fields.Char('Client Name') # Клиент (+"не известный" в первой строке - все клиенты, чьи телефоны не найдены в контактах)
    client_1c_id = fields.Char('Client 1C ID') # origin_id

    plan = fields.Float(string='Plan this month') # План на текущий месяц (макс(среднее в день за предыдущий месяц; среднее в день за 3 месяца) * кол-во дней в текущем месяце)
    # plan_percentage = fields.Float('Plan percantage') # Процент выполнения плана, поле долно быть вычисляемым, чтобы корректно работало при группировках
    prediction = fields.Float('Prediction') # Прогноз выручки на текущий месяц (среднее в день за 30 дней * количество дней в текущем месяце)
    plan_predicted_percentage = fields.Float('Plan prediction percantage') # >100% = Рост (зеленым)/ <100% = падение (красным) в % относительно плана
    turnover_lacking = fields.Float('Lacking Turnover') # Недостающая выручка
    turnover_this_mounth = fields.Float('Turnover this month') # Выручка текущего месяца
    turnover_previous_mounth = fields.Float('Turnover last month') # Выручка предыдущего месяца
    debt = fields.Float('Debt amount') # Размер долга
    overdue_debt = fields.Float('Overdue debt amount') # Просроченный долг
    task_count = fields.Float('Task count') # Задач по клиенту
    interaction_count = fields.Float('Interactions count') # Взаимодействий по клиенту
    calls_in_count = fields.Float('Calls in count') # Вх.звонков (шт разных клиентов) из реч.аналитики
    calls_out_count = fields.Float('Calls out count') # исх.звонков (шт разных клиентов) из реч.аналитики
    calls_minute = fields.Float('Calls minutes') # Вх+исх.звонков (минут) из реч.аналитики
    sonder_calls_count = fields.Float('Sonder calls count') # Sonder (шт разных клиентов) из реч.аналитики

    def _select(self):
        return """
            SELECT
                max(indicators.id) as id,
                timezone('Europe/Moscow',date_trunc('month',now())) as date,
                COALESCE(s1user.description, COALESCE(indicators.identifier_ib, 'Unknown manager')) as manager_name,
                COALESCE(indicators.identifier_ib, 'Unknown_ID') as manager_1c_id,
                COALESCE(indicators.origin_id, 'Unknown_ID') as client_1c_id,
                COALESCE(case
                    when min(indicators.turnover_percent) <= 0.8 then '4_main'
                    when min(indicators.turnover_percent) <= 0.9 then '5_mean'
                    else '6_other' end,'1_unknown') as type_client,
                COALESCE(case when min(indicators.debs_percent) <= 0.8 then '4_main' else '5_other' end,'1_unknown') as type_debts,

                COALESCE(client.full_name,'Unknown client') as client_name,

                GREATEST(
                    sum(indicators.turnover_previous_mounth),
                    sum(indicators.turnover_last_3month) / 3,
                    sum(indicators.turnover_last_30days)
                ) as plan,
                case when extract(day from now()) < 16 then
                    sum(indicators.turnover_last_30days) else
                    sum(indicators.turnover_this_mounth) / (extract(day from now()) -1 ) * (DATE_PART('days', DATE_TRUNC('month', NOW())  + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL))
                end as prediction,
                case when sum(plan) > 0 then sum(prediction) / sum(plan) else 0 end as plan_predicted_percentage,
                case when sum(plan) - sum(prediction) > 0 then sum(plan) - sum(prediction) else 0 end as turnover_lacking,
                sum(indicators.turnover_this_mounth) as turnover_this_mounth,
                sum(indicators.turnover_previous_mounth) as turnover_previous_mounth,
                sum(indicators.debt) as debt,
                sum(indicators.overdue_debt) as overdue_debt,
                sum(indicators.task_count) as task_count,
                sum(COALESCE(interaction.cnt, 0)) as interaction_count,
                sum(COALESCE(imot.calls_in_count, 0)) as calls_in_count,
                sum(COALESCE(imot.calls_out_count, 0)) as calls_out_count,
                sum(COALESCE(imot.calls_minute, 0)) as calls_minute,
                sum(COALESCE(imot.sonder_calls_count, 0)) as sonder_calls_count
        """

    def _from(self):
        return """
            FROM tmtr_exchange_1c_indicators AS indicators
        """

    def _join(self):
        return """
            LEFT JOIN tmtr_exchange_1c_partner as client ON indicators.origin_id = client.code
            LEFT JOIN (SELECT timot.client_origin_id, p2user.identifier_ib,
                sum(case when timot.type_call = 'Входящий'  then 1 else 0 end) as calls_in_count,
                sum(case when timot.type_call = 'Исходящий' then 1 when timot.type_call = 'Входящий' then 0 when COALESCE(timot.type_call, 'null') = 'null' then 1 else 0 end) as calls_out_count,
                sum(COALESCE(timot.duration,0)) / 60 as calls_minute,
                sum(case when timot.tags_rule_unique like '%Sonder%' then 1 else 0 end) as sonder_calls_count
                FROM  voximplant_imot as timot
                LEFT JOIN voximplant_operator_phone p2user on timot.operator_phone = p2user.operator_phone
                WHERE date_trunc('month', cast(to_timestamp(timot.call_time) as timestamp)) = date_trunc('month',now())  and COALESCE(timot.duration,0) > 7
                GROUP BY timot.client_origin_id, p2user.identifier_ib
                ) as imot on imot.client_origin_id = indicators.origin_id and indicators.identifier_ib = imot.identifier_ib
            LEFT JOIN tmtr_exchange_1c_user as s1user ON s1user.identifier_ib = indicators.identifier_ib
            LEFT JOIN (SELECT tinteraction.onec_member_id, tinteraction.responsible_key, count(tinteraction.responsible_key) as cnt
                FROM tmtr_exchange_1c_interaction as tinteraction
                WHERE date_trunc('month',tinteraction.date) = date_trunc('month',now())
                GROUP BY tinteraction.onec_member_id, tinteraction.responsible_key
                ) as interaction on client.id = interaction.onec_member_id and s1user.ref_key = interaction.responsible_key
        """

    def _where(self):
        return ''
        ####
        return """
            WHERE indicators.origin_id = '00-00023608' and indicators.identifier_ib = '370515e0-f824-48f3-89ba-89db66b1d618'
        """

    def _group(self):
        return """
            GROUP BY manager_name, manager_1c_id, client_name, client_1c_id
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
        sorted_records = sorted(records, key=lambda r: r.overdue_debt, reverse=True)
        _logger.info(sorted_records)
        return {
            'doc_ids' : docids,
            'doc_model' : 'efficiency.saler.report',
            'data' : data,
            'docs' : sorted_records,
        }

    @api.model
    def _render_html_by_manager(self, manager_1c_ids):
        docids = self.search([('manager_1c_id','in',manager_1c_ids)]).ids
        return self.env['ir.ui.view'].with_context(lang='ru_RU')._render_template('tmtr_exchange.efficiency_report_template',
            self._get_report_values(docids,{})
        )

    @api.model
    def _render_html_all(self):
        docids = self.search([]).ids
        return self.env['ir.ui.view'].with_context(lang='ru_RU')._render_template('tmtr_exchange.efficiency_report_template',
            self._get_report_values(docids,{})
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

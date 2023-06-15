from odoo import fields, models, tools, api


class EfficiencySalerReport(models.Model):
    """ Efficiency Saler Analysis """

    _name = "efficiency.saler.report"
    _auto = False#Обсудить False
    _description = "Efficiency Saler Report"
    _rec_name = 'id'

    manager_name = fields.Char('Manager Name')
    client_name = fields.Char('Client Name')
    type_client = fields.Char('Type client')
    date = fields.Datetime('Date')

    prediction = fields.Float('Forecast sale')
    turnover_this_mounth = fields.Float('Proceed now')
    turnover_previous_mounth = fields.Float('Proceed last')
    debt = fields.Float('Debt amount')
    overdue_debt = fields.Float('Overdue debt amount')
    task_count = fields.Integer('Task client')
    plan = fields.Float(string='План на текущий месяц')
    
    def _select(self):
        return """
            SELECT
                1 as id,
                'manager' as manager_name,
                indicators.partner_id as client_name,
                null as type_client,
                '2023-06-01' as date,

                null as prediction,
                sum(indicators.proceeds_this_mounth) as turnover_this_mounth,
                sum(indicators.proceeds_previous_mounth) as turnover_previous_mounth,
                sum(indicators.debt) as debt,
                sum(indicators.overdue_debt) as overdue_debt,
                sum(indicators.task_count) as task_count,
                sum(indicators.plan) as plan
        """

    def _from(self):
       return """
           FROM tmtr_exchange_1c_indicators AS indicators
       """

    def _join(self):
        return ''
#        return """
#            INNER JOIN voximplant_operator_phone ON imot.operator_phone = voximplant_operator_phone.operator_phone
#            LEFT JOIN tmtr_exchange_1c_partner ON voximplant_operator_phone.ref_key = tmtr_exchange_1c_partner.main_manager_key
#            RIGHT JOIN tmtr_exchange_1c_indicators ON tmtr_exchange_1c_partner.ref_key = tmtr_exchange_1c_indicators.ref_key
#        """

    def _where(self):
        return ''
#        return """
#            WHERE
#                tmtr_exchange_1c_indicators.plan IS NOT NULL
#        """

    def _group(self):
        return """
            GROUP BY client_name
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
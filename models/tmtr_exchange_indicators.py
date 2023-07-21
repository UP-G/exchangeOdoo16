from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta
from odoo import Command
import json
import pyodbc

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCIndicators(models.Model):
    _name = 'tmtr.exchange.1c.indicators'
    _description = 'finance indicators from bitrix'

    partner_id = fields.Many2one('tmtr.exchange.1c.partner', string='Partner', compute='_compute_partner_link', store=True)
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
    capacity = fields.Float('Client Capacity', compute="_compute_capacity", store=True) # Емкость клиента
    capacity_percent = fields.Float('Accumulated percent on Client Capacity') # Накопленный процент емкости клиента
    in_work_date = fields.Date(string='Date of commencement') #дата передачи в работу
    efficiency_id = fields.Many2one('efficiency.saler.report', string='Efficiency Info', compute='_compute_efficiency_link', store=True)
    interaction_ids = fields.One2many('tmtr.exchange.1c.interaction', string='Interactions from 1C', compute='_compute_interactions_link', store=False, compute_sudo=True)
    call_ids = fields.One2many("voximplant.imot", string='Calls', compute='_compute_calls_link', store=False, compute_sudo=True)
    
    metrics = fields.Char(string='Metrics About Company')

    level_code = fields.Char(string="Price Level Code")
    level_updated = fields.Datetime(string="Price Level Info Last Updated")
    level_info = fields.Char(string="JSON about Price Level")

    """ Metrics:
            "groups_3month"        => 0,  //: МассивДанных.Добавить(Выборка.Выр3Мес_1);   //товарных групп (подушки, РМК, тормоза, фильтры)
            "sonder_3month"        => 1,  //: МассивДанных.Добавить(Выборка.Выр3Мес_2);   //Sonder
            "sonder_abs_3month"    => 2,  //: МассивДанных.Добавить(Выборка.Выр3Мес_3);   //амортизаторы Sonder
            "ebs_3month"           => 3,  //: МассивДанных.Добавить(Выборка.Выр3Мес_4);   //EBS
            "turnover_3month"      => 4,  //: МассивДанных.Добавить(Выборка.Выр3Мес_5);   //Общая
                         //Выручка за 30 предыдущих дней
            "groups_30days"        => 5,  //: МассивДанных.Добавить(Выборка.ВырМесДо_1);  //товарных групп (подушки, РМК, тормоза, фильтры)
            "sonder_30days"        => 6,  //: МассивДанных.Добавить(Выборка.ВырМесДо_2);  //Sonder
            "sonder_abs_30days"    => 7,  //: МассивДанных.Добавить(Выборка.ВырМесДо_3);  //амортизаторы Sonder
            "ebs_30days"           => 8,  //: МассивДанных.Добавить(Выборка.ВырМесДо_4);  //EBS
            "turnover_30days"      => 9,  //: МассивДанных.Добавить(Выборка.ВырМесДо_5);  //Общая
                        //Выручка за предыдущий месяц
            "groups_prevmonth"     => 10, //: МассивДанных.Добавить(Выборка.ВырПредМес_1);//товарных групп (подушки, РМК, тормоза, фильтры)
            "sonder_prevmonth"     => 11, //: МассивДанных.Добавить(Выборка.ВырПредМес_2);//Sonder
            "sonder_abs_prevmonth" => 12, //: МассивДанных.Добавить(Выборка.ВырПредМес_3);//амортизаторы Sonder
            "ebs_prevmonth"        => 13, //: МассивДанных.Добавить(Выборка.ВырПредМес_4);//EBS
            "turnover_prevmonth"   => 14, //: МассивДанных.Добавить(Выборка.ВырПредМес_5);//Общая
                        //Выручка за текущий месяц
            "groups_thismonth"     => 15, //: МассивДанных.Добавить(Выборка.ВырТекМес_1); //товарных групп (подушки, РМК, тормоза, фильтры)
            "sonder_thismonth"     => 16, //: МассивДанных.Добавить(Выборка.ВырТекМес_2); //Sonder
            "sonder_abs_thismonth" => 17, //: МассивДанных.Добавить(Выборка.ВырТекМес_3); //амортизаторы Sonder
            "ebs_thismonth"        => 18, //: МассивДанных.Добавить(Выборка.ВырТекМес_4); //EBS
            "turnover_thismonth"   => 19, //: МассивДанных.Добавить(Выборка.ВырТекМес_5); //Общая

            "docs_total_90days"    => 20, //: МассивДанных.Добавить(Выборка.КолДокВсего); //Количество реализаций всего за 90 дней
            "docs_opened"          => 21, //: МассивДанных.Добавить(Выборка.КолДокНезакр);//Количество не отгруженных реализаций

    """

    @api.depends('origin_id')
    def _compute_partner_link(self):
        if self.ids:
            partner_ids = dict((r.code,r.id) for r in self.env['tmtr.exchange.1c.partner'].search([('code','in',self.mapped('origin_id'))]))
            for rec in self:
                rec.partner_id = partner_ids.get(rec.origin_id, False)

    @api.depends('origin_id')
    def _compute_efficiency_link(self):
        for rec in self:
            rec.efficiency_id = rec.id

    @api.depends('task_count')
    def _compute_interactions_link(self):
        for rec in self:
            ids = self.env['tmtr.exchange.1c.interaction'].search([('onec_member_id','=',rec.partner_id.id)]).ids
            rec.interaction_ids = ids if len(ids) else False

    @api.depends('task_count')
    def _compute_calls_link(self):
        for rec in self:
            ids = self.env['voximplant.imot'].search([('client_origin_id','=',rec.origin_id)]).ids
            rec.call_ids = ids if len(ids) else False

    @api.depends('partner_id')
    def _compute_capacity(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.capacity != rec.capacity:
                rec.capacity = rec.partner_id.capacity
            elif not rec.partner_id and rec.capacity != 0:
                rec.capacity = 0

    @api.depends('origin_id')
    def _compute_efficiency_link(self):
        for rec in self:
            rec.efficiency_id = rec.id

    def calculate_percent_new(self):
        self.search([('partner_id','=',False)])._compute_partner_link()
        self.search([('partner_id','!=',False)])._compute_capacity()
        managers = self.read_group([],[
            'identifier_ib',
            'debts:sum(overdue_debt)',
            'turnover:sum(turnover_last_3month)',
            'turnover_lacking:sum(turnover_lacking)',
            'capacity:sum(capacity)',
        ], ['identifier_ib'])
        for manager_total in managers:
            metrics = self.search([('identifier_ib','=', manager_total['identifier_ib'])], order='turnover_last_3month DESC')
            if manager_total['turnover'] == 0:
                metrics.update({
                    'turnover_percent': 1, # 100%
                })
            else:
                accumulative_turnover_percent = 0
                for metric in metrics: # already sorted by order='turnover_last_3month DESC'
                    accumulative_turnover_percent += metric.turnover_last_3month / manager_total['turnover']
                    metric.update({
                        'turnover_percent': accumulative_turnover_percent,
                    })
            if manager_total['debts'] == 0:
                metrics.update({
                    'debs_percent': 1, # 100%
                })
            else:
                accumulative_debt_percent = 0
                for metric in metrics.sorted('overdue_debt', reverse=True):
                    accumulative_debt_percent += metric.overdue_debt / manager_total['debts']
                    metric.update({
                        'debs_percent': accumulative_debt_percent,
                    })
            if manager_total['turnover_lacking'] == 0:
                metrics.update({
                    'turnover_lacking_percent': 1, # 100%
                })
            else:
                accumulative_lacking_percent = 0
                for metric in metrics.sorted('turnover_lacking', reverse=True):
                    accumulative_lacking_percent += metric.turnover_lacking / manager_total['turnover_lacking']
                    metric.update({
                        'turnover_lacking_percent': accumulative_lacking_percent,
                    })
            if manager_total['capacity'] == 0:
                metrics.update({
                    'capacity_percent': 1, # 100%
                })
            else:
                accumulative_capacity_percent = 0
                for metric in metrics.sorted('capacity', reverse=True):
                    accumulative_capacity_percent += metric.capacity / manager_total['capacity']
#                    accumulative_capacity_percent += (metric.partner_id.capacity if metric.partner_id else metric.capacity) / manager_total['capacity']
                    metric.update({
                        'capacity_percent': accumulative_capacity_percent,
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
                'turnover_this_mounth': jsonValue.get('turnover_thismonth'),
                'turnover_last_3month': jsonValue.get('turnover_3month'),
                'turnover_last_30days': jsonValue.get('turnover_30days'),
                'turnover_previous_mounth': jsonValue.get('turnover_prevmonth'),
                'overdue_debt': jsonValue.get('debt'),
                'task_count': jsonValue.get('task_count'),
                'origin_id': jsonValue.get('origin_id'),
                'identifier_ib': jsonValue.get('manager_id'),
                'debt': jsonValue.get('balance'),
                'metrics': json.dumps(jsonValue),
        }
        if not indicator:
            _logger.info(jsonValue)
            indicator = self.create(item)
        else:
            indicator.write(item)
        return indicator.id if indicator else 0

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.browse(docids)
        records._compute_efficiency_link()
        records._compute_interactions_link()
        records._compute_calls_link()
        return {
            'doc_ids' : docids,
            'doc_model' : 'tmtr.exchange.1c.indicators',
            'data' : data,
            'docs' : records,
        }

    @api.model
    def update_price_level_cron(self):
        price_level_actuality = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.price_level_actuality','12'))
        level_updated_old = datetime.now() - timedelta(hours=price_level_actuality)
        recs = self.search(['|',('level_updated','=',False),('level_updated','<',level_updated_old)])
        return recs.update_price_level_selected()

    @api.model
    def get_conn_db_analisys(self):
        price_level_connection = json.loads(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.price_level_connection','{}'))
        cnxn = pyodbc.connect(driver='FreeTDS',
            #    server='DCSRV-ERP-03.tmtr.ru,1433', 
            server=price_level_connection.get('server',''),
            database=price_level_connection.get('database',''),
            host_is_server=True,
            TDS_Version='7.4',
            user=price_level_connection.get('user',''),
            password=price_level_connection.get('password',''))
        return cnxn.cursor()

    def update_price_level_selected(self):
        level_updated_now = datetime.now()
        clients = self 
        cursor = self.get_conn_db_analisys()
        if len(clients) > 0:
            cursor.execute("""select client_code, CONCAT('L',mark) as Mark, [manual] as [manual], cur_date as [cur_date], IsNULL(days_duration,'') as days_duration
                from [analysis_op].[GetPrice].[init_clients] 
                Where client_code in ({clients})""".format(
                clients=','.join(["'{}'".format(i) for i in clients.mapped('origin_id')])
                ))
            cnt = 0
            for row in cursor:
                level_json = {
                    'client_code': row[0],
                    'mark': row[1],
                    'manual': row[2],
                    'cur_date': row[3].strftime('%Y-%m-%d'),
                    'days_duration': row[4],
                    }
                #_logger.info(','.join(['{}={}'.format(k,v) for k,v in level_json.items()]))
                rec = clients.filtered(lambda r: r.origin_id == level_json.get('client_code'))
                if rec:
                    rec.update({
                        'level_updated': level_updated_now,
                        'level_code': level_json.get('mark'),
                        'level_info': json.dumps(level_json),
                    })
                cnt += 1
            return cnt
        else:
            return 0

    @api.model
    def _render_html_best_one(self, client_origin_id, data=None):
        docids = self.search([('origin_id','=', client_origin_id)]).ids
        return self.env['ir.ui.view'].with_context(lang='ru_RU')._render_template('tmtr_exchange.best_one_report_template',
            self._get_report_values(docids, data)
        )

    def get_json_metrics(self):
        try:
            return json.loads(self.metrics) if self.metrics else {}
        except ValueError:
            return {}

    def get_json_price_level(self):
        try:
            return json.loads(self.level_info) if self.level_info else {}
        except ValueError:
            return {}

    def get_interaction_ids(self):
        return self.env['tmtr.exchange.1c.interaction'].search([('onec_member_id','in',self.mapped('partner_id.id'))]).ids

    def get_call_ids(self):
        return self.env['voximplant.imot'].search([('client_origin_id','=',self.mapped('origin_id'))]).ids


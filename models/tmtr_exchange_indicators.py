from odoo import api, fields, models, _
import logging
from datetime import datetime 
from odoo import Command

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCIndicators(models.Model):
    _name = 'tmtr.exchange.1c.indicators'
    _description = 'finance indicators from bitrix'

    partner_id = fields.Many2one('tmtr.exchange.1c.partner', string='Partner')
    plan = fields.Float(string='План на текущий месяц')
    prediction= fields.Float(string="Прогноз выручки на текущий месяц")
    proceeds_this_mounth=fields.Float(string="Выручка текущего месяца")
    proceeds_previous_mounth = fields.Float(string="Выручка предыдущего месяца")
    debt=fields.Float(string="Размер долга")
    overdue_debt= fields.Float(string="Просроченный долг")
    task_count = fields.Integer(string="Задач по клиенту")
    company_ref_key = fields.Char(string= 'Ref key')
    origin_id = fields.Char(string='origin id fron bitrix')
    manager_id = fields.Char(string="manager id")

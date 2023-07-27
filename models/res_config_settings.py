# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tag_1c_contact = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_contact')
    tag_1c_partner = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_partner')
    tag_1c_counterparty = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_counterparty')
    tag_1c_saler = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_saler')

    registration_date_partner = fields.Datetime(config_parameter='tmtr_exchange.registration_date_partner') #Стандартная дата регистрации партнера, если при выгрузке даты нет

    template_1c_manager = fields.Many2one('res.users', config_parameter='tmtr_exchange.template_1c_manager')# Шаблон для создания пользователя (Менеджера)

    best_one_filter = fields.Char(config_parameter='tmtr_exchange.best_one_filters',
        default="""[
            {"days": "30", "order": "overdue_debt DESC", "filter": [["type_debts","in",["4_main","5_mean"]],["overdue_debt",">","0"]]},
            {"days": "30", "order": "turnover_lacking DESC", "filter": [["type_client","in",["4_main","5_mean"]],["plan_predicted_percentage","<","0.8"]]},
            {"days": "14", "order": "overdue_debt DESC", "filter": [["type_debts","in",["4_main"]],["overdue_debt",">","0"]]},
            {"days": "30", "order": "capacity_lacking DESC", "filter": [["type_capacity","in",["4_main"]],["capacity_percentage","<","0.3"]]},
            {"days": "14", "order": "turnover_lacking DESC", "filter": [["type_client","in",["4_main","5_mean"]],["plan_predicted_percentage","<","0.95"]]},
            {"days": "7", "order": "overdue_debt DESC", "filter": [["type_debts","in",["4_main"]],["overdue_debt",">","0"]]},
            {"days": "7", "order": "turnover_lacking DESC", "filter": [["type_client","in",["4_main"]],["plan_predicted_percentage","<","1"]]}, 
            {"days": "14", "order": "capacity_lacking DESC", "filter": [["type_capacity","in",["4_main","5_mean"]],["capacity_percentage","<","0.3"]]}, 
            {"days": "30", "order": "turnover_lacking DESC", "filter": [["type_client","in",["4_main","5_mean"]],["plan_predicted_percentage","<","1"]]}, 
            {"days": "14", "order": "capacity_lacking DESC", "filter": [["type_capacity","in",["4_main","5_mean","6_other"]],["capacity_percentage","<","0.3"],["capacity",">","500"]]}
            ]"""
        )

    purchase_order_last_date = fields.Datetime(config_parameter='tmtr_exchange.last_order_date')

    price_level_connection = fields.Char(config_parameter='tmtr_exchange.price_level_connection', 
        help='{"server": "servername,port", "database": "basename", "user": "username", "password": "secret" }',
        default='{"server": "192.168.0.20,1433", "database": "analysis", "user": "DWHUser", "password": "secret" }')

    price_level_actuality = fields.Integer(config_parameter='tmtr_exchange.price_level_actuality', default="23")

    tmtr_default_team_id = fields.Many2one('crm.team', config_parameter='tmtr_exchange.default_team_id') # Команда продаж по умолчанию, если иная команда не найдена

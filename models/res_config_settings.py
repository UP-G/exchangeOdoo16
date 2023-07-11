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

    best_one_filter = fields.Char(config_parameter='tmtr_exchange.best_one_filters')

    purchase_order_last_date = fields.Datetime(config_parameter='tmtr_exchange.last_order_date')
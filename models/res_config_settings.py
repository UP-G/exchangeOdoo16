# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tag_1c_contact = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_contact')
    tag_1c_partner = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_partner')
    tag_1c_counterparty = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_counterparty')
    tag_1c_saler = fields.Many2one('res.partner.category', config_parameter='tmtr_exchange.tag_1c_saler')

    registration_date_partner = fields.Datetime(config_parameter='tmtr_exchange.registration_date_partner')

    template_1c_manager = fields.Many2one('res.users', config_parameter='tmtr_exchange.template_1c_manager')

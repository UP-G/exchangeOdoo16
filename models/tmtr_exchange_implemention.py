from odoo import api, fields, models, _

import json

class TmtrExchangeOneCImplemention(models.Model):
    _name = 'tmtr.exchange.1c.implemention'
    _description = '1C Implemention'

    ref_key = fields.Char(string='Ref key')
    impl_num = fields.Char(string='Номер реализации')
    address= fields.Char(string='Адрес')
    phone = fields.Char(string='Телефон')
    partner_key = fields.Many2one('tmtr.exchange.1c.partner', string='Контрагент key')
    order_id = fields.Many2one('tmtr.exchange.1c.purchase.order', string='Заказ id')





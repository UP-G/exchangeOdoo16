from odoo import api, fields, models, _

import json

class TmtrExchangeOneCImplemention(models.Model):
    _name = 'tmtr.exchange.1c.implemention'
    _description = '1C Implemention'

    ref_key = fields.Char(string='Ref key')
    impl_num = fields.Char(string='Implementation number') #Номер реализации
    address= fields.Char(string='Address')
    phone = fields.Char(string='Number phone')
    partner_key = fields.Many2one('tmtr.exchange.1c.partner', string='Counterparty id')
    order_id = fields.Many2one('tmtr.exchange.1c.purchase.order', string='Order id')
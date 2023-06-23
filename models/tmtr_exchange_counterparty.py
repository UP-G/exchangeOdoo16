from odoo import api, fields, models, _
import logging
from datetime import datetime 
from odoo import Command
import time

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCCounterparty(models.Model):
    _name = 'tmtr.exchange.1c.counterparty'
    _description = '1C Counterparty'

    partner_id = fields.Many2one('res.partner', string='Partner')
    ref_key = fields.Char(string='ref_key')
    data_version= fields.Char(string="DataVersion")
    description=fields.Char(string="Description")
    full_name = fields.Char(string="НаименованиеПолное")
    partner_key=fields.Char(string="Партнер_Key")
    ur_fiz_face= fields.Char(string="ЮрФизЛицо")
    tm_code = fields.Char(string="ТМ_Код")
    contact= fields.Text('КонтактнаяИнформация')

    def add_entry_cron(self):
        start_time = time.time()
        skip = 0
        top = 100
        while time.time() - start_time < 60:
            try:
                counterparty_list= self.env['tmtr.exchange.1c.counterparty'].search([('tm_code', "!=", None)],order="tm_code desc",limit=1)
                maxCode = '0000000000'
                if counterparty_list:
                    maxCode = counterparty_list.tm_code
                data = self.env['odata.1c.route'].get_by_route("1c_ut/get_catalog/", {"catalog_name": "Catalog_Контрагенты", "filter": f"DeletionMark eq false and ТМ_Код ge '{maxCode}'&$orderby=ТМ_Код&$top={top}&$skip={skip}"})["value"]
                if not data:
                    continue 
                for json_data in data:
                    counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("ref_key", "=", json_data['Ref_Key'])])
                    if not counterparty:
                        self.env['tmtr.exchange.1c.counterparty'].create({
                                'ref_key' : json_data['Ref_Key'],
                                'data_version' : json_data['DataVersion'],
                                'description' : json_data['Description'],
                                'full_name' : json_data['НаименованиеПолное'],
                                'partner_key' : json_data['Партнер_Key'],
                                'ur_fiz_face' : json_data['ЮрФизЛицо'],
                                'tm_code' : json_data['ТМ_Код'],
                                'contact':'\n'.join([f"{contact['Тип']}: {contact['Представление']}" for contact in json_data['КонтактнаяИнформация']])
                            })
            except Exception as e:
                _logger.info(e)
            skip += top
    def upload_parnter_ref(self):
        limit = 1000
        partners = self.env['tmtr.exchange.1c.partner'].search([("partner_id", "=", None)], limit=limit)
        
        for partner in partners:
            counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("partner_id", "=", partner['ref_key'])], limit=1)
            if not counterparty:
                continue
            partner.update({
                'partner_id': counterparty.id
                })

    def add_res_partner(self):
        # obj = {}
        start_time = time.time()
        limit = 100
        while time.time() - start_time < 60:
            counterparty_tag_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.tag_1c_counterparty'))
            if not counterparty_tag_id:
                continue
            counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("partner_id", "=", None)], limit=limit)
            for data_counterparty in counterparty:
                name = data_counterparty['full_name'] if data_counterparty['full_name'] else data_counterparty['description']
                if not name:
                    continue
                s = data_counterparty['contact']
                lines = s.split('\n')
                phone = ''
                addres = ''
                for line in lines:
                    type_contact=line.split(":")[0].strip()
                    if type_contact == 'Телефон':
                        phone = line.split(":")[1].strip()
                    if type_contact == 'Адрес':
                        addres = line.split(":")[1].strip()
                new_counterparty = self.env['res.partner'].create({
                    'name': name,
                    'is_company': True,
                    'comment': '{} \n {}'.format(data_counterparty['description'],data_counterparty['contact']),
                    'street': addres,
                    'phone': phone,
                    'category_id': [(6, 0, [counterparty_tag_id])],
                })
                data_counterparty.write({
                    'partner_id': new_counterparty.id
                })
            
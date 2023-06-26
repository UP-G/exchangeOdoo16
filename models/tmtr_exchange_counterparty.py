from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta
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
    full_name = fields.Char(string="Full name counterparty")
    partner_key=fields.Char(string="Partner Key")
    ur_fiz_face= fields.Char(string="Legal entity (physical person)")
    tm_code = fields.Char(string="TM_Code")
    contact= fields.Text(string='Contact information')

    def upload_new_counterparty(self, tm_code_max=None, top=100, skip=0):

        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        while datetime.now() < finish_before:
            try:
                if not tm_code_max:
                    counterparty_list= self.env['tmtr.exchange.1c.counterparty'].search([('tm_code', "!=", None)],order="tm_code desc",limit=1)
                
                    if not counterparty_list:
                        return
                    tm_code_max = counterparty_list.tm_code

                data = self.env['odata.1c.route'].get_by_route(
                    "1c_ut/get_counterparty/", 
                    {
                        "tm_code": tm_code_max, 
                        "top": top,
                        "skip": skip
                        })["value"]

                if not data:
                    return

                ref_key_ids = [r['Ref_Key'] for r in data]
                counterparty_exists = dict((r.ref_key, r.ref_key) for r in self.search([("ref_key", "in", ref_key_ids)]))
                for json_date in data:
                    #counterparty = self.env['tmtr.exchange.1c.counterparty'].search([("ref_key", "=", json_data['Ref_Key'])])
                    if json_date['Ref_Key'] in counterparty_exists:
                        continue
                    new_counterparty = self.create_new_counterparty(json_date)
                skip += top

            except Exception as e:
                _logger.info(e)
            

    def create_new_counterparty(self, json_date):
        self.env['tmtr.exchange.1c.counterparty'].create({
            'ref_key' : json_date['Ref_Key'],
            'data_version' : json_date['DataVersion'],
            'description' : json_date['Description'],
            'full_name' : json_date['НаименованиеПолное'],
            'partner_key' : json_date['Партнер_Key'],
            'ur_fiz_face' : json_date['ЮрФизЛицо'],
            'tm_code' : json_date['ТМ_Код'],
            'contact':'\n'.join([f"{contact['Тип']}: {contact['Представление']}" for contact in json_date['КонтактнаяИнформация']])
            })
        return

    def upload_parnter_ref(self, limit=1000): #Непонятно, что делает данный метод: Андрей чурилов
        
        partners = self.env['tmtr.exchange.1c.partner'].search([("partner_id", "=", None)], limit=limit)
        
        for partner in partners:
            counterpartys = self.env['tmtr.exchange.1c.counterparty'].search([("partner_id", "=", partner['ref_key'])])
            if not counterpartys:
                continue
            for counterparty in counterpartys:
                partner.update({
                    'partner_id': counterparty.id
                    })

    def add_res_partner(self, limit=100):
        # obj = {}
        start_time = time.time()
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
            
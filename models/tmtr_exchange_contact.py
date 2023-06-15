from odoo import api, fields, models, _
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from odoo import Command

class TmtrExchangeOneCContact(models.Model):
    _name = 'tmtr.exchange.1c.contact'
    _description = '1C Contact'

    ref_key = fields.Char(string='Ref_key')
    owner_key = fields.Char(string='Owner_Key')
    description = fields.Char(string='Description')
    communication_registration_date = fields.Datetime(string= 'Дата Регистрации Связи')

    contacts = fields.Text(string='Контактная информация')

    onec_partner_id = fields.Many2one('tmtr.exchange.1c.partner', string='1C Partner')
    partner_id = fields.Many2one('res.partner', string = 'Partner')

    def update_contact_from_max_date(self, top, skip):
  
        max_date = self.env['tmtr.exchange.1c.contact'].search([], limit=1, order="communication_registration_date ASC")
        max_date_str = max_date.communication_registration_date.strftime('%Y-%m-%dT%H:%M:%S')

        data = self.env['odata.1c.route'].get_by_route(
             "1c_ut/get_contact_partner/", 
             {
                  "date": max_date_str,
                  "top": top,
                  "skip": skip
                  })

        contact_partner = data['value']
        for data_contact in contact_partner:
                if data_contact['DeletionMark'] == True:
                    continue
                contact = self.env['tmtr.exchange.1c.contact'].search([("ref_key", "=", data_contact['Ref_Key'])])
                if contact:
                     continue
                self.env['tmtr.exchange.1c.contact'].create({
                        'ref_key' : data_contact['Ref_Key'],
                        'owner_key' : data_contact['Owner_Key'],
                        'description' : data_contact['Description'],
                        'communication_registration_date' : datetime.strptime(data_contact['ДатаРегистрацииСвязи'], '%Y-%m-%dT%H:%M:%S'),
                        'contacts': '\n'.join([f"{contact['Тип']}: {contact['Представление']}" for contact in data_contact['КонтактнаяИнформация']]),
                        'onec_partner_id': self.get_owner_contact_partner(owner_key = data_contact['Owner_Key']),
                    })
    
    def get_owner_contact_partner(self, owner_key):
         onec_partner = self.env['tmtr.exchange.1c.partner'].search([("ref_key", "=", owner_key)])
         return onec_partner.id
    
    def update_onec_partner_id(self, limit):
        contact_partner = self.env['tmtr.exchange.1c.contact'].search([("onec_partner_id", "=", None)], limit=limit)
        for data_contact in contact_partner:
            data_contact['onec_partner_id'] = self.get_owner_contact_partner(owner_key=data_contact['owner_key'])

    def update_child_ids(self):
         
        return

    def create_contact_in_res_partner(self, limit):

        contact = self.env['tmtr.exchange.1c.contact'].search([("partner_id", "=", None)], limit=limit)

        contact_tag_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.tag_1c_contact'))

        if not contact_tag_id:
            return

        for data_contact in contact:
                if data_contact['description'] == None or data_contact['description'] == "-":
                    continue

                obj = {
                        'name': data_contact['description'],
                        'is_company': False,
                        'category_id': [(6, 0, [contact_tag_id])]
                       }

                string_contact = data_contact['contacts']
                lines = string_contact.split('\n')
                for line in lines:
                    type_contact=line.split(":")[0].strip()
                    if type_contact == 'Телефон':
                        obj.update({'phone': line.split(":")[1].strip()})
                    if type_contact == 'АдресЭлектроннойПочты':
                        obj.update({'email': line.split(":")[1].strip()})

                        new_contact = self.env['res.partner'].create(obj)
                        data_contact.partner_id = new_contact.id   

                obj = {}

    # def create_res_partner_cron(self, limit):
    #     contact = self.env['tmtr.exchange.1c.contact'].search([("partner_id", "=", None)], limit=limit)
    #     self.create_contact_in_res_partner(contact=contact)
            

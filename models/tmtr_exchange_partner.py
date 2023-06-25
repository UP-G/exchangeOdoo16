from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta
from odoo import Command
import time

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCPartner(models.Model):
    _name = 'tmtr.exchange.1c.partner'
    _description = '1C Partner'

    partner_id = fields.Many2one('res.partner', string='Partner')
    ref_key = fields.Char(string='Ref_key')
    parent_key = fields.Char(string='Parent key')
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    full_name = fields.Char(string='Full client name')
    main_manager_key = fields.Char(string='Main manager key')
    date_of_registration = fields.Datetime(string='Date of Registration')

    user_id = fields.Many2one('res.users', string='Manager')

    def upload_new_partner(self, code=None, skip=0, top=100):
        try:
            finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой

            if not code: #Если не указан с какого code начинаем выкачиваем
                partner_list= self.env['tmtr.exchange.1c.partner'].search([('code', 'not like', '%УТ')],
                                                                      order="code desc",limit=1) #Берем максимальный code
                if not partner_list:
                    code = '00-00000000'
                else:
                    code = partner_list.code
            while datetime.now() < finish_before:
                data = self.env['odata.1c.route'].get_by_route(
                    "1c_ut/get_partner/", 
                    {
                        "code": code,
                        "skip": skip,
                        "top": top
                    })["value"]
                
                if not data:
                    return 
                for json_data in data:
                    self.create_by_odata_array(json_data)
                skip += top
        except Exception as e:
            _logger.info(e)
            return

    def create_by_odata_array(self, json_data):
        partner = self.env['tmtr.exchange.1c.partner'].search([("ref_key", "=", json_data['Ref_Key'])])
        if not partner:
            return 1 if self.env['tmtr.exchange.1c.partner'].create({
                            'ref_key' : json_data['Ref_Key'],
                            'parent_key' : json_data['Parent_Key'],
                            'code' : json_data['Code'],
                            'description' : json_data['Description'],
                            'full_name' : json_data['НаименованиеПолное'],
                            'main_manager_key' : json_data['ОсновнойМенеджер_Key'],
                            'date_of_registration' : self.parse_date(json_data['ДатаРегистрации']),
                        }) else 0
        else:
            return 0

    def get_partner_by_name(self, names):
        cnt = 0
        for name in names:
            data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_catalog/", {
                    "catalog_name": "Catalog_Партнеры", 
                    "filter": f"Description eq '{name}'&$orderby=Code&$top=1&$skip=0"
                })['value']
            for json_data in data:
                cnt += 1 if self.create_by_odata_array(json_data) > 0 else 0
        return cnt

    def get_partner_by_origin_id(self, origin_ids):
        cnt = 0
        for origin_id in origin_ids:
            data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_catalog/", {
                    "catalog_name": "Catalog_Партнеры", 
                    "filter": f"Code eq '{origin_id}'&$orderby=Code&$top=1&$skip=0"
                })['value']
            for json_data in data:
                cnt += 1 if self.create_by_odata_array(json_data) > 0 else 0
        return {'cnt': len(origin_ids), 'exists': cnt}


    def parse_date(self, string_date):
        default_date = self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.registration_date_partner')
        if string_date == '0001-01-01T00:00:00' or string_date == None:
            return datetime.strptime(default_date, '%Y-%m-%d %H:%M:%S')
        
        return datetime.strptime(string_date, '%Y-%m-%dT%H:%M:%S')
        
    def add_partner_in_res_partner(self, limit):

        partner_tag_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.tag_1c_partner'))

        if not partner_tag_id:
            return

        partner = self.env['tmtr.exchange.1c.partner'].search([("partner_id", "=", None)], limit=limit)

        for data_partner in partner:
            if not data_partner['full_name'] or not data_partner['description']:
                continue

            name = data_partner['full_name'] if data_partner['full_name'] else data_partner['description']

            if not name:
                continue
            
            cur_partner = self.env['res.partner'].search([('name', '=', name)])

            if cur_partner:
                continue

            new_partner = self.env['res.partner'].create({
                'name': name,
                'is_company': True,
                'category_id': [(6, 0, [partner_tag_id])]
            })

            data_partner['partner_id'] = new_partner.id

        return

    def update_child_ids(self):
        onec_contacts = self.env['tmtr.exchange.1c.contact'].search((["&",('partner_id', '!=', None),
                                                                        ('onec_partner_id.partner_id', '!=', None)]))

        for contact in onec_contacts:
            contact.onec_partner_id.partner_id.write({
            'child_ids': [(6, 0, [contact.partner_id.id])]
        })
        return
    
    def update_seller(self):
        onec_partner = self.env['tmtr.exchange.1c.partner']
        main_managers = self.env['tmtr.exchange.1c.user'].search(["&", ('ref_key', '!=', None),
                                          ('user_id', '!=', None)])
        

        for manager in main_managers:
            partner = onec_partner.search(["&",('user_id', '=', None),
                                            ('main_manager_key', '=', manager['ref_key'])])
            
            partner.update({
                'user_id': manager['user_id']
            })

        return
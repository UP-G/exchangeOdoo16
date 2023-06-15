from odoo import api, fields, models, _
import logging
from datetime import datetime
from odoo import Command

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCPartner(models.Model):
    _name = 'tmtr.exchange.1c.partner'
    _description = '1C Partner'

    partner_id = fields.Many2one('res.partner', string='Partner')
    ref_key = fields.Char(string='ref_key')
    data_version = fields.Char(string='data version')
    parent_key = fields.Char(string='parent key')
    code = fields.Char(string='code')
    description = fields.Char(string='description')
    business_region_key = fields.Char(string='business region key')
    registration_date = fields.Datetime(string='registration date')
    is_client = fields.Boolean(string="is client")
    is_provider = fields.Boolean(string = "is provider")
    full_name = fields.Char(string='full client name')
    main_manager_key = fields.Char(string='main manager key')
    is_competitor = fields.Boolean(string = "is competitor")
    other_relation = fields.Boolean(string='other relation')
    is_served_by_sales = fields.Boolean(string='is served by Sales representatives')


    def add_entry_cron(self, skip, top):
        try:
            partner_list= self.env['tmtr.exchange.1c.partner'].search([('code', 'not like', '%УТ')],order="code desc",limit=1)
            if not partner_list:
                maxCode = '00-00000000'
            else:
                maxCode = partner_list.code
            data = self.env['odata.1c.route'].get_by_route("1c_ut/get_catalog/", {"catalog_name": "Catalog_Партнеры", "filter": f"DeletionMark eq false and Code ge '{maxCode}'&$orderby=Code&$top={top}&$skip={skip}"})["value"]
            if not data:
                return 
            for json_data in data:
                partner = self.env['tmtr.exchange.1c.partner'].search([("ref_key", "=", json_data['Ref_Key'])])
                if not partner:
                    self.env['tmtr.exchange.1c.partner'].create({
                            'ref_key' : json_data['Ref_Key'],
                            'data_version' : json_data['DataVersion'],
                            'parent_key' : json_data['Parent_Key'],
                            'code' : json_data['Code'],
                            'description' : json_data['Description'],
                            'business_region_key' : json_data['БизнесРегион_Key'],
                            'registration_date' : datetime.strptime(json_data['ДатаРегистрации'], '%Y-%m-%dT%H:%M:%S'),
                            'is_client' : json_data['Клиент'],
                            'is_provider' : json_data['Поставщик'],
                            'full_name' : json_data['НаименованиеПолное'],
                            'main_manager_key' : json_data['ОсновнойМенеджер_Key'],
                            'is_competitor' : json_data['Конкурент'],
                            'other_relation' : json_data['ПрочиеОтношения'],
                            'is_served_by_sales' : json_data['ОбслуживаетсяТорговымиПредставителями'],
                        })
        except Exception as e:
            _logger.info(e)
            return
        
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
            
            new_partner = self.env['res.partner'].create({
                'name': name,
                'is_company': True,
                'category_id': [(6, 0, [partner_tag_id])]
            })

            data_partner['partner_id'] = new_partner.id

            contact = self.env['tmtr.exchange.1c.contact'].search(["&", ("onec_partner_id", "=", data_partner['id']),
                                                                   ("partner_id", "!=", None)])

            for data_contact in contact:
                new_partner.write({
                    'child_ids': [(4, data_contact['partner_id'])]
                    })
                return
        
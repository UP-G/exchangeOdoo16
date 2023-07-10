from odoo import api, fields, models, _

class TmtrExchangeOneCUser(models.Model):
    _name = 'tmtr.exchange.1c.user'
    _description = '1C User'

    user_id = fields.Many2one('res.users', string='user id')
    ref_key = fields.Char(string='Ref_key')
    identifier_ib = fields.Char(string='identifier user ib', index=True)
    code = fields.Char(string='Code')
    description = fields.Char(string='Description')
    contacts = fields.Text()

    def add_in_res_users(self, limit):
        template_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.template_1c_manager'))

        manager_tag_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.tag_1c_saler'))

        if not template_id:
            return
        
        onec_user = self.env['tmtr.exchange.1c.user'].search(["&", ('user_id', '=', None), 
                                                              ('identifier_ib', '!=', '00000000-0000-0000-0000-000000000000')], 
                                                              limit=limit)

        for onec_user_data in onec_user:     
            manager = self.env['tmtr.exchange.1c.interaction'].search(["&", ('responsible_key', '!=', onec_user_data['ref_key']),
                                                                           ('user_id', '=', None)], limit=limit)

            if not manager:
                continue

            user = self.env['res.users'].search([('name', '=', onec_user_data['description'])])

            if user:
                continue
            
            obj = {}
            if onec_user_data['description'] == None:
                continue

            obj = {
            'name': onec_user_data['description'],
            'category_id': [(6, 0, [manager_tag_id])],
            }

            template_manager = self.env['res.users'].search([("id", "=", template_id)])

            string_contact = onec_user_data['contacts']
            lines = string_contact.split('\n')
            for line in lines:
                type_contact=line.split(":")[0].strip()
                if type_contact == 'Телефон':
                    obj.update({'phone': line.split(":")[1].strip()})
                if type_contact == 'АдресЭлектроннойПочты':
                    obj.update({'email': line.split(":")[1].strip()})
                    if not 'login' in obj and "@tmtr.ru" in line.split(":")[1].strip():
                        obj.update({'login': line.split(":")[1].strip()})

            if 'login' in obj:
                user = self.env['res.users'].search([('login', '=', obj['login'])])
                if user:
                    continue
                new_manager = template_manager.copy(default=obj)
                
            obj = {}
    
    def upload_user(self, top, skip):
        max_code_user = self.env['tmtr.exchange.1c.user'].search([('code', "!=", None)],order="code desc",limit=1)['code']

        if not max_code_user:
            max_code_user = '00000000000'

        data = self.env['odata.1c.route'].get_by_route(
            "1c_ut/get_users/", 
            {
                "top": top,
                "skip": skip,
                "code": max_code_user
        })['value']

        for data_user in data:
            self.create_by_odata_json(data_user)


    def create_by_odata_json(self, data_user):
        onec_user = self.env['tmtr.exchange.1c.user'].search([('ref_key', "=", data_user['Ref_Key'])])
        if onec_user:
            return onec_user
        return self.env['tmtr.exchange.1c.user'].create({
                'ref_key': data_user['Ref_Key'],
                'description': data_user['Description'],
                'code': data_user['Code'],
                'identifier_ib': data_user['ИдентификаторПользователяИБ'],
                'contacts': '\n'.join([f"{contact['Тип']}: {contact['Представление']}" for contact in data_user['КонтактнаяИнформация']]),
            })


    def upload_by_sec_id(self, sec_ids):
        cnt = 0
        for sec_id in sec_ids:
            data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_users_by_sec_id/", 
                {
                    "sec_id": sec_id
            })['value']
            for data_user in data:
                cnt += 1 if self.create_by_odata_json(data_user) else 0
        return {'cnt': len(sec_ids), 'exists': cnt}


    def update_user_id(self, limit):
        users = self.env['tmtr.exchange.1c.user'].search([('user_id', "=", None)], limit=limit)

        for user in users:
            res_user = self.env['res.users'].search([('name', "=", user['description'])])['id']
            if not res_user:
                continue
            user['user_id'] = res_user

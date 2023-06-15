from odoo import api, fields, models, _

class TmtrExchangeOneCUser(models.Model):
    _name = 'tmtr.exchange.1c.user'
    _description = '1C User'

    user_id = fields.Many2one('res.users', string='user id')
    ref_key = fields.Char(string='Ref_key')
    ib_user_id = fields.Char(string='IB User ID')

    def add_in_res_users(self, limit):
        template_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.template_1c_manager'))
        if not template_id:
            return
        
        manager = self.env['tmtr.exchange.1c.interaction'].search(["&",('responsible_key', '!=', None),
                                                                           ('user_id', '=', None)], limit=limit)

        for data_manager in manager:

            obj = {}
            data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_user/", 
                {
                    "Ref_Key": data_manager['Ref'],
            })['value']

            for cur_manager in data:
                if cur_manager['Description'] == None:
                    continue

                obj = {
                    'name': cur_manager['Description'],
                    }
                
                template_manager = self.env['res.users'].search([("id", "=", template_id)])

                for contacts in cur_manager['КонтактнаяИнформация']:
                    if contacts['Тип'] == 'Телефон':
                        obj.update({'phone': contacts['Представление']})
                    if contacts['Тип'] == 'АдресЭлектроннойПочты':
                        obj.update({'email': contacts['Представление']})
                        if not 'login' in obj and "@tmtr.ru" in contacts['Представление']:
                            obj.update({'login': contacts['Представление']})

                new_manager = template_manager.copy(default=obj)

                data_manager.user_id = new_manager.id

            

from odoo import api, fields, models, _

import json
from datetime import datetime

class TmtrExchangeOneCInteraction(models.Model):
    _name = 'tmtr.exchange.1c.interaction'
    _description = '1C Interaction'

    ref = fields.Char(string='Ref')
    ref_type = fields.Char(string='Ref type')
    date = fields.Datetime(string='Date')
    importance = fields.Char(string='Важность')
    tm_theme = fields.Char(string='ТМ_Тема')
    members = fields.Char(string='Members')
    author_key = fields.Char(string='Author_Key')
    responsible_key = fields.Char(string='Responsible_Key')
    user_id = fields.Many2one('res.users', string='Responsible saler')

    onec_member_id = fields.Many2one('tmtr.exchange.1c.partner', string='Member (Partner)')

    def test_button(self):
        return

    def update_interaction_on_date(self, date, top, skip):
             
        interaction_data = self.env['odata.1c.route'].get_by_route(
             "1c_ut/get_journal_interaction/", 
             {
                "date": date,
                "top": top,
                "skip": skip
                })['value']
        
        for json_data in interaction_data:
            if json_data['DeletionMark'] == True:
                continue
            interaction = self.env['tmtr.exchange.1c.interaction'].search([("ref", "=", json_data['Ref'])])
            if interaction:
                continue
            
            new_interaction = self.env['tmtr.exchange.1c.interaction'].create({
                    'ref' : json_data['Ref'],
                    'ref_type' : json_data['Ref_Type'],
                    'date' : datetime.strptime(json_data['Date'], '%Y-%m-%dT%H:%M:%S'),
                    'importance' : json_data['Важность'],
                    'tm_theme' : json_data['ТМ_Тема'],
                    'author_key': json_data['Автор_Key'],
                    'responsible_key': json_data['Ответственный_Key']
                })
                
            if "," not in json_data['Участники']:
                partner = self.env['tmtr.exchange.1c.partner'].search([("full_name", "=", json_data['Участники'])], limit=1)
                new_interaction.update({
                    'members': json_data['Участники']
                })
                new_interaction.update({
                    'onec_member_id': partner.id
                })
            else:
                words = [w.strip() for w in json_data['Участники'].split(",") if "," not in w and w.strip()]
                result = ", ".join(words)
                new_interaction.update({
                    'members': result
                })

    def upload_members_interaction(self, limit):
        interactions_no_member_ids = self.env['tmtr.exchange.1c.interaction'].search([("onec_member_id", "=", None)], limit=limit)
        for interactions in interactions_no_member_ids:
            partner = self.env['tmtr.exchange.1c.partner'].search([("full_name", "=", interactions['members'])])
            if not partner:
                continue
            interactions.update({
                'onec_member_id': partner.id
                })
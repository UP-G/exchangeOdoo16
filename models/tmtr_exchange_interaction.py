from odoo import api, fields, models, _

import json
from datetime import datetime, timedelta

class TmtrExchangeOneCInteraction(models.Model):
    _name = 'tmtr.exchange.1c.interaction'
    _description = '1C Interaction'

    ref = fields.Char(string='Ref', index=True) # Т.к выкачываем журнал то вместо ref_key -> ref
    ref_type = fields.Char(string='Ref type') # То куда указвыает ref
    date = fields.Datetime(string='Date', index=True)
    importance = fields.Char(string='Importance') # Важность
    tm_theme = fields.Char(string='TM_theme') # Тема взаимодействия 
    members = fields.Char(string='Members') # Участники
    author_key = fields.Char(string='Author_Key')
    responsible_key = fields.Char(string='Responsible_Key', index=True)

    user_id = fields.Many2one('res.users', string='Responsible saller')
    partner_id = fields.Many2one('res.partner', string='Partner')
    onec_member_id = fields.Many2one('tmtr.exchange.1c.partner', string='Member (Partner)') # В случаи если один участник то ссылка на него

    def test_button(self):
        return


    def upload_new_interaction(self, from_date = None, top = 100, skip = 0):
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        if not from_date:
            from_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param('tmtr.exchange.1c_interaction_date','2023-06-20 00:00:00'))
            #self.env['ir.config_parameter'].set_param('tmtr.exchange.1c_interaction_date', from_date)
        date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
        date_till = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") # не искать дальше текущей даты
        stop_import = False
        total_cnt = 0
        members_cache = {}
        while datetime.now() < finish_before and not stop_import:
            interaction_data = self.env['odata.1c.route'].get_by_route(
                 "1c_ut/get_journal_interaction/", 
                {
                    "date": date,
                    "top": top,
                    "skip": skip
                    })['value']
            ref_ids = [r['Ref'] for r in interaction_data if r['DeletionMark'] != True]
            members = dict((r['Участники'],r['Участники']) for r in interaction_data if r['DeletionMark'] != True and not r['Участники'] in members_cache)
            members_part = self.env['tmtr.exchange.1c.partner'].search([("full_name", "in", list(members.keys()))])
            if members_part:
                members_cache.update(dict((r.full_name, r.id) for r in members_part))
            interaction_exists = dict((r.ref, r.ref) for r in self.search([("ref", "in", ref_ids)]))
            cnt = 0
            for item in interaction_data:
                if not item['Ref'] in interaction_exists:
                    new_interaction = self.create_interaction(item, members_cache)
                    cnt += 1
            skip += top
            total_cnt += cnt
            if date < date_till and cnt == 0:
                # перейти к следующему дню, если он в прошлом
                from_date += timedelta(days=1)
                date = from_date.strftime("%Y-%m-%dT%H:%M:%S")
                skip = 0
            elif date >= date_till and cnt == 0:
                # за текущий день больше не чего импортировать, прервать импорт
                stop_import = True
        # Сохранить день, на котором остановился импорт
        if date <= date_till:
            self.env['ir.config_parameter'].set_param('tmtr.exchange.1c_interaction_date', from_date)
        return {'cnt': total_cnt, 'data': from_date}

    """ Алгоритм создает слишком большую нагрузку на 1С
    def upload_interaction_on_max_date(self, top, skip):
        interaction = self.search([('date', '!=', None)],order="date asc",limit=1)
        # date = '2009-02-08T00:00:00'
        date = '2009-06-20T00:00:00'
        if interaction:
            date = interaction.date.strftime("%Y-%m-%dT%H:%M:%S")
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
            interaction = self.search([("ref", "=", json_data['Ref'])])
            if interaction:
                continue
            new_interaction = self.create_interaction(json_data)
    """

    def create_interaction(self, json_data, members_cache = {}):
        new_interaction = self.create({
                    'ref' : json_data['Ref'],
                    'ref_type' : json_data['Ref_Type'],
                    'date' : datetime.strptime(json_data['Date'], '%Y-%m-%dT%H:%M:%S'),
                    'importance' : json_data['Важность'],
                    'tm_theme' : json_data['ТМ_Тема'],
                    'author_key': json_data['Автор_Key'],
                    'responsible_key': json_data['Ответственный_Key']
                })
        if "," not in json_data['Участники']:
                if len(members_cache) > 0:
                    partner_id = members_cache.get(json_data['Участники'])
                else:
                    partner = self.env['tmtr.exchange.1c.partner'].search([("full_name", "=", json_data['Участники'])], limit=1)
                    partner_id = partner.id if partner else 0
                new_interaction.update({
                    'members': json_data['Участники']
                })
                new_interaction.update({
                    'onec_member_id': partner_id
                })
        else:
                words = [w.strip() for w in json_data['Участники'].split(",") if "," not in w and w.strip()]
                result = ", ".join(words)
                new_interaction.update({
                    'members': result
                })
        return new_interaction


    def update_members_interaction(self):
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        members_unknown = self.read_group([("onec_member_id", "=", None)], fields=['members', 'cnt:count(id)'], groupby=['members', 'cnt'])
        cnt = self.search_count([("onec_member_id", "=", None)])
        members_to_cache = self.env['tmtr.exchange.1c.partner'].search([("description", "in", [r['members'] for r in members_unknown])])
        members_cache = dict((r.description, r.id) for r in members_to_cache)
        members_to_update = self.search([("onec_member_id", "=", None),('members','in',list(members_cache.keys()))])
        updated = 0
        for item in members_unknown:
            if datetime.now() < finish_before and item['members'] in members_cache:
                recs_to_update = members_to_update.filtered(lambda x: (x.members == item['members']))
                recs_to_update.update({'onec_member_id': members_cache[item['members']]})
                updated += len(recs_to_update)
        return {'unknown': cnt, 'exists': len(members_to_update), 'updated': updated}

    def get_unknown_1c_partners(self, recs = None, limit = None):
        if not recs:
            members_unknown = self.read_group([("onec_member_id", "=", None)], fields=['members', 'cnt:count(id)'], groupby=['members', 'cnt'])
        else:
            members_unknown = self.read_group([("id", "in", recs.ids)], fields=['members', 'cnt:count(id)'], groupby=['members', 'cnt'])
        if len(members_unknown) > 0:
            return self.env['tmtr.exchange.1c.partner'].get_partner_by_name([r['members'] for r in (members_unknown if limit == None else members_unknown[0:min(len(members_unknown),limit)])])
        else:
            return 0

    def update_manager_interaction(self, limit):
        interaction = self.search([('user_id', '=', None)], limit=limit)

        for interaction_data in interaction:
            manager = self.env['tmtr.exchange.1c.user'].search([
                ('user_id', '!=', None),
                ('ref_key', '=', interaction_data['responsible_key'])
            ])
            if not manager:
                continue
            interaction_data.user_id = manager.user_id

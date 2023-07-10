from odoo import api, fields, models, _

import json
from datetime import datetime, timedelta

class TmtrExchangeOneCBusinessType(models.Model):
    _name = 'tmtr.exchange.1c.business_type'
    _description = '1C Business Type'

    ref = fields.Char(string='Ref', index=True) # ref_key
    code = fields.Char(string='Business Type Code') # Code
    name = fields.Char(string='Business Type Name') # Description

    def upload_new(self, from_code = '000000000', top = 100, skip = 0):
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        nothing2import = 0
        total_cnt = 0
        while datetime.now() < finish_before and nothing2import < 3:
            json_data = self.env['odata.1c.route'].get_by_route(
                 "1c_ut/get_business_type/",
                {
                    "code": from_code,
                    "top": top,
                    "skip": skip
                    })['value']
            cnt = 0
            for item in json_data:
                if item['DeletionMark'] != True:
                    rec = self.create_by_odata_json(item)
                    cnt += 1
            skip += top
            total_cnt += cnt
            nothing2import += 1 if cnt == 0 else 0
        return {'cnt': total_cnt, 'code': from_code, 'last_code': rec.code if rec else False}

    def create_by_odata_json(self, json_data):
        rec = self.create({
                    'ref' : json_data['Ref_Key'],
                    'code' : json_data['Code'],
                    'name' : json_data['Description'],
                })
        return rec

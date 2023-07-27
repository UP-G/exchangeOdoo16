from odoo import api, fields, models, _
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCBusinessType(models.Model):
    _name = 'tmtr.exchange.1c.business_region'
    _description = '1C Business Region'

    ref_key = fields.Char(string='Ref', index=True) # Ref_Key
    name = fields.Char(string='Business Region Name') # Description
    main_manager_key = fields.Char(string='Main manager key') # ОсновнойМенеджер_Key
    team_id = fields.Many2one('crm.team')

    def upload_new(self, top = 100, skip = 0):
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        nothing2import = 0
        total_cnt = 0
        rec = None
        while datetime.now() < finish_before and nothing2import < 3:
            json_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_catalog/", {
                    "catalog_name": "Catalog_БизнесРегионы",
                    "filter": f"DeletionMark eq false&$orderby=ОсновнойМенеджер_Key&$top={top}&$skip={skip}"
                })['value']
            cnt = 0
            for item in json_data:
                if item['DeletionMark'] != True:
                    rec = self.create_by_odata_json(item)
                    cnt += 1
            skip += top
            total_cnt += cnt
            nothing2import += 1 if cnt == 0 else 0
        return {'cnt': total_cnt, 'last_manager_key': rec.main_manager_key if rec else False}

    def update_fields(self, model_fields=['name', 'main_manager_key'], manager_keys=None, skip=0, top=100, do_limit={}):
        try:
            if do_limit:
                finish_before = datetime.now() + timedelta(seconds=do_limit.get('seconds',0), minutes=do_limit.get('minutes',0)) # ограничить время работы скрипта
            else:
                finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта

            if manager_keys == None:
                if len(self) > 0:
                    manager_keys = set(self.mapped('main_manager_key'))
                else:
                    manager_keys = set(self.search([]).mapped('main_manager_key'))
            cnt = 0
            last_updated = ''
            skip_default = skip
            for manager_key in manager_keys:
                empty_result = 0
                skip = skip_default
                while datetime.now() < finish_before and empty_result < 2:
                    data = self.env['odata.1c.route'].get_by_route(
                        "1c_ut/get_catalog/", {
                            "catalog_name": "Catalog_БизнесРегионы",
                            "filter": f"ОсновнойМенеджер_Key eq guid'{manager_key}'&$orderby=Ref_Key&$top={top}&$skip={skip}"
                        })['value']
                    if data:
                        for item in data:
                            if self.update_by_odata_json(item, model_fields=model_fields):
                                cnt += 1
                            else:
                                rec = self.create_by_odata_json(item)
                                cnt += 1 if len(rec) > 0 else 0
                            last_updated = item['ОсновнойМенеджер_Key']
                    else:
                        empty_result += 1
                    if skip+1 >= top * 1:
                        if last_updated:
                            code = last_updated
                            skip = 1
                        else:
                            empty_result += 1
                    else:
                        skip += top
                    #_logger.info(f'empty_result={empty_result}, cnt={cnt}')
                    skip += top
            return {'count': cnt, 'last_updated': last_updated}
        except Exception as e:
            _logger.info(e)
            return


    def create_by_odata_json(self, json_data):
        rec = self.search([("ref_key", "=", json_data.get('Ref_Key'))])
        if not rec:
            return self.create(self.odata_array_to_model(json_data, ['all']))
        else:
            return rec

    def update_by_odata_json(self, json_data, model_fields=[]):
        partner = self.search([("ref_key", "=", json_data['Ref_Key'])])
        if model_fields and partner:
            partner.update(self.odata_array_to_model(json_data,model_fields))
        return partner

    def odata_array_to_model(self, json_data, model_fields=[]):
        odata2model = {
            'ref_key': 'Ref_Key',
            'name': 'Description',
            'main_manager_key' : 'ОсновнойМенеджер_Key',
        }
        data = {}
        if 'all' in model_fields:
            model_fields = list(odata2model.keys())
        for field in model_fields:
            odata_src = odata2model.get(field, '')
            if odata_src:
                data.update({field: json_data.get(odata_src,'') if isinstance(odata_src, str) else odata_src[1](json_data.get(odata_src[0],''))})
        return data

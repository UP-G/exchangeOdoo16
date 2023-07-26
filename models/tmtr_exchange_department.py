from odoo import api, fields, models, _
import json
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCCompanyStructure(models.Model):
    _name = 'tmtr.exchange.1c.department'
    _description = '1C Company Structure'

    ref_key = fields.Char(string='Ref', index=True) # Ref_Key
    name = fields.Char(string='Dividion Name') # Description
    code = fields.Char(string='Dividion Code') # Code
    head_manager_key = fields.Char(string='Head manager key') # ТекущийРуководитель_Key
    parent_ref_key = fields.Char(string='Parent department key') # Parent_Key
    code_income = fields.Char(string='Income Code') # ТМ_КодДоходов
    sales_channel_code = fields.Char(string='Sales channel Code') # ТМ_КаналСбыта
    main_stock_key = fields.Char(string='Main stock key') # ТМ_Склад_Key

    team_id = fields.Many2one('crm.team') # Команда продаж
    department_id = fields.Many2one('hr.department') # Подразделение компании

    def upload_new(self, code=None, top = 100, skip = 0):
        finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой
        nothing2import = 0
        total_cnt = 0
        rec = None
        code = code if code else '00-00000000'
        while datetime.now() < finish_before and nothing2import < 3:
            json_data = self.env['odata.1c.route'].get_by_route(
                "1c_ut/get_catalog/", {
                    "catalog_name": "Catalog_СтруктураПредприятия",
                    "filter": f"DeletionMark eq false and Code ge '{code}'&$orderby=Code&$top={top}&$skip={skip}"
                })['value']
            cnt = 0
            for item in json_data:
                if item['DeletionMark'] != True:
                    rec = self.create_by_odata_json(item)
                    cnt += 1
            skip += top
            total_cnt += cnt
            nothing2import += 1 if cnt == 0 else 0
        return {'cnt': total_cnt, 'last_code': rec.code if rec else False}

    def update_fields(self, model_fields=['name', 'head_manager_key'], codes=None, skip=0, top=100, do_limit={}):
        try:
            if do_limit:
                finish_before = datetime.now() + timedelta(seconds=do_limit.get('seconds',0), minutes=do_limit.get('minutes',0)) # ограничить время работы скрипта
            else:
                finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта

            if codes == None:
                if len(self) > 0:
                    codes = self.mapped('code')
                else:
                    codes = self.search([]).mapped('code')
            elif type(codes) == string:
                codes = codes.split(',')
            cnt = 0
            last_updated = ''
            code = codes[0] if codes else ''
            nothing2import = 0
            while datetime.now() < finish_before and nothing2import < 3:
                data = self.env['odata.1c.route'].get_by_route(
                        "1c_ut/get_catalog/", {
                            "catalog_name": "Catalog_СтруктураПредприятия",
                            "filter": f"Code ge '{code}'&$orderby=Code&$top={top}&$skip={skip}"
                        })['value']
                for item in data:
                        if item.get('DeletionMark') != True and item.get('DeletionMark') in codes:
                            if self.update_by_odata_json(item, model_fields=model_fields):
                                cnt += 1
                            else:
                                rec = self.create_by_odata_json(item)
                                cnt += 1 if len(rec) > 0 else 0
                            last_updated = item['Code']
                if not data:
                        nothing2import += 1
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
            'code': 'Code',
            'head_manager_key': 'ТекущийРуководитель_Key',
            'parent_ref_key': 'Parent_Key',
            'code_income': 'ТМ_КодДоходов',
            'sales_channel_code': 'ТМ_КаналСбыта',
            'main_stock_key': 'ТМ_Склад_Key',
        }
        data = {}
        if 'all' in model_fields:
            model_fields = list(odata2model.keys())
        for field in model_fields:
            odata_src = odata2model.get(field, '')
            if odata_src:
                data.update({field: json_data.get(odata_src,'') if isinstance(odata_src, str) else odata_src[1](json_data.get(odata_src[0],''))})
        return data

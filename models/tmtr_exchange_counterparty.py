from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta
from odoo import Command
import time

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCCounterparty(models.Model):
    _name = 'tmtr.exchange.1c.counterparty'
    _description = '1C Counterparty'

    partner_id = fields.Many2one('res.partner', string='Partner')
    ref_key = fields.Char(string='ref_key') # Ref_Key
    code = fields.Char(string="TM_Code") # ТМ_Код
    description = fields.Char(string="Description") # Description
    full_name = fields.Char(string="Full name counterparty") # НаименованиеПолное
    partner_key = fields.Char(string="Partner Key") # Партнер_Key
    legal_type = fields.Char(string="Legal Type") # ФизЛицо, ИндивидуальныйПредприниматель, ЮрЛицо
    contact = fields.Text(string='Contact information') # КонтактнаяИнформация.Представление
    credit_limit = fields.Float(string="Credit limit") # ДИТ_ЛимитКредита
    credit_days = fields.Integer(string="Credit days") # ДИТ_ЛимитСрока
    inn = fields.Char(string="Tax ID") # ИНН
    okpo = fields.Char(string="OKPO") # КодПоОКПО
    kpp = fields.Char(string="KPP") # КПП
    ogrn = fields.Char(string="OGRN") # ДИТ_ОГРН
    status = fields.Char(string="Status") # СтатусКонтрагента = НеДействующий
    # ДИТ_Маршруты

    def upload_new(self, code=None, skip=0, top=500, do_limit={}):
        try:
            if do_limit:
                finish_before = datetime.now() + timedelta(seconds=do_limit.get('seconds',0), minutes=do_limit.get('minutes',0)) # ограничить время работы скрипта
            else:
                finish_before = datetime.now() + timedelta(minutes=1) # ограничить время работы скрипта одной минутой

            if not code: #Если не указан с какого code начинаем выкачиваем
                recs = self.search([('code', 'like', '000')],
                          order="code desc",limit=1) #Берем максимальный code
                if not recs:
                    code = '0'
                else:
                    code = recs[0].code
            cnt = 0
            last_created = ''
            empty_result = 0
            while datetime.now() < finish_before and empty_result < 3:
                data = self.env['odata.1c.route'].get_by_route(
                    "1c_ut/get_counterparty/", 
                    {
                        "tm_code": code, 
                        "top": top,
                        "skip": skip
                        })["value"]
                if data:
                    for item in data:
                        cnt += self.create_by_odata_json(item)
                        last_created = item['ТМ_Код']
                else:
                    empty_result += 1
                if skip+1 >= top * 1:
                    if last_created:
                        code = last_created
                        skip = 1
                    else:
                        empty_result += 1
                else:
                    skip += top
            return {'count': cnt, 'last_code': code, 'last_created': last_created}
        except Exception as e:
            _logger.info(e)
            return

    def update_fields(self, model_fields=[
            'description', 'full_name', 'partner_key', 'credit_limit', 'credit_days', 'status'
            ], code=None, skip=0, top=500, do_limit={}, limit_minutes=1):
        try:
            if do_limit:
                finish_before = datetime.now() + timedelta(seconds=do_limit.get('seconds',0), minutes=do_limit.get('minutes',0)) # ограничить время работы скрипта
            else:
                finish_before = datetime.now() + timedelta(minutes=limit_minutes) # ограничить время работы скрипта
            if not code: #Если не указан с какого code начинаем выкачиваем
                if len(self) == 0:
                    recs = self.search([('code', 'like', '000')],
                          order="write_date asc",limit=1) #Берем последний обновленный code
                    if not recs:
                        code = '0'
                    else:
                        code = recs.code
                else:
                    # TODO: заменить на гарантированную обработку всего списка, но экономя нагрузку на 1С УТ
                    codes = self.mapped('code')
                    codes.sort()
                    code = codes[0]
            cnt = 0
            last_updated = ''
            empty_result = 0
            while datetime.now() < finish_before and empty_result < 3:
                data = self.env['odata.1c.route'].get_by_route(
                    "1c_ut/get_counterparty/", 
                    {
                        "tm_code": code,
                        "skip": skip,
                        "top": top
                    })["value"]
                if data:
                    for item in data:
                        cnt += self.update_by_odata_json(item, model_fields=model_fields)
                        last_updated = item['ТМ_Код']
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
            return {'count': cnt, 'last_code': code, 'last_updated': last_updated}
        except Exception as e:
            _logger.info(e)
            return


    def create_by_odata_json(self, json_data):
        partner = self.search([("ref_key", "=", json_data['Ref_Key'])])
        if not partner:
            return 1 if self.create(self.odata_array_to_model(json_data, ['all'])) else 0
        else:
            return 0


    def odata_array_to_model(self, json_data, model_fields=[]):
        odata2model = {
            'ref_key': 'Ref_Key',
            'code': 'ТМ_Код',
            'description': 'Description',
            'full_name': 'НаименованиеПолное',
            'partner_key': 'Партнер_Key',
            'legal_type': 'ЮрФизЛицо',
            'contact': ('КонтактнаяИнформация', lambda j: '\n'.join([f"{contact['Тип']}: {contact['Представление']}" for contact in j])),
            'credit_limit': 'ДИТ_ЛимитКредита',
            'credit_days': 'ДИТ_ЛимитСрока',
            'inn': 'ИНН',
            'okpo': 'КодПоОКПО',
            'kpp': 'КПП',
            'ogrn': 'ДИТ_ОГРН',
            'status': 'СтатусКонтрагента',
        }
        data = {}
        if 'all' in model_fields:
            model_fields = list(odata2model.keys())
        for field in model_fields:
            odata_src = odata2model.get(field, '')
            if odata_src:
                data.update({field: json_data.get(odata_src,'') if isinstance(odata_src, str) else odata_src[1](json_data.get(odata_src[0],''))})
        return data


    def update_by_odata_json(self, json_data, model_fields=[]):
        partner = self.search([("ref_key", "=", json_data['Ref_Key'])])
        if model_fields and partner:
            partner.update(self.odata_array_to_model(json_data,model_fields))
            return 1
        else:
            return 0


    def add_res_partner(self, limit=100):
        # obj = {}
        start_time = time.time()
        while time.time() - start_time < 60:
            counterparty_tag_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.tag_1c_counterparty'))
            if not counterparty_tag_id:
                continue
            counterparty = self.search([("partner_id", "=", None)], limit=limit)
            for data_counterparty in counterparty:
                name = data_counterparty['full_name'] if data_counterparty['full_name'] else data_counterparty['description']
                if not name:
                    continue
                s = data_counterparty['contact']
                lines = s.split('\n')
                phone = ''
                addres = ''
                for line in lines:
                    type_contact=line.split(":")[0].strip()
                    if type_contact == 'Телефон':
                        phone = line.split(":")[1].strip()
                    if type_contact == 'Адрес':
                        addres = line.split(":")[1].strip()
                new_counterparty = self.env['res.partner'].create({
                    'name': name,
                    'is_company': True,
                    'comment': '{} \n {}'.format(data_counterparty['description'],data_counterparty['contact']),
                    'street': addres,
                    'phone': phone,
                    'category_id': [(6, 0, [counterparty_tag_id])],
                })
                data_counterparty.write({
                    'partner_id': new_counterparty.id
                })

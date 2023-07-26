from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCTransportCompany(models.Model):
    _name = 'tmtr.exchange.1c.transport.company'
    _description = '1C transport company'

    ref_key = fields.Char(string='ref_key')
    full_name = fields.Char(string="Full name company")
    code = fields.Char(string="code")
    tc_type = fields.Char(string="transport company type")
    carrier_id = fields.Many2one('tms.carrier', string='carrier id')

    def upload_new_companys(self, top=100, skip =0):
            finish_before = datetime.now() + timedelta(minutes=1)
            cnt =0
            max_code_entry = self.search([], order="code desc", limit=1)
            max_code = '000000001' if not max_code_entry else max_code_entry.code
            while datetime.now() < finish_before:
                try:
                    json_data = self.env['odata.1c.route'].get_by_route(
                        "1c_ut/get_transport_company/", 
                        {
                            "code": max_code,
                            "top": top,
                            "skip": skip,
                            })["value"]

                    if not json_data:
                        _logger.info("can not find companys from 1c")
                        return
                    for data in json_data:
                        new_company = self.create_new_company(data)
                        cnt+=1
                    skip+=top
                except Exception as e:
                    _logger.info(e)
            return cnt

    def create_new_company(self, json_date):
        self.create({
            'ref_key' : json_date['Ref_Key'],
            'full_name' : json_date['Description'],
            'code' : json_date['Code'],
            'tc_type': json_date['ТипТК'],
            })
        return
    
    def create_new_tms_carriers(self):
            data = self.search([])
            if not data:
                return

            code_ids = [r.code for r in data]
            company_exists = dict((r.code, r.code) for r in self.env['tms.carrier'].search([("code", "in", code_ids)]))
            for company in data:
                if company.code in company_exists:
                    continue
                new_company = self.create_tms_company(company)
                company.carrier_id = new_company.id

    def create_tms_company(self, company):
        try:
            new_comapny = self.env['tms.carrier'].create({
                'name' : company.full_name,
                'code': company.code,
                'tc_type': company.tc_type,
            })
            return new_comapny
        except Exception as e:
            _logger.info(e)
            return False
             

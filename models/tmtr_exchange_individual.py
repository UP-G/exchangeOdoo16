from odoo import api, fields, models, _
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)
class TmtrExchangeOneCIndividual(models.Model):
    _name = 'tmtr.exchange.1c.individual'
    _description = '1C individual'

    ref_key = fields.Char(string='ref_key')
    full_name = fields.Char(string="Full name individual")
    inn = fields.Char(string="INN")
    tm_code = fields.Char(string="TM code")
    tm_department_Key = fields.Char(string='ТМ Department Key')
    snils = fields.Char(string='InsuranceNumberPFR')
    user_id = fields.Many2one('res.users')
    carrier_driver_id = fields.Many2one('tms.carrier.driver', string="carrier driver id")
    # transport_company_ids = fields.Many2many('tmtr.exchange.1c.transport.company', 
    #                                          relation='tmtr_exchange_1c_transport_company_tmtr_exch_1c_individual_rel')

    def set_transport_company(self, ref_key):
        
        return

    def get_individual(self, ref_key):
        individual = self.upload_new_individual(ref_key)
        if individual:
            if not individual.carrier_driver_id:
                new_driver = self.create_driver(individual)
                individual.carrier_driver_id = new_driver.id
                return new_driver
            return individual.carrier_driver_id
        else:
            return False

    def upload_new_individual(self, ref_key):
            try:
                if not ref_key:
                    _logger.info("can not find ref key")
                    return False
                individual = self.search([('ref_key', "=",ref_key)])
                if individual:
                    _logger.info("the individual with this ref key is exist")
                    return individual #individual.carrier_driver_id if individual.carrier_driver_id else False
                data = self.env['odata.1c.route'].get_by_route(
                    "1c_ut/get_individual/", 
                    {
                        "ref_key": ref_key,
                        })

                if not data:
                    _logger.info("can not find individual from 1c")
                    return

                new_individual = self.create_new_individual(data)
                return new_individual
            except Exception as e:
                _logger.info(e)

    def create_new_individual(self, json_date):
        self.create({
            'ref_key' : json_date['Ref_Key'],
            'full_name' : json_date['Description'],
            'tm_code' : json_date['ТМ_Код'],
            'inn' : json_date['ИНН'],
            'tm_department_Key' : json_date['ТМ_Подразделение_Key'],#по данному полю можно определить где работает сотрудник(слишком сложно, оставим до след. версии)
            'snils': json_date['СтраховойНомерПФР']
            })
        return
    
    def create_new_tms_drivers(self):#сделать выгрузку из tmtr.exchange в водителей, когда произойдет слияние веток в гите 
        try:
            data = self.search([('carrier_driver_id', '=', False)])
            if not data:
                return

            # tm_code_ids = [r.tm_code for r in data]
            # individual_exists = dict((r.tm_code, r.tm_code) for r in self.env['tms.carrier.driver'].search([("tm_code", "in", tm_code_ids)]))
            for individual in data:
                # if individual.tm_code in individual_exists:
                #     continue
                new_driver = self.create_driver(individual)
                individual.carrier_driver_id = new_driver.id

        except Exception as e:
            _logger.info(e)
        
    def create_driver(self, individual):
        new_driver = self.env['tms.carrier.driver'].create({
            'name' : individual.full_name,
            'ref_key': individual.ref_key,
        })
        return new_driver

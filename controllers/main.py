import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class TmtrComtrollers(http.Controller):
    
    @http.route('/tmtr_odoo/set_ClientInfo/', type='http', auth='public', methods=['POST'], csrf=False) 
    def set_info(self, **args):
        jsonValues = request.get_json_data()
        for jsonValue in jsonValues:
            indicator = http.request.env['tmtr.exchange.1c.indicators'].search([('origin_id', '=', jsonValue['origin_id'])], limit=1)
            try:
                if not indicator:
                    _logger.info(jsonValue)
                    new_indicator = http.request.env['tmtr.exchange.1c.indicators'].create({
                        'plan': max([float(jsonValue['turnover_prevmonth']),(float(jsonValue['turnover_3month']/3))]),#(макс(среднее за предыдущий месяц; среднее за 3 месяца) * кол-во дней месяце)
                        'prediction': jsonValue['turnover_30days'],#Прогноз выручки на текущий месяц (среднее в день за 30 дней * количество дней в текущем месяце)
                        'turnover_this_mounth': jsonValue['turnover_thismonth'],
                        'turnover_last_3month': jsonValue['turnover_3month'],
                        'turnover_last_30days': jsonValue['turnover_30days'],
                        'turnover_previous_mounth': jsonValue['turnover_prevmonth'],
                        'overdue_debt': jsonValue['debt'],
                        'task_count': jsonValue['task_count'],
                        'origin_id': jsonValue['origin_id'],
                        'identifier_ib': jsonValue['manager_id'],
                        'debt': jsonValue['balance'],
                    })
                else:
                    indicator.write({
                       'plan': max([float(jsonValue['turnover_prevmonth']),(float(jsonValue['turnover_3month']/3))]),#(макс(среднее за предыдущий месяц; среднее за 3 месяца) * кол-во дней месяце)
                        'prediction': jsonValue['turnover_30days'],#Прогноз выручки на текущий месяц (среднее в день за 30 дней * количество дней в текущем месяце)
                        'turnover_this_mounth': jsonValue['turnover_thismonth'],
                        'turnover_last_3month': jsonValue['turnover_3month'],
                        'turnover_last_30days': jsonValue['turnover_30days'],
                        'turnover_previous_mounth': jsonValue['turnover_prevmonth'],
                        'overdue_debt': jsonValue['debt'],
                        'task_count': jsonValue['task_count'],
                        'origin_id': jsonValue['origin_id'],
                        'identifier_ib': jsonValue['manager_id'], 
                        'debt': jsonValue['balance'],
                    })
            except Exception as e:
                _logger.info(e)
                continue

    @http.route('/tmtr_odoo/get_BestTask', type='http', auth='public', methods=['POST'], csrf=False)
    def best(self, **args):
        return http.request.env["tmtr.exchange.1c.indicators"].get_best_one(request.get_json_data())

    @http.route('/tmtr_odoo/report/sale_efficiency/', type='http', auth="user", methods=['POST'], csrf=False) 
    def sale_efficiency(self, manager_ids, **args):
        return http.request.env["efficiency.saler.report"]._render_html_by_manager(manager_ids if type(manager_ids) is list else [])

    @http.route('/tmtr_odoo/report/sale_efficiency_no_auth/', type='json', auth="public", methods=['POST','GET'], csrf=False)
    def sale_efficiency_no_auth(self, manager_ids, **args):
        #return '\n\nresult: OK\n{}\n{}\n'.format(json.dumps(args),http.request.params)
        #manager_ids = request.get_json_data()['manager_ids']
        #return '\n\n<p>{}</p>\n'.format(','.join(manager_ids))
        return http.request.env["efficiency.saler.report"]._render_html_by_manager(manager_ids if type(manager_ids) is list else [])
        #return http.request.env["efficiency.saler.report"]._render_html_all()    



    


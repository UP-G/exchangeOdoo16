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
            try:
                http.request.env['tmtr.exchange.1c.indicators'].update_from_json(jsonValue)
            except Exception as e:
                _logger.info(e)
                continue

    @http.route('/tmtr_odoo/get_best_task/', type='json', auth="public", methods=['POST','GET'], csrf=False)
    def grt_best_task(self, identifier_ib, exclude_client_ids, **args):
        return http.request.env["efficiency.saler.report"].get_best_one(identifier_ib, exclude_client_ids)

    @http.route('/tmtr_odoo/report/sale_efficiency/', type='http', auth="user", methods=['POST','GET'], csrf=False) 
    def sale_efficiency(self, manager_ids, view='', **args):
        return http.request.env["efficiency.saler.report"]._render_html_by_manager(manager_ids if type(manager_ids) is list else [], data={'view': view})

    @http.route('/tmtr_odoo/report/sale_efficiency_no_auth/', type='json', auth="public", methods=['POST','GET'], csrf=False)
    def sale_efficiency_no_auth(self, manager_ids, view='', **args):
        return http.request.env["efficiency.saler.report"]._render_html_by_manager(manager_ids if type(manager_ids) is list else [], data={'view': view})

    @http.route('/tmtr_odoo/report/sale_efficiency_test/<string:manager_ids>', type='http', auth="public", methods=['POST','GET'], csrf=False)
    def sale_efficiency_no_auth(self, manager_ids, view='', **args):
        return http.request.env["efficiency.saler.report"]._render_html_by_manager(manager_ids if type(manager_ids) is list else ([manager_ids] if manager_ids else ['3c849afc-78d0-4b66-bc9f-81dcc0bbf035']), data={'view': view})


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
                http.request.env['tmtr.exchange.1c.indicators'].sudo().update_from_json(jsonValue)
            except Exception as e:
                _logger.info(e)
                continue

    @http.route('/tmtr_odoo/get_best_task/', type='json', auth="public", methods=['POST','GET'], csrf=False)
    def get_best_task(self, identifier_ib, exclude_client_ids, with_template = 'default', **args):
        result = http.request.env["efficiency.saler.report"].sudo().get_best_one(identifier_ib, exclude_client_ids)
        if with_template and result and result.get('origin_id'):
            template = http.request.env['tmtr.exchange.1c.indicators'].sudo()._render_html_best_one(result.get('origin_id'), data={'view': with_template})
            if template:
                info = http.request.env['tmtr.exchange.1c.indicators'].sudo().search([('origin_id','=', result.get('origin_id'))])
                metrics = info.get_json_metrics()
                if not metrics:
                    metrics = {}
                result.update({
                    'html': str(template),
                    'manager_xml_id': info.efficiency_id.manager_1c_id if info and info.efficiency_id else '',
                    'manager_bitrix_id': metrics.get('manager_bitrix_id', ''),
                    'client_name': info.efficiency_id.client_name if info and info.efficiency_id else '',
                    'client_id': result.get('origin_id'),
                    'client_bitrix_id': metrics.get('client_bitrix_id', ''),
                })
            return result
        else:
            return result

    @http.route([
        '/tmtr_odoo/report/sale_efficiency/',
        '/tmtr_odoo/report/sale_efficiency',
        '/tmtr_odoo/report/sale_efficiency_no_auth/<string:view>',
        '/tmtr_odoo/report/sale_efficiency_no_auth/<string:view>/'
        ], type='json', auth="user", methods=['POST','GET'], csrf=False) 
    def sale_efficiency(self, manager_ids, view='grouped_by_manager', **args):
        return http.request.env["efficiency.saler.report"].sudo()._render_html_by_manager(manager_ids if type(manager_ids) is list else [], data={'view': view})

    @http.route([
        '/tmtr_odoo/report/sale_efficiency_no_auth',
        '/tmtr_odoo/report/sale_efficiency_no_auth/',
        '/tmtr_odoo/report/sale_efficiency_no_auth/<string:view>',
        '/tmtr_odoo/report/sale_efficiency_no_auth/<string:view>/'
        ], type='json', auth="public", methods=['POST','GET'], csrf=False)
    def sale_efficiency_no_auth(self, manager_ids, view='grouped_by_manager', **args):
        return http.request.env["efficiency.saler.report"].sudo()._render_html_by_manager(manager_ids if type(manager_ids) is list else [], data={'view': view})

    @http.route([
        '/tmtr_odoo/report/sale_efficiency_test/<string:manager_ids>/',
        '/tmtr_odoo/report/sale_efficiency_test/<string:manager_ids>'
        ], type='http', auth="public", methods=['POST','GET'], csrf=False)
    def sale_efficiency_no_auth_test(self, manager_ids, view='', **args):
        return http.request.env["efficiency.saler.report"].sudo()._render_html_by_manager(manager_ids.split(',') if manager_ids else ['3c849afc-78d0-4b66-bc9f-81dcc0bbf035'], data={'view': view})

    @http.route([
        '/tmtr_odoo/report/best_one_test/<string:client_origin_id>/',
        '/tmtr_odoo/report/best_one_test/<string:client_origin_id>'
        ], type='http', auth="public", methods=['POST','GET'], csrf=False)
    def best_one_test(self, client_origin_id, view='', **args):
        return http.request.env['tmtr.exchange.1c.indicators'].sudo()._render_html_best_one(client_origin_id if client_origin_id else '00-00012053', data={'view': view})

    @http.route([
        '/tmtr_odoo/report/debts/',
        '/tmtr_odoo/report/debts'
        ], type='json', auth='public', methods=['POST'], csrf=False) 
    def report_debts(self, client_origin_id, **args):
        return http.request.env['tmtr.exchange.1c.partner'].sudo()._render_debts(client_origin_id)

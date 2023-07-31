from odoo import models, fields, api
import datetime


class Base_bi_Sales_plans(models.Model):
    _inherit = 'base_bi.sales_plan'

    avg_sales = fields.Monetary(string="Average sales last three months", currency_field='currency_id', compute='_compute_avg_sales')

    @api.depends("date")
    def _compute_avg_sales(self):
        for rec in self:
            actual_period = min(self.date if self.date else datetime.date.today(), datetime.date.today()) - datetime.timedelta(days=31)
            rec.avg_sales = sum(self.env['tmtr.exchange.1c.indicators'].search([('write_date','>=',actual_period)]).mapped('plan'))

    def fill_by_sales(self):
        self.row_ids.unlink()
        actual_period = min(self.date if self.date else datetime.date.today(), datetime.date.today()) - datetime.timedelta(days=31)
        team_avg_sales = self.env['tmtr.exchange.1c.indicators'].read_group([('write_date','>=',actual_period)],['team_id','avg_plan:sum(plan)'],['team_id'],orderby='avg_plan desc')
        total_avg_sales = sum([ r.get('avg_plan') for r in team_avg_sales ])
        default_team_id = int(self.env['ir.config_parameter'].sudo().get_param('tmtr_exchange.default_team_id'))
        for team_avg in team_avg_sales:
            self.row_ids.create({
                'plan_id': self.id,
                'team_id': team_avg.get('team_id')[0] if team_avg.get('team_id')[0] else default_team_id,
                'target': self.target * team_avg.get('avg_plan') / total_avg_sales if total_avg_sales > 0 else self.target,
            })

class Base_bi_Sales_plan_rows(models.Model):
    _inherit = 'base_bi.sales_plan.row'

    avg_sales = fields.Float(string="Avg Sales", copy=False, compute='_compute_avg_sales')
    client_count = fields.Integer(string="Client count", copy=False, compute='_compute_avg_sales')
    client_ids = fields.Many2one('tmtr.exchange.1c.indicators', string="Clients", copy=False, compute='_compute_avg_sales')

    @api.depends("plan_id.date")
    def _compute_avg_sales(self):
        if len(self) > 0:
            for rec in self:
                actual_period = min(rec.plan_id.date if rec.plan_id and rec.plan_id.date else datetime.date.today(), datetime.date.today()) - datetime.timedelta(days=31)
                clients = self.env['tmtr.exchange.1c.indicators'].search([('write_date','>=',actual_period),('team_id.id','=',rec.team_id.id)])
                plans = clients.mapped('plan')
                rec.avg_sales = sum(plans)
                rec.client_count = len(plans)
                rec.client_ids = clients.ids

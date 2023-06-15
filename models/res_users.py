from odoo import fields, models, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    ref_key = fields.Char(compute="_compute_get_ref_key", store=True)
    #ib_user_id = fields.Char(compute="_compute_get_ib_user_id", store=True)

    def _compute_get_ref_key(self):
        onec_user = self.env['tmtr.exchange.1c.user']
        for user in self:
            user.ref_key = onec_user.search([("user_id", "=", user.id)])['ref_key'] or None
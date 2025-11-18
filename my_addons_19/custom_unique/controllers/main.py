# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.addons.mail.controllers.mail import MailController
from odoo import http
from odoo.http import request
import json   # <-- Add this line
from odoo import http, fields



_logger = logging.getLogger(__name__)


class PartnerConfirmationController(http.Controller):

    @http.route('/partner/confirmation/<string:token>', type='http', auth='public', website=True)
    def partner_confirmation_portal(self, token, **kw):
        partner = request.env['res.partner'].sudo().search([('token', '=', token)], limit=1)
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n==================", partner)
        if not partner:
            return request.not_found()

        return request.render('custom_unique.partner_confirmation_template', {
            'partner': partner
        })

    @http.route('/partner/approve/<string:token>', type='http', auth='public', website=True, methods=['POST'])
    def approve_partner(self, token, **kw):
        partner = request.env['res.partner'].sudo().search([('token', '=', token)], limit=1)
        user = request.env.user
        if user.is_boss:
            if partner:
                partner.sudo().write({
                    'approved_by_boss': True,
                    'approval_date': fields.Date.today(),
                    'confirmation_state': 'approved',
                })
                if partner.approved_by_boss:
                    template = request.env.ref('custom_unique.partner_approved_mail_template', raise_if_not_found=False)
                    print("\n\n\n\n\n\n\n\n\n\n\n\n==Template is", template)
                    if not template:
                        return

                    boss = request.env['res.partner'].sudo().search([('is_boss', '=', True), ('email', '!=', False)], limit=1)
                    print(">>>>>>>>>>", boss)

                    if not boss:
                        return
                    email_values = {
                        'email_to': partner.user_id.email,
                        'email_from': boss.email,
                    }
                    ctx = {
                        'boss_name': boss.name or 'Boss',
                    }
                    template.sudo().with_context(ctx).send_mail(partner.id, email_values=email_values, force_send=True)

                    if partner.user_id:
                        message = f"Hello {partner.user_id.name}, your partner '{partner.name}' is approved by the Boss!"
                        request.env['bus.bus']._sendone(
                            partner.user_id.partner_id,
                            'simple_notification',
                            {
                                'type': 'info',
                                'message': message,
                                'sticky': True,
                                'className': 'bg-info',
                            }
                        )

                print(f"\n Partner {token} has been approved successfully.\n")
                return json.dumps(True)
            print(f"\n❌ Partner with token {token} not found.\n")
            return json.dumps(False)

    @http.route('/partner/block/<string:token>', type='http', auth='public', website=True, methods=['POST'])
    def block_partner(self, token, **kw):
        partner = request.env['res.partner'].sudo().search([('token', '=', token)], limit=1)
        user = request.env.user
        if user.is_boss:
            if partner:
                partner.sudo().write({
                    'blocked_by_boss': True,
                    'block_date': fields.Date.today(),
                    'confirmation_state': 'rejected',
                })
                if partner.user_id:
                    message = (
                        f"Hello {partner.user_id.name}, your partner "
                        f"'{partner.name}' is rejected by the Boss."
                    )
                    self.env['bus.bus']._sendone(
                        partner.user_id.partner_id,
                        'simple_notification',
                        {
                            'type': 'danger',
                            'message': message,
                            'sticky': True,
                            'className': 'bg-danger',
                        }
                    )
                print(f"\n Partner {token} has been blocked.\n")
                return json.dumps(True)
            print(f"\n❌ Failed to block Partner {token}. Missing reason or not found.\n")
            return json.dumps(False)

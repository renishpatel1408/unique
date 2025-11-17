# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import uuid
import logging

_logger = logging.getLogger(__name__)


class EnquiryLead(models.Model):
    _name = "enquiry.lead"
    _description = "Enquiry/Lead"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    enquiry_ref = fields.Char(string="Enquiry Reference", readonly=True, copy=False, index=True, default='New')
    name = fields.Char(string="")
    client_department_id = fields.Many2one("client.department", string="Client Department", required=True)
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='client_id.sector')
    calcification = fields.Selection([
        ('client', 'Client'),
        ('shipyard', 'Shipyard'),
        ('government', 'Government'),
        ('ship_management', 'Ship Management'),
        ('vessel_owner', 'Vessel Owner'),
        ('process_plant', 'Process Plant'),
        ('construction', 'Construction'),
        ('power_plant', 'Power Plant'),
        ('sme', 'SME'),
    ], string='Calcification', required=True)
    state = fields.Selection(
        [
            ('active', 'Active'),
            ('approved', 'Approved'),
            ('reject', 'Rejected')
        ],
        string='Status',
        default='active', group_expand="read_group_stage_ids",
        tracking=True
    )
    website = fields.Char(string="Website", related='client_id.website')
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False), ('approved_by_boss', '=', True)]", required=True)
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]", required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, related='client_id.company_id')
    # Related address fields (auto-filled from client)
    street = fields.Char(string="Street", related='client_id.street', store=True)
    street2 = fields.Char(string="Street2", related='client_id.street2', store=True)
    city = fields.Char(string="City", related='client_id.city', store=True)
    state_id = fields.Many2one('res.country.state', string="State", related='client_id.state_id', store=True)
    zip = fields.Char(string="ZIP", related='client_id.zip', store=True)
    country_id = fields.Many2one('res.country', string="Country", related='client_id.country_id', store=True,
                                 )
    mobile = fields.Char(string="Contact No.", related='client_id.phone', help="Enter multiple mobile numbers separated by commas or new lines.")
    email = fields.Char(string='Email', related='client_id.email', store=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        default=lambda self: self.env.user
    )
    enquiry_date = fields.Date(
        string="Enquiry Date",
        default=fields.Date.context_today,
        required=True,
        help="The date when the enquiry was created."
    )
    enq_probability = fields.Float(string='Probability (%)', default=1)
    notes = fields.Text(string='Notes')
    department_id = fields.Many2one("enquiry.department", string="Department", required=True)
    token = fields.Char(string="Access Token", copy=False, readonly=False)
    sale_enquiry_count = fields.Integer(compute='_compute_sale_enquiry_count')
    sale_enquiry_id = fields.Many2one('sale.enquiry', string='Enquiry', index=True, store=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.token:
                record.token = str(uuid.uuid4())
            if record.enquiry_ref == 'New' or not record.enquiry_ref:
                company = record.company_id
                dept = record.department_id
                current_year = datetime.now().year
                seq_code = self.env['ir.sequence'].next_by_code('enquiry.lead') or '001'

                company_code = company.code if company else 'CMP'
                dept_code = dept.code if dept else 'DEPT'

                record.enquiry_ref = (
                    f"{company_code}-LEAD-{dept_code}-{current_year}-{seq_code.split('-')[-1]}"
                )
        return records

    def write(self, vals):
        print("\n\n\n\n\n\n\n\nValue is.....", vals)
        res = super().write(vals)
        for record in self:
            if 'company_id' in vals or 'department_id' in vals:
                company_code = record.company_id.code
                dept_code = record.department_id.code
                current_year = datetime.now().year
                seq_number = record.enquiry_ref.split('-')[-1] if record.enquiry_ref else '001'
                record.enquiry_ref = f"{company_code}-LEAD-{dept_code}-{current_year}-{seq_number}"
                print("\n\n\n\n\n\n\n\nSequence is.....", record.enquiry_ref)
        return res

        self.enquiry_ref = f"{company_code}-{dept_code}-{current_year}-{seq_number}"

    @api.model
    def read_group_stage_ids(self, stages, domain):
        return [key for key, val in self._fields['state'].selection]

    # def action_open_portal_url(self):
    #     self._send_boss_email()


    @api.onchange('mobile')
    def _onchange_mobile(self):
        if self.mobile:
            import re
            text = self.mobile.strip()
            text = re.sub(r'(\d{10})\s+', r'\1,', text)
            text = re.sub(r',+', ', ', text)
            self.mobile = text

    def _compute_sale_enquiry_count(self):
        for rec in self:
            sale_enquiry = self.env['sale.enquiry'].search_count([('enquiry_id', '=', rec.id)])
            self.sale_enquiry_count = sale_enquiry

    def action_view_sale_enquiry(self):
        self.ensure_one()
        sale_enquiry = self.env['sale.enquiry'].search([('enquiry_id', '=', self.id)], limit=1)
        if sale_enquiry:
            return {
                'name': _('Sale Enquiry'),
                'type': 'ir.actions.act_window',
                'res_model': 'sale.enquiry',
                'view_mode': 'form',
                'views': [(self.env.ref('custom_unique.sale_enquiry_form_view').id, 'form')],
                'target': 'current',
                'res_id': sale_enquiry.id,
            }

    def action_approve(self):
        for record in self:
            record.state = 'approved'
            if record.state == 'approved':
                sale_enquiry = self.env['sale.enquiry'].sudo().create({
                    'enquiry_id': record.id
                })
                if sale_enquiry:
                    record.sale_enquiry_id = sale_enquiry.id

    def action_reject(self):
        for record in self:
            record.state = 'reject'

    @api.onchange('client_id')
    def _onchange_client_id(self):
        if self.client_id:
            # get the first child contact of the selected client
            child_contacts = self.env['res.partner'].search([
                ('parent_id', '=', self.client_id.id)
            ], order='id ASC', limit=1)
            if child_contacts:
                self.contact_person_id = child_contacts[0]
            else:
                self.contact_person_id = False
        else:
            self.contact_person_id = False

    def unlink(self):
        for record in self:
            if record.state == 'approved':
                raise UserError(_("You cannot delete an approved enquiry."))
        return super(EnquiryLead, self).unlink()


class ClientDepartment(models.Model):
    _name = 'client.department'
    _description = "Client Department"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)

class EnquiryDepartment(models.Model):
    _name = 'enquiry.department'
    _description = "Enquiry Department"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)

class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char(string="Company Code", help="Short code for company, used in enquiry reference generation")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_boss = fields.Boolean(string="Is Boss", help="Check if this partner is a Boss")
    approved_by_boss = fields.Boolean(string="Approved by Boss",help="Indicates whether this partner has been approved by the boss")
    blocked_by_boss = fields.Boolean(string="Blocked by Boss",help="Indicates whether this partner has been blocked by the boss")
    token = fields.Char(string="Access Token", copy=False, readonly=False)
    user_id = fields.Many2one(
        'res.users',string='Salesperson',compute='_compute_user_id',
        precompute=True,
        readonly=False,
        store=True,
        default=lambda self: self.env.user,
        help='The internal user in charge of this contact.'
    )
    approval_date = fields.Date(string="Approval Date")
    block_date = fields.Date(string="Block Date")
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', required=True)
    confirmation_state = fields.Selection([('approved', 'Approved'),('rejected', 'Rejected')], string="Status", tracking=True)
    # company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
    #                              default=lambda self: self.env.company)

    @api.onchange('country_id')
    def _onchange_phone_add_code(self):
        for record in self:
            if record.country_id:
                code = record.country_id.phone_code or ''
                if record.phone:
                    # If phone exists but does not start with the correct code
                    if not record.phone.startswith(f"+{code}"):
                        # Remove any existing '+' prefix before adding
                        clean_phone = record.phone.lstrip('+').split(' ', 1)[-1]
                        record.phone = f"+{code} {clean_phone}"
                else:
                    record.phone = f"+{code}"

    def _compute_display_name(self):
        for partner in self:
            partner.display_name = partner.name or ''
        return False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.token:
                record.token = str(uuid.uuid4())
                print("\n\n\n\n\n\n\n=====>>>>", record.token)
            if record.parent_id:
                print("Record.Parent_id is....", record.parent_id)
                record.sector = record.parent_id.sector
                record.company_id = record.parent_id.company_id.id
                record.user_id = record.parent_id.user_id.id
            if not record.parent_id and not self.env.context.get('skip_boss_email'):
                print("Send Mail is....")
                record._send_boss_email()
        return records

    def portal_url(self):
        """Redirect to the portal page using a secure token."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/partner/confirmation/{self.token}"
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': url,
        }

    def _send_boss_email(self):
        template = self.env.ref('custom_unique.partner_confirmation_mail_template', raise_if_not_found=False)
        if not template:
            return

        # Find the boss partner (who has is_boss=True and has an email)
        boss_partner = self.search([('is_boss', '=', True), ('email', '!=', False)], limit=1)
        if not boss_partner:
            _logger.warning("No boss found!")
            return

        # Get the related user account for the boss
        boss_user = self.env['res.users'].search([('partner_id', '=', boss_partner.id)], limit=1)
        if not boss_user:
            _logger.warning(f"Boss {boss_partner.name} has no user account!")
            return

        # Generate portal URL for this partner
        action = self.portal_url()
        partner_link = action.get('url') if isinstance(action, dict) else action

        # Send email to the boss
        email_values = {
            'email_to': boss_partner.email,
            'email_from': self.user_id.email or self.env.company.email,
        }
        ctx = {
            'boss_name': boss_partner.name or 'Boss',
            'partner_link': partner_link,
        }
        template.with_context(ctx).send_mail(self.id, email_values=email_values, force_send=True)

        # --- Send a Systray notification only to the boss user ---
        message = f"Hello {boss_partner.name}! Your approval is required for the new partner {self.name}."

        # Odoo 19 real-time notification
        self.env['bus.bus']._sendone(
            boss_user.partner_id,
            'simple_notification',
            {
                'type': 'info',
                'message': message,
                'sticky': True,
                'className': 'bg-info',
                'links': [{
                    'label': 'View Partner',
                    'url': partner_link,
                }]
            }
        )

        _logger.info(f"Notification sent to Boss {boss_partner.name} (User ID: {boss_user.id})")


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_boss = fields.Boolean(string="Is Boss", help="Check if this user is a Boss")

    @api.model_create_multi
    def create(self, vals_list):
        user = super(ResUsers, self.with_context(skip_boss_email=True)).create(vals_list)
        if 'is_boss' in vals_list:
            user.partner_id.is_boss = vals_list['is_boss']
        return user

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        if 'is_boss' in vals:
            for user in self:
                user.partner_id.is_boss = vals['is_boss']
        return res

    @api.onchange('country_id')
    def _onchange_phone_add_code(self):
        for record in self:
            if record.country_id:
                code = record.country_id.phone_code or ''
                if record.phone:
                    # If phone exists but does not start with the correct code
                    if not record.phone.startswith(f"+{code}"):
                        # Remove any existing '+' prefix before adding
                        clean_phone = record.phone.lstrip('+').split(' ', 1)[-1]
                        record.phone = f"+{code} {clean_phone}"
                else:
                    record.phone = f"+{code}"



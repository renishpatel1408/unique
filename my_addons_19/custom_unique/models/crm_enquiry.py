# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import uuid
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


class EnquiryLead(models.Model):
    _name = "enquiry.lead"
    _description = "Enquiry/Lead"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    enquiry_ref = fields.Char(string="Enquiry Reference", readonly=True, copy=False, index=True, default='New', tracking=True)
    name = fields.Char(string="", tracking=True)
    client_department_id = fields.Many2one("client.department", string="Client Department", required=True, tracking=True)
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='client_id.sector', tracking=True)
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
    ], string='Calcification', required=True, tracking=True)
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
    website = fields.Char(string="Website", related='client_id.website', tracking=True)
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False), ('approved_by_boss', '=', True)]", tracking=True, required=True)
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, related='client_id.company_id', tracking=True)
    # Related address fields (auto-filled from client)
    street = fields.Char(string="Street", related='client_id.street', store=True, tracking=True)
    street2 = fields.Char(string="Street2", related='client_id.street2', store=True, tracking=True)
    city = fields.Char(string="City", related='client_id.city', store=True, tracking=True)
    state_id = fields.Many2one('res.country.state', string="State", related='client_id.state_id', store=True, tracking=True)
    zip = fields.Char(string="ZIP", related='client_id.zip', store=True, tracking=True)
    country_id = fields.Many2one('res.country', string="Country", related='client_id.country_id', store=True, tracking=True
                                 )
    mobile = fields.Char(string="Contact No.", related='client_id.phone', help="Enter multiple mobile numbers separated by commas or new lines.", tracking=True)
    email = fields.Char(string='Email', related='client_id.email', store=True, tracking=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        default=lambda self: self.env.user
    , tracking=True)
    enquiry_date = fields.Date(
        string="Enquiry Date",
        default=fields.Date.context_today,
        required=True,
        help="The date when the enquiry was created."
    , tracking=True)
    enq_probability = fields.Float(string='Probability (%)', default=1, tracking=True)
    notes = fields.Text(string='Notes', tracking=True)
    department_id = fields.Many2one("enquiry.department", string="Department", required=True, tracking=True)
    token = fields.Char(string="Access Token", copy=False, readonly=False, tracking=True)
    sale_enquiry_count = fields.Integer(compute='_compute_sale_enquiry_count', tracking=True)
    sale_enquiry_id = fields.Many2one('sale.enquiry', string='Enquiry', index=True, store=True, tracking=True)

    def send_gom_notification(self):
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            "gom_channel",
            {
                "type": "gom_notification",
                "message": "Attendance Missing! Do you want to update now?",
            }
        )
        return True

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
                record.enquiry_ref = f"{company_code}-{dept_code}-{current_year}-{seq_number}"
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

    def action_send_systray_notification(self):
        self.env['mail.message'].create({
            'message_type': "notification",
            'subtype_id': self.env.ref("mail.mt_comment").id,
            'body': "Hello! This message is shown in your bell icon.",
            'subject': "New Notification",
            'model': self._name,  # optional
            'res_id': self.id,  # optional
        })

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

    name = fields.Char(string="Name", required=True, tracking=True)

class EnquiryDepartment(models.Model):
    _name = 'enquiry.department'
    _description = "Enquiry Department"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)

class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char(string="Company Code", help="Short code for company, used in enquiry reference generation", tracking=True)
    hp_number = fields.Char(string="Hp No.")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_boss = fields.Boolean(string="Is Boss", help="Check if this partner is a Boss", tracking=True)
    approved_by_boss = fields.Boolean(string="Approved by Boss",help="Indicates whether this partner has been approved by the boss", tracking=True)
    blocked_by_boss = fields.Boolean(string="Blocked by Boss",help="Indicates whether this partner has been blocked by the boss", tracking=True)
    token = fields.Char(string="Access Token", copy=False, readonly=False, tracking=True)
    user_id = fields.Many2one(
        'res.users',string='Salesperson',compute='_compute_user_id',
        precompute=True,
        readonly=False,
        store=True,
        default=lambda self: self.env.user,
        help='The internal user in charge of this contact.', tracking=True
    )
    approval_date = fields.Date(string="Approval Date", tracking=True)
    block_date = fields.Date(string="Block Date", tracking=True)
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', required=True, tracking=True)
    confirmation_state = fields.Selection([('approved', 'Approved'),('rejected', 'Rejected')], string="Status", tracking=True)
    # is_approved_required_from_boss = fields.Boolean()
    # company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
    #                              default=lambda self: self.env.company)

    def action_approve_partner(self):
        for partner in self:
            user = self.env.user

            if not user.is_boss:
                raise UserError("Only boss can approve partner.")
            partner.write({
                'approved_by_boss': True,
                'approval_date': fields.Date.today(),
                'confirmation_state': 'approved',
            })
            template = self.env.ref(
                'custom_unique.partner_approved_mail_template',
                raise_if_not_found=False
            )
            if template:
                boss = self.env['res.partner'].sudo().search([
                    ('is_boss', '=', True),
                    ('email', '!=', False)
                ], limit=1)

                if boss:
                    email_values = {
                        'email_to': partner.user_id.email if partner.user_id else False,
                        'email_from': boss.email,
                    }

                    ctx = {
                        'boss_name': boss.name or 'Boss',
                    }

                    template.sudo().with_context(ctx).send_mail(
                        partner.id,
                        email_values=email_values,
                        force_send=True
                    )

            if partner.user_id:
                message = (
                    f"Hello {partner.user_id.name}, your partner "
                    f"'{partner.name}' is approved by the Boss!"
                )

                self.env['bus.bus']._sendone(
                    partner.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'message': message,
                        'sticky': True,
                        'className': 'bg-info',
                    }
                )

        return True

    def action_reject_partner(self):
        for partner in self:
            user = self.env.user

            if not user.is_boss:
                raise UserError("Only boss can reject/block partner.")
            partner.write({
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

        return True

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
                record.is_approved_required_from_boss = True
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
        # Template
        template = self.env.ref('custom_unique.partner_confirmation_mail_template', raise_if_not_found=False)
        if not template:
            return

        boss_partner = self.search([('is_boss', '=', True), ('email', '!=', False)], limit=1)
        if not boss_partner:
            return

        boss_user = self.env['res.users'].search([('partner_id', '=', boss_partner.id)], limit=1)
        if not boss_user:
            return

        # Create Backend Form URL for this Partner
        partner_link = f"/web#id={self.id}&model=res.partner&view_type=form"

        # Send email
        email_values = {
            'email_to': boss_partner.email,
            'email_from': self.user_id.email or self.env.company.email,
        }
        ctx = {
            'boss_name': boss_partner.name or 'Boss',
            'partner_link': partner_link,
        }
        template.with_context(ctx).send_mail(self.id, email_values=email_values, force_send=True)

        # --- Real-time Notification ---
        message = f"Hello {boss_partner.name}! Approval is required for partner <a href='{partner_link}' target='_blank'>{self.name}</a>."

        self.env["bus.bus"]._sendone(
            boss_user.partner_id,
            "simple_notification",
            {
                "title": "Partner Approval",
                "message": message,  # Message now contains clickable partner name
                "sticky": True,
                "html": True,  # Allow HTML inside notification
                "buttons": [
                    {
                        "label": "Open Partner Form",
                        "url": partner_link
                    }
                ]
            }
        )


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_boss = fields.Boolean(string="Is Boss", help="Check if this user is a Boss", tracking=True)
    hp_number = fields.Char(string="Hp No.")

    # @api.onchange('role')
    # def _onchange_role(self):
    #     group_admin = self.env.ref('base.group_system')
    #     group_user = self.env.ref('base.group_user')
    #     group_gom_admin = self.env.ref('custom_unique.group_unique_administrator')
    #
    #     for user in self:
    #         if not user.role:
    #             continue
    #
    #         # Remove old role groups
    #         groups = user.group_ids - (group_admin + group_user + group_gom_admin)
    #         groups = user.group_ids - (group_admin + group_user + group_gom_admin)
    #
    #         if user.role == 'admin':  # CORRECT VALUE
    #             user.group_ids = groups + group_admin + group_gom_admin
    #
    #         elif user.role == 'user':  # CORRECT VALUE
    #             user.group_ids = groups + group_user

    @api.onchange('role')
    def _onchange_role(self):
        group_admin = self.env['res.groups'].new(origin=self.env.ref('base.group_system'))
        group_user = self.env['res.groups'].new(origin=self.env.ref('base.group_user'))
        group_gom_admin = self.env['res.groups'].new(origin=self.env.ref('custom_unique.group_unique_administrator'))
        print("\n\n\n\n\n\n======>>>>>>>", group_gom_admin)
        for user in self:
            if user.role and user.has_group('base.group_user'):
                groups = user.group_ids - (group_admin + group_user + group_gom_admin)
                print("\n\n\n\n\n\n\n<><><><<><><><><><><><><><><><><><><><><><><><><><><><><><><>", groups)
                user.group_ids = groups + (group_admin + group_gom_admin if user.role == 'group_system' else group_user)
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++", user.group_ids)



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



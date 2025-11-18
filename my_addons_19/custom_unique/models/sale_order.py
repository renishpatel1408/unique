# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_enquiry_id = fields.Many2one('sale.enquiry', string='Enquiry', index=True, store=True, tracking=True)
    enquiry_id = fields.Many2one('enquiry.lead', string='Enquiry', index=True, related="sale_enquiry_id.enquiry_id",
                                 tracking=True)
    department_id = fields.Many2one("enquiry.department", string="Department", required=True,
                                    related="enquiry_id.department_id", store=True, tracking=True)
    enquiry_date = fields.Datetime(string="Enquiry Date", help="Date when the enquiry was created.",
                                   related="enquiry_id.create_date", store=True, tracking=True)
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False)]",
                                related="enquiry_id.client_id", tracking=True)
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]",
                                        related="enquiry_id.contact_person_id", tracking=True)
    mobile = fields.Char(string="Contact No.", readonly=False,
                         help="Enter multiple mobile numbers separated by commas or new lines.",
                         related="client_id.phone", tracking=True)
    email = fields.Char(string='Email', store=True, readonly=False, related="client_id.email", tracking=True)
    ref_no = fields.Char(string="Ref No.", related="sale_enquiry_id.ref_no", tracking=True)
    client_department_id = fields.Many2one("client.department", string="Client Department", required=False,
                                           related="enquiry_id.client_department_id", tracking=True)
    subject = fields.Char(string="Subject", tracking=True)
    location = fields.Char(string="Location", tracking=True)
    gst_type = fields.Selection([
        ('gst_9', 'GST 9%'),
        ('gst_zero', 'GST Zero Rated'),
    ], string="GST", tracking=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', tracking=True, related="enquiry_id.priority")
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='client_id.sector', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=False, index=True,
                                 related='client_id.company_id', store=True, tracking=True)
    enq_probability = fields.Float(string='Probability (%)', related="enquiry_id.enq_probability", tracking=True)
    deadline = fields.Datetime(string="Deadline & Time", related='sale_enquiry_id.deadline', tracking=True)
    project_id = fields.Many2one('project.project', string='Project', required=False, tracking=True)
    project_number = fields.Char(string='Project Number', required=False, related="project_id.project_ref",
                                 tracking=True)
    project_name = fields.Char(string="Project Name", related='project_id.name', tracking=True)
    vessel_name = fields.Char(string="Vessel Name", related="project_id.name", tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id, tracking=True)
    service_amount = fields.Monetary(string="Total", store=True, compute='_compute_service_amounts', tracking=True)
    discount_percent = fields.Float(string="Discount (%)", default=0.0, tracking=True)
    discount_amt = fields.Float(string="Discount Amt", store=True, tracking=True)
    total_discount_amount = fields.Monetary(string="Total Discount Amount", compute="_compute_service_amounts",
                                            store=True, tracking=True)
    amount_after_discount = fields.Monetary(string="Less Discount", compute="_compute_service_amounts", store=True,
                                            tracking=True)
    gst_amount = fields.Monetary(string="GST Amount", compute="_compute_service_amounts", store=True, tracking=True)
    net_amount = fields.Monetary(string="Net Amount", compute="_compute_service_amounts", store=True, tracking=True)
    gst_percent = fields.Selection([
        ('9_percent', '9%'),
    ], string="GST", default='9_percent', tracking=True)
    yeard_id = fields.Many2one('res.partner', string='Yeard', domain="[('parent_id', '=', False)]",
                               related='sale_enquiry_id.yeard_id', tracking=True)
    user_id = fields.Many2one('res.users', string='Sales Person', default=lambda self: self.env.user,
                              related='enquiry_id.user_id', tracking=True)
    boss_approval_required = fields.Boolean(tracking=True)
    calcification = fields.Selection([
        ('client', 'Client'),
        ('shipyard', 'Shipyard'),
        ('government', 'Government'),
        ('ship_management', 'Ship Management'),
        ('vessel_owner', 'Vessel Owner'),
        ('process_plant', 'Process Plant'),
        ('construction', 'Construction'),
        ('power_plant', 'Power Plant'),
    ], string='Calcification', related='enquiry_id.calcification', tracking=True)
    discount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('amount', 'Amount'),
    ], string="Discount Type", default='percent', tracking=True)
    system = fields.Char(string="System", tracking=True)
    scope = fields.Text(string="Scope", tracking=True)
    net_amount_total_words = fields.Char(string="Amount total in words", compute="_compute_net_amount_total_words",
                                         tracking=True)
    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string="Approval Status", default='draft', tracking=True)

    @api.depends('net_amount', 'currency_id')
    def _compute_net_amount_total_words(self):
        for order in self:
            order.net_amount_total_words = order.currency_id.amount_to_text(order.net_amount).replace(',', '')

    @api.constrains('warehouse_id', 'state', 'order_line')
    def _check_warehouse(self):
        return False

    def _get_sale_order_states(self):
        """Remove 'sent' state from dropdown"""
        states = [
            ('draft', "Quotation"),
            ('approved', "Quotation Approved"),
            ('sale', "Sales Order"),
            ('cancel', "Cancelled"),
        ]
        return states

    state = fields.Selection(
        selection=lambda self: self._get_sale_order_states(),
        string="Status",
        readonly=True, copy=False, index=True, tracking=3, default='draft'
    )

    @api.onchange('discount_percent')
    def _onchange_discount_percent(self):
        for rec in self:
            if rec.discount_percent > 100:
                rec.discount_percent = False
                raise ValidationError("Discount cannot be greater than 100%.")

    @api.onchange('discount_amt')
    def _onchange_discount_amt(self):
        if self.discount_amt and self.service_amount and self.discount_amt > self.service_amount:
            raise ValidationError("Discount amount cannot be greater than the Net Amount!")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None

                company_id = vals.get('company_id')
                dept_id = vals.get('department_id')

                current_year = datetime.now().year
                seq_code = self.env['ir.sequence'].next_by_code('sale.enquiry') or 'OT-000'
                seq_number = seq_code.split('-')[-1]

                company_code = 'CMP'
                if company_id:
                    company = self.env['res.company'].browse(company_id)
                    if company and hasattr(company, 'code') and company.code:
                        company_code = company.code

                dept_code = 'DEPT'
                if dept_id:
                    dept = self.env['enquiry.department'].browse(dept_id)
                    if dept and hasattr(dept, 'code') and dept.code:
                        dept_code = dept.code

                vals['name'] = f"{company_code}-QT-{dept_code}-{current_year}-{seq_number}"

        return super().create(vals_list)

    @api.depends('order_line.price_subtotal', 'discount_type', 'discount_percent', 'discount_amt', 'gst_type')
    def _compute_service_amounts(self):
        for rec in self:
            total = sum(line.price_subtotal for line in rec.order_line)

            total_discount_amount = 0.0
            if rec.discount_type == 'percent':
                discount_percent = min(rec.discount_percent, 100)
                total_discount_amount = (total * discount_percent / 100)
            elif rec.discount_type == 'amount':
                if rec.discount_amt > total:
                    rec.discount_amt = 0.0
                    raise ValidationError("❗ Discount amount cannot be greater than Total Amount!")
                total_discount_amount = rec.discount_amt or 0.0

            amount_after_discount = total - total_discount_amount
            gst_rate = 9 / 100 if rec.gst_type == 'gst_9' else 0.0
            gst_amount = amount_after_discount * gst_rate
            net_amount = amount_after_discount + gst_amount

            rec.service_amount = total
            rec.total_discount_amount = total_discount_amount
            rec.amount_after_discount = amount_after_discount
            rec.gst_amount = gst_amount
            rec.net_amount = net_amount

    def action_approve_quotation(self):
        boss_group = self.env.ref("custom_unique.group_unique_administrator")
        for rec in self:
            if not rec.order_line:
                raise UserError("You cannot approve this quotation because there are no items added.")

            if rec.net_amount > 25000:
                if self.env.user in boss_group.user_ids:
                    rec.state = 'approved'
                    if rec.user_id:
                        message = f"Hello {rec.user_id.name}, your quotation '{rec.name}' (Amount: {rec.net_amount}) has been approved by the Boss!"
                        self.env['bus.bus']._sendone(
                            rec.user_id.partner_id,
                            'simple_notification',
                            {
                                'type': 'success',
                                'message': message,
                                'sticky': True,
                                'className': 'bg-success',
                            }
                        )
                    continue
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Boss Approval Required',
                    'res_model': 'approve.sale.quotation.wizard',
                    'view_mode': 'form',
                    'view_id': self.env.ref('custom_unique.view_approve_sale_order_wizard').id,
                    'target': 'new',
                    'context': {
                        'default_sale_order_id': rec.id,
                    }
                }
            else:
                rec.state = 'approved'

    def action_confirm(self):
        for rec in self:
            if rec.name:
                parts = rec.name.split("-")
                if len(parts) >= 5:
                    company_code = parts[0]
                    dept_code = parts[2]
                    year = parts[3]
                    seq = parts[4]
                    new_name = f"{company_code}-SO-{dept_code}-{year}-{seq}"
                    rec.name = new_name

        return super(SaleOrder, self).action_confirm()

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        return orders.write({
            'state': 'draft',
            'signature': False,
            'signed_by': False,
            'signed_on': False,
            'boss_approval_required': False,
        })

    def action_cancel_approval(self):
        for order in self:
            order.approval_state = 'cancelled'

    def _confirmation_error_message(self):
        return False

    def action_create_invoice(self):
        """Create invoice from sale order with all custom fields and lines"""
        self.ensure_one()

        if self.state != 'sale':
            raise UserError("You can only create invoices for confirmed sales orders.")

        # Check if invoice already exists
        existing_invoice = self.env['account.move'].search([
            ('sale_order_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel')
        ], limit=1)

        if existing_invoice:
            # Show notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invoice Already Exists'),
                    'message': _('An invoice has already been created for this sale order.'),
                    'type': 'warning',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'name': _('Customer Invoice'),
                        'res_model': 'account.move',
                        'res_id': existing_invoice.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                }
            }

        # Prepare invoice values - Transfer ALL fields from Sale Order
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': self.name,
            'sale_order_id': self.id,

            # Transfer all custom fields
            'subject': self.subject,
            'location': self.location,
            'gst_type': self.gst_type,
            'discount_type': self.discount_type,
            'discount_percent': self.discount_percent,
            'discount_amt': self.discount_amt,
            'gst_percent': self.gst_percent,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id if self.company_id else self.env.company.id,
        }

        # Create the invoice
        invoice = self.env['account.move'].create(invoice_vals)

        # Create invoice lines from sale order lines
        for line in self.order_line:
            # Get the income account from product or fallback
            account = line.product_id.property_account_income_id or \
                      line.product_id.categ_id.property_account_income_categ_id

            if not account:
                raise UserError(_(
                    'Please define income account for product: %s or its category.'
                ) % line.product_id.name)

            invoice_line_vals = {
                'move_id': invoice.id,
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'product_uom_id': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'account_id': account.id,

                # Transfer custom fields
                'product_description': line.product_description,
                'remarks': line.remarks,
                'service_note': line.service_note,
                'uom_id': line.uom_id.id if line.uom_id else False,
                'cost_of_sales': line.cost_of_sales,
            }

            self.env['account.move.line'].create(invoice_line_vals)

        # Compute amounts after lines are created
        invoice._compute_service_amounts()

        # Show success notification and open invoice
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _('Invoice created successfully from Sale Order %s') % self.name,
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('Customer Invoice'),
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            }
        }

    def action_view_project(self):
        self.ensure_one()
        if self.project_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Project'),
                'view_mode': 'form',
                'res_model': 'project.project',
                'res_id': self.project_id.id,
                'target': 'current',
            }
        else:
            raise UserError(_("No Project linked with this Sale Order."))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    percentage = fields.Float(string="%", help="Enter percentage if applicable", compute="_compute_margin")
    product_description = fields.Text(string="Description", related="product_id.description_sale", readonly=False)
    remarks = fields.Char(string="Remarks")
    service_note = fields.Char(string="Note")
    uom_id = fields.Many2one('uom.uom', string='UOM')
    cost_of_sales = fields.Monetary(string="Cost of Sales")

    @api.depends('price_subtotal', 'cost_of_sales')
    def _compute_margin(self):
        """Compute profit percentage = ((Amount - Cost) / Cost) * 100"""
        for rec in self:
            if rec.cost_of_sales:
                rec.percentage = ((rec.price_subtotal - rec.cost_of_sales) / rec.cost_of_sales) * 100
            else:
                rec.percentage = 0.0
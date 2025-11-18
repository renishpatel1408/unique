# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', tracking=True)
    enquiry_id = fields.Many2one('enquiry.lead', string='Enquiry', index=True, related="sale_order_id.enquiry_id",
                                 tracking=True)
    department_id = fields.Many2one("enquiry.department", string="Department", required=True,
                                    related="enquiry_id.department_id", tracking=True)
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
    ref_no = fields.Char(string="Ref No.", related="sale_order_id.ref_no", tracking=True)
    client_department_id = fields.Many2one("client.department", string="Client Department",
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
    enq_probability = fields.Float(string='Probability (%)', related="enquiry_id.enq_probability", tracking=True)
    deadline = fields.Datetime(string="Deadline & Time", related='sale_order_id.deadline', tracking=True)
    project_id = fields.Many2one('project.project', string='Project Number', required=False,
                                 related="sale_order_id.project_id", tracking=True)
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
                               related='sale_order_id.yeard_id', tracking=True)
    user_id = fields.Many2one('res.users', string='Sales Person', default=lambda self: self.env.user,
                              related='enquiry_id.user_id', tracking=True)
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
    status_in_payment = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
    ], string="Payment Status", default='draft', tracking=True)

    @api.onchange('discount_percent')
    def _onchange_discount_percent(self):
        for rec in self:
            if rec.discount_percent > 100:
                rec.discount_percent = False
                raise ValidationError("Discount cannot be greater than 100%.")

    @api.onchange('discount_amt')
    def _onchange_discount_amt(self):
        if self.discount_amt and self.service_amount and self.discount_amt > self.service_amount:
            raise ValidationError("Discount amount cannot be greater than the Total Amount!")

    @api.depends('invoice_line_ids.price_subtotal', 'discount_type', 'discount_percent', 'discount_amt', 'gst_type')
    def _compute_service_amounts(self):
        for rec in self:
            total = sum(line.price_subtotal for line in rec.invoice_line_ids)

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

    def action_confirm_invoice(self):
        """Custom confirm button to post the invoice with notification"""
        for move in self:
            if not move.invoice_line_ids:
                raise UserError("Cannot confirm invoice without any invoice lines!")

            # Post the invoice using Odoo's standard method
            move.action_post()

            # Update custom status
            move.status_in_payment = 'posted'

            # Send notification to the salesperson
            if move.user_id:
                message = f"Invoice {move.name} has been confirmed! Amount: {move.currency_id.symbol}{move.net_amount:.2f}"
                self.env['bus.bus']._sendone(
                    move.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'message': message,
                        'sticky': True,
                        'className': 'bg-success',
                    }
                )

            # Post message in chatter
            move.message_post(
                body=f"Invoice confirmed by {self.env.user.name} on {fields.Datetime.now()}",
                subject="Invoice Confirmed"
            )

        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success!'),
                'message': _('Invoice has been confirmed successfully!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_sale_order(self):
        """Navigate back to the originating sale order"""
        self.ensure_one()
        if self.sale_order_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Sale Order'),
                'res_model': 'sale.order',
                'res_id': self.sale_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_("No Sale Order linked to this invoice."))


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

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
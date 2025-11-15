# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    enquiry_id = fields.Many2one('enquiry.lead', string='Enquiry', index=True, related="sale_order_id.enquiry_id")
    department_id = fields.Many2one("enquiry.department", string="Department", required=True,
                                    related="enquiry_id.department_id")
    enquiry_date = fields.Datetime(
        string="Enquiry Date",
        help="Date when the enquiry was created.",
        related="enquiry_id.create_date",
        store=True
    )
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False)]",
                                related="enquiry_id.client_id")
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]",
                                        related="enquiry_id.contact_person_id")
    mobile = fields.Char(string="Contact No.", readonly=False,
                         help="Enter multiple mobile numbers separated by commas or new lines.",
                         related="client_id.phone")
    email = fields.Char(string='Email', store=True, readonly=False, related="client_id.email")
    ref_no = fields.Char(string="Ref No.", related="sale_order_id.ref_no")
    client_department_id = fields.Many2one("client.department", string="Client Department",
                                           related="enquiry_id.client_department_id")
    subject = fields.Char(string="Subject")
    location = fields.Char(string="Location")
    gst_type = fields.Selection([
        ('gst_9', 'GST 9%'),
        ('gst_zero', 'GST Zero Rated'),
    ], string="GST")

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
    ], string='Sector', related='client_id.sector')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True,
                                 related='client_id.company_id')

    enq_probability = fields.Float(string='Probability (%)', related="enquiry_id.enq_probability")
    deadline = fields.Datetime(string="Deadline & Time", related='sale_order_id.deadline')
    project_id = fields.Many2one('project.project', string='Project Number', required=False,
                                 related="sale_order_id.project_id")
    project_name = fields.Char(string="Project Name", related='project_id.name')
    vessel_name = fields.Char(string="Vessel Name", related="project_id.name")
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    service_amount = fields.Monetary(string="Total", tracking=5)
    discount_percent = fields.Float(string="Discount (%)", default=0.0)
    discount_amt = fields.Float(string="Discount Amt", store=True)
    total_discount_amount = fields.Monetary(string="Total Discount Amount")
    amount_after_discount = fields.Monetary(string="Less Discount")
    gst_amount = fields.Monetary(string="GST Amount")
    net_amount = fields.Monetary(string="Net Amount")
    gst_percent = fields.Selection([
        ('9_percent', '9%'),
    ], string="GST", default='9_percent')
    yeard_id = fields.Many2one('res.partner', string='Yeard', domain="[('parent_id', '=', False)]",
                               related='sale_order_id.yeard_id')
    user_id = fields.Many2one('res.users', string='Sales Person', default=lambda self: self.env.user,
                              related='enquiry_id.user_id')

    calcification = fields.Selection([
        ('client', 'Client'),
        ('shipyard', 'Shipyard'),
        ('government', 'Government'),
        ('ship_management', 'Ship Management'),
        ('vessel_owner', 'Vessel Owner'),
        ('process_plant', 'Process Plant'),
        ('construction', 'Construction'),
        ('power_plant', 'Power Plant'),
    ], string='Calcification', related='enquiry_id.calcification')
    discount_type = fields.Selection([('percent', 'Percentage'),
                                      ('amount', 'Amount'),
                                      ], string="Discount Type", default='percent')
    # account_service_lines = fields.One2many('account.service.order.line', 'move_id',string="Service Lines")

    # @api.onchange('discount_percent')
    # def _onchange_discount_percent(self):
    #     for rec in self:
    #         if rec.discount_percent > 100:
    #             rec.discount_percent = False
    #             print("dszfxcghjksdzxfcg", rec.discount_percent)
    #             raise ValidationError("Discount cannot be greater than 100%.")
    #
    # @api.onchange('discount_amt')
    # def _onchange_discount_amt(self):
    #     if self.discount_amt and self.service_amount and self.discount_amt > self.service_amount:
    #         raise ValidationError("Discount amount cannot be greater than the Net Amount!")
    #
    # @api.depends('account_service_lines.service_price_subtotal', 'discount_type', 'discount_percent', 'discount_amt',
    #              'gst_type')
    # def _compute_service_amounts(self):
    #     for rec in self:
    #         total = sum(line.service_price_subtotal for line in rec.account_service_lines)
    #
    #         total_discount_amount = 0.0
    #         if rec.discount_type == 'percent':
    #             discount_percent = min(rec.discount_percent, 100)
    #             total_discount_amount = (total * discount_percent / 100)
    #         elif rec.discount_type == 'amount':
    #             if rec.discount_amt > total:
    #                 rec.discount_amt = 0.0
    #                 raise ValidationError("❗ Discount amount cannot be greater than Total Amount!")
    #             total_discount_amount = rec.discount_amt or 0.0
    #             print("\n\n\n\n\n\n\n\n\n\nsdfghsadfghsdSWAEFRGTHYJASDFGHMJHTGfg", total_discount_amount)
    #
    #         amount_after_discount = total - total_discount_amount
    #
    #         gst_rate = 9 / 100 if rec.gst_type == 'gst_9' else 0.0
    #         gst_amount = amount_after_discount * gst_rate
    #
    #         net_amount = amount_after_discount + gst_amount
    #         rec.service_amount = total
    #         rec.total_discount_amount = total_discount_amount
    #         rec.amount_after_discount = amount_after_discount
    #         rec.gst_amount = gst_amount
    #         rec.net_amount = net_amount


    def action_confirm_invoice(self):
        """Custom confirm button to post the invoice"""
        for move in self:
            move.state = 'posted'
            move.status_in_payment = 'posted'

            # # This calls Odoo's built-in post logic
            # move.action_post()

#             # You can add extra logic if needed (for example, notifications)
#             # move.message_post(body="Invoice confirmed by user: %s" % self.env.user.name)

        return True


# class AccountServiceOrderLine(models.Model):
#     _name = 'account.service.order.line'
#
#     move_id = fields.Many2one('account.move', required=True, ondelete='cascade', index=True)
#     department_id = fields.Many2one("enquiry.department", string="Department", required=True)
#     department_description = fields.Char(string="Description")
#     qty = fields.Float(string="Qty", readonly=False, required=True, precompute=True)
#     uom_id = fields.Many2one('uom.uom',string='UOM')
#     cost_of_sales = fields.Monetary(string="Cost of Sales")
#     percentage = fields.Float(string="%", help="Enter percentage if applicable", compute="_compute_margin")
#     remarks = fields.Char(string="Remarks")
#     service_note = fields.Char(string="Note")
#     service_price_unit = fields.Monetary(
#         string="Amount Quotated",
#         digits='Product Price',
#         store=True, readonly=False, required=True, precompute=True)
#     service_price_subtotal = fields.Monetary(
#         string="Amount",
#         compute='_compute_service_amount',
#         store=True, precompute=True)
#     currency_id = fields.Many2one('res.currency', string='Currency',
#                                   default=lambda self: self.env.company.currency_id.id)
#
#     @api.depends('service_price_subtotal', 'cost_of_sales')
#     def _compute_margin(self):
#         """Compute profit percentage = ((Amount - Cost) / Cost) * 100"""
#         for rec in self:
#             if rec.cost_of_sales:
#                 rec.percentage = ((rec.service_price_subtotal - rec.cost_of_sales) / rec.cost_of_sales) * 100
#             else:
#                 rec.percentage = 0.0
#
#     @api.depends('service_price_unit', 'qty')
#     def _compute_service_amount(self):
#         for rec in self:
#             rec.service_price_subtotal = rec.service_price_unit * rec.qty





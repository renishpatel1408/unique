# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from email.policy import default

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import uuid

class SaleEnquiry(models.Model):
    _name = "sale.enquiry"
    _description = "Sale Enquiry"
    _rec_name = 'sale_enquiry_ref'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Enquiry Information
    sale_enquiry_ref = fields.Char(string="Enquiry Ref", readonly=True, copy=False, index=True, default='New')
    sale_order_id = fields.Many2one('sale.order', string='Quotation')
    enquiry_id = fields.Many2one('enquiry.lead', string='Enquiry', index=True)
    enquiry_date = fields.Datetime(
        string="Enquiry Date",
        help="Date when the enquiry was created.",
        related="enquiry_id.create_date",
        store=True
    )
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False)]",related="enquiry_id.client_id")
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]", related="enquiry_id.contact_person_id")
    work_location = fields.Selection([('office', 'Office'),('shipyard', 'Shipyard'),('onsite', 'On Site'),('client_site', 'Client Site'),('warehouse', 'Warehouse'),('other', 'Other'),
    ], string="Work Location", help="Select the location where the work will take place.")
    mobile = fields.Char(string="Contact No.", related='client_id.phone',
                         help="Enter multiple mobile numbers separated by commas or new lines.")
    email = fields.Char(string='Email', related='client_id.email', store=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, related="client_id.company_id")
    client_department_id = fields.Many2one("client.department", string="Client Department", related='enquiry_id.client_department_id')
    ref_no = fields.Char(string="Client Ref No",help="Enter the client's reference number (e.g., BBQ 200).")
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
    department_id = fields.Many2one("enquiry.department", string="Department", related='enquiry_id.department_id')

    # Sale Person information
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', tracking=True, related='enquiry_id.priority')

    user_id = fields.Many2one('res.users',string='Sales Person',default=lambda self: self.env.user, related='enquiry_id.user_id')
    enq_probability = fields.Float(string='Probability (%)', default=1, related='enquiry_id.enq_probability')
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='client_id.sector', readonly=False)
    yeard_id = fields.Many2one('res.partner', string='Yard')

    #Project information

    deadline = fields.Datetime(string="Deadline & Time")
    project_id = fields.Many2one('project.project', string='Vessel Name', required=False)
    project_name = fields.Char(string="Project Name")
    vessel_name = fields.Char(string="Vessel Name")
    sale_quotations_count = fields.Integer(compute='_compute_sale_quotations_count')
    state = fields.Selection([('approved', 'Approved'),('reject', 'Rejected')], string='Status',tracking=True)
    is_approved = fields.Boolean(default=True)
    
    def _compute_sale_quotations_count(self):
        for rec in self:
            sale_quotations = self.env['sale.order'].search_count([('id', '=', rec.sale_order_id.id)])
            self.sale_quotations_count = sale_quotations

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.sale_enquiry_ref or record.sale_enquiry_ref == 'New':
                company = record.company_id
                dept = record.department_id
                current_year = datetime.now().year
                seq_code = self.env['ir.sequence'].next_by_code('sale.enquiry') or 'SENQ-000'
                seq_number = seq_code.split('-')[-1]
                company_code = company.code if hasattr(company, 'code') and company.code else 'CMP'
                dept_code = dept.code if hasattr(dept, 'code') and dept.code else 'DEPT'
                record.sale_enquiry_ref = f"{company_code}-ENQ-{dept_code}-{current_year}-{seq_number}"
        return records

    def action_create_quotation(self):
        Project = self.env['project.project']
        for enquiry in self:
            sale_order = self.env['sale.order'].create({
                'enquiry_id': enquiry.enquiry_id.id,
                'sale_enquiry_id': enquiry.id,
                'partner_id': enquiry.contact_person_id.id,
                'company_id': enquiry.company_id.id,
                'department_id': enquiry.department_id.id,
            })
            enquiry.write({'sale_order_id': sale_order.id})

            project_title = False
            if enquiry.vessel_name:
                project_title = enquiry.vessel_name
            elif enquiry.project_name:
                project_title = enquiry.project_name
            if project_title:
                project = Project.create({
                    'name': project_title,
                    'company_id': enquiry.company_id.id,
                    'partner_id': enquiry.contact_person_id.id,
                    'sale_order_id': sale_order.id,
                })
                sale_order.project_id = project.id
            return {
                'name': 'Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': sale_order.id,
            }

    def action_view_quotations(self):
        self.ensure_one()
        order_id = self.env['sale.order'].search([('sale_enquiry_id', '=', self.id)], limit=1)
        if order_id:
            return {
                'name': 'Quotation',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': order_id.id,
            }

    def action_enquiry_approve(self):
        for record in self:
            record.state = 'approved'
            record.is_approved = False
        return True

    def action_enquiry_reject(self):
        for record in self:
            record.state = 'reject'
            record.is_approved = False
        return True

    def unlink(self):
        for record in self:
            if record.state == 'approved':
                raise UserError(_("You cannot delete an approved enquiry."))
        return super(SaleEnquiry, self).unlink()


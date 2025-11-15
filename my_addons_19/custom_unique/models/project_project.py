# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    project_ref = fields.Char(string="Project No.", readonly=True, copy=False, index=True, default='New')
    sale_order_id = fields.Many2one('sale.order', string='Quotation', store=True,  readonly=False)
    department_id = fields.Many2one("enquiry.department", string="Department", related="sale_order_id.department_id",  readonly=False, store=True)
    start_date = fields.Datetime(string="Start Date", readonly=False)
    end_date = fields.Datetime(string="End Date", readonly=False)
    yeard_id = fields.Many2one('res.partner', string='Yard', domain="[('parent_id', '=', False)]", related="sale_order_id.yeard_id", readonly=False)
    quotation_date = fields.Datetime(string="Quotation Date", related="sale_order_id.date_order", readonly=False)
    client_id = fields.Many2one('res.partner', string='Company Name', domain="[('parent_id', '=', False)]",
                                related="sale_order_id.client_id", readonly=False, store=True)
    contact_person_id = fields.Many2one('res.partner', string='Contact Name', domain="[('parent_id', '=', client_id)]",
                                        related="sale_order_id.contact_person_id", readonly=False, store=True)
    mobile = fields.Char(string="Contact No.", readonly=False,
                         help="Enter multiple mobile numbers separated by commas or new lines.",
                         related="client_id.phone")
    email = fields.Char(string='Email', store=True, readonly=False, related="client_id.email")
    ref_no = fields.Char(string="Ref No.", related="sale_order_id.ref_no",readonly=False)
    client_department_id = fields.Many2one("client.department", string="Client Department",
                                           related="sale_order_id.client_department_id", readonly=False, store=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase No.', readonly=False)

    calcification = fields.Selection([
        ('client', 'Client'),
        ('shipyard', 'Shipyard'),
        ('government', 'Government'),
        ('ship_management', 'Ship Management'),
        ('vessel_owner', 'Vessel Owner'),
        ('process_plant', 'Process Plant'),
        ('construction', 'Construction'),
        ('power_plant', 'Power Plant'),
        ('power_plant', 'Power Plant'),
    ], string='Calcification', related='sale_order_id.calcification', readonly=False)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', tracking=True, related='sale_order_id.priority', readonly=False)

    user_id = fields.Many2one('res.users', string='Sales Person', default=lambda self: self.env.user,
                              related='sale_order_id.user_id', readonly=False)
    enq_probability = fields.Float(string='Probability (%)', default=1, related='sale_order_id.enq_probability', readonly=False)
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='client_id.sector', readonly=False)
    company_id = fields.Many2one('res.company', string='Company', index=True, related="client_id.company_id", readonly=False)

    deadline = fields.Datetime(string="Deadline & Time", related="sale_order_id.deadline", readonly=False)
    vessel_name = fields.Char(string="Vessel Name", related="sale_order_id.vessel_name", readonly=False)
    state = fields.Selection([('approved', 'Approved'), ('reject', 'Rejected')], string='Status', tracking=True, readonly=False)
    estimation_line_ids = fields.One2many('project.estimation.line', 'project_id',string='Lines', readonly=False)
    employee_ids = fields.One2many('project.employee', 'project_id',string='Employee Details', readonly=False)
    project_complete_percent = fields.Float(string='Project compliance %', readonly=False, default=0.0)
    location = fields.Char(string="Location", related="sale_order_id.location")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.project_ref or record.project_ref == 'New':
                company = record.company_id
                dept = record.department_id
                current_year = datetime.now().year
                seq_code = self.env['ir.sequence'].next_by_code('project.project') or 'OT-000'
                seq_number = seq_code.split('-')[-1]
                company_code = company.code if hasattr(company, 'code') and company.code else 'CMP'
                dept_code = dept.code if hasattr(dept, 'code') and dept.code else 'DEPT'
                record.project_ref = f"{company_code}-PRO-{current_year}-{seq_number}"
        return records


class ProjectEstimationLine(models.Model):
    _name = 'project.estimation.line'
    _description = 'Project Estimation Line'
    _order = 'id asc'

    project_id = fields.Many2one('project.project', string='Project', ondelete='cascade')
    estimate_man_hrs = fields.Monetary(string='Estimate Man Hrs')
    rate_per_hr = fields.Monetary(string='Rate per Hour')
    est_man_power_cost = fields.Monetary(string='Est. Man Power Cost', compute='_compute_est_man_power_cost', store=True)
    est_dia_weight_uom = fields.Char(string='Est. DIA / Weight UOM')
    po_amount = fields.Monetary(string='P.O Amount')
    vor_not_approved = fields.Monetary(string='VOR / Not Approved')
    total_project_value = fields.Monetary(string='Total Project Value')
    total_project_value_2 = fields.Monetary(string='Total Project Value 2', compute='_compute_total_project_values', store=True)
    percent_completed = fields.Float(string='% Completed')
    wip_value = fields.Monetary(string='WIP Value', compute='_compute_total_project_values', store=True)
    percent_pending = fields.Float(string='% Pending', compute='_compute_percent_calculation', store=True)
    pending_amount = fields.Monetary(string='Pending Amount', compute='_compute_percent_calculation', store=True)
    expected_closing_date = fields.Date(string='Expected Closing Date of the Job')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)
    working_date = fields.Date(string="Work Date")

    @api.depends('estimate_man_hrs', 'rate_per_hr')
    def _compute_est_man_power_cost(self):
        for line in self:
            line.est_man_power_cost = (line.estimate_man_hrs or 0.0) * (line.rate_per_hr or 0.0)

    @api.depends('total_project_value', 'po_amount', 'vor_not_approved', 'percent_completed')
    def _compute_total_project_values(self):
        for line in self:
            total_value = (line.total_project_value or 0.0) + (line.po_amount or 0.0) + (line.vor_not_approved or 0.0)
            line.total_project_value_2 = total_value
            line.wip_value = total_value * ((line.percent_completed or 0.0) / 100)

    @api.depends('project_id.estimation_line_ids.percent_completed',
                 'project_id.estimation_line_ids.total_project_value_2',
                 'percent_completed', 'total_project_value_2')
    def _compute_percent_calculation(self):
        for line in self:
            if line.project_id:
                all_lines = line.project_id.estimation_line_ids.sorted('id')

                # Calculate percent pending
                total_completed_percent = 0.0
                total_wip_amount = 0.0

                for l in all_lines:
                    total_completed_percent += (l.percent_completed or 0.0)
                    total_wip_amount += (l.wip_value or 0.0)

                    if l.id == line.id:
                        break

                line.percent_pending = max(0.0, 100 - total_completed_percent)

                # Calculate pending amount progressively
                # Pending Amount = Total Project Value 2 - Cumulative WIP Value up to this line
                line.pending_amount = (line.total_project_value_2 or 0.0) - total_wip_amount

                # Update project completion percentage
                total_completed_all_lines = sum((l.percent_completed or 0.0) for l in all_lines)
                project_complete = max(0.0, min(100.0, total_completed_all_lines))
                line.project_id.project_complete_percent = project_complete
            else:
                line.percent_pending = 100.0
                line.pending_amount = line.total_project_value_2 or 0.0

    @api.depends('total_project_value_2', 'wip_value')
    def _compute_pending_amount(self):
        """Pending Amount = Total Project Value 2 − WIP Value"""
        for line in self:
            line.pending_amount = (line.total_project_value_2 or 0.0) - (line.wip_value or 0.0)


class ProjectEmployee(models.Model):
    _name = 'project.employee'
    _description = 'Project Employee'

    project_id = fields.Many2one('project.project', string='Project', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    working_dept = fields.Many2one('hr.department', string='Working Dept', related="employee_id.department_id")
    designation_id = fields.Many2one('hr.job', related="employee_id.job_id", string="Designation")
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='employee_id.sector')
    employee_code = fields.Char(string='Employee Code', related="employee_id.code")
    location = fields.Char(string="Location", related="project_id.location", readonly=False)
    employee_total_work = fields.Float(string="Worked Hours")





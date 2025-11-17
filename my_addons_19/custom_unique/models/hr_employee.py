# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, exceptions, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError
import xlsxwriter
import base64
from io import BytesIO
import pytz
import logging

_logger = logging.getLogger(__name__)


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    code = fields.Char(string="Code")
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector')

    rate_per_hour = fields.Monetary(string="Rate Per Hour")
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    salary_rate_per_hour = fields.Monetary(string="Salary Rate Per Hour")
    cpf_amount = fields.Monetary(string="CPF")
    levy_amount = fields.Monetary(string="Levy")
    accomodation_amount = fields.Monetary(string="Accommodation")
    transportation_amount = fields.Monetary(string="Transportation")
    insurance_amount = fields.Monetary(string="Insurance")
    admin_cost_amount = fields.Monetary(string="Admin Cost")
    certification_audit_cost_amount = fields.Monetary(string="Certification / Audit Cost")
    office_rent_amount = fields.Monetary(string="Office Rent")
    oh_cost_amount = fields.Monetary(string="OH Cost")
    others_cost_amount = fields.Monetary(string="Others")

    # REMOVED: working_days_month field

    @api.model
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('hr.employee') or _('New')
        return super(HREmployee, self).create(vals_list)

    def _compute_hours_last_month(self):
        now = fields.Datetime.now()
        now_utc = pytz.utc.localize(now)
        for employee in self:
            tz = pytz.timezone(employee.tz or 'UTC')
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)
            end_tz = now_tz
            end_naive = end_tz.astimezone(pytz.utc).replace(tzinfo=None)

            current_month_attendances = employee.attendance_ids.filtered(
                lambda att: att.check_in >= start_naive and att.check_out and att.check_out <= end_naive
            )

            hours = 0
            overtime_hours = 0

            for att in current_month_attendances:
                hours += att.worked_hours or 0
                overtime_hours += att.validated_overtime_hours or 0

            employee.hours_last_month = round(hours, 2)
            employee.hours_last_month_overtime = round(overtime_hours, 2)

    def action_open_working_days(self):
        return {
            'name': 'This Month Attendance',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance',
            'views': [[self.env.ref('custom_unique.view_employee_attendance_working_day_list').id, "list"]],
            'domain': [
                ('employee_id', '=', self.id),
            ],
            'context': {
                'group_by': ['attendance_date:month'],
                'default_employee_id': self.id,
            }
        }

    def get_working_days_for_month(self, month, year):
        """
        Get unique working days count for employee in specific month/year
        """
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('attendance_date', '!=', False)
        ])

        working_dates = set()
        for att in attendances:
            att_date = att.attendance_date
            if att_date.month == month and att_date.year == year:
                working_dates.add(att_date)

        return len(working_dates)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    _order = "attendance_date asc"

    project_id = fields.Many2one('project.project', string="Project")
    project_ref = fields.Char(string="Project No.", readonly=True, related="project_id.project_ref")
    attendance_date = fields.Date(string="Attendance Date")
    attendance_day = fields.Char(string="Day", compute='_compute_attendance_day', store=True)
    client_id = fields.Many2one('res.partner', string='Client',
                                domain="[('parent_id', '=', False), ('approved_by_boss', '=', True)]",
                                related="project_id.client_id")
    enquiry_department_id = fields.Many2one("enquiry.department", string="Project Department")
    enquiry_department_code = fields.Char(related="enquiry_department_id.code", store=True)
    vessel_name = fields.Char(string="Vessel Name", related="project_id.name")
    worked_hours = fields.Float(string="Worked Hours", compute="_compute_worked_hours", store=True)
    overtime_hours = fields.Float(string="Overtime Hours", compute="_compute_overtime_hours", store=True)
    weekend_overtime_hours = fields.Float(string="Weekend Overtime Hours", compute="_compute_overtime_hours",
                                          store=True)
    weekday_overtime_hours = fields.Float(string="WeekDay Overtime Hours", compute="_compute_overtime_hours",
                                          store=True)
    rate_per_hour = fields.Monetary(string="Rate Per Hour", related="employee_id.rate_per_hour", store=True)
    salary_rate_per_hour = fields.Monetary(string="Salary Rate Per Hour", related="employee_id.salary_rate_per_hour",
                                           store=True)

    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    # CPF and other expense fields - will be auto-calculated
    cpf_amount = fields.Monetary(string="CPF")
    levy_amount = fields.Monetary(string="Levy")
    accomodation_amount = fields.Monetary(string="Accommodation")
    transportation_amount = fields.Monetary(string="Transportation")
    insurance_amount = fields.Monetary(string="Insurance")
    admin_cost_amount = fields.Monetary(string="Admin Cost")
    certification_audit_cost_amount = fields.Monetary(string="Certification / Audit Cost")
    office_rent_amount = fields.Monetary(string="Office Rent")
    oh_cost_amount = fields.Monetary(string="OH Cost")
    others_cost_amount = fields.Monetary(string="Others")

    emp_working_dept = fields.Many2one('hr.department', string='Employee Working Department',
                                       related="employee_id.department_id")
    employee_department = fields.Char(string='Department', related="emp_working_dept.name")
    designation_id = fields.Many2one('hr.job', related="employee_id.job_id", string="Designation")
    sector = fields.Selection([
        ('marine', 'Marine'),
        ('process', 'Process'),
        ('construction', 'Construction'),
        ('employment_agency', 'Employment Agency'),
    ], string='Sector', related='employee_id.sector')
    employee_code = fields.Char(string='Employee Code', related="employee_id.code")
    work_location_id = fields.Many2one(related='employee_id.work_location_id', string='Location', related_sudo=False)
    company_id = fields.Many2one('res.company', string='Company', index=True, related='employee_id.company_id')
    company_code = fields.Char(related="company_id.code")
    total_expense = fields.Monetary(string="Total Expense")
    resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', store=True, check_company=True)
    normal_hour = fields.Float(string="Normal Hour", compute="_compute_normal_hour", store=True)
    total_hours_amount = fields.Monetary(string="Total (Hours × Rate)")
    st_salary_total_hour = fields.Monetary(string="ST Total")
    misc_amount = fields.Monetary(string="Misc")
    check_in = fields.Datetime(string="Check In", required=True, tracking=True, index=True)
    check_out = fields.Datetime(string="Check Out", tracking=True)

    def convert_utc_to_local_time_only(self, dt, tz_name='Asia/Kolkata'):
        """
        Convert UTC datetime → Any timezone → return only HH:MM string.

        Default timezone: Asia/Kolkata
        Example usage: 'Asia/Singapore'
        """
        if not dt:
            return False

        # If datetime is naive, make it UTC aware
        if not dt.tzinfo:
            dt = pytz.UTC.localize(dt)

        # Convert to target timezone
        try:
            local_tz = pytz.timezone(tz_name)
        except Exception:
            local_tz = pytz.timezone('Asia/Kolkata')  # fallback

        dt_local = dt.astimezone(local_tz)
        return dt_local.strftime('%H:%M')

    _auto_update_flag = False  # Temporary flag

    @api.onchange('attendance_date')
    def _onchange_attendance_date(self):
        # Mark context to indicate automatic update
        self = self.with_context(_auto_update=True)

        if self.attendance_date:
            # Update check_in to match attendance_date
            if self.check_in:
                check_in_time = self.check_in.time()
                self.check_in = datetime.combine(self.attendance_date, check_in_time)

            # Update check_out to match attendance_date
            if self.check_out:
                check_out_time = self.check_out.time()
                self.check_out = datetime.combine(self.attendance_date, check_out_time)

    @api.onchange('check_in', 'check_out')
    def _onchange_check_times(self):
        # Skip check if automatic update via context
        if self.env.context.get('_auto_update'):
            return

        warning = {}
        if self.attendance_date:
            if self.check_in and self.check_in.date() != self.attendance_date:
                self.check_in = False  # Clear value
                warning = {
                    'title': _("Check-In Date Error"),
                    'message': _("Check-In date must match Attendance Date.")
                }
                return {'warning': warning}

            if self.check_out and self.check_out.date() != self.attendance_date:
                self.check_out = False  # Clear value
                warning = {
                    'title': _("Check-Out Date Error"),
                    'message': _("Check-Out date must match Attendance Date.")
                }
                return {'warning': warning}


    def _calculate_attendance_costs(self):
        """
        Calculate all costs for this attendance record based on working days
        Uses direct write to avoid triggering write() method recursion
        """
        if not self.employee_id or not self.attendance_date:
            return

        employee = self.employee_id
        month = self.attendance_date.month
        year = self.attendance_date.year
        misc_amount = self.misc_amount

        # Get working days for this employee in this month
        total_working_days = employee.get_working_days_for_month(month, year)

        if total_working_days == 0:
            total_working_days = 1  # Avoid division by zero

        # Calculate hour-based amounts
        worked_hours = self.worked_hours or 0.0
        weekday_ot = self.weekday_overtime_hours or 0.0
        weekend_ot = self.weekend_overtime_hours or 0.0
        rate = self.rate_per_hour or 0.0
        salary_rate = self.salary_rate_per_hour or 0.0

        normal_hours = worked_hours - weekday_ot - weekend_ot
        if normal_hours < 0:
            normal_hours = 0

        weekday_ot_pay = weekday_ot * (rate * 1.5)
        weekend_ot_pay = weekend_ot * (rate * 2)
        normal_pay = normal_hours * rate

        total_hours_amount = normal_pay + weekday_ot_pay + weekend_ot_pay
        st_salary_total_hour = worked_hours * salary_rate

        # Set department
        enquiry_department_id = False
        if self.project_id and self.project_id.department_id:
            enquiry_department_id = self.project_id.department_id.id

        # Calculate per-day expense amounts
        cpf_amount = (employee.cpf_amount or 0.0) / total_working_days
        levy_amount = (employee.levy_amount or 0.0) / total_working_days
        accomodation_amount = (employee.accomodation_amount or 0.0) / total_working_days
        transportation_amount = (employee.transportation_amount or 0.0) / total_working_days
        insurance_amount = (employee.insurance_amount or 0.0) / total_working_days
        admin_cost_amount = (employee.admin_cost_amount or 0.0) / total_working_days
        certification_audit_cost_amount = (employee.certification_audit_cost_amount or 0.0) / total_working_days
        office_rent_amount = (employee.office_rent_amount or 0.0) / total_working_days
        oh_cost_amount = (employee.oh_cost_amount or 0.0) / total_working_days
        others_cost_amount = (employee.others_cost_amount or 0.0) / total_working_days

        # Calculate total expense
        total_expense = sum([
            cpf_amount, levy_amount, accomodation_amount,
            transportation_amount, insurance_amount, admin_cost_amount,
            certification_audit_cost_amount, office_rent_amount,
            oh_cost_amount, others_cost_amount, st_salary_total_hour, misc_amount
        ])

        # CRITICAL: Use with_context to prevent recursion
        # This bypasses the write() override and prevents recalculation loop
        self.with_context(skip_recalculation=True).write({
            'total_hours_amount': total_hours_amount,
            'st_salary_total_hour': st_salary_total_hour,
            'enquiry_department_id': enquiry_department_id,
            'cpf_amount': cpf_amount,
            'levy_amount': levy_amount,
            'accomodation_amount': accomodation_amount,
            'transportation_amount': transportation_amount,
            'insurance_amount': insurance_amount,
            'admin_cost_amount': admin_cost_amount,
            'certification_audit_cost_amount': certification_audit_cost_amount,
            'office_rent_amount': office_rent_amount,
            'oh_cost_amount': oh_cost_amount,
            'others_cost_amount': others_cost_amount,
            'misc_amount': misc_amount,
            'total_expense': total_expense,
        })

    def _recalculate_month_attendances(self, employee_id, month, year):
        """
        Recalculate all attendance costs for a specific employee-month
        This is called when working days change
        """
        attendances = self.search([
            ('employee_id', '=', employee_id),
            ('attendance_date', '!=', False)
        ])

        # Filter for specific month/year
        month_attendances = attendances.filtered(
            lambda a: a.attendance_date.month == month and a.attendance_date.year == year
        )

        # Recalculate each attendance
        for att in month_attendances:
            att._calculate_attendance_costs()

    @api.model
    def create(self, vals_list):
        # Clean up seconds
        cleaned_vals_list = []
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nCreate Method is.......")
        for vals in vals_list:
            vals_copy = vals.copy()
            if vals_copy.get('check_in'):
                vals_copy['check_in'] = self._remove_seconds(vals_copy['check_in'])
            if vals_copy.get('check_out'):
                vals_copy['check_out'] = self._remove_seconds(vals_copy['check_out'])
            cleaned_vals_list.append(vals_copy)

        # Create records
        records = super(HrAttendance, self).create(cleaned_vals_list)

        # Process each created record
        months_to_recalculate = set()

        for attendance in records:
            # Update project relations
            if attendance.employee_id and attendance.project_id:
                self._update_project_employee_hours(attendance.employee_id, attendance.project_id)

            if attendance.project_id and attendance.attendance_date:
                self._update_project_estimation_line(attendance.project_id, attendance.attendance_date)

            # Track which months need recalculation
            if attendance.employee_id and attendance.attendance_date:
                months_to_recalculate.add((
                    attendance.employee_id.id,
                    attendance.attendance_date.month,
                    attendance.attendance_date.year
                ))

        # Recalculate all attendances for affected employee-months
        for emp_id, month, year in months_to_recalculate:
            self._recalculate_month_attendances(emp_id, month, year)

        return records

    def write(self, vals):
        # CRITICAL: Check if we should skip recalculation to prevent infinite loop
        if self.env.context.get('skip_recalculation'):
            return super(HrAttendance, self).write(vals)

        # Store old data
        old_data = []
        months_to_recalculate = set()

        for rec in self:
            old_data.append({
                'employee_id': rec.employee_id,
                'project_id': rec.project_id,
                'worked_hours': rec.worked_hours,
                'attendance_date': rec.attendance_date,
            })

            # Track old month
            if rec.employee_id and rec.attendance_date:
                months_to_recalculate.add((
                    rec.employee_id.id,
                    rec.attendance_date.month,
                    rec.attendance_date.year
                ))

        # Clean seconds
        if vals.get('check_in'):
            vals['check_in'] = self._remove_seconds(vals['check_in'])
        if vals.get('check_out'):
            vals['check_out'] = self._remove_seconds(vals['check_out'])

        # Update records
        res = super(HrAttendance, self).write(vals)

        # Track affected combinations
        affected_combinations = set()
        affected_estimation_dates = set()

        for rec, old in zip(self, old_data):
            # Add old combination
            if old['employee_id'] and old['project_id']:
                affected_combinations.add((old['employee_id'].id, old['project_id'].id))
                if old['attendance_date']:
                    affected_estimation_dates.add((old['project_id'].id, old['attendance_date']))

            # Add new combination
            if rec.employee_id and rec.project_id:
                affected_combinations.add((rec.employee_id.id, rec.project_id.id))
                if rec.attendance_date:
                    affected_estimation_dates.add((rec.project_id.id, rec.attendance_date))

            # Track new month
            if rec.employee_id and rec.attendance_date:
                months_to_recalculate.add((
                    rec.employee_id.id,
                    rec.attendance_date.month,
                    rec.attendance_date.year
                ))

        # Update project hours
        for emp_id, proj_id in affected_combinations:
            employee = self.env['hr.employee'].browse(emp_id)
            project = self.env['project.project'].browse(proj_id)
            self._update_project_employee_hours(employee, project)

        # Update estimation lines
        for proj_id, att_date in affected_estimation_dates:
            project = self.env['project.project'].browse(proj_id)
            self._update_project_estimation_line(project, att_date)

        # Recalculate affected months
        for emp_id, month, year in months_to_recalculate:
            self._recalculate_month_attendances(emp_id, month, year)

        return res

    def unlink(self):
        # Store data before deletion
        combinations_to_update = []
        estimation_dates_to_update = []
        months_to_recalculate = set()

        for rec in self:
            if rec.employee_id and rec.project_id:
                combinations_to_update.append({
                    'employee_id': rec.employee_id.id,
                    'project_id': rec.project_id.id,
                })
                if rec.attendance_date:
                    estimation_dates_to_update.append({
                        'project_id': rec.project_id.id,
                        'attendance_date': rec.attendance_date,
                    })

                    # Track month for recalculation
                    months_to_recalculate.add((
                        rec.employee_id.id,
                        rec.attendance_date.month,
                        rec.attendance_date.year
                    ))

        # Delete records
        res = super(HrAttendance, self).unlink()

        # Update project records
        for combo in combinations_to_update:
            employee = self.env['hr.employee'].browse(combo['employee_id'])
            project = self.env['project.project'].browse(combo['project_id'])
            self._update_project_employee_hours(employee, project)

        # Update estimation lines
        for item in estimation_dates_to_update:
            project = self.env['project.project'].browse(item['project_id'])
            self._update_project_estimation_line(project, item['attendance_date'])

        # Recalculate remaining attendances in affected months
        for emp_id, month, year in months_to_recalculate:
            self._recalculate_month_attendances(emp_id, month, year)

        return res

    def _update_project_employee_hours(self, employee, project):
        if not employee or not project:
            return

        attendances = self.search([
            ('employee_id', '=', employee.id),
            ('project_id', '=', project.id)
        ])

        total_hours = sum(attendances.mapped('worked_hours'))

        project_emp = self.env['project.employee'].search([
            ('employee_id', '=', employee.id),
            ('project_id', '=', project.id)
        ], limit=1)

        if total_hours > 0:
            if project_emp:
                project_emp.write({'employee_total_work': total_hours})
            else:
                self.env['project.employee'].create({
                    'employee_id': employee.id,
                    'project_id': project.id,
                    'employee_total_work': total_hours,
                    'location': project.location if project else False,
                })
        else:
            if project_emp:
                project_emp.unlink()

    def _update_project_estimation_line(self, project, attendance_date):
        if not project or not attendance_date:
            return

        attendances = self.search([
            ('project_id', '=', project.id),
            ('attendance_date', '=', attendance_date)
        ])

        total_hours = sum(attendances.mapped('worked_hours'))

        estimation_line = self.env['project.estimation.line'].search([
            ('project_id', '=', project.id),
            ('working_date', '=', attendance_date)
        ], limit=1)

        if total_hours > 0:
            if estimation_line:
                estimation_line.write({'estimate_man_hrs': total_hours})
            else:
                self.env['project.estimation.line'].create({
                    'project_id': project.id,
                    'working_date': attendance_date,
                    'estimate_man_hrs': total_hours,
                })
        else:
            if estimation_line:
                estimation_line.unlink()

    def _remove_seconds(self, dt_value):
        if isinstance(dt_value, str):
            dt_value = fields.Datetime.from_string(dt_value)
        if dt_value:
            return dt_value.replace(second=0, microsecond=0)
        return dt_value

    @api.depends('worked_hours', 'rate_per_hour')
    def _compute_total_hours_amount(self):
        for rec in self:
            rec.total_hours_amount = (rec.worked_hours or 0.0) * (rec.rate_per_hour or 0.0)

    @api.depends('attendance_date', 'resource_calendar_id')
    def _compute_normal_hour(self):
        for rec in self:
            if rec.attendance_date and rec.resource_calendar_id:
                day_of_week = rec.attendance_date.weekday()
                if day_of_week in [0, 1, 2, 3, 4]:
                    rec.normal_hour = rec.resource_calendar_id.mon_to_fri_hours
                elif day_of_week == 5:
                    rec.normal_hour = rec.resource_calendar_id.saturday_hours
                else:
                    rec.normal_hour = 0.0
            else:
                rec.normal_hour = 0.0

    @api.depends('attendance_date')
    def _compute_attendance_day(self):
        for rec in self:
            if rec.attendance_date:
                rec.attendance_day = rec.attendance_date.strftime('%A')
            else:
                rec.attendance_day = False

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                delta = rec.check_out - rec.check_in
                rec.worked_hours = delta.total_seconds() / 3600.0
            else:
                rec.worked_hours = 0.0

    @api.depends('worked_hours', 'check_in', 'check_out', 'employee_id', 'attendance_date')
    def _compute_overtime_hours(self):
        for rec in self:
            rec.overtime_hours = 0.0
            rec.weekday_overtime_hours = 0.0
            rec.weekend_overtime_hours = 0.0

            if not rec.check_in or not rec.employee_id or not rec.attendance_date:
                continue

            calendar = rec.employee_id.resource_calendar_id
            if not calendar:
                continue

            local_check_in = fields.Datetime.context_timestamp(rec, rec.check_in)
            day_of_week = int(local_check_in.strftime('%w'))

            if day_of_week in [1, 2, 3, 4, 5]:
                daily_limit = calendar.mon_to_fri_hours
                is_weekend = False
            elif day_of_week == 6:
                daily_limit = calendar.saturday_hours
                is_weekend = True
            else:
                daily_limit = 0.0
                is_weekend = True

            all_records = self.env['hr.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('attendance_date', '=', rec.attendance_date),
                ('check_in', '!=', False),
                ('check_out', '!=', False),
            ], order='check_in ASC')

            if not all_records:
                continue

            cumulative_hours = 0.0

            for idx, att in enumerate(all_records):
                att_worked = att.worked_hours

                if att.id == rec.id:
                    remaining_normal = max(0, daily_limit - cumulative_hours)

                    if att_worked <= remaining_normal:
                        rec.overtime_hours = 0.0
                    else:
                        overtime = att_worked - remaining_normal
                        rec.overtime_hours = overtime

                        if is_weekend:
                            rec.weekend_overtime_hours = overtime
                        else:
                            rec.weekday_overtime_hours = overtime
                    break
                else:
                    cumulative_hours += att_worked

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        return False

    @api.constrains('employee_id', 'check_in', 'check_out', 'project_id', 'attendance_date')
    def _check_attendance_validations(self):
        """
        Complete attendance validation with improved error messages and warnings.
        Validates:
        1. Mandatory fields
        2. Time logic (check-out after check-in)
        3. Overlapping records prevention
        4. Leave conflicts
        5. Public holidays
        6. Mandatory attendance days
        """
        for rec in self:
            try:
                self._validate_mandatory_fields(rec)
                # self._check_public_holiday(rec)
                self._check_leave_conflict(rec)
                # self._check_mandatory_attendance(rec)
                check_in_utc, check_out_utc = self._validate_and_normalize_times(rec)
                self._check_overlapping_attendance(rec, check_in_utc, check_out_utc)

            except ValidationError as e:
                # Re-raise validation errors with additional context
                _logger.warning(
                    "Attendance validation failed for employee %s on %s: %s",
                    rec.employee_id.name,
                    rec.attendance_date,
                    str(e)
                )
                raise

    def _validate_mandatory_fields(self, rec):
        """Validate that all mandatory fields are filled."""
        missing_fields = []

        if not rec.employee_id:
            missing_fields.append(_("Employee"))
        if not rec.project_id:
            missing_fields.append(_("Project"))
        if not rec.attendance_date:
            missing_fields.append(_("Attendance Date"))

        if missing_fields:
            raise ValidationError(
                _("Missing required fields: %s\n\nPlease fill in all mandatory information before saving.")
                % ", ".join(missing_fields)
            )

        if not rec.check_in or not rec.check_out:
            # Convert to local time for display if values exist
            check_in_display = self.convert_utc_to_local_time_only(rec.check_in) if rec.check_in else _("Not set")
            check_out_display = self.convert_utc_to_local_time_only(rec.check_out) if rec.check_out else _("Not set")

            raise ValidationError(
                _("Both Check-in and Check-out times are required.\n\n"
                  "Current values:\n"
                  "• Check-in: %s\n"
                  "• Check-out: %s")
                % (check_in_display, check_out_display)
            )

        # if self.check_in:
        #     check_in_date = fields.Datetime.context_timestamp(self, self.check_in).date()
        #     if check_in_date != self.attendance_date:
        #         raise ValidationError("Check In date does not match Attendance Date!\nPlease select the correct date.")
        # if self.check_out:
        #     check_out_date = fields.Datetime.context_timestamp(self, self.check_out).date()
        #     if check_out_date != self.attendance_date:
        #         raise ValidationError("Check Out date does not match Attendance Date!\nPlease select the correct date.")

    def _validate_and_normalize_times(self, rec):
        """Normalize times to UTC and validate time logic."""
        # Normalize to UTC if not already timezone-aware
        check_in_utc = rec.check_in if rec.check_in.tzinfo else pytz.UTC.localize(rec.check_in)
        check_out_utc = rec.check_out if rec.check_out.tzinfo else pytz.UTC.localize(rec.check_out)

        if check_out_utc <= check_in_utc:
            # Convert to local time for display
            check_in_local = self.convert_utc_to_local_time_only(check_in_utc)
            check_out_local = self.convert_utc_to_local_time_only(check_out_utc)
            print("================================================", check_in_local, check_out_local)

            raise ValidationError(
                _("Invalid time range: Check-out must be after Check-in.\n\n"
                  "Current times:\n"
                  "• Check-in: %s (%s)\n"
                  "• Check-out: %s (%s)\n\n"
                  "Please adjust the times accordingly.")
                % (rec.attendance_date.strftime("%d/%m/%Y"), check_in_local,
                   rec.attendance_date.strftime("%d/%m/%Y"), check_out_local)
            )

        return check_in_utc, check_out_utc

    def _check_overlapping_attendance(self, rec, check_in_utc, check_out_utc):
        """Check for overlapping attendance records."""
        existing_records = self.env['hr.attendance'].search([
            ('id', '!=', rec.id),
            ('employee_id', '=', rec.employee_id.id),
            ('attendance_date', '=', rec.attendance_date),
        ])

        for ex in existing_records:
            ex_check_in = ex.check_in if ex.check_in.tzinfo else pytz.UTC.localize(ex.check_in)
            ex_check_out = ex.check_out if ex.check_out.tzinfo else pytz.UTC.localize(ex.check_out)

            # Check for time overlap
            overlap = check_in_utc < ex_check_out and check_out_utc > ex_check_in

            if overlap:
                # Convert all times to local format for display
                ex_check_in_local = self.convert_utc_to_local_time_only(ex_check_in)
                ex_check_out_local = self.convert_utc_to_local_time_only(ex_check_out)
                check_in_local = self.convert_utc_to_local_time_only(check_in_utc)
                check_out_local = self.convert_utc_to_local_time_only(check_out_utc)

                if ex.project_id == rec.project_id:
                    raise ValidationError(
                        _("⚠️ Overlapping Attendance Detected\n\n"
                          "Employee '%s' already has attendance for the same project during this time.\n\n"
                          "📋 Details:\n"
                          "• Date: %s\n"
                          "• Project: %s\n"
                          "• Existing Time: %s - %s\n"
                          "• New Time: %s - %s\n\n"
                          "💡 Solution: Adjust the check-in/check-out times to avoid overlap or delete the existing record.")
                        % (rec.employee_id.name,
                           rec.attendance_date.strftime("%d/%m/%Y"),
                           ex.project_id.name,
                           ex_check_in_local,
                           ex_check_out_local,
                           check_in_local,
                           check_out_local)
                    )
                else:
                    raise ValidationError(
                        _("⚠️ Multi-Project Conflict Detected\n\n"
                          "Employee '%s' cannot work on multiple projects during the same time period.\n\n"
                          "📋 Conflict Details:\n"
                          "• Date: %s\n"
                          "• Existing Project: %s (%s - %s)\n"
                          "• Enter Project: %s (%s - %s)\n\n"
                          "💡 Solution: Adjust times to avoid overlap or reassign one of the projects.")
                        % (rec.employee_id.name,
                           rec.attendance_date.strftime("%d/%m/%Y"),
                           ex.project_id.name,
                           ex_check_in_local,
                           ex_check_out_local,
                           rec.project_id.name,
                           check_in_local,
                           check_out_local)
                    )

    def _check_leave_conflict(self, rec):
        """Check if employee is on approved leave."""
        leave_exists = self.env['hr.leave'].search([
            ('employee_id', '=', rec.employee_id.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', rec.attendance_date),
            ('request_date_to', '>=', rec.attendance_date),
        ], limit=1)
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n============", leave_exists)

        if leave_exists:
            raise ValidationError(
                _("🚫 Leave Conflict\n\n"
                  "Employee '%s' has an approved leave on this date.\n"
                  "Attendance cannot be recorded during leave periods.\n\n"
                  "📋 Leave Details:\n"
                  "• Leave Type: %s\n"
                  "• Leave Period: %s to %s\n"
                  "• Status: %s\n\n"
                  "💡 Solution: Cancel the leave request first or choose a different date.")
                % (rec.employee_id.name,
                   leave_exists.holiday_status_id.name,
                   leave_exists.request_date_from.strftime("%d/%m/%Y"),
                   leave_exists.request_date_to.strftime("%d/%m/%Y"),
                   dict(leave_exists._fields['state'].selection).get(leave_exists.state))
            )

    def _check_public_holiday(self, rec):
        """Check if the date is a public holiday."""
        if not rec.employee_id.resource_calendar_id:
            _logger.warning(
                "No working calendar assigned to employee %s. Skipping public holiday check.",
                rec.employee_id.name
            )
            return

        public_holiday = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', rec.employee_id.resource_calendar_id.id),
            ('date_from', '<=', rec.attendance_date),
            ('date_to', '>=', rec.attendance_date),
        ], limit=1)
        print("\n\n\n\n\n\n\n================>>>>>>>>>>>>>>>>>>", public_holiday)

        if public_holiday:
            # Check if it's specifically marked as public holiday (if field exists)
            raise ValidationError(
                _("🏖️ Public Holiday\n\n"
                  "The date %s is a public holiday.\n"
                  "Regular attendance cannot be recorded on public holidays.\n\n"
                  "📋 Holiday Details:\n"
                  "• Holiday Name: %s\n"
                  "💡 Note: If this is overtime or special work, please use the appropriate "
                  "attendance type or contact HR.")
                % (rec.attendance_date.strftime("%d/%m/%Y"),
                   public_holiday.name)
            )

    def _check_mandatory_attendance(self, rec):
        """Check mandatory attendance days."""
        mandatory_day = self.env['hr.leave.mandatory.day'].search([
            ('start_date', '<=', rec.attendance_date),
            ('end_date', '>=', rec.attendance_date)
        ], limit=1)

        if mandatory_day:
            _logger.info(
                "Attendance recorded on mandatory day %s for employee %s",
                rec.attendance_date,
                rec.employee_id.name
            )

            # Raise warning for mandatory day
            raise ValidationError(
                _("Warning: %s is a mandatory attendance day.\n"
                  "Reason: %s\n"
                  "Employee: %s") % (
                    rec.attendance_date,
                    mandatory_day.name or 'Mandatory Attendance Required',
                    rec.employee_id.name
                )
            )

    @api.model
    def action_export_attendance_excel(self, attendance_ids, wizard_data=None):
        """Generate Excel report - values are already calculated on attendance records"""
        if not attendance_ids:
            raise UserError("No attendance records selected for export.")

        attendances = self.browse(attendance_ids)

        date_type = wizard_data.get('date_type', 'today') if wizard_data else 'today'

        start_date = wizard_data.get('start_date') if wizard_data else fields.Date.today()
        if isinstance(start_date, str):
            start_date = fields.Date.from_string(start_date)

        end_date = wizard_data.get('end_date') if wizard_data else fields.Date.today()
        if isinstance(end_date, str):
            end_date = fields.Date.from_string(end_date)

        employee_names = wizard_data.get('employee_names', 'All Employees') if wizard_data else 'All Employees'
        project_names = wizard_data.get('project_names', 'All Projects') if wizard_data else 'All Projects'

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Attendance Report')

        # FORMATS
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'bg_color': '#f0f0f0',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        filter_label_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        filter_value_format = workbook.add_format({
            'bg_color': '#F2F2F2',
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#f0f0f0',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        currency_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '$#,##0.00'
        })

        date_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy'
        })

        time_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # SET COLUMN WIDTHS
        column_widths = [8, 15, 15, 25, 25, 25, 25, 25, 25, 25, 25, 25,
                         25, 25, 12, 12, 12, 12, 12, 12, 18, 18, 18, 18,
                         18, 18, 18, 18, 18, 18, 22, 20, 20, 20, 20, 20]

        for col_num, width in enumerate(column_widths):
            worksheet.set_column(col_num, col_num, width)

        worksheet.set_row(0, 20)
        worksheet.set_row(1, 30)
        worksheet.merge_range(1, 0, 1, 35, 'ATTENDANCE REPORT', title_format)

        filter_row = 3

        if date_type == 'today':
            date_range_text = start_date.strftime('%d/%m/%Y')
        else:
            date_range_text = f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"

        worksheet.merge_range(filter_row, 0, filter_row, 1, 'Date Range:', filter_label_format)
        worksheet.merge_range(filter_row, 2, filter_row, 35, date_range_text, filter_value_format)

        filter_row += 1
        worksheet.merge_range(filter_row, 0, filter_row, 1, 'Employees:', filter_label_format)
        worksheet.merge_range(filter_row, 2, filter_row, 35, employee_names, filter_value_format)

        filter_row += 1
        worksheet.merge_range(filter_row, 0, filter_row, 1, 'Projects:', filter_label_format)
        worksheet.merge_range(filter_row, 2, filter_row, 35, project_names, filter_value_format)

        filter_row += 2
        header_row = filter_row

        headers = [
            'S.No', 'Date', 'Day', 'Project No', 'Project Department',
            'Client Name', 'Vessel Name', 'Employee Name', 'Designation',
            'Company', 'Sector', 'Employee Code', 'Employee Department',
            'Location', 'Time In', 'Time Out', 'Normal', '1.5 Times',
            '2.0 Times', 'Total Hrs', 'Rate Per Hr', 'Sub Total',
            'Salary Rate Per Hour', 'ST-Salary Sub total', 'CPF', 'LAVY',
            'Accommodation', 'Transportation', 'Insurance', 'Admin Cost',
            'Certification / Audit Cost', 'Office Rent', 'OH Cost',
            'Others', 'Misc', 'Total Expense'
        ]

        for col_num, header in enumerate(headers):
            worksheet.write(header_row, col_num, header, header_format)

        data_start_row = header_row + 1

        for counter, attendance in enumerate(attendances, start=1):
            row = data_start_row + counter - 1
            col = 0

            worksheet.write(row, col, counter, cell_format)
            col += 1

            if attendance.attendance_date:
                date_obj = fields.Date.from_string(attendance.attendance_date)
                worksheet.write(row, col, date_obj, date_format)
            else:
                worksheet.write(row, col, '', cell_format)
            col += 1

            worksheet.write(row, col, attendance.attendance_day or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.project_ref or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.enquiry_department_code or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.client_id.name if attendance.client_id else '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.vessel_name or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.employee_id.name if attendance.employee_id else '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.designation_id.name if attendance.designation_id else '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.company_code or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.sector or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.employee_code or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.employee_department or '-', cell_format)
            col += 1
            worksheet.write(row, col, attendance.work_location_id.name if attendance.work_location_id else '-',
                            cell_format)
            col += 1

            # Time In - Using convert_utc_to_local_time_only method
            time_in = self.convert_utc_to_local_time_only(attendance.check_in, 'Asia/Kolkata')
            worksheet.write(row, col, time_in if time_in else '-', time_format)
            col += 1

            # Time Out - Using convert_utc_to_local_time_only method
            time_out = self.convert_utc_to_local_time_only(attendance.check_out, 'Asia/Kolkata')
            worksheet.write(row, col, time_out if time_out else '-', time_format)
            col += 1

            worksheet.write(row, col, self._format_hours(attendance.normal_hour), cell_format)
            col += 1
            worksheet.write(row, col, self._format_hours(attendance.weekday_overtime_hours), cell_format)
            col += 1
            worksheet.write(row, col, self._format_hours(attendance.weekend_overtime_hours), cell_format)
            col += 1
            worksheet.write(row, col, self._format_hours(attendance.worked_hours), cell_format)
            col += 1
            worksheet.write(row, col, attendance.rate_per_hour or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.total_hours_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.salary_rate_per_hour or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.st_salary_total_hour or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.cpf_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.levy_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.accomodation_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.transportation_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.insurance_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.admin_cost_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.certification_audit_cost_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.office_rent_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.oh_cost_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.others_cost_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.misc_amount or 0, currency_format)
            col += 1
            worksheet.write(row, col, attendance.total_expense or 0, currency_format)

        workbook.close()
        output.seek(0)

        if date_type == 'today':
            filename = f"Attendance_Report_{start_date.strftime('%d-%m-%Y')}.xlsx"
        else:
            filename = f"Attendance_Report_{start_date.strftime('%d-%m-%Y')}_to_{end_date.strftime('%d-%m-%Y')}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'store_fname': filename,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _format_hours(self, hours):
        if not hours:
            return '00:00'
        h = int(hours)
        m = round((hours % 1) * 60)
        if m == 60:
            h += 1
            m = 0
        return f'{h:02d}:{m:02d}'


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    saturday_hours = fields.Float(string="Saturday Hours", default=4.0)
    mon_to_fri_hours = fields.Float(string="Mon–Fri Hours", default=8.0)
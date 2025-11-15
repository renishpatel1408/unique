# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import pytz


class HRAttendanceReportWizard(models.TransientModel):
    _name = 'hr.attendance.report.wizard'
    _description = 'HR Attendance Report Wizard'

    date_type = fields.Selection(
        [('today', 'Today'), ('custom', 'Custom')],
        string='Date Type',
        default='today',
        required=True
    )
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    project_ids = fields.Many2many('project.project', string='Projects')

    total_hours = fields.Float(string='Total Worked Hours', readonly=True)

    @api.onchange('date_type')
    def _onchange_date_type(self):
        if self.date_type == 'today':
            today = fields.Date.context_today(self)
            self.start_date = today
            self.end_date = today
        else:
            self.start_date = None
            self.end_date = None

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

    def action_generate_report(self):
        """
        Generate the attendance report and send properly formatted values to the frontend.
        """

        # Step 1: Validate dates
        if not self.start_date or not self.end_date:
            raise UserError(_("Start Date and End Date are required."))

        if self.end_date < self.start_date:
            raise UserError(_("End Date cannot be earlier than Start Date."))

        # Step 2: Define search domain
        domain = [
            ('attendance_date', '>=', self.start_date),
            ('attendance_date', '<=', self.end_date)
        ]

        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        if self.project_ids:
            domain.append(('project_id', 'in', self.project_ids.ids))

        # Step 3: Fetch attendance records
        attendances = self.env['hr.attendance'].search(domain)

        if not attendances:
            raise UserError(_("No attendance records found for the selected filters."))

        # Step 4: Convert time fields to local timezone and prepare data
        attendance_data = []
        for att in attendances:
            att_dict = {
                'id': att.id,
                'attendance_date': att.attendance_date,
                'attendance_day': att.attendance_day,
                'project_ref': att.project_ref,
                'enquiry_department_code': att.enquiry_department_code,
                'client_id': att.client_id.id if att.client_id else False,
                'vessel_name': att.vessel_name,
                'employee_id': [att.employee_id.id, att.employee_id.name] if att.employee_id else False,
                'designation_id': [att.designation_id.id, att.designation_id.name] if att.designation_id else False,
                'company_code': att.company_code,
                'sector': att.sector,
                'employee_code': att.employee_code,
                'employee_department': att.employee_department,
                'work_location_id': [
                    att.work_location_id.id,
                    att.work_location_id.name
                ] if att.work_location_id else False,

                # ✅ Time fields in local timezone in HH:MM string format
                'check_in': self.convert_utc_to_local_time_only(att.check_in),
                'check_out': self.convert_utc_to_local_time_only(att.check_out),

                # Numeric fields
                'normal_hour': att.normal_hour,
                'weekday_overtime_hours': att.weekday_overtime_hours,
                'weekend_overtime_hours': att.weekend_overtime_hours,
                'worked_hours': att.worked_hours,
                'rate_per_hour': att.rate_per_hour,
                'total_hours_amount': att.total_hours_amount,
                'salary_rate_per_hour': att.salary_rate_per_hour,
                'st_salary_total_hour': att.st_salary_total_hour,
                'cpf_amount': att.cpf_amount,
                'levy_amount': att.levy_amount,
                'accomodation_amount': att.accomodation_amount,
                'transportation_amount': att.transportation_amount,
                'insurance_amount': att.insurance_amount,
                'admin_cost_amount': att.admin_cost_amount,
                'certification_audit_cost_amount': att.certification_audit_cost_amount,
                'office_rent_amount': att.office_rent_amount,
                'oh_cost_amount': att.oh_cost_amount,
                'others_cost_amount': att.others_cost_amount,
                'misc_amount': att.misc_amount,
                'total_expense': att.total_expense,
            }

            print("++++++++++++++++", att_dict)
            attendance_data.append(att_dict)

        # Step 5: Prepare filter names
        employee_names = 'All Employees'
        if self.employee_ids:
            employee_names = ', '.join(self.employee_ids.mapped('name'))

        project_names = 'All Projects'
        if self.project_ids:
            project_names = ', '.join(self.project_ids.mapped('name'))

        # Step 6: Return action with fully formatted data
        return {
            'type': 'ir.actions.client',
            'tag': 'custom_unique.attendance_report',
            'context': {
                'attendance_data': attendance_data,  # send full prepared data
                'date_type': self.date_type,
                'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
                'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
                'employee_names': employee_names,
                'project_names': project_names,
            },
        }

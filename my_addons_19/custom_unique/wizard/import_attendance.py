# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time
import base64
from io import BytesIO
import openpyxl
import pytz


# class AttendanceImportWizard(models.TransientModel):
#     _name = 'attendance.import.wizard'
#     _description = 'Attendance Import Wizard'
#
#     file = fields.Binary(string="Upload File", required=True)
#     file_name = fields.Char(string="File Name")
#
#     # -----------------------------------------------------
#     # Helper Method: Parse Time (Supports Excel datetime/time)
#     # -----------------------------------------------------
#     def _parse_excel_time(self, value):
#         if not value:
#             return None
#         if isinstance(value, datetime):
#             return value.time()
#         if isinstance(value, time):
#             return value
#         if isinstance(value, str):
#             value = value.strip().upper()
#             try:
#                 return datetime.strptime(value, "%I:%M %p").time()
#             except ValueError:
#                 raise ValidationError(
#                     _("Invalid time format '%s'. Please use format like 06:30 PM or 10:00 AM.") % value
#                 )
#         raise ValidationError(_("Invalid time value: %s") % str(value))
#
#     # -----------------------------------------------------
#     # Helper Method: Parse Date (DD/MM/YY or DD/MM/YYYY)
#     # -----------------------------------------------------
#     def _parse_excel_date(self, value):
#         """Parse Excel date supporting multiple formats."""
#         if not value:
#             return None
#
#         if isinstance(value, datetime):
#             return value.date()
#
#         if isinstance(value, str):
#             value = value.strip()
#             for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d",
#                         "%d.%m.%Y", "%d.%m.%y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
#                 try:
#                     return datetime.strptime(value, fmt).date()
#                 except ValueError:
#                     continue
#             raise ValidationError(_("Invalid date format '%s'.") % value)
#
#         return None
#
#     # -----------------------------------------------------
#     # Main Import Logic
#     # -----------------------------------------------------
#
#     def _to_float(self, value):
#         """Safely convert misc_amount to float for Monetary field."""
#         if value in (None, "", False):
#             return 0.0
#         try:
#             return float(value)
#         except Exception:
#             return 0.0
#
#     def action_import_attendance(self):
#         if not self.file:
#             raise UserError(_("Please upload an Excel file."))
#
#         file_content = base64.b64decode(self.file)
#         workbook = openpyxl.load_workbook(BytesIO(file_content))
#         sheet = workbook.active
#
#         local_tz = pytz.timezone("Asia/Kolkata")
#
#         error_messages = []
#         imported_count = 0
#         valid_records = []
#
#         # ----------------------
#         # Step 1: Parse Excel Rows
#         # ----------------------
#         for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
#             if not any(row):
#                 continue
#
#             row = [str(x).strip().replace('\n', '').replace('\r', '') if isinstance(x, str) else x for x in row]
#             date_str, project_ref, employee_name, check_in, check_out, misc_amount = row
#             row_errors = []
#
#             # --- Required Fields ---
#             if not date_str:
#                 row_errors.append("Missing Date.")
#             if not employee_name:
#                 row_errors.append("Missing Employee Name.")
#             if not project_ref:
#                 row_errors.append("Missing Project Reference.")
#             if not check_in:
#                 row_errors.append("Missing Check In.")
#             if not check_out:
#                 row_errors.append("Missing Check Out.")
#
#             # --- Validate Employee ---
#             employee = None
#             if employee_name:
#                 employee = self.env['hr.employee'].search([('name', '=', employee_name)], limit=1)
#                 if not employee:
#                     row_errors.append(f"Employee '{employee_name}' not found.")
#
#             # --- Validate Project ---
#             project = None
#             if project_ref:
#                 project = self.env['project.project'].search([('project_ref', '=', project_ref)], limit=1)
#                 if not project:
#                     row_errors.append(f"Project '{project_ref}' not found.")
#
#             # --- Validate Date ---
#             attendance_date = self._parse_excel_date(date_str)
#             if not attendance_date:
#                 row_errors.append(f"Invalid Date format '{date_str}'. Expected DD/MM/YYYY or DD/MM/YY.")
#
#             # --- Parse Times ---
#             check_in_time = self._parse_excel_time(check_in)
#             check_out_time = self._parse_excel_time(check_out)
#
#             # --- Combine Date + Time ---
#             check_in_dt = check_out_dt = None
#             if check_in_time and check_out_time and attendance_date:
#                 local_check_in = local_tz.localize(datetime.combine(attendance_date, check_in_time))
#                 local_check_out = local_tz.localize(datetime.combine(attendance_date, check_out_time))
#
#                 if local_check_out <= local_check_in:
#                     row_errors.append(f"Check Out ({check_out}) is earlier than Check In ({check_in}).")
#
#                 check_in_dt = local_check_in.astimezone(pytz.UTC).replace(tzinfo=None)
#                 check_out_dt = local_check_out.astimezone(pytz.UTC).replace(tzinfo=None)
#
#             if misc_amount:
#                 misc_amount = self._to_float(misc_amount)
#                 print("========>>>>>>>>>>>>>>>>>", misc_amount)
#
#             # --- Store Valid Record ---
#             if not row_errors:
#                 valid_records.append({
#                     'employee_id': employee.id,
#                     'project_id': project.id,
#                     'check_in': check_in_dt,
#                     'check_out': check_out_dt,
#                     'attendance_date': attendance_date,
#                     'misc_amount': misc_amount,
#                 })
#                 imported_count += 1
#             else:
#                 error_messages.append(f"Row {row_index}: " + ", ".join(row_errors))
#
#         # --- Show Errors if any ---
#         if error_messages:
#             raise ValidationError("⚠️ Errors found:\n\n" + "\n".join(error_messages))
#
#         # ----------------------
#         # Step 2: Create Attendance & Update Project Employee
#         # ----------------------
#         for rec in valid_records:
#             attendance = self.env['hr.attendance'].create({
#                 'employee_id': rec['employee_id'],
#                 'project_id': rec['project_id'],
#                 'check_in': rec['check_in'],
#                 'check_out': rec['check_out'],
#                 'attendance_date': rec['attendance_date'],
#                 'misc_amount': rec['misc_amount'],
#             })
#
#         # Create success message
#         message = _('%s attendance records imported successfully!') % imported_count
#
#         # Send notification via bus
#         self.env['bus.bus']._sendone(
#             self.env.user.partner_id,
#             'simple_notification',
#             {
#                 'title': _('Success'),
#                 'message': message,
#                 'type': 'success',
#                 'sticky': False,
#             }
#         )
#
#         # Return action to open attendance list
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Attendances'),
#             'res_model': 'hr.attendance',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'target': 'current',
#             'domain': [],
#             'context': dict(self.env.context, search_default_project=1),
#         }

class ApproveSaleOrderWizard(models.TransientModel):
    _name = 'approve.sale.quotation.wizard'
    _description = 'Approve Sale Quotation Wizard'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")

    def action_approve_sale_order(self):
        print("\n\n\n\n\n\n\n\n=====")
        self.sale_order_id.boss_approval_required = True
        boss_group = self.env.ref("custom_unique.group_unique_administrator")
        boss_users = boss_group.user_ids
        notify_msg = (
            f"The quotation {self.sale_order_id.name} requires your approval because "
            f"the amount is above $25,000."
        )
        for boss_user in boss_users:
            # Send notification
            self.env['bus.bus']._sendone(
                boss_user.partner_id,
                'simple_notification',
                {
                    'message': notify_msg,
                    'type': 'info',
                    'sticky': True,
                }
            )

class ProjectCancelReasonWizard(models.TransientModel):
    _name = 'project.cancel.reason'
    _description = 'Project Cancel Reason'

    project_id = fields.Many2one('project.project', string='Project', required=False)
    cancel_reason = fields.Text(string="Reason")


    def action_confirm_cancel(self):
        if self.project_id:
            print("========================", self.project_id)
            self.project_id.state = 'cancel'
            self.project_id.cancel_reason = self.cancel_reason
            print("========================", self.project_id.state, self.project_id.cancel_reason)
        return {'type': 'ir.actions.act_window_close'}

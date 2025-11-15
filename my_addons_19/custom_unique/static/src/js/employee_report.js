/** @odoo-module **/
import { registry } from '@web/core/registry';
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AttendanceReport extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const context = this.props.action?.context || {};

        this.state = useState({
            attendances: [],
            loading: true,
            wizardData: null,
        });

        console.log("=== Full Action Props ===", this.props);
        console.log("=== Context Data ===", context);

        onWillStart(async () => {
            // ✅ Backend already sends converted data directly
            let attendanceData = context.attendance_data || [];

            // Store wizard data for display and export
            this.state.wizardData = {
                date_type: context.date_type || 'today',
                start_date: context.start_date || new Date().toISOString().split('T')[0],
                end_date: context.end_date || new Date().toISOString().split('T')[0],
                employee_names: context.employee_names || 'All Employees',
                project_names: context.project_names || 'All Projects',
            };

            console.log("🎯 Wizard Data:", this.state.wizardData);
            console.log("🎯 Attendance Data:", attendanceData);

            if (attendanceData && attendanceData.length > 0) {
                // ✅ Use data directly – no API call required
                this.state.attendances = attendanceData;
                console.log("✅ Attendance records loaded:", attendanceData.length);
            } else {
                console.error("❌ No attendance data found in context!");
            }
            this.state.loading = false;
        });
    }

    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-GB');
    }

    formatFilterDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString + 'T00:00:00');
        return date.toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }

    formatDateTime(dateTimeString) {
        if (!dateTimeString) return '';
        const date = new Date(dateTimeString);
        return date.toLocaleString('en-GB');
    }

    formatHours(hours) {
        if (!hours) return '00:00';
        const h = Math.floor(hours);
        const m = Math.round((hours % 1) * 60);
        const fixedMinutes = m === 60 ? 0 : m;
        const fixedHours = m === 60 ? h + 1 : h;
        return `${fixedHours.toString().padStart(2, '0')}:${fixedMinutes.toString().padStart(2, '0')}`;
    }

    // Not needed anymore – backend already sends formatted "HH:MM"
    formatTime(timeString) {
        return timeString || "-";
    }

    formatCurrency(amount, currencyCode = 'SGD') {
        if (!amount && amount !== 0) return '-';
        return new Intl.NumberFormat('en-SG', {
            style: 'currency',
            currency: currencyCode,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }

    // Export Excel Report with Wizard Data
    async exportReport() {
        try {
            if (!this.state.attendances || this.state.attendances.length === 0) {
                this.notification.add("No records available for export!", { type: "warning" });
                return;
            }

            this.notification.add("Generating Excel report...", { type: "info" });

            const attendanceIds = this.state.attendances.map(att => att.id);

            // Prepare wizard data for backend
            const wizardData = {
                date_type: this.state.wizardData.date_type,
                start_date: this.state.wizardData.start_date,
                end_date: this.state.wizardData.end_date,
                employee_names: this.state.wizardData.employee_names,
                project_names: this.state.wizardData.project_names,
            };

            console.log("📤 Sending wizard data to backend:", wizardData);

            // Call backend with wizard data
            const action = await this.orm.call(
                'hr.attendance',
                'action_export_attendance_excel',
                [attendanceIds, wizardData]
            );

            if (action && action.url) {
                window.location.href = action.url;
                this.notification.add("Report exported successfully!", { type: "success" });
            }

        } catch (error) {
            console.error("Export error:", error);
            this.notification.add("Failed to export report. Please try again.", { type: "danger" });
        }
    }
}

AttendanceReport.template = "custom_unique.attendance_report";
registry.category("actions").add("custom_unique.attendance_report", AttendanceReport);

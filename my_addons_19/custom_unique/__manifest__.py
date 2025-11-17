# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Unique CRM/sale/Purchase/Project',
    'version': '19.0.0',
    'category': 'crm',
    'sequence': 1,
    'depends': ['base', 'crm', 'website', 'contacts', 'sale','sale_management', 'project', 'purchase', 'account', 'hr', 'stock', 'hr_attendance'],
    'data': [
        'data/sequence.xml',
        'data/mail_template.xml',

        'security/ir.model.access.csv',
        'security/res_groups.xml',

        'views/crm_enquiry_view.xml',
        'views/res_user_view.xml',
        'views/sale_enquiry_view.xml',
        'views/sale_order_view_inherit.xml',
        'views/project_project_view.xml',
        # 'views/account_move_view.xml',
        'views/hr_employee_view.xml',
        'report/sale_quotation_report.xml',
        'views/menu_view.xml',

        'wizard/import_attendance_view.xml',
        # 'wizard/attendance_report_wizard_view.xml',
        # Template
        'views/partner_confirmation_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_unique/static/src/js/unique.js',
        ],
    # 'web.assets_backend': [
    #     'custom_unique/static/src/js/employee_report.js',
    #     'custom_unique/static/src/xml/employee_report.xml',
    # ],
    },
    'installable': True,
    'license': 'LGPL-3',

}

# sale_quotation_report.xml

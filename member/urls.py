from django.urls import path
from django.views.generic import RedirectView

from rbac import views as rbac_views

from . import attendance_views, instruction_views, note_views, views

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password_view, name="forgot-password"),
    path("", views.root_redirect, name="root-redirect"),

    # Member
    path("member/dashboard/", views.dashboard, name="member-dashboard"),
    path("member/hotels/", views.hotels, name="member-hotels"),
    path("member/flights/", views.flights, name="member-flights"),
    path("member/transports/", views.transports, name="member-transports"),
    path("member/packages/", views.packages, name="member-packages"),
    path("member/packages/<int:package_id>/", views.package_detail, name="member-package-detail"),
    path("member/bookings/", views.bookings, name="member-bookings"),
    path("member/bookings/insights/", views.booking_insights, name="member-booking-insights"),
    path("member/bookings/<int:booking_id>/notes/", note_views.booking_notes, name="member-booking-notes"),
    path("member/notes/<int:note_id>/delete/", note_views.booking_note_delete, name="member-booking-note-delete"),
    path("member/bookings/save/", views.booking_worksheet_save, name="member-booking-worksheet-save"),
    path("member/bookings/new/", views.booking_worksheet_new, name="member-booking-new"),
    path("member/bookings/<int:booking_id>/", views.booking_detail, name="member-booking-detail"),
    path("member/bookings/<int:booking_id>/update/", views.booking_update, name="member-booking-update"),
    path("member/bookings/<int:booking_id>/delete/", views.booking_delete, name="member-booking-delete"),
    path(
        "member/bookings/<int:booking_id>/voucher/",
        views.booking_voucher_print,
        name="member-booking-voucher-print",
    ),
    path(
        "member/bookings/<int:booking_id>/voucher.pdf",
        views.booking_voucher_pdf,
        name="member-booking-voucher-pdf",
    ),
    path("member/approvals/", views.approvals, name="member-approvals"),
    path("member/approvals/insights/", views.approval_insights, name="member-approval-insights"),
    path("member/<str:kind>/insights/", views.inventory_insights, name="member-inventory-insights"),
    path("member/approvals/<int:booking_id>/approve/", views.approval_approve, name="member-approval-approve"),
    path("member/approvals/<int:booking_id>/reject/", views.approval_reject, name="member-approval-reject"),
    path("member/ledger/", views.ledger, name="member-ledger"),
    path("member/ledger/report/", views.ledger_report, name="member-ledger-report"),
    path("member/ledger/export/", views.ledger_export, name="member-ledger-export"),
    path("member/attendance/", views.attendance, name="member-attendance"),
    # Self check-in (member/attendance.py has the verification rules)
    path("member/attendance/me/", attendance_views.my_attendance, name="attendance-me"),
    path("member/attendance/scan/", attendance_views.attendance_scan, name="attendance-scan"),
    path("member/attendance/check/", attendance_views.attendance_check, name="attendance-check"),
    path("member/attendance/correction/", attendance_views.attendance_correction_request, name="attendance-correction"),
    path("member/attendance/corrections/<int:correction_id>/review/", attendance_views.attendance_correction_review,
         name="attendance-correction-review"),
    path("member/settings/", views.settings_home, name="settings-home"),
    path("member/settings/attendance/", attendance_views.attendance_settings, name="attendance-settings"),
    path("member/attendance/settings/", RedirectView.as_view(pattern_name="attendance-settings", permanent=True)),
    path("attendance/display/<str:token>/", attendance_views.attendance_display, name="attendance-display"),
    path("attendance/display/<str:token>/qr.svg", attendance_views.attendance_display_qr, name="attendance-display-qr"),
    path("member/contacts/", views.contacts, name="member-contacts"),
    path("member/contacts/create/", views.contact_create, name="member-contact-create"),
    path("member/contacts/<int:contact_id>/update/", views.contact_update, name="member-contact-update"),
    path("member/contacts/<int:contact_id>/delete/", views.contact_delete, name="member-contact-delete"),
    path("member/contacts/instructions/add/", instruction_views.instruction_add, name="instruction-add"),
    path("member/contacts/instructions/standard/", instruction_views.instruction_load_standard, name="instruction-standard"),
    path("member/contacts/instructions/<int:instruction_id>/update/", instruction_views.instruction_update, name="instruction-update"),
    path("member/contacts/instructions/<int:instruction_id>/delete/", instruction_views.instruction_delete, name="instruction-delete"),
    path("member/contacts/instructions/<int:instruction_id>/move/", instruction_views.instruction_move, name="instruction-move"),

    # Team & Roles (rbac app)
    path("member/team/", rbac_views.team_list, name="member-team"),
    path("member/team/invite/", rbac_views.staff_invite, name="member-team-invite"),
    path("member/team/<int:user_id>/role/", rbac_views.staff_update_role, name="member-team-update-role"),
    path("member/team/<int:user_id>/deactivate/", rbac_views.staff_deactivate, name="member-team-deactivate"),
    path("member/roles/", rbac_views.roles_list, name="member-roles"),
    path("member/roles/<int:role_id>/", rbac_views.role_detail, name="member-role-detail"),
    path("member/roles/<int:role_id>/clone/", rbac_views.role_clone, name="member-role-clone"),
    path("member/activity-log/", rbac_views.activity_log, name="member-activity-log"),

    path("profile/", views.profile, name="profile"),
    path("profile/update-branding/", views.profile_update_branding, name="profile-update-branding"),
    path("settings/language/", views.language_settings, name="language-settings"),

    # Public (no auth)
    path("public/voucher/<str:token>/", views.public_voucher, name="public-voucher"),
]

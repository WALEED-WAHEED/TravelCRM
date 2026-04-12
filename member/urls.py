from django.urls import path
from . import views

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
    path("member/mutamers/", views.mutamers, name="member-mutamers"),
    path("member/bookings/", views.bookings, name="member-bookings"),
    path("member/bookings/save/", views.booking_worksheet_save, name="member-booking-worksheet-save"),
    path("member/bookings/create/", views.booking_create, name="member-booking-create"),
    path("member/bookings/<int:booking_id>/", views.booking_detail, name="member-booking-detail"),
    path("member/bookings/<int:booking_id>/update/", views.booking_update, name="member-booking-update"),
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
    path("member/vouchers/", views.vouchers, name="member-vouchers"),
    path("member/approvals/", views.approvals, name="member-approvals"),
    path("member/ledger/", views.ledger, name="member-ledger"),
    path("member/ledger/report/", views.ledger_report, name="member-ledger-report"),
    path("member/attendance/", views.attendance, name="member-attendance"),
    path("member/attendance/unlock/", views.attendance_unlock, name="member-attendance-unlock"),
    path("member/attendance/password/change/", views.attendance_password_change, name="member-attendance-password-change"),
    path("member/attendance/password/reset/", views.attendance_password_reset, name="member-attendance-password-reset"),
    path("member/attendance/mark/", views.attendance_mark, name="member-attendance-mark"),
    path("member/attendance/delete/", views.attendance_delete, name="member-attendance-delete"),
    path("member/contacts/", views.contacts, name="member-contacts"),
    path("member/contacts/create/", views.contact_create, name="member-contact-create"),
    path("member/contacts/<int:contact_id>/update/", views.contact_update, name="member-contact-update"),
    path("member/contacts/<int:contact_id>/delete/", views.contact_delete, name="member-contact-delete"),
    path("profile/", views.profile, name="profile"),
    path("profile/update-branding/", views.profile_update_branding, name="profile-update-branding"),

    # Public (no auth)
    path("public/voucher/<str:token>/", views.public_voucher, name="public-voucher"),
]

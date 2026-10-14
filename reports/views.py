
from django.http import HttpResponse
from django.shortcuts import redirect, render

from rbac.decorators import permission_required

from . import analytics


@permission_required('reports', 'view')
def reports_home(request):
    """One analytics page: every chart and table follows the same period filter."""
    agency = request.user.agency
    if not agency:
        return redirect('member-dashboard')
    period = analytics.resolve_period(request.GET)
    report = analytics.build_report(agency, period)

    if request.GET.get('export') in ('xlsx', 'csv'):
        from django.utils import translation

        from .export import build_xlsx
        data = build_xlsx(agency, period, report, rtl=translation.get_language_bidi())
        response = HttpResponse(
            data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = (
            f'attachment; filename="report-{period["start"]:%Y%m%d}-{period["end"]:%Y%m%d}.xlsx"'
        )
        return response

    return render(request, 'reports/home.html', {
        'page_title': 'Reports',
        'period': period,
        'report': report,
        'presets': analytics.PRESETS,
        'chart_data': {
            'series': report['series'],
            'breakdowns': report['breakdowns'],
            'granularity': period['granularity'],
        },
    })


def _legacy_redirect(request):
    """Old per-topic report URLs now live on the single Reports page."""
    query = request.GET.copy()
    query.pop('months', None)
    query.pop('export', None)
    target = redirect('reports-home')
    if query:
        target['Location'] += '?' + query.urlencode()
    return target


revenue_report = bookings_report = ledger_summary_report = (
    permission_required('reports', 'view')(_legacy_redirect)
)

from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext
from django.views.decorators.http import require_POST

from member.decorators import member_required

from . import engine
from .models import LANGUAGE_CHOICES, ChatSession, PendingAction


def _session_context(session):
    messages_out = []
    for m in session.messages.exclude(role='tool').order_by('created_at'):
        if not m.content and not (m.tool_payload and m.tool_payload.get('pending_action_id')):
            continue
        entry = {'role': m.role, 'content': m.content, 'created_at': m.created_at.isoformat()}
        pending_id = (m.tool_payload or {}).get('pending_action_id')
        if pending_id:
            pending = PendingAction.objects.filter(pk=pending_id).first()
            if pending:
                entry['pending_action'] = {'id': pending.id, 'summary': pending.summary, 'status': pending.status}
        messages_out.append(entry)
    return messages_out


def fresh_session(agency, user):
    """An empty chat to start typing in. Reuses the user's latest still-empty chat so
    opening the page repeatedly doesn't pile up blank entries in the history."""
    empty = (ChatSession.objects.filter(agency=agency, user=user)
             .annotate(n=Count('messages')).filter(n=0).order_by('-updated_at').first())
    return follow_user_language(empty, user) if empty else ChatSession.objects.create(
        agency=agency, user=user, preferred_language=user.preferred_language)


def follow_user_language(session, user):
    """Chats always answer in the language picked in Settings -> Language
    (blank there = auto-detect from what the user writes)."""
    if session.preferred_language != user.preferred_language:
        session.preferred_language = user.preferred_language
        session.save(update_fields=['preferred_language'])
    return session


@member_required
def chat_home(request):
    """Opens on a new chat; ?session=<id> reopens a past one to carry on from there."""
    agency = request.user.agency
    session_id = request.GET.get('session')
    if session_id and session_id.isdigit():
        session = follow_user_language(
            get_object_or_404(ChatSession, pk=int(session_id), agency=agency, user=request.user), request.user)
    else:
        session = fresh_session(agency, request.user)
    history = list(
        ChatSession.objects.filter(agency=agency, user=request.user)
        .annotate(n=Count('messages')).filter(n__gt=0).order_by('-updated_at')[:40]
    )
    return render(request, 'assistant/chat.html', {
        'page_title': 'AI Assistant',
        'session': session,
        'chat_messages': _session_context(session),
        'history': history,
        'voice_provider': settings.VOICE_PROVIDER,
    })


@member_required
def new_session(request):
    return redirect('assistant-chat')


@member_required
@require_POST
def delete_session(request, session_id):
    session = get_object_or_404(ChatSession, pk=session_id, agency=request.user.agency, user=request.user)
    current = request.POST.get('current') or ''
    deleted_open_chat = current == str(session.pk)
    session.delete()
    # Deleting another chat from the list keeps you in the one you had open.
    if current.isdigit() and not deleted_open_chat:
        return redirect(f"{reverse('assistant-chat')}?session={current}")
    return redirect('assistant-chat')


@member_required
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    agency = request.user.agency
    session_id = request.POST.get('session_id')
    session = get_object_or_404(ChatSession, pk=session_id, agency=agency)
    text = (request.POST.get('message') or '').strip()
    if not text:
        return JsonResponse({'error': gettext('Empty message.')}, status=400)

    result = engine.run_turn(session, request.user, text)
    update_fields = ['updated_at']
    if not session.title:
        session.title = text[:80]
        update_fields.append('title')
    session.save(update_fields=update_fields)

    payload = {'type': result['type'], 'text': result.get('text', '')}
    if result['type'] == 'confirmation_needed':
        pa = result['pending_action']
        payload['pending_action'] = {'id': pa.id, 'summary': pa.summary, 'status': pa.status}
    return JsonResponse(payload)


@member_required
def resolve_action(request, pending_action_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    agency = request.user.agency
    pending = get_object_or_404(PendingAction, pk=pending_action_id, agency=agency)
    if pending.status != 'pending':
        return JsonResponse({'error': gettext('This action has already been resolved.')}, status=400)

    approve = request.POST.get('approve') == 'true'
    result = engine.resolve_pending_action(pending, approve, request.user)
    return JsonResponse({'type': result['type'], 'text': result.get('text', ''), 'status': pending.status})


@member_required
def set_language(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    agency = request.user.agency
    session_id = request.POST.get('session_id')
    session = get_object_or_404(ChatSession, pk=session_id, agency=agency)
    lang = (request.POST.get('language') or '').strip() or None
    valid_codes = {code for code, _ in LANGUAGE_CHOICES}
    if lang is not None and lang not in valid_codes:
        return JsonResponse({'error': gettext('Unknown language code.')}, status=400)
    session.preferred_language = lang
    session.save(update_fields=['preferred_language', 'updated_at'])
    return JsonResponse({'ok': True, 'preferred_language': lang})

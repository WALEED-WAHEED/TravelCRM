"""
Turn orchestration: takes a user message, replays recent history to the
model, executes read tools in a loop, and stops — without writing
anything — the moment the model wants to call a write tool, handing
control back to the human via a PendingAction.
"""
from django.utils import timezone

from travelcrm.languages import SUPPORTED_LANGUAGES

from .llm import AssistantNotConfigured, AssistantProviderError, ToolCall, get_llm_client
from .models import ChatMessage, PendingAction
from .tools import READ_TOOL_FUNCS, READ_TOOL_SPECS, WRITE_TOOL_NAMES, WRITE_TOOL_SPECS, summarize_write_tool_call

MAX_HISTORY_MESSAGES = 20
MAX_TOOL_ROUNDS = 5

LANGUAGE_NAMES = dict(SUPPORTED_LANGUAGES)


def _system_prompt(agency, session):
    language_rule = (
        "Detect the language of the user's most recent message and respond in that same language, "
        "even if it changes between messages in the conversation."
        if not session.preferred_language else
        f"Always respond in {LANGUAGE_NAMES.get(session.preferred_language, session.preferred_language)}, "
        "regardless of what language the user writes in, until told otherwise."
    )
    return (
        f"You are the AI assistant inside a travel agency CRM, helping staff at '{agency.name}'. "
        f"You can answer questions about this agency's own bookings, revenue, ledger, and supplier payables "
        f"using the read tools available to you — always use a tool to get real numbers rather than guessing. "
        f"You can also help draft messages, itinerary text, or explain how a feature works. "
        f"You may propose recording a payment or adding an installment using the write tools, but those are "
        f"never executed by you directly — the user always sees an explicit confirmation card with the exact "
        f"values first, and only their approval executes it. Never claim an action has been completed unless "
        f"a tool result actually confirms it. "
        f"{language_rule} "
        f"Keep answers concise and concrete — cite real figures from tool results, not estimates."
    )


def _history_as_messages(session):
    """Rebuild the generic message list the LLM client expects, from the
    last MAX_HISTORY_MESSAGES persisted rows."""
    rows = list(session.messages.order_by('-created_at')[:MAX_HISTORY_MESSAGES])
    rows.reverse()
    messages = []
    for row in rows:
        if (row.tool_payload or {}).get('error'):
            continue
        if row.role == 'user':
            messages.append({'role': 'user', 'content': row.content})
        elif row.role == 'assistant':
            if row.tool_payload and row.tool_payload.get('tool_calls'):
                tool_calls = [ToolCall(**tc) for tc in row.tool_payload['tool_calls']]
                messages.append({'role': 'assistant', 'tool_calls': tool_calls})
            else:
                messages.append({'role': 'assistant', 'content': row.content})
        elif row.role == 'tool':
            messages.append({'role': 'tool', 'tool_call_id': row.tool_payload.get('tool_call_id', ''), 'name': row.tool_name, 'content': row.tool_payload.get('result', {})})
    return messages


def _error(session, text):
    """Keep the failure visible in the chat history (so a reopened chat never shows
    unanswered questions), flagged so it is not replayed to the model."""
    ChatMessage.objects.create(session=session, agency=session.agency, role='assistant',
                               content=text, tool_payload={'error': True})
    return {'type': 'error', 'text': text}


def run_turn(session, user, user_text):
    """Persists the user's message, drives the tool-calling loop, and
    returns either {'type': 'message', 'text': ...} or
    {'type': 'confirmation_needed', 'pending_action': PendingAction, 'text': ...}."""
    agency = session.agency
    ChatMessage.objects.create(session=session, agency=agency, role='user', content=user_text)

    try:
        client = get_llm_client()
    except AssistantNotConfigured as e:
        return _error(session, str(e))

    system_prompt = _system_prompt(agency, session)
    all_tools = READ_TOOL_SPECS + WRITE_TOOL_SPECS

    for _round in range(MAX_TOOL_ROUNDS):
        messages = _history_as_messages(session)
        try:
            response = client.generate(system_prompt, messages, all_tools)
        except AssistantProviderError as e:
            return _error(session, f"The assistant is temporarily unavailable: {e}")

        if not response.tool_calls:
            ChatMessage.objects.create(session=session, agency=agency, role='assistant', content=response.text)
            return {'type': 'message', 'text': response.text}

        write_call = next((tc for tc in response.tool_calls if tc.name in WRITE_TOOL_NAMES), None)
        if write_call:
            summary = summarize_write_tool_call(agency, write_call.name, write_call.arguments)
            pending = PendingAction.objects.create(
                session=session, agency=agency, tool_name=write_call.name,
                arguments=write_call.arguments, summary=summary, created_by=user,
            )
            note = response.text or "I'd like to do the following — please confirm:"
            ChatMessage.objects.create(
                session=session, agency=agency, role='assistant', content=note,
                tool_payload={'tool_calls': [{'id': write_call.id, 'name': write_call.name, 'arguments': write_call.arguments}], 'pending_action_id': pending.id},
            )
            return {'type': 'confirmation_needed', 'pending_action': pending, 'text': note}

        # All calls this round are read tools — execute them and loop back.
        ChatMessage.objects.create(
            session=session, agency=agency, role='assistant', content=response.text,
            tool_payload={'tool_calls': [{'id': tc.id, 'name': tc.name, 'arguments': tc.arguments} for tc in response.tool_calls]},
        )
        for tc in response.tool_calls:
            func = READ_TOOL_FUNCS.get(tc.name)
            result = func(agency, **tc.arguments) if func else {'error': f"Unknown tool '{tc.name}'."}
            ChatMessage.objects.create(
                session=session, agency=agency, role='tool', tool_name=tc.name,
                tool_payload={'tool_call_id': tc.id, 'result': result},
            )

    return _error(session, "That request needed more tool calls than allowed — try asking a narrower question.")


def resolve_pending_action(pending_action, approve, user):
    from .tools import execute_write_tool

    agency = pending_action.agency
    if not approve:
        pending_action.status = 'rejected'
        pending_action.resolved_at = timezone.now()
        pending_action.save(update_fields=['status', 'resolved_at'])
        ChatMessage.objects.create(session=pending_action.session, agency=agency, role='assistant', content="Okay, I won't make that change.")
        return {'type': 'message', 'text': "Okay, I won't make that change."}

    try:
        result = execute_write_tool(agency, user, pending_action.tool_name, pending_action.arguments)
        pending_action.status = 'executed'
        pending_action.result = result
    except Exception as e:
        pending_action.status = 'failed'
        pending_action.result = {'error': str(e)}
    pending_action.resolved_at = timezone.now()
    pending_action.save(update_fields=['status', 'result', 'resolved_at'])

    if pending_action.status == 'executed':
        text = f"Done — {pending_action.summary}"
    else:
        text = f"That didn't go through: {pending_action.result.get('error', 'unknown error')}"
    ChatMessage.objects.create(
        session=pending_action.session, agency=agency, role='tool', tool_name=pending_action.tool_name,
        tool_payload={'tool_call_id': f'confirm-{pending_action.id}', 'result': pending_action.result},
    )
    ChatMessage.objects.create(session=pending_action.session, agency=agency, role='assistant', content=text)
    return {'type': 'message', 'text': text}

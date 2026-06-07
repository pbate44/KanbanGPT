import traceback
import threading
import docx
import csv
from io import BytesIO, StringIO

from django.conf import settings
from django.utils import timezone

from frontend.models import Card, AIInteraction, CardLogEntry, AIChatMessage, Subtask
from PyPDF2 import PdfReader


STATIC_INSTRUCTIONS = """You are a helpful AI assistant for a project management system.
Answer questions based on the card context provided. If the information isn't in the context,
acknowledge this but provide helpful general advice related to the card's topic.
Keep your answers concise and professional."""

CONTEXT_UPDATE_INSTRUCTIONS = """You are maintaining a compact knowledge summary for a project task card.
You will be given the current summary (may be empty) and recent activity data.
Produce an updated summary that captures all key facts, decisions, blockers, and progress.
Be concise but complete. Do not invent information. Output only the updated summary text, nothing else."""

FREE_MODEL                = "openai/gpt-oss-120b:free"
CONTEXT_COMPRESSION_MODEL = "openai/gpt-oss-120b:free"

LOG_LIMIT          = 20
FILE_LIMIT         = 5
CHAT_HISTORY_LIMIT = 10


def _openrouter_client():
    from openai import OpenAI
    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )


_context_update_in_progress: set = set()
_context_update_lock = threading.Lock()


def _ask_openrouter(model, card_context, question, history=None, web_search=False):
    client = _openrouter_client()
    system_message = (
        f"{STATIC_INSTRUCTIONS}\n\n"
        f"You have access to the following information about a card (task):\n\n{card_context}"
    )
    messages = [{"role": "system", "content": system_message}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    extra_kwargs = {}
    if web_search:
        extra_kwargs["extra_body"] = {"plugins": [{"id": "web"}]}

    response = client.chat.completions.create(
        model=model,
        max_tokens=1500,
        temperature=0.3,
        messages=messages,
        **extra_kwargs,
    )
    prompt_tokens     = response.usage.prompt_tokens     if response.usage else 0
    completion_tokens = response.usage.completion_tokens if response.usage else 0
    return response.choices[0].message.content, prompt_tokens, completion_tokens


def _ask_openrouter_raw(model, system_text, user_text):
    client = _openrouter_client()
    stream = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ],
        stream=True,
    )
    content = ""
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            content += delta.content
    return content


class CardAIAssistant:

    MAX_QUESTION_LENGTH = 2000

    def _needs_context_update(self, card):
        if not card.ai_context_updated_at:
            return (
                CardLogEntry.objects.filter(card=card).exists() or
                card.attachments.exists()
            )
        cutoff = card.ai_context_updated_at
        has_new_logs  = CardLogEntry.objects.filter(card=card, created_at__gt=cutoff).exists()
        has_new_files = card.attachments.filter(upload_date__gt=cutoff).exists()
        return has_new_logs or has_new_files

    def _build_recent_data_snapshot(self, card, include_file_content=False):
        parts = [
            f"CARD TITLE: {card.title}",
            f"CARD DESCRIPTION: {card.description}",
        ]

        subtasks = card.subtasks.all()
        if subtasks:
            parts.append("\nSUBTASKS:")
            for subtask in subtasks:
                status = "complete" if subtask.is_complete else "incomplete"
                due    = f" (due: {subtask.due_date})" if subtask.due_date else ""
                parts.append(f"- [{status}] {subtask.title}{due}")
                if subtask.description:
                    parts.append(f"  {subtask.description}")

        log_entries = list(
            CardLogEntry.objects.filter(card=card).order_by('-created_at')[:LOG_LIMIT]
        )
        log_entries.reverse()
        if log_entries:
            parts.append(f"\nRECENT LOG ENTRIES (last {LOG_LIMIT}):")
            for entry in log_entries:
                timestamp = entry.created_at.strftime("%Y-%m-%d %H:%M")
                parts.append(f"[{timestamp}] ({entry.source}) {entry.text}")

        attachments = list(card.attachments.order_by('-upload_date')[:FILE_LIMIT])
        if attachments:
            if include_file_content:
                parts.append(f"\nRECENT ATTACHED FILES (last {FILE_LIMIT}):")
                for attachment in attachments:
                    try:
                        parts.append(f"\nCONTENT FROM FILE: {attachment.filename}")
                        file_content = get_file_content_from_storage(attachment)
                        if len(file_content) > 5000:
                            parts.append(file_content[:5000] + "... [truncated]")
                        else:
                            parts.append(file_content)
                    except Exception as e:
                        parts.append(f"[Error reading file: {str(e)}]")
            else:
                parts.append("\nATTACHED FILES (select one in chat to include its content):")
                for attachment in attachments:
                    date_str = attachment.upload_date.strftime("%Y-%m-%d") if attachment.upload_date else "unknown"
                    parts.append(f"- {attachment.filename} ({attachment.file_type}, uploaded {date_str})")

        return "\n".join(parts)

    def get_card_context(self, card):
        parts = []
        if card.ai_context:
            parts.append("ACCUMULATED CARD CONTEXT (compressed history):")
            parts.append(card.ai_context)
            parts.append("")
        parts.append(self._build_recent_data_snapshot(card))
        return "\n".join(parts)

    def get_chat_history(self, card_id, session_id=None):
        qs = AIChatMessage.objects.filter(role__in=['user', 'assistant'])
        if session_id:
            qs = qs.filter(session_id=session_id)
        else:
            qs = qs.filter(card__id=card_id)
        recent_messages = qs.order_by('-created_at')[:CHAT_HISTORY_LIMIT]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(list(recent_messages))
        ]

    def _update_context_async(self, card_id):
        with _context_update_lock:
            if card_id in _context_update_in_progress:
                return
            _context_update_in_progress.add(card_id)

        def _run():
            try:
                card        = Card.objects.get(id=card_id)
                recent_data = self._build_recent_data_snapshot(card, include_file_content=True)

                user_text = (
                    f"CURRENT SUMMARY:\n{card.ai_context or '(none yet)'}\n\n"
                    f"RECENT ACTIVITY DATA:\n{recent_data}\n\n"
                    "Please produce an updated compact summary capturing all key facts, "
                    "decisions, progress, and blockers from both the current summary and "
                    "the recent activity data."
                )

                new_context = _ask_openrouter_raw(
                    CONTEXT_COMPRESSION_MODEL, CONTEXT_UPDATE_INSTRUCTIONS, user_text
                )

                Card.objects.filter(id=card_id).update(
                    ai_context=new_context,
                    ai_context_updated_at=timezone.now(),
                )
            except Exception:
                pass
            finally:
                with _context_update_lock:
                    _context_update_in_progress.discard(card_id)

        threading.Thread(target=_run, daemon=True).start()

    def ask_question(self, card_id, question, user_profile, session_id=None, web_search=False, attachment_ids=None):
        if len(question) > self.MAX_QUESTION_LENGTH:
            return (
                f"Your question is too long (max {self.MAX_QUESTION_LENGTH} characters). "
                "Please shorten it and try again."
            )

        model = FREE_MODEL if not user_profile.is_premium() else (user_profile.ai_model or FREE_MODEL)

        try:
            card = Card.objects.get(id=card_id)
        except Card.DoesNotExist:
            return "Card not found."

        card_context = self.get_card_context(card)

        if attachment_ids:
            from frontend.models import CardAttachment
            file_sections = []
            for att_id in attachment_ids:
                try:
                    attachment   = CardAttachment.objects.get(id=att_id, card=card)
                    file_content = get_file_content_from_storage(attachment)
                    if len(file_content) > 8000:
                        file_content = file_content[:8000] + "... [truncated]"
                    file_sections.append(
                        f"FILE ATTACHED TO THIS QUESTION — {attachment.filename}:\n{file_content}"
                    )
                except CardAttachment.DoesNotExist:
                    pass
            if file_sections:
                card_context += "\n\n" + "\n\n".join(file_sections)

        history = self.get_chat_history(card_id, session_id=session_id)

        try:
            response_text, _, _ = _ask_openrouter(
                model, card_context, question, history, web_search=web_search
            )

            AIInteraction.objects.create(card=card, question=question, response=response_text)

            if self._needs_context_update(card):
                self._update_context_async(card_id)

            return response_text

        except Exception as e:
            print(f"Error calling OpenRouter API: {str(e)}")
            print(traceback.format_exc())
            return "There was a problem contacting the AI service. Please try again in a moment."


def get_file_content_from_storage(attachment):
    try:
        with attachment.file.open('rb') as f:
            file_bytes = f.read()
    except Exception as e:
        return f"[Error reading file from storage: {str(e)}]"

    file_type = attachment.file_type.lower()

    try:
        if 'pdf' in file_type:
            pdf = PdfReader(BytesIO(file_bytes))
            return "\n".join(page.extract_text() for page in pdf.pages)
        elif 'word' in file_type or 'docx' in file_type or 'doc' in file_type:
            doc = docx.Document(BytesIO(file_bytes))
            return "\n".join(para.text for para in doc.paragraphs)
        elif 'text' in file_type or 'txt' in file_type:
            return file_bytes.decode('utf-8', errors='replace')
        elif 'csv' in file_type:
            reader = csv.reader(StringIO(file_bytes.decode('utf-8', errors='replace')))
            return "\n".join(",".join(row) for row in reader)
        else:
            return "[Unsupported file type for content extraction]"
    except Exception as e:
        return f"[Error extracting file content: {str(e)}]"

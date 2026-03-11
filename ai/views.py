from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import MentorMessageForm, MentorStartForm, StudioForm
from .models import AIDraft, AtlasDocument, MentorMessage, MentorThread, RiskSignal
from .services import atlas as atlas_service
from .services import radar as radar_service
from .services import studio as studio_service
from .services.openai_client import OpenAIError, create_response, extract_output_text, is_configured


def _staff_required(user):
    return user.is_staff or user.is_superuser


def _build_context_block(documents):
    if not documents:
        return "Nenhum conteudo do Atlas foi encontrado para esta pergunta."
    lines = ["Contexto Atlas:"]
    for index, doc in enumerate(documents, start=1):
        lines.append(f"[{index}] {doc.title} :: {doc.content}")
    return "\n".join(lines)


def _mentor_system_prompt(mode):
    return (
        "Voce e o Mentor IA do CursosOnline."
        " Ajude o aluno com clareza, sem respostas genericas."
        " Explique passo a passo, cite duvidas e proponha uma micro-atividade."
        " Se faltar informacao, faca ate 2 perguntas objetivas."
        " Responda em portugues do Brasil."
    )


def _mentor_reply(thread, user_message):
    docs = atlas_service.search_atlas(user_message, course=thread.course)
    citations = [
        {"title": doc.title, "url": doc.source_url, "id": doc.id}
        for doc in docs
    ]
    if not is_configured():
        fallback = (
            "IA indisponivel. Configure OPENAI_API_KEY para respostas completas.\n"
            "Sugestao: revise os materiais do curso e tente novamente."
        )
        return fallback, citations

    context_block = _build_context_block(docs)
    input_messages = [
        {
            "role": "system",
            "content": [
                {"type": "input_text", "text": _mentor_system_prompt(thread.mode)}
            ],
        }
    ]

    history = list(thread.messages.order_by("created_at"))[-6:]
    if history and history[-1].role == "user" and history[-1].content.strip() == user_message.strip():
        history = history[:-1]
    for msg in history:
        input_messages.append(
            {
                "role": msg.role,
                "content": [{"type": "input_text", "text": msg.content}],
            }
        )

    user_block = f"Pergunta: {user_message}\n\n{context_block}"
    input_messages.append(
        {"role": "user", "content": [{"type": "input_text", "text": user_block}]}
    )

    try:
        response = create_response(input_messages)
        text = extract_output_text(response)
        return text or "", citations
    except OpenAIError as exc:
        return f"Erro ao chamar IA: {exc}", citations


@login_required
def mentor_home(request):
    threads = MentorThread.objects.filter(user=request.user)
    atlas_count = AtlasDocument.objects.filter(active=True).count()
    form = MentorStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        title = form.cleaned_data.get("title") or f"Sessao {datetime.now():%d/%m %H:%M}"
        course = form.cleaned_data.get("course")
        message = form.cleaned_data.get("message")
        thread = MentorThread.objects.create(
            user=request.user,
            course=course,
            title=title,
            last_used=timezone.now(),
        )
        MentorMessage.objects.create(
            thread=thread, role="user", content=message or ""
        )
        reply_text, citations = _mentor_reply(thread, message)
        MentorMessage.objects.create(
            thread=thread, role="assistant", content=reply_text, citations=citations
        )
        return redirect("ai:mentor_thread", pk=thread.pk)

    context = {
        "threads": threads,
        "form": form,
        "atlas_count": atlas_count,
    }
    return render(request, "ai/mentor_home.html", context)


@login_required
def mentor_thread(request, pk):
    thread = get_object_or_404(MentorThread, pk=pk, user=request.user)
    thread_messages = thread.messages.order_by("created_at")
    atlas_count = AtlasDocument.objects.filter(active=True).count()
    form = MentorMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.cleaned_data.get("message")
        MentorMessage.objects.create(thread=thread, role="user", content=message)
        reply_text, citations = _mentor_reply(thread, message)
        MentorMessage.objects.create(
            thread=thread, role="assistant", content=reply_text, citations=citations
        )
        thread.last_used = timezone.now()
        thread.save(update_fields=["last_used", "updated_at"])
        return redirect("ai:mentor_thread", pk=thread.pk)

    context = {
        "thread": thread,
        "thread_messages": thread_messages,
        "form": form,
        "atlas_count": atlas_count,
    }
    return render(request, "ai/mentor_thread.html", context)


@user_passes_test(_staff_required)
def atlas_rebuild(request):
    if request.method == "POST":
        atlas_service.build_atlas(embed=True)
        messages.success(request, "Atlas reconstruido com sucesso.")
        return redirect("ai:atlas_rebuild")
    atlas_count = AtlasDocument.objects.filter(active=True).count()
    return render(
        request,
        "ai/atlas_rebuild.html",
        {"atlas_count": atlas_count},
    )


@user_passes_test(_staff_required)
def radar_dashboard(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "analyze":
            radar_service.compute_risk_signals()
            messages.success(request, "Analise concluida. Sinais atualizados.")
        elif action == "review":
            signal_id = request.POST.get("signal_id")
            signal = get_object_or_404(RiskSignal, pk=signal_id)
            signal.status = "reviewed"
            signal.reviewed_at = timezone.now()
            signal.reviewed_by = request.user
            signal.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            messages.success(request, "Sinal marcado como revisado.")
        return redirect("ai:radar_dashboard")

    signals = RiskSignal.objects.select_related("user", "course")
    return render(
        request,
        "ai/radar_dashboard.html",
        {"signals": signals},
    )


@user_passes_test(_staff_required)
def studio(request):
    form = StudioForm(request.POST or None)
    drafts = AIDraft.objects.select_related("course", "created_by")

    if request.method == "POST":
        action = request.POST.get("action", "generate")
        if action == "generate" and form.is_valid():
            payload = form.cleaned_data
            output, _response = studio_service.generate_draft(payload)
            AIDraft.objects.create(
                course=payload.get("course"),
                created_by=request.user,
                draft_type=payload.get("draft_type"),
                title=payload.get("title") or payload.get("draft_type"),
                input_context={
                    "audience": payload.get("audience"),
                    "goals": payload.get("goals"),
                    "constraints": payload.get("constraints"),
                    "tone": payload.get("tone"),
                    "source_material": payload.get("source_material"),
                },
                output=output,
            )
            messages.success(request, "Rascunho criado.")
            return redirect("ai:studio")
        if action == "approve":
            draft_id = request.POST.get("draft_id")
            draft = get_object_or_404(AIDraft, pk=draft_id)
            draft.status = "approved"
            draft.reviewed_at = timezone.now()
            draft.reviewed_by = request.user
            draft.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            messages.success(request, "Rascunho aprovado.")
            return redirect("ai:studio")
        if action == "archive":
            draft_id = request.POST.get("draft_id")
            draft = get_object_or_404(AIDraft, pk=draft_id)
            draft.status = "archived"
            draft.reviewed_at = timezone.now()
            draft.reviewed_by = request.user
            draft.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            messages.success(request, "Rascunho arquivado.")
            return redirect("ai:studio")

    return render(
        request,
        "ai/studio.html",
        {"form": form, "drafts": drafts},
    )



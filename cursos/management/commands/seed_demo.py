import base64
import random
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import ResetarSenha
from accounts.utils import generate_hash_key
from ai.models import (
    AIDraft,
    AtlasDocument,
    LearningEvent,
    MentorMessage,
    MentorThread,
    RiskSignal,
)
from ai.services.openai_client import OpenAIError, create_image, extract_image_results, is_configured
from cursos.models import Aulas, Anuncios, Comentarios, Cursos, Enrollment, Materiais
from forum.models import Reply, Thread

COURSE_SEEDS = [
    {
        "pt": {
            "nome": "Fundamentos de Python",
            "descricao": "Bases de sintaxe, logica e boas praticas.",
            "sobre": "Consolide conceitos essenciais com exercicios guiados.",
        },
        "en": {
            "nome": "Python Foundations",
            "descricao": "Core syntax, logic, and best practices.",
            "sobre": "Build essential skills with guided practice.",
        },
    },
    {
        "pt": {
            "nome": "Analise de Dados",
            "descricao": "Fluxos praticos com dados reais.",
            "sobre": "Da importacao a visualizacao com foco em decisoes.",
        },
        "en": {
            "nome": "Data Analysis",
            "descricao": "Practical workflows with real data.",
            "sobre": "From ingest to visualization with decision focus.",
        },
    },
    {
        "pt": {
            "nome": "Front-end Moderno",
            "descricao": "Interfaces responsivas e acessiveis.",
            "sobre": "Construa layouts consistentes com boas praticas.",
        },
        "en": {
            "nome": "Modern Front-end",
            "descricao": "Responsive, accessible interfaces.",
            "sobre": "Craft consistent layouts with strong patterns.",
        },
    },
    {
        "pt": {
            "nome": "IA Aplicada",
            "descricao": "Automacoes e copilotos inteligentes.",
            "sobre": "Aprenda a desenhar fluxos assistidos por IA.",
        },
        "en": {
            "nome": "Applied AI",
            "descricao": "Automations and smart copilots.",
            "sobre": "Design AI-assisted learning workflows.",
        },
    },
    {
        "pt": {
            "nome": "Produto Digital",
            "descricao": "Da ideia ao MVP com estrategia.",
            "sobre": "Estruture proposta, validacao e entrega.",
        },
        "en": {
            "nome": "Digital Product",
            "descricao": "From idea to MVP with strategy.",
            "sobre": "Structure value prop, validation, and delivery.",
        },
    },
]

LESSON_SEEDS = [
    {
        "pt": {"nome": "Introducao e setup", "descricao": "Configurar ambiente e primeiros passos."},
        "en": {"nome": "Introduction and setup", "descricao": "Setup environment and first steps."},
    },
    {
        "pt": {"nome": "Fluxo pratico", "descricao": "Executar o fluxo principal com exemplos."},
        "en": {"nome": "Practical flow", "descricao": "Run the main flow with examples."},
    },
    {
        "pt": {"nome": "Projeto guiado", "descricao": "Aplicar conceitos em um mini projeto."},
        "en": {"nome": "Guided project", "descricao": "Apply concepts in a mini project."},
    },
    {
        "pt": {"nome": "Otimizacao", "descricao": "Melhorias e ajustes finos."},
        "en": {"nome": "Optimization", "descricao": "Improvements and fine tuning."},
    },
    {
        "pt": {"nome": "Proximos passos", "descricao": "Direcoes para aprofundamento."},
        "en": {"nome": "Next steps", "descricao": "Directions for deeper study."},
    },
]

MATERIAL_SEEDS = [
    {
        "pt": {"nome": "Resumo da aula", "embutido": "<p>Resumo dos principais pontos.</p>"},
        "en": {"nome": "Lesson summary", "embutido": "<p>Summary of key takeaways.</p>"},
    },
    {
        "pt": {"nome": "Checklist", "embutido": "<p>Checklist de revisao.</p>"},
        "en": {"nome": "Checklist", "embutido": "<p>Review checklist.</p>"},
    },
    {
        "pt": {"nome": "Guia rapido", "embutido": "<p>Guia rapido para consulta.</p>"},
        "en": {"nome": "Quick guide", "embutido": "<p>Quick reference guide.</p>"},
    },
    {
        "pt": {"nome": "Exemplo aplicado", "embutido": "<p>Exemplo aplicado ao contexto.</p>"},
        "en": {"nome": "Applied example", "embutido": "<p>Example applied to context.</p>"},
    },
    {
        "pt": {"nome": "Recursos extras", "embutido": "<p>Links e materiais adicionais.</p>"},
        "en": {"nome": "Extra resources", "embutido": "<p>Links and additional materials.</p>"},
    },
]

ANNOUNCEMENT_SEEDS = [
    {
        "pt": {"titulo": "Boas-vindas ao curso", "conteudo": "Estamos animados com sua chegada."},
        "en": {"titulo": "Welcome to the course", "conteudo": "We are excited to have you here."},
    },
    {
        "pt": {"titulo": "Novo material liberado", "conteudo": "Confira a aula mais recente."},
        "en": {"titulo": "New material available", "conteudo": "Check the latest lesson."},
    },
    {
        "pt": {"titulo": "Desafio da semana", "conteudo": "Aplique o que aprendeu em um desafio."},
        "en": {"titulo": "Weekly challenge", "conteudo": "Apply what you learned in a challenge."},
    },
    {
        "pt": {"titulo": "Sessao ao vivo", "conteudo": "Participe da sessao ao vivo de duvidas."},
        "en": {"titulo": "Live session", "conteudo": "Join the live Q&A session."},
    },
    {
        "pt": {"titulo": "Atualizacao do curso", "conteudo": "Novas melhorias e exemplos."},
        "en": {"titulo": "Course update", "conteudo": "New improvements and examples."},
    },
]

COMMENT_SEEDS = [
    {
        "pt": "Conteudo direto e facil de seguir.",
        "en": "Clear content, easy to follow.",
    },
    {
        "pt": "Gostei do ritmo e dos exemplos.",
        "en": "Loved the pace and examples.",
    },
    {
        "pt": "Poderia ter mais exercicios praticos.",
        "en": "Could use more hands-on exercises.",
    },
    {
        "pt": "Boa explicacao do conceito principal.",
        "en": "Great explanation of the core concept.",
    },
    {
        "pt": "Material bem organizado.",
        "en": "Well-organized materials.",
    },
]

THREAD_SEEDS = [
    {
        "pt": {"titulo": "Como revisar para a prova?", "mensagem": "Quais tecnicas funcionam melhor?"},
        "en": {"titulo": "How to review for the exam?", "mensagem": "Which techniques work best?"},
    },
    {
        "pt": {"titulo": "Dicas para praticar todos os dias", "mensagem": "Como manter consistencia?"},
        "en": {"titulo": "Tips to practice daily", "mensagem": "How to stay consistent?"},
    },
    {
        "pt": {"titulo": "Ferramentas recomendadas", "mensagem": "Quais ferramentas voces usam?"},
        "en": {"titulo": "Recommended tools", "mensagem": "Which tools do you use?"},
    },
    {
        "pt": {"titulo": "Projeto final", "mensagem": "Como planejar o projeto final?"},
        "en": {"titulo": "Final project", "mensagem": "How to plan the final project?"},
    },
    {
        "pt": {"titulo": "Feedback sobre o curso", "mensagem": "O que pode melhorar?"},
        "en": {"titulo": "Course feedback", "mensagem": "What could be improved?"},
    },
]

REPLY_SEEDS = [
    {
        "pt": "Comece com revisoes curtas e frequentes.",
        "en": "Start with short, frequent reviews.",
    },
    {
        "pt": "Monte uma rotina pequena e sustentavel.",
        "en": "Build a small, sustainable routine.",
    },
    {
        "pt": "Use checklists e checkpoints semanais.",
        "en": "Use checklists and weekly checkpoints.",
    },
    {
        "pt": "Divida o projeto em entregas pequenas.",
        "en": "Break the project into small deliverables.",
    },
    {
        "pt": "Colete feedback e ajuste o ritmo.",
        "en": "Collect feedback and adjust the pace.",
    },
]

AI_PROMPTS = [
    "Clean illustration of an online course on {course}, soft gradient background, modern learning vibe.",
    "Isometric scene of a learning workspace related to {course}, warm lighting, minimal elements.",
    "Abstract cover art for a course titled '{course}', layered shapes, professional palette.",
    "Digital classroom illustration inspired by {course}, friendly and modern style.",
    "Creative flat illustration representing {course}, balanced composition, subtle texture.",
]

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _apply_updates(instance, updates, overwrite=False):
    changed_fields = []
    for field, value in updates.items():
        if value is None:
            continue
        current = getattr(instance, field, None)
        should_update = overwrite or current in (None, "")
        if should_update and current != value:
            setattr(instance, field, value)
            changed_fields.append(field)
    if changed_fields:
        instance.save(update_fields=changed_fields)


def _collect_static_images(static_dir):
    if not static_dir.exists():
        return []
    images = []
    for path in static_dir.iterdir():
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            if path.stat().st_size < 10_000:
                continue
            images.append(path)
    return sorted(images)


def _assign_course_images(courses, images, media_dir):
    media_dir.mkdir(parents=True, exist_ok=True)
    if not images:
        return
    for idx, course in enumerate(courses, start=1):
        src = images[(idx - 1) % len(images)]
        dest_name = f"seed-{course.slug}-{src.name}"
        dest_path = media_dir / dest_name
        if not dest_path.exists():
            shutil.copyfile(src, dest_path)
        new_rel = str(Path("cursos/imagens") / dest_name)
        if not course.imagem or course.imagem.name.endswith("course-image.png"):
            course.imagem.name = new_rel
            course.save(update_fields=["imagem"])


def _generate_ai_image_bytes(prompt, model=None):
    response = create_image(
        prompt,
        model=model,
        size=getattr(settings, "OPENAI_IMAGE_SIZE", None),
        quality=getattr(settings, "OPENAI_IMAGE_QUALITY", None),
        background=getattr(settings, "OPENAI_IMAGE_BACKGROUND", None),
    )
    results = extract_image_results(response)
    if not results:
        return None
    return base64.b64decode(results[0])


class Command(BaseCommand):
    help = "Seed demo data for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="How many records to create per main entity (default: 5).",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="demo12345",
            help="Password for demo users (default: demo12345).",
        )
        parser.add_argument(
            "--ai-images",
            action="store_true",
            help="Generate AI images for some courses (requires OpenAI key).",
        )
        parser.add_argument(
            "--ai-limit",
            type=int,
            default=0,
            help="Limit how many AI images to generate (0 = all seeded courses).",
        )
        parser.add_argument(
            "--ai-model",
            type=str,
            default="",
            help="Override the model used for AI images (default: OPENAI_IMAGE_TOOL_MODEL).",
        )

    def handle(self, *args, **options):
        count = max(1, options["count"])
        password = options["password"]
        ai_images = options["ai_images"]
        ai_limit = max(0, options["ai_limit"])
        ai_model = (options.get("ai_model") or "").strip() or None
        User = get_user_model()

        media_root = Path(settings.MEDIA_ROOT or (Path(settings.BASE_DIR) / "media"))
        media_course_dir = media_root / "cursos" / "imagens"
        static_img_dir = Path(settings.BASE_DIR) / "static" / "img"

        default_image_rel = "cursos/imagens/course-image.png"
        default_image_path = media_root / default_image_rel
        source_image_path = static_img_dir / "course-image.png"
        if source_image_path.exists():
            default_image_path.parent.mkdir(parents=True, exist_ok=True)
            if not default_image_path.exists():
                shutil.copyfile(source_image_path, default_image_path)

        with transaction.atomic():
            users = []
            for i in range(1, count + 1):
                username = f"demo{i}"
                email = f"demo{i}@example.com"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": email},
                )
                if created:
                    user.set_password(password)
                    user.save()
                users.append(user)

            staff, created = User.objects.get_or_create(
                username="staff",
                defaults={"email": "staff@example.com", "is_staff": True},
            )
            if created:
                staff.set_password(password)
                staff.save()

            highlight_count = max(1, min(3, count))
            courses = []
            for i in range(1, count + 1):
                seed = COURSE_SEEDS[(i - 1) % len(COURSE_SEEDS)]
                suffix = f" {i}" if count > len(COURSE_SEEDS) else ""
                name_pt = f"{seed['pt']['nome']}{suffix}"
                name_en = f"{seed['en']['nome']}{suffix}"
                slug = slugify(name_pt)
                course_defaults = {
                    "nome": name_pt,
                    "nome_en": name_en,
                    "descricao": seed["pt"]["descricao"],
                    "descricao_en": seed["en"]["descricao"],
                    "sobre": seed["pt"]["sobre"],
                    "sobre_en": seed["en"]["sobre"],
                    "data_inicial": timezone.now().date(),
                }
                course, _created = Cursos.objects.get_or_create(
                    slug=slug,
                    defaults=course_defaults,
                )
                _apply_updates(course, course_defaults)
                is_featured = i <= highlight_count
                if course.destaque != is_featured:
                    course.destaque = is_featured
                    course.save(update_fields=["destaque"])
                if not course.imagem and default_image_path.exists():
                    course.imagem.name = default_image_rel
                    course.save(update_fields=["imagem"])
                courses.append(course)

            images = _collect_static_images(static_img_dir)
            _assign_course_images(courses, images, media_course_dir)

            lessons = []
            for i in range(1, count + 1):
                course = courses[(i - 1) % len(courses)]
                seed = LESSON_SEEDS[(i - 1) % len(LESSON_SEEDS)]
                lesson, _created = Aulas.objects.get_or_create(
                    curso=course,
                    numero=i,
                    defaults={
                        "nome": seed["pt"]["nome"],
                        "nome_en": seed["en"]["nome"],
                        "descricao": seed["pt"]["descricao"],
                        "descricao_en": seed["en"]["descricao"],
                        "inicio": timezone.now().date(),
                    },
                )
                _apply_updates(
                    lesson,
                    {
                        "nome_en": seed["en"]["nome"],
                        "descricao_en": seed["en"]["descricao"],
                    },
                )
                lessons.append(lesson)

            for i in range(1, count + 1):
                lesson = lessons[(i - 1) % len(lessons)]
                seed = MATERIAL_SEEDS[(i - 1) % len(MATERIAL_SEEDS)]
                material, _created = Materiais.objects.get_or_create(
                    aula=lesson,
                    nome=seed["pt"]["nome"],
                    defaults={
                        "nome_en": seed["en"]["nome"],
                        "embutido": seed["pt"]["embutido"],
                        "embutido_en": seed["en"]["embutido"],
                    },
                )
                _apply_updates(
                    material,
                    {
                        "nome_en": seed["en"]["nome"],
                        "embutido_en": seed["en"]["embutido"],
                    },
                )

            announcements = []
            for i in range(1, count + 1):
                course = courses[(i - 1) % len(courses)]
                seed = ANNOUNCEMENT_SEEDS[(i - 1) % len(ANNOUNCEMENT_SEEDS)]
                anuncio, _created = Anuncios.objects.get_or_create(
                    curso=course,
                    titulo=seed["pt"]["titulo"],
                    defaults={
                        "titulo_en": seed["en"]["titulo"],
                        "conteudo": seed["pt"]["conteudo"],
                        "conteudo_en": seed["en"]["conteudo"],
                    },
                )
                _apply_updates(
                    anuncio,
                    {
                        "titulo_en": seed["en"]["titulo"],
                        "conteudo_en": seed["en"]["conteudo"],
                    },
                )
                announcements.append(anuncio)

            for i in range(1, count + 1):
                anuncio = announcements[(i - 1) % len(announcements)]
                user = users[(i - 1) % len(users)]
                seed = COMMENT_SEEDS[(i - 1) % len(COMMENT_SEEDS)]
                comentario, _created = Comentarios.objects.get_or_create(
                    anuncio=anuncio,
                    usuario=user,
                    comentario=seed["pt"],
                )
                _apply_updates(comentario, {"comentario_en": seed["en"]})

            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                course = courses[(i - 1) % len(courses)]
                enrollment, _created = Enrollment.objects.get_or_create(
                    usuario=user,
                    curso=course,
                )
                if enrollment.status != 1:
                    enrollment.status = 1
                    enrollment.save(update_fields=["status"])

            threads = []
            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                seed = THREAD_SEEDS[(i - 1) % len(THREAD_SEEDS)]
                title = seed["pt"]["titulo"]
                slug = slugify(f"{title}-{i}")
                thread, _created = Thread.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "title": title,
                        "title_en": seed["en"]["titulo"],
                        "body": seed["pt"]["mensagem"],
                        "body_en": seed["en"]["mensagem"],
                        "author": user,
                    },
                )
                _apply_updates(
                    thread,
                    {
                        "title_en": seed["en"]["titulo"],
                        "body_en": seed["en"]["mensagem"],
                    },
                )
                thread.tags.add("demo", f"topic-{i}")
                threads.append(thread)

            for i in range(1, count + 1):
                thread = threads[(i - 1) % len(threads)]
                user = users[(i - 1) % len(users)]
                seed = REPLY_SEEDS[(i - 1) % len(REPLY_SEEDS)]
                reply, _created = Reply.objects.get_or_create(
                    thread=thread,
                    author=user,
                    reply=seed["pt"],
                )
                _apply_updates(reply, {"reply_en": seed["en"]})

            mentor_threads = []
            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                course = courses[(i - 1) % len(courses)]
                thread, _created = MentorThread.objects.get_or_create(
                    user=user,
                    title=f"Mentor Session {i}",
                    defaults={
                        "course": course,
                        "mode": "study",
                        "last_used": timezone.now(),
                    },
                )
                mentor_threads.append(thread)

            for i in range(1, count + 1):
                thread = mentor_threads[(i - 1) % len(mentor_threads)]
                MentorMessage.objects.get_or_create(
                    thread=thread,
                    role="user",
                    content=f"User question {i} for {thread.title}.",
                )
                MentorMessage.objects.get_or_create(
                    thread=thread,
                    role="assistant",
                    content=f"Assistant answer {i} for {thread.title}.",
                )

            for i in range(1, count + 1):
                course = courses[(i - 1) % len(courses)]
                AIDraft.objects.get_or_create(
                    course=course,
                    created_by=staff,
                    draft_type="quiz",
                    title=f"Quiz Draft {i}",
                    defaults={
                        "input_context": {
                            "audience": "Beginners",
                            "goals": "Practice",
                            "constraints": "5 questions",
                            "tone": "direct",
                            "source_material": "Course notes",
                        },
                        "output": f"Draft content for Quiz {i}.",
                    },
                )

            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                course = courses[(i - 1) % len(courses)]
                LearningEvent.objects.get_or_create(
                    user=user,
                    course=course,
                    event_type="view_course",
                    defaults={"metadata": {"seed": True}},
                )

            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                course = courses[(i - 1) % len(courses)]
                RiskSignal.objects.get_or_create(
                    user=user,
                    course=course,
                    label=f"Low engagement {i}",
                    defaults={
                        "score": 2.5,
                        "evidence": {"seed": True},
                        "notes": "Seeded for demo.",
                    },
                )

            for i in range(1, count + 1):
                course = courses[(i - 1) % len(courses)]
                AtlasDocument.objects.get_or_create(
                    source_type="curso",
                    source_id=course.id,
                    defaults={
                        "course": course,
                        "title": course.nome,
                        "content": course.sobre or course.descricao,
                        "source_url": f"/cursos/{course.slug}/",
                        "source_hash": f"seed-{course.id}",
                        "embedding_model": "seed",
                    },
                )

            for i in range(1, count + 1):
                user = users[(i - 1) % len(users)]
                key = generate_hash_key(user.username)
                ResetarSenha.objects.get_or_create(
                    user=user,
                    key=key,
                    defaults={"confirmed": False},
                )

        if ai_images:
            if not is_configured():
                self.stdout.write(self.style.WARNING("OPENAI_API_KEY not configured. Skipping AI images."))
            else:
                limit = ai_limit or len(courses)
                for course in courses[:limit]:
                    prompt = random.choice(AI_PROMPTS).format(course=course.nome_en or course.nome)
                    try:
                        image_bytes = _generate_ai_image_bytes(prompt, model=ai_model)
                    except OpenAIError as exc:
                        message = str(exc)
                        self.stdout.write(self.style.WARNING(f"OpenAI image error: {message}"))
                        if "verify" in message.lower() and "organization" in message.lower():
                            self.stdout.write(self.style.WARNING("Organization verification is required to generate images with this model."))
                            break
                        continue
                    if not image_bytes:
                        self.stdout.write(self.style.WARNING("No image data returned for prompt."))
                        continue
                    media_course_dir.mkdir(parents=True, exist_ok=True)
                    dest_name = f"ai-{course.slug}.png"
                    dest_path = media_course_dir / dest_name
                    dest_path.write_bytes(image_bytes)
                    course.imagem.name = str(Path("cursos/imagens") / dest_name)
                    course.save(update_fields=["imagem"])

        self.stdout.write(self.style.SUCCESS("Demo data generated successfully."))

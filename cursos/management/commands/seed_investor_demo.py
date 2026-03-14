import base64
import hashlib
import io
import math
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
import urllib.error
import urllib.request

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

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageFilter = ImageFont = ImageOps = None


@dataclass(frozen=True)
class CourseDef:
    key: str
    pt_nome: str
    en_nome: str
    pt_tagline: str
    en_tagline: str
    hours: int
    prereqs_pt: str
    prereqs_en: str
    audience_pt: str
    audience_en: str
    outcomes_pt: list[str]  # 4 items
    outcomes_en: list[str]  # 4 items
    capstone_pt: str
    capstone_en: str
    modules_pt: list[str]  # 6 items
    modules_en: list[str]  # 6 items
    faq_pt: list[str]  # 4 items
    faq_en: list[str]  # 4 items


def _now_stamp():
    return timezone.now().strftime("%Y%m%d-%H%M%S")


def _stable_int(s: str) -> int:
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)


def _backup_sqlite_db():
    db_path = Path(settings.DATABASES["default"]["NAME"])
    if not db_path.exists():
        return None
    backup_dir = Path(settings.BASE_DIR) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"db.sqlite3.backup-{_now_stamp()}"
    shutil.copy2(db_path, dest)
    return dest


def _purge_everything_except_users():
    MentorMessage.objects.all().delete()
    MentorThread.objects.all().delete()
    LearningEvent.objects.all().delete()
    RiskSignal.objects.all().delete()
    AIDraft.objects.all().delete()
    AtlasDocument.objects.all().delete()

    Reply.objects.all().delete()
    Thread.objects.all().delete()

    Comentarios.objects.all().delete()
    Anuncios.objects.all().delete()
    Materiais.objects.all().delete()
    Aulas.objects.all().delete()
    Enrollment.objects.all().delete()
    Cursos.objects.all().delete()

    ResetarSenha.objects.all().delete()

    try:
        from taggit.models import TaggedItem, Tag
    except Exception:
        TaggedItem = Tag = None
    if TaggedItem is not None:
        TaggedItem.objects.all().delete()
    if Tag is not None:
        Tag.objects.all().delete()


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


def _hsl_to_rgb(h, s, l):
    c = (1 - abs(2 * l - 1)) * s
    hp = (h / 60.0) % 6
    x = c * (1 - abs(hp % 2 - 1))
    r1, g1, b1 = 0, 0, 0
    if 0 <= hp < 1:
        r1, g1, b1 = c, x, 0
    elif 1 <= hp < 2:
        r1, g1, b1 = x, c, 0
    elif 2 <= hp < 3:
        r1, g1, b1 = 0, c, x
    elif 3 <= hp < 4:
        r1, g1, b1 = 0, x, c
    elif 4 <= hp < 5:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    m = l - c / 2
    return (int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255))


def _pick_palette(key: str):
    n = _stable_int(key) % 360
    primary = _hsl_to_rgb(n, 0.82, 0.46)
    accent = _hsl_to_rgb((n + 40) % 360, 0.85, 0.56)
    deep = _hsl_to_rgb((n + 12) % 360, 0.65, 0.16)
    return primary, accent, deep


def _load_font(size: int, bold: bool = False):
    if ImageFont is None:
        return None
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _draw_soft_gradient(size, a, b):
    if Image is None:
        return None
    w, h = size
    base = Image.new("RGB", (w, h), a)
    top = Image.new("RGB", (w, h), b)
    mask = Image.new("L", (w, h))
    px = mask.load()
    for y in range(h):
        t = y / max(1, h - 1)
        t = 0.5 - 0.5 * math.cos(math.pi * t)
        v = int(max(0, min(255, t * 255)))
        for x in range(w):
            px[x, y] = v
    return Image.composite(top, base, mask)


def _generate_hd_cover(course: Cursos, out_dir: Path, *, brand: str = "CursosOnline"):
    if Image is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"seed-hd-{course.slug}.png"
    dest_path = out_dir / dest_name

    seed = _stable_int(course.slug) % (2**32)
    rnd = random.Random(seed)

    primary, accent, deep = _pick_palette(course.slug)
    bg = _draw_soft_gradient((1920, 1080), deep, primary).convert("RGBA")

    vignette = Image.new("L", bg.size, 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((-420, -280, 1920 + 420, 1080 + 280), fill=210)
    vignette = vignette.filter(ImageFilter.GaussianBlur(90))
    bg.putalpha(vignette)

    img = bg.convert("RGBA")
    d = ImageDraw.Draw(img)

    for i in range(9):
        x0 = rnd.randint(-220, 1580)
        y0 = rnd.randint(-220, 900)
        x1 = x0 + rnd.randint(520, 1280)
        y1 = y0 + rnd.randint(260, 820)
        alpha = rnd.randint(22, 62)
        color = accent if i % 2 == 0 else primary
        d.rounded_rectangle([x0, y0, x1, y1], radius=rnd.randint(40, 120), fill=(*color, alpha))

    title = course.nome_en or course.nome
    subtitle = "Featured / Destaque" if course.destaque else "IT / Tech"

    font_title = _load_font(86, bold=True)
    font_sub = _load_font(34, bold=False)
    font_brand = _load_font(26, bold=True)

    x, y = 96, 520
    block_w, block_h = 1120, 380
    d.rounded_rectangle([x, y, x + block_w, y + block_h], radius=42, fill=(10, 14, 18, 168))
    d.rounded_rectangle([x + 18, y + 18, x + block_w - 18, y + block_h - 18], radius=34, outline=(255, 255, 255, 28), width=2)

    if font_brand:
        d.text((x + 44, y + 38), brand.upper(), font=font_brand, fill=(255, 255, 255, 200))

    chip_x, chip_y = x + 44, y + 88
    d.rounded_rectangle([chip_x, chip_y, chip_x + 420, chip_y + 44], radius=22, fill=(*accent, 200))
    if font_sub:
        d.text((chip_x + 18, chip_y + 8), subtitle, font=font_sub, fill=(15, 18, 22, 240))

    def _wrap(text, max_chars):
        words = text.split()
        lines, cur = [], []
        for w in words:
            nxt = (" ".join(cur + [w])).strip()
            if len(nxt) <= max_chars:
                cur.append(w)
            else:
                if cur:
                    lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))
        return lines[:2]

    ty = y + 160
    for line in _wrap(title, 26):
        if font_title:
            d.text((x + 44, ty), line, font=font_title, fill=(255, 255, 255, 245))
        ty += 96

    hint = "Projeto prático + materiais + fórum + mentor IA"
    if font_sub:
        d.text((x + 44, y + block_h - 56), hint, font=font_sub, fill=(255, 255, 255, 160))

    img.convert("RGB").save(dest_path, format="PNG", optimize=True)
    return dest_name


def _generate_ai_image_bytes(prompt, model=None):
    response = create_image(
        prompt,
        model=model,
        size=getattr(settings, "OPENAI_IMAGE_SIZE", "1792x1024"),
        quality=getattr(settings, "OPENAI_IMAGE_QUALITY", "high"),
        background=getattr(settings, "OPENAI_IMAGE_BACKGROUND", None),
    )
    results = extract_image_results(response)
    if not results:
        return None
    return base64.b64decode(results[0])


def _build_sobre(defn: CourseDef, *, lang: str) -> str:
    if lang == "en":
        outcomes = "\n".join(f"- {x}" for x in defn.outcomes_en)
        return (
            f"Goal: {defn.en_tagline}\n\n"
            f"You will learn:\n{outcomes}\n\n"
            f"Capstone: {defn.capstone_en}\n"
            f"Audience: {defn.audience_en}\n"
            f"Prereqs: {defn.prereqs_en}\n"
            f"Workload: {defn.hours}h."
        )
    outcomes = "\n".join(f"- {x}" for x in defn.outcomes_pt)
    return (
        f"Objetivo: {defn.pt_tagline}\n\n"
        f"Você vai aprender:\n{outcomes}\n\n"
        f"Projeto prático: {defn.capstone_pt}\n"
        f"Público-alvo: {defn.audience_pt}\n"
        f"Pré-requisitos: {defn.prereqs_pt}\n"
        f"Carga horária: {defn.hours}h."
    )


def _material_html(title: str, bullets: list[str]):
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return f"<h3>{title}</h3><ul>{items}</ul><p><strong>Status:</strong> em preparação (demo).</p>"


AI_PROMPTS = [
    "Professional HD cover image for an online course titled '{course}', modern geometric design, high contrast, clean typography, premium tech aesthetic, no logos.",
    "HD course cover for '{course}', abstract gradient shapes, elegant composition, premium learning platform aesthetic, no text.",
    "Premium tech course cover inspired by '{course}', minimal, bold, clean, cinematic lighting, no watermarks.",
]


STOCK_COVERS = {
    # Free photos under the Unsplash License. Downloaded via source.unsplash.com for stable IDs.
    # Keep keys aligned with CourseDef.key.
    "k8s-gitops": {
        "provider": "unsplash",
        "id": "ZfVyuV8l7WU",
        "credit": "Growtika",
        "slug": "kubernetes-e-gitops-em-producao",
    },
    "zero-trust": {
        "provider": "unsplash",
        "id": "lwoqEPMUOzo",
        "credit": "FlyD",
        "slug": "seguranca-zero-trust-e-defesa-em-profundidade",
    },
    "lakehouse-dbt": {
        "provider": "unsplash",
        "id": "KU9ABpm7eV8",
        "credit": "Luke Chesser",
        "slug": "data-engineering-lakehouse-com-dbt",
    },
    "otel": {
        "provider": "unsplash",
        "id": "vSprjjDbu60",
        "credit": "Taylor Vick",
        "slug": "observabilidade-com-opentelemetry",
    },
    "terraform": {
        "provider": "unsplash",
        "id": "c-lSQecD9oI",
        "credit": "Umberto",
        "slug": "terraform-e-infraestrutura-como-codigo",
    },
    "architecture": {
        "provider": "unsplash",
        "id": "fNxmdlYHRm8",
        "credit": "Kenny Eliason",
        "slug": "arquitetura-de-software-decisoes-e-trade-offs",
    },
    "django-api": {
        "provider": "unsplash",
        "id": "5eBW5GomfhY",
        "credit": "Rafael Pol",
        "slug": "apis-modernas-com-django",
    },
    "kafka": {
        "provider": "unsplash",
        "id": "kD-r2np8POE",
        "credit": "Markus Spiske",
        "slug": "event-driven-com-kafka-e-outbox",
    },
    "react-ts": {
        "provider": "unsplash",
        "id": "aZsn0bJYqBU",
        "credit": "Growtika",
        "slug": "front-end-react-typescript-de-alto-nivel",
    },
    "mlops": {
        "provider": "unsplash",
        "id": "NIRbWfpKhQ8",
        "credit": "Google DeepMind",
        "slug": "mlops-e-llmops-deploy-de-modelos",
    },
    "rag": {
        "provider": "unsplash",
        "id": "t4TSibE1wq8",
        "credit": "OpenClipart",
        "slug": "rag-e-produtos-com-llm",
    },
    "sre": {
        "provider": "unsplash",
        "id": "OnI_TNcIv9U",
        "credit": "Taylor Vick",
        "slug": "sre-essentials-incidentes-e-confiabilidade",
    },
}


def _download_bytes(url: str, *, timeout: int = 25) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CursosOnlineInvestorSeeder/1.0 (+https://localhost)",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _save_stock_cover(course: Cursos, *, unsplash_id: str, out_dir: Path) -> str | None:
    """
    Download a free HD cover image and normalize it to 1920x1080 for consistent visuals.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    dest_name = f"stock-hd-{course.slug}.jpg"
    dest_path = out_dir / dest_name

    # source.unsplash.com is frequently rate-limited (503). Use the official download redirect instead.
    url = f"https://unsplash.com/photos/{unsplash_id}/download?force=true"
    try:
        data = _download_bytes(url)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None
    if not data:
        return None

    if Image is None:
        dest_path.write_bytes(data)
        return dest_name

    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return None

    img = ImageOps.fit(img, (1920, 1080), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    # Subtle overlay to keep a consistent “platform” look across varied photos.
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 0, 1920, 1080], fill=(6, 10, 14, 24))
    od.rectangle([0, 0, 1920, 380], fill=(6, 10, 14, 58))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    img.save(dest_path, format="JPEG", quality=92, optimize=True, progressive=True)
    return dest_name


def _catalog() -> list[CourseDef]:
    items: list[CourseDef] = []
    items.append(
        CourseDef(
            key="k8s-gitops",
            pt_nome="Kubernetes e GitOps em Produção",
            en_nome="Kubernetes & GitOps in Production",
            pt_tagline="Deploys previsíveis, clusters bem governados e entregas contínuas com Argo CD.",
            en_tagline="Predictable deploys, governed clusters, and continuous delivery with Argo CD.",
            hours=24,
            prereqs_pt="Docker, Git e noções de redes.",
            prereqs_en="Docker, Git, and basic networking.",
            audience_pt="Devs, DevOps e SREs que querem operar com maturidade.",
            audience_en="Developers, DevOps, and SREs aiming for reliable operations.",
            outcomes_pt=[
                "Empacotar aplicações com Helm/Kustomize e padrões de rollout/rollback",
                "Estruturar multi-ambiente (dev/stage/prod) sem duplicação perigosa",
                "Aplicar RBAC/NetworkPolicies e estratégias seguras para secrets",
                "Usar SLOs/telemetria como critério de release e investigação",
            ],
            outcomes_en=[
                "Package apps with Helm/Kustomize and rollout/rollback patterns",
                "Structure multi-env (dev/stage/prod) without risky duplication",
                "Apply RBAC/NetworkPolicies and safer secrets strategies",
                "Use SLOs/telemetry as release gates and investigation tools",
            ],
            capstone_pt="Plataforma GitOps completa com app-of-apps, políticas e checklist de incident response.",
            capstone_en="A complete GitOps platform with app-of-apps, policy gates, and incident checklists.",
            modules_pt=[
                "Cluster e workloads: o que realmente roda",
                "Helm/Kustomize sem dor: padronizando manifests",
                "Argo CD: do básico ao app-of-apps",
                "Segredos, RBAC e políticas: segurança operável",
                "Observabilidade como critério de release",
                "Hardening e troubleshooting: quando o pager toca",
            ],
            modules_en=[
                "Clusters and workloads: what actually runs",
                "Helm/Kustomize done right: standardizing manifests",
                "Argo CD: from basics to app-of-apps",
                "Secrets, RBAC, policies: operable security",
                "Observability as a release gate",
                "Hardening and troubleshooting: when the pager goes off",
            ],
            faq_pt=[
                "Quando usar HPA vs VPA (ou ambos) sem bagunçar requests/limits?",
                "GitOps e segredos: como evitar vazamento e ainda manter rastreabilidade?",
                "Drift no cluster: como detectar e corrigir sem susto?",
                "SLOs: exemplos práticos para uma API interna com picos?",
            ],
            faq_en=[
                "When should I use HPA vs VPA (or both) without fighting requests/limits?",
                "GitOps and secrets: how to stay safe and still keep auditability?",
                "Cluster drift: how do you detect and fix it without drama?",
                "SLOs: practical targets for an internal API with spikes?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="zero-trust",
            pt_nome="Segurança: Zero Trust e Defesa em Profundidade",
            en_nome="Security: Zero Trust & Defense-in-Depth",
            pt_tagline="Arquitetura, processos e controles para reduzir blast radius no dia a dia.",
            en_tagline="Architecture, processes, and controls to reduce blast radius day-to-day.",
            hours=18,
            prereqs_pt="HTTP, redes e autenticação básica.",
            prereqs_en="HTTP, networking, and basic authentication.",
            audience_pt="Devs, DevOps e tech leads.",
            audience_en="Developers, DevOps, and tech leads.",
            outcomes_pt=[
                "Threat modeling focado em rotas reais de ataque",
                "Controles práticos: MFA, least privilege, segmentação e hardening",
                "Detecção e resposta: logs, auditoria, alertas e playbooks",
                "Cultura: segurança como produto, não como checklist",
            ],
            outcomes_en=[
                "Threat modeling focused on real attack paths",
                "Practical controls: MFA, least privilege, segmentation, hardening",
                "Detection/response: logs, audit, alerts, playbooks",
                "Culture: security as a product, not a checklist",
            ],
            capstone_pt="Mini SOC com alertas, playbooks e um plano de mitigação priorizado.",
            capstone_en="A mini SOC: alerts, playbooks, and a prioritized mitigation plan.",
            modules_pt=[
                "Zero Trust na prática",
                "Threat modeling sem burocracia",
                "Identidade e acesso (IAM) para produto",
                "Logs, auditoria e detecção",
                "Resposta a incidentes",
                "Hardening e governança contínua",
            ],
            modules_en=[
                "Zero Trust in practice",
                "Threat modeling without bureaucracy",
                "Product-minded IAM",
                "Logs, audit, and detection",
                "Incident response",
                "Hardening and continuous governance",
            ],
            faq_pt=[
                "Como priorizar riscos sem travar o roadmap?",
                "MFA: quais armadilhas na adoção e como evitar bypass?",
                "Segredos: onde guardar e como rotacionar sem quebrar deploy?",
                "Logs úteis: o que NÃO logar (privacidade e custo)?",
            ],
            faq_en=[
                "How do you prioritize risk without blocking the roadmap?",
                "MFA: adoption pitfalls and how to avoid bypasses?",
                "Secrets: where to store and how to rotate without breaking deploys?",
                "Useful logs: what should you NOT log (privacy and cost)?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="lakehouse-dbt",
            pt_nome="Data Engineering: Lakehouse com dbt",
            en_nome="Data Engineering: Lakehouse with dbt",
            pt_tagline="Modelagem analítica, qualidade de dados e pipelines confiáveis no padrão do mercado.",
            en_tagline="Analytics modeling, data quality, and reliable pipelines with modern patterns.",
            hours=20,
            prereqs_pt="SQL intermediário.",
            prereqs_en="Intermediate SQL.",
            audience_pt="Analistas, DEs e devs migrando para dados.",
            audience_en="Analysts, data engineers, and developers moving into data.",
            outcomes_pt=[
                "Modelar staging/marts com convenções e testes úteis",
                "Criar documentação/lineage para explicar números com confiança",
                "Operar freshness/backfills e otimizar custos/performance",
                "Versionar e fazer deploy de dados com CI e guardrails",
            ],
            outcomes_en=[
                "Model staging/marts with conventions and useful tests",
                "Generate docs/lineage to explain metrics confidently",
                "Operate freshness/backfills and optimize cost/performance",
                "Version and deploy data with CI and guardrails",
            ],
            capstone_pt="Mini warehouse para métricas de produto (retenção, funil e receita) com testes e docs.",
            capstone_en="A mini warehouse for product metrics (retention, funnel, revenue) with tests and docs.",
            modules_pt=[
                "Lakehouse: camadas e trade-offs",
                "Modelagem com dbt: staging e marts",
                "Testes e contratos de dados",
                "Documentação e lineage",
                "Observabilidade e custos",
                "Deploy e governança",
            ],
            modules_en=[
                "Lakehouse layers and trade-offs",
                "dbt modeling: staging and marts",
                "Tests and data contracts",
                "Documentation and lineage",
                "Observability and costs",
                "Deploy and governance",
            ],
            faq_pt=[
                "Incremental model: quando NÃO usar?",
                "Testes dbt: quais são os “obrigatórios” para evitar bugs graves?",
                "Lineage: como explicar para stakeholders sem virar aula teórica?",
                "Custos explodindo: quais alavancas práticas funcionam?",
            ],
            faq_en=[
                "Incremental models: when should you NOT use them?",
                "dbt tests: which are ‘mandatory’ to avoid serious bugs?",
                "Lineage: how to explain to stakeholders without a theory class?",
                "Costs exploding: what practical levers work?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="otel",
            pt_nome="Observabilidade com OpenTelemetry",
            en_nome="Observability with OpenTelemetry",
            pt_tagline="Traces, métricas e logs com contexto — do código ao painel.",
            en_tagline="Traces, metrics, and logs with context — from code to dashboards.",
            hours=16,
            prereqs_pt="HTTP e debugging básico.",
            prereqs_en="HTTP and basic debugging.",
            audience_pt="Devs e SREs.",
            audience_en="Developers and SREs.",
            outcomes_pt=[
                "Instrumentar spans/traces e correlacionar com logs",
                "Escolher métricas (RED/USE) e desenhar SLOs com propósito",
                "Controlar cardinalidade, sampling e custo",
                "Investigar incidentes com narrativa e evidências",
            ],
            outcomes_en=[
                "Instrument spans/traces and correlate with logs",
                "Pick metrics (RED/USE) and design purposeful SLOs",
                "Control cardinality, sampling, and costs",
                "Investigate incidents with a clear evidence trail",
            ],
            capstone_pt="Instrumentar uma API e conduzir uma investigação guiada por tracing até root cause.",
            capstone_en="Instrument an API and run a tracing-driven investigation to root cause.",
            modules_pt=[
                "O que é OTel (de verdade)",
                "Traces e spans: do request ao DB",
                "Métricas e SLOs",
                "Logs com contexto",
                "Sampling e custos",
                "Investigação guiada",
            ],
            modules_en=[
                "What OTel actually is",
                "Traces and spans: request to DB",
                "Metrics and SLOs",
                "Contextual logs",
                "Sampling and costs",
                "Guided investigation",
            ],
            faq_pt=[
                "Cardinalidade alta: como detectar cedo (antes da fatura)?",
                "Naming de spans: existe um padrão simples e consistente?",
                "Sampling: head-based vs tail-based — qual escolher?",
                "SLO: como definir latência “boa” sem chute?",
            ],
            faq_en=[
                "High cardinality: how to detect early (before the bill)?",
                "Span naming: is there a simple consistent standard?",
                "Sampling: head-based vs tail-based — which to choose?",
                "SLO: how to define ‘good’ latency without guessing?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="terraform",
            pt_nome="Terraform e Infraestrutura como Código",
            en_nome="Terraform & Infrastructure as Code",
            pt_tagline="IaC com módulos, ambientes e governança — do MVP ao compliance.",
            en_tagline="IaC with modules, environments, governance — from MVP to compliance.",
            hours=18,
            prereqs_pt="Noções de cloud.",
            prereqs_en="Basic cloud concepts.",
            audience_pt="DevOps e platform engineers.",
            audience_en="DevOps and platform engineers.",
            outcomes_pt=[
                "Organizar state, locking e ambientes com clareza",
                "Criar módulos reutilizáveis com interfaces estáveis",
                "Aplicar guardrails (políticas, validações, plan review)",
                "Refatorar/migrar com baixo risco (import/move/rollback)",
            ],
            outcomes_en=[
                "Organize state, locking, and environments cleanly",
                "Build reusable modules with stable interfaces",
                "Apply guardrails (policy, validation, plan review)",
                "Refactor/migrate with low risk (import/move/rollback)",
            ],
            capstone_pt="Stack completo (rede + app + observabilidade) com pipeline e revisões de plan.",
            capstone_en="A full stack (network + app + observability) with pipelines and plan reviews.",
            modules_pt=[
                "Estado e organização",
                "Módulos e reuso",
                "Ambientes e variáveis",
                "Políticas e validações",
                "Refactor e migração",
                "CI para IaC",
            ],
            modules_en=[
                "State and organization",
                "Modules and reuse",
                "Environments and variables",
                "Policies and validation",
                "Refactor and migration",
                "CI for IaC",
            ],
            faq_pt=[
                "Como evitar ‘terraform apply’ perigoso em prod?",
                "Módulos: quando vira overengineering?",
                "Drift: como detectar e corrigir mudanças manuais?",
                "Import: qual passo a passo seguro para recursos existentes?",
            ],
            faq_en=[
                "How do you avoid dangerous ‘terraform apply’ in prod?",
                "Modules: when is it overengineering?",
                "Drift: how do you detect and fix manual changes?",
                "Import: what’s a safe step-by-step for existing resources?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="architecture",
            pt_nome="Arquitetura de Software: Decisões e Trade-offs",
            en_nome="Software Architecture: Decisions & Trade-offs",
            pt_tagline="Monólito, microsserviços, filas e consistência — escolhendo com clareza.",
            en_tagline="Monoliths, microservices, queues, consistency — choosing with clarity.",
            hours=14,
            prereqs_pt="Experiência com APIs e banco de dados.",
            prereqs_en="Experience with APIs and databases.",
            audience_pt="Tech leads e devs seniores.",
            audience_en="Tech leads and senior developers.",
            outcomes_pt=[
                "Registrar decisões (ADRs) e evitar debates circulares",
                "Avaliar microserviços vs monólito modular por critérios",
                "Aplicar padrões (outbox, saga, idempotência) com segurança",
                "Planejar migração gradual com redução de risco",
            ],
            outcomes_en=[
                "Record decisions (ADRs) and stop circular debates",
                "Evaluate microservices vs modular monolith with criteria",
                "Apply patterns (outbox, saga, idempotency) safely",
                "Plan gradual migrations with risk reduction",
            ],
            capstone_pt="Plano evolutivo do MVP ao scale-up com ADRs, métricas e estratégia de migração.",
            capstone_en="An evolutionary plan from MVP to scale-up with ADRs, metrics, migration strategy.",
            modules_pt=[
                "Critérios de decisão e ADRs",
                "Monólito modular vs microserviços",
                "Consistência e transações",
                "Event-driven com segurança",
                "Migração gradual (strangler)",
                "Arquitetura e times",
            ],
            modules_en=[
                "Decision criteria and ADRs",
                "Modular monolith vs microservices",
                "Consistency and transactions",
                "Event-driven safely",
                "Gradual migration (strangler)",
                "Architecture and teams",
            ],
            faq_pt=[
                "Quando microsserviços realmente valem a pena?",
                "Outbox: como implementar e garantir idempotência/retries?",
                "ADRs: como não virar burocracia?",
                "Eventual consistency: como explicar impacto de UX para produto?",
            ],
            faq_en=[
                "When do microservices actually pay off?",
                "Outbox: how to implement and ensure idempotency/retries?",
                "ADRs: how do you avoid bureaucracy?",
                "Eventual consistency: how to explain UX impact to product?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="django-api",
            pt_nome="APIs Modernas com Django",
            en_nome="Modern APIs with Django",
            pt_tagline="APIs bem desenhadas, seguras e performáticas — prontas para crescer.",
            en_tagline="Well-designed, secure, performant APIs — ready to scale.",
            hours=22,
            prereqs_pt="Python e Django básico.",
            prereqs_en="Python and basic Django.",
            audience_pt="Devs backend e full-stack.",
            audience_en="Backend and full-stack developers.",
            outcomes_pt=[
                "Definir contratos: paginação, filtros, versionamento e erros",
                "Implementar autenticação/autorização com clareza",
                "Melhorar performance: cache, índices e evitar N+1",
                "Criar testes/observabilidade para reduzir regressões",
            ],
            outcomes_en=[
                "Define contracts: pagination, filters, versioning, errors",
                "Implement authN/authZ with clarity",
                "Improve performance: caching, indexes, avoid N+1",
                "Add tests/observability to reduce regressions",
            ],
            capstone_pt="API de catálogo com busca, perfis e auditoria, pronta para integração com front.",
            capstone_en="A catalog API with search, profiles, auditing, ready for frontend integration.",
            modules_pt=[
                "Design de API e contratos",
                "Autenticação e autorização",
                "Performance de queries",
                "Cache e rate limiting",
                "Async onde faz sentido",
                "Testes e observabilidade",
            ],
            modules_en=[
                "API design and contracts",
                "Authentication and authorization",
                "Query performance",
                "Caching and rate limiting",
                "Async where it makes sense",
                "Tests and observability",
            ],
            faq_pt=[
                "Paginação: cursor vs offset — quando cursor é essencial?",
                "Permissões: RBAC ou ABAC em regras por time e recurso?",
                "N+1: como detectar e evitar antes de ir para prod?",
                "Rate limiting: como escolher limites sem punir usuários legítimos?",
            ],
            faq_en=[
                "Pagination: cursor vs offset — when is cursor essential?",
                "Permissions: RBAC or ABAC for team/resource rules?",
                "N+1: how do you detect and prevent before production?",
                "Rate limiting: how to choose limits without hurting legit users?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="kafka",
            pt_nome="Event-Driven com Kafka e Outbox",
            en_nome="Event-Driven with Kafka & Outbox",
            pt_tagline="Mensageria com confiabilidade: eventos, consumidores e consistência transacional.",
            en_tagline="Reliable messaging: events, consumers, transactional consistency.",
            hours=18,
            prereqs_pt="APIs e banco de dados.",
            prereqs_en="APIs and databases.",
            audience_pt="Backends e arquitetos.",
            audience_en="Backend developers and architects.",
            outcomes_pt=[
                "Definir contratos de eventos e versionar sem quebrar consumidores",
                "Construir consumidores idempotentes com retries e DLQ",
                "Aplicar outbox/CDC e lidar com duplicidade corretamente",
                "Monitorar lag e investigar gargalos com rapidez",
            ],
            outcomes_en=[
                "Define event contracts and version without breaking consumers",
                "Build idempotent consumers with retries and DLQ",
                "Apply outbox/CDC and handle duplicates correctly",
                "Monitor lag and debug bottlenecks quickly",
            ],
            capstone_pt="Fluxo de pedidos com eventos, outbox e reprocessamento seguro.",
            capstone_en="An orders flow with events, outbox, and safe reprocessing.",
            modules_pt=[
                "Eventos: contrato e semântica",
                "Versionamento e compatibilidade",
                "Consumidores idempotentes",
                "Outbox e CDC",
                "Lag e observabilidade",
                "Reprocessamento e backfills",
            ],
            modules_en=[
                "Events: contracts and semantics",
                "Versioning and compatibility",
                "Idempotent consumers",
                "Outbox and CDC",
                "Lag and observability",
                "Reprocessing and backfills",
            ],
            faq_pt=[
                "Idempotência: como modelar chave de dedupe (order_id, event_id…)?",
                "DLQ: quando mandar vs retry infinito?",
                "Outbox: como reduzir inconsistência e duplicidade no mundo real?",
                "Lag alto: como isolar causa (CPU, I/O, particionamento, downstream)?",
            ],
            faq_en=[
                "Idempotency: how do you model a dedupe key (order_id, event_id…)?",
                "DLQ: when to send vs infinite retries?",
                "Outbox: how do you reduce inconsistency and duplicates in practice?",
                "High lag: isolating root cause (CPU, I/O, partitioning, downstream)?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="react-ts",
            pt_nome="Front-end: React + TypeScript de Alto Nível",
            en_nome="Front-end: React + TypeScript at a High Bar",
            pt_tagline="Design systems, performance e acessibilidade — UI com acabamento de produto.",
            en_tagline="Design systems, performance, accessibility — product-level UI polish.",
            hours=20,
            prereqs_pt="JavaScript moderno.",
            prereqs_en="Modern JavaScript.",
            audience_pt="Front-ends e full-stacks.",
            audience_en="Frontend and full-stack developers.",
            outcomes_pt=[
                "Criar componentes/tokens com consistência (design system)",
                "Tratar acessibilidade como requisito (teclado, semântica, contraste)",
                "Melhorar performance com profiling e decisões explícitas",
                "Criar testes de UI com ROI e evitar suítes lentas",
            ],
            outcomes_en=[
                "Build consistent components/tokens (design system)",
                "Treat accessibility as a requirement (keyboard, semantics, contrast)",
                "Improve performance using profiling and explicit decisions",
                "Create high-ROI UI tests without slow suites",
            ],
            capstone_pt="Front completo (catálogo + dashboard) com padrões de estado, a11y e performance.",
            capstone_en="A full frontend (catalog + dashboard) with state patterns, a11y, performance.",
            modules_pt=[
                "Arquitetura de componentes",
                "Estado e dados",
                "Acessibilidade de verdade",
                "Performance e profiling",
                "Qualidade e testes",
                "Entrega e manutenção",
            ],
            modules_en=[
                "Component architecture",
                "State and data",
                "Accessibility that matters",
                "Performance and profiling",
                "Quality and tests",
                "Delivery and maintenance",
            ],
            faq_pt=[
                "Acessibilidade: por onde começar sem travar o time?",
                "Memoization: quando ajuda vs atrapalha?",
                "Design tokens: como manter consistência ao escalar?",
                "Testes de UI: o que vale automatizar primeiro?",
            ],
            faq_en=[
                "Accessibility: where do you start without stalling the team?",
                "Memoization: when does it help vs hurt?",
                "Design tokens: how do you keep consistency at scale?",
                "UI tests: what should you automate first?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="mlops",
            pt_nome="MLOps e LLMOps: Deploy de Modelos",
            en_nome="MLOps & LLMOps: Deploying Models",
            pt_tagline="Do notebook ao serviço: versionamento, avaliação, rollout e monitoramento.",
            en_tagline="From notebook to service: versioning, evals, rollout, monitoring.",
            hours=18,
            prereqs_pt="Python e ML básico.",
            prereqs_en="Python and basic ML.",
            audience_pt="Devs e data scientists.",
            audience_en="Developers and data scientists.",
            outcomes_pt=[
                "Versionar dados/modelos e garantir reprodutibilidade",
                "Criar evals com slicing e testes de regressão",
                "Fazer rollout (canary/shadow) com rollback e guardrails",
                "Monitorar drift, feedback e custo de serving",
            ],
            outcomes_en=[
                "Version data/models and ensure reproducibility",
                "Build evals with slicing and regression tests",
                "Roll out (canary/shadow) with rollback and guardrails",
                "Monitor drift, feedback loops, and serving costs",
            ],
            capstone_pt="Publicar um modelo e operar com métricas, alertas e plano de rollback.",
            capstone_en="Deploy a model and operate it with metrics, alerts, and a rollback plan.",
            modules_pt=[
                "Reprodutibilidade e versionamento",
                "Evals e slicing",
                "Serving e latência",
                "Rollout e rollback",
                "Monitoramento e drift",
                "Custo e governança",
            ],
            modules_en=[
                "Reproducibility and versioning",
                "Evals and slicing",
                "Serving and latency",
                "Rollout and rollback",
                "Monitoring and drift",
                "Cost and governance",
            ],
            faq_pt=[
                "Evals: como evitar overfitting em benchmark?",
                "Drift: como detectar sem falso positivo?",
                "Canary vs shadow: quando usar cada um?",
                "Custos: como controlar serving (cache, batching, distillation)?",
            ],
            faq_en=[
                "Evals: how do you avoid benchmark overfitting?",
                "Drift: how to detect without false positives?",
                "Canary vs shadow: when do you use each?",
                "Costs: how do you control serving (cache, batching, distillation)?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="rag",
            pt_nome="RAG e Produtos com LLM",
            en_nome="RAG & LLM Product Engineering",
            pt_tagline="Busca, contexto e segurança — sem alucinação como feature.",
            en_tagline="Search, context, and security — without hallucinations as a feature.",
            hours=16,
            prereqs_pt="APIs e noções de NLP.",
            prereqs_en="APIs and basic NLP.",
            audience_pt="Devs e PMs técnicos.",
            audience_en="Developers and technical PMs.",
            outcomes_pt=[
                "Desenhar pipeline RAG (chunking, retrieval, rerank) com métricas",
                "Criar grounding com citações e evals focadas em utilidade",
                "Mitigar prompt injection e vazamento com defesa em camadas",
                "Iterar produto com métricas e feedback (não só CSAT)",
            ],
            outcomes_en=[
                "Design a RAG pipeline (chunking, retrieval, rerank) with metrics",
                "Add grounding with citations and usefulness-focused evals",
                "Mitigate prompt injection and leakage with layered defenses",
                "Iterate product with metrics and feedback (beyond CSAT)",
            ],
            capstone_pt="Mentor com base de conhecimento, permissões e trilhas — pronto para demo.",
            capstone_en="A mentor app with a knowledge base, permissions, and learning paths — demo-ready.",
            modules_pt=[
                "Fundamentos de RAG",
                "Chunking e índices",
                "Retrieval e reranking",
                "Evals e grounding",
                "Segurança e permissões",
                "Produto e iteração",
            ],
            modules_en=[
                "RAG fundamentals",
                "Chunking and indexes",
                "Retrieval and reranking",
                "Evals and grounding",
                "Security and permissions",
                "Product and iteration",
            ],
            faq_pt=[
                "Chunking: existe tamanho ideal para docs longos com tabelas?",
                "Prompt injection: como mitigar na prática?",
                "Citações: como evitar fonte inventada?",
                "Métricas: como medir valor real em chatbot?",
            ],
            faq_en=[
                "Chunking: is there an ideal size for long docs with tables?",
                "Prompt injection: what practical mitigations work?",
                "Citations: how to prevent fabricated sources?",
                "Metrics: how do you measure real chatbot value?",
            ],
        )
    )
    items.append(
        CourseDef(
            key="sre",
            pt_nome="SRE Essentials: Incidentes e Confiabilidade",
            en_nome="SRE Essentials: Incidents & Reliability",
            pt_tagline="SLOs, alertas, on-call e postmortems que melhoram o sistema de verdade.",
            en_tagline="SLOs, alerts, on-call, and postmortems that actually improve systems.",
            hours=14,
            prereqs_pt="Noções de operação.",
            prereqs_en="Operational basics.",
            audience_pt="Devs, SREs e leads.",
            audience_en="Developers, SREs, and leads.",
            outcomes_pt=[
                "Definir SLOs/error budget como linguagem com produto",
                "Desenhar alertas acionáveis e reduzir ruído",
                "Conduzir incident command e comunicação clara",
                "Escrever postmortems com ações fecháveis",
            ],
            outcomes_en=[
                "Define SLOs/error budgets as a shared language with product",
                "Design actionable alerts and reduce noise",
                "Run incident command and communicate clearly",
                "Write postmortems with closed-loop actions",
            ],
            capstone_pt="Simulação de incidentes + playbooks + SLOs e um backlog de confiabilidade.",
            capstone_en="Incident simulations + playbooks + SLOs and a reliability backlog.",
            modules_pt=[
                "SLO e error budget",
                "Alertas acionáveis",
                "Runbooks e on-call",
                "Incident command",
                "Postmortem de qualidade",
                "Melhoria contínua",
            ],
            modules_en=[
                "SLO and error budget",
                "Actionable alerts",
                "Runbooks and on-call",
                "Incident command",
                "High-quality postmortems",
                "Continuous improvement",
            ],
            faq_pt=[
                "Como reduzir ruído de alerta sem perder sinal?",
                "Error budget: como explicar para produto sem virar briga?",
                "Postmortem: quais perguntas geram ações reais?",
                "Runbooks: o que vale escrever e como manter vivo?",
            ],
            faq_en=[
                "How do you reduce alert noise without losing signal?",
                "Error budgets: how do you explain to product without conflict?",
                "Postmortems: which questions lead to real actions?",
                "Runbooks: what’s worth writing and how to keep them alive?",
            ],
        )
    )
    return items


class Command(BaseCommand):
    help = "Seed an investor-ready demo dataset (12 IT courses + realistic interactions)."

    def add_arguments(self, parser):
        parser.add_argument("--purge", action="store_true", help="Delete all data except users before seeding.")
        parser.add_argument("--purge-media", action="store_true", help="Also remove generated course images under media/cursos/imagens.")
        parser.add_argument("--students", type=int, default=18, help="How many demo students to ensure (default: 18).")
        parser.add_argument("--password", type=str, default="demo12345", help="Password for demo users (default: demo12345).")
        parser.add_argument(
            "--stock-images",
            action="store_true",
            help="Download free HD stock covers for each course (default: off).",
        )
        parser.add_argument("--ai-images", action="store_true", help="Try generating AI HD covers (requires a valid OpenAI key).")
        parser.add_argument("--ai-model", type=str, default="", help="Override OpenAI image model (default: OPENAI_IMAGE_TOOL_MODEL).")
        parser.add_argument("--ai-limit", type=int, default=0, help="Limit AI image generations (0 = all courses).")

    def handle(self, *args, **options):
        password = options["password"]
        do_purge = bool(options["purge"])
        purge_media = bool(options["purge_media"])
        students_target = max(1, int(options["students"]))
        stock_images = bool(options["stock_images"])
        ai_images = bool(options["ai_images"])
        ai_limit = max(0, int(options["ai_limit"]))
        ai_model = (options.get("ai_model") or "").strip() or None

        media_root = Path(settings.MEDIA_ROOT or (Path(settings.BASE_DIR) / "media"))
        media_course_dir = media_root / "cursos" / "imagens"

        # Seeding announcements triggers an email signal; disable it to keep the command fast and quiet.
        try:
            from django.db.models import signals

            signals.post_save.disconnect(sender=Anuncios, dispatch_uid="envio_anuncio_email")
        except Exception:
            pass

        if do_purge:
            backup = _backup_sqlite_db()
            if backup:
                self.stdout.write(self.style.SUCCESS(f"DB backup created: {backup}"))
            with transaction.atomic():
                _purge_everything_except_users()
            self.stdout.write(self.style.SUCCESS("Database cleaned (users preserved)."))

            if purge_media and media_course_dir.exists():
                removed = 0
                for p in media_course_dir.glob("seed-*.png"):
                    p.unlink(missing_ok=True)
                    removed += 1
                for p in media_course_dir.glob("ai-*.png"):
                    p.unlink(missing_ok=True)
                    removed += 1
                if removed:
                    self.stdout.write(self.style.SUCCESS(f"Removed {removed} generated course images from media."))

        User = get_user_model()

        staff, created = User.objects.get_or_create(
            username="staff",
            defaults={"email": "staff@example.com", "is_staff": True},
        )
        if created:
            staff.set_password(password)
            staff.save()

        base_usernames = [
            "ana_dev", "bruno_data", "carla_sec", "diego_sre", "eli_front",
            "felipe_ml", "gi_arch", "heitor_cloud", "iris_prod", "joao_backend",
            "karen_ops", "leo_ai", "mari_qa", "nina_platform", "otavio_kafka",
            "paula_ux", "rafa_finops", "sofia_ds", "tiago_devops", "vitor_eng",
        ]
        random.shuffle(base_usernames)
        students = []
        for i in range(students_target):
            username = base_usernames[i % len(base_usernames)]
            user, u_created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if u_created:
                user.set_password(password)
                user.save()
            students.append(user)

        catalog = _catalog()
        if len(catalog) != 12:
            raise SystemExit(f"Catalog has {len(catalog)} courses; expected 12. Fill _catalog().")

        featured = {slugify("Kubernetes e GitOps em Produção"), slugify("Segurança: Zero Trust e Defesa em Profundidade"), slugify("RAG e Produtos com LLM")}

        created_courses: list[Cursos] = []
        created_threads: list[Thread] = []
        created_replies: list[Reply] = []
        course_by_key: dict[str, Cursos] = {}

        with transaction.atomic():
            for defn in catalog:
                slug = slugify(defn.pt_nome)
                course_defaults = {
                    "nome": defn.pt_nome,
                    "nome_en": defn.en_nome,
                    "slug": slug,
                    "descricao": defn.pt_tagline,
                    "descricao_en": defn.en_tagline,
                    "sobre": _build_sobre(defn, lang="pt"),
                    "sobre_en": _build_sobre(defn, lang="en"),
                    "data_inicial": timezone.now().date(),
                    "destaque": slug in featured,
                }
                course, _ = Cursos.objects.get_or_create(slug=slug, defaults=course_defaults)
                _apply_updates(course, course_defaults, overwrite=True)
                created_courses.append(course)
                course_by_key[defn.key] = course

                enrolled = random.sample(students, k=min(len(students), random.randint(7, 12)))
                for u in enrolled:
                    Enrollment.objects.get_or_create(usuario=u, curso=course, defaults={"status": 1})

                # Lessons + materials
                for idx in range(6):
                    lesson, _ = Aulas.objects.get_or_create(
                        curso=course,
                        numero=idx + 1,
                        defaults={
                            "nome": defn.modules_pt[idx],
                            "nome_en": defn.modules_en[idx],
                            "descricao": f"Parte {idx + 1}: {defn.pt_tagline}",
                            "descricao_en": f"Part {idx + 1}: {defn.en_tagline}",
                            "inicio": timezone.now().date(),
                        },
                    )
                    _apply_updates(
                        lesson,
                        {
                            "nome": defn.modules_pt[idx],
                            "nome_en": defn.modules_en[idx],
                            "descricao": f"Parte {idx + 1}: {defn.pt_tagline}",
                            "descricao_en": f"Part {idx + 1}: {defn.en_tagline}",
                        },
                        overwrite=True,
                    )

                    for j, (m_pt, m_en, html) in enumerate(
                        [
                            (
                                "Resumo da aula",
                                "Lesson summary",
                                _material_html("Resumo + checklist", ["Pontos-chave", "Erros comuns", "Mini exercício"]),
                            ),
                            (
                                "Laboratório guiado",
                                "Guided lab",
                                _material_html("Laboratório (hands-on)", ["Passo a passo", "Checkpoints", "Extensões"]),
                            ),
                        ],
                        start=1,
                    ):
                        mat, _ = Materiais.objects.get_or_create(
                            aula=lesson,
                            nome=f"{m_pt} {j}",
                            defaults={"nome_en": f"{m_en} {j}", "embutido": html, "embutido_en": html},
                        )
                        _apply_updates(mat, {"nome_en": f"{m_en} {j}", "embutido": html, "embutido_en": html}, overwrite=True)

                # Announcements + comments
                for t_pt, t_en, c_pt, c_en in [
                    (
                        "Bem-vindo ao curso",
                        "Welcome to the course",
                        "Aqui está o mapa do curso: objetivos, ritmo e como tirar o máximo.",
                        "Here is the course map: goals, pacing, and how to get the most out of it.",
                    ),
                    (
                        "Projeto prático: evidências de qualidade",
                        "Hands-on project: quality evidence",
                        "Vamos focar em entregas pequenas com evidências (prints, métricas e checklist).",
                        "We'll focus on small deliveries with evidence (screenshots, metrics, checklist).",
                    ),
                ]:
                    anuncio, _ = Anuncios.objects.get_or_create(
                        curso=course,
                        titulo=t_pt,
                        defaults={"titulo_en": t_en, "conteudo": c_pt, "conteudo_en": c_en},
                    )
                    _apply_updates(anuncio, {"titulo_en": t_en, "conteudo": c_pt, "conteudo_en": c_en}, overwrite=True)
                    for u in random.sample(enrolled, k=min(len(enrolled), random.randint(2, 4))):
                        Comentarios.objects.get_or_create(
                            anuncio=anuncio,
                            usuario=u,
                            comentario="Curti a estrutura. Tem uma trilha sugerida?",
                            defaults={"comentario_en": "Loved the structure. Is there a suggested learning path?"},
                        )

                # Forum: 4 tópicos por curso
                for t_idx in range(4):
                    pt_title = f"Dúvida: {defn.faq_pt[t_idx]}"
                    en_title = f"Question: {defn.faq_en[t_idx]}"
                    thread_slug = f"{course.slug}-{t_idx + 1}-{slugify(defn.faq_pt[t_idx])}"[:100]
                    thread, _ = Thread.objects.get_or_create(
                        slug=thread_slug,
                        defaults={
                            "title": pt_title,
                            "title_en": en_title,
                            "body": "Contexto: estou aplicando o conteúdo no meu projeto e quero uma recomendação prática (com trade-offs).",
                            "body_en": "Context: I'm applying this to my project and want a practical recommendation (with trade-offs).",
                            "author": random.choice(enrolled),
                            "views": random.randint(60, 420),
                        },
                    )
                    _apply_updates(thread, {"title_en": en_title}, overwrite=True)
                    try:
                        thread.tags.set([course.slug, defn.key, "faq"])
                    except Exception:
                        pass
                    created_threads.append(thread)

                    created_replies.append(
                        Reply.objects.create(
                            thread=thread,
                            author=random.choice([u for u in enrolled if u != thread.author]),
                            reply="Eu começaria definindo objetivo e restrições; depois escolheria a opção mínima com rollback.",
                            reply_en="I’d start by defining goals/constraints, then pick the minimal option with a rollback plan.",
                            correct=False,
                        )
                    )
                    created_replies.append(
                        Reply.objects.create(
                            thread=thread,
                            author=staff,
                            reply="Resposta oficial: vou sugerir 3 abordagens com critério de decisão e checklist.",
                            reply_en="Official answer: I’ll suggest 3 approaches with decision criteria and a checklist.",
                            correct=True,
                        )
                    )

                # Mentor IA sessions (2 por curso)
                for s_i in range(2):
                    mt = MentorThread.objects.create(
                        user=random.choice(enrolled),
                        course=course,
                        title=f"Mentoria: {defn.modules_pt[s_i]}",
                        mode="coach" if s_i == 0 else "study",
                        last_used=timezone.now(),
                    )
                    MentorMessage.objects.create(
                        thread=mt,
                        role="user",
                        content=f"Estou estudando '{defn.modules_pt[s_i]}'. Qual o melhor caminho prático para aplicar hoje?",
                    )
                    MentorMessage.objects.create(
                        thread=mt,
                        role="assistant",
                        content=(
                            "Roteiro: objetivo → risco → experimento → evidência. "
                            "Me diga seu contexto (stack, volume, restrições) e eu adapto o plano."
                        ),
                    )

                # Drafts/quizzes
                for dtype, title in [
                    ("quiz", "Quiz de avaliação (rascunho)"),
                    ("rubric", "Rubrica do projeto (rascunho)"),
                    ("lesson_outline", "Plano de aula (rascunho)"),
                    ("announcement", "Comunicado (rascunho)"),
                ]:
                    AIDraft.objects.create(
                        course=course,
                        created_by=staff,
                        draft_type=dtype,
                        title=title,
                        input_context={"course": course.nome, "audience": "iniciante-intermediário", "seed": True},
                        output=(
                            f"RASCUNHO ({dtype}):\n"
                            f"- Objetivo: validar entendimento aplicado.\n"
                            f"- Estrutura: 5 questões + 1 desafio prático.\n"
                            f"- Critérios: clareza, evidência, justificativa.\n"
                            f"- Nota: conteúdo gerado para demonstração.\n"
                        ),
                    )

                # Radar realism
                for u in random.sample(enrolled, k=min(len(enrolled), 6)):
                    LearningEvent.objects.create(user=u, course=course, event_type="view_course", metadata={"seed": True, "profile": "investor"})
                    LearningEvent.objects.create(user=u, course=course, event_type="view_forum", metadata={"seed": True, "profile": "investor"})
                rs_user = random.choice(enrolled)
                RiskSignal.objects.create(
                    user=rs_user,
                    course=course,
                    label="Baixa participação no fórum",
                    score=2.40,
                    evidence={"threads_read": random.randint(0, 2), "replies_posted": random.randint(0, 1), "seed": True},
                    notes="Sinal gerado para demo (Radar).",
                )

            # Atlas documents
            for course in created_courses:
                AtlasDocument.objects.update_or_create(
                    source_type="curso",
                    source_id=course.id,
                    defaults={
                        "course": course,
                        "title": course.nome,
                        "content": course.sobre or course.descricao,
                        "source_url": f"/cursos/{course.slug}/",
                        "source_hash": f"seed-inv-curso-{course.id}",
                        "embedding_model": "seed",
                        "active": True,
                    },
                )
            for thread in created_threads[:96]:
                AtlasDocument.objects.update_or_create(
                    source_type="forum_thread",
                    source_id=thread.id,
                    defaults={
                        "course": created_courses[_stable_int(thread.slug) % len(created_courses)],
                        "title": thread.title,
                        "content": thread.body,
                        "source_url": thread.get_absolute_url(),
                        "source_hash": f"seed-inv-thread-{thread.id}",
                        "embedding_model": "seed",
                        "active": True,
                    },
                )
            for reply in created_replies[:240]:
                AtlasDocument.objects.update_or_create(
                    source_type="forum_reply",
                    source_id=reply.id,
                    defaults={
                        "course": created_courses[_stable_int(str(reply.thread_id)) % len(created_courses)],
                        "title": f"Reply {reply.id}",
                        "content": reply.reply,
                        "source_url": reply.thread.get_absolute_url(),
                        "source_hash": f"seed-inv-reply-{reply.id}",
                        "embedding_model": "seed",
                        "active": True,
                    },
                )

            for u in students:
                key = generate_hash_key(u.username)
                ResetarSenha.objects.get_or_create(user=u, key=key, defaults={"confirmed": False})

        # Covers: local HD by default; optionally override with OpenAI.
        media_course_dir.mkdir(parents=True, exist_ok=True)
        for defn in catalog:
            course = course_by_key.get(defn.key)
            if not course:
                continue
            dest_name = None
            if stock_images:
                src = STOCK_COVERS.get(defn.key)
                if src and src.get("provider") == "unsplash":
                    dest_name = _save_stock_cover(course, unsplash_id=src["id"], out_dir=media_course_dir)
            if not dest_name:
                dest_name = _generate_hd_cover(course, media_course_dir)
            if dest_name:
                course.imagem.name = str(Path("cursos/imagens") / dest_name)
                course.save(update_fields=["imagem"])

        if ai_images:
            if not is_configured():
                self.stdout.write(self.style.WARNING("OPENAI_API_KEY not configured. Keeping local HD covers."))
            else:
                limit = ai_limit or len(created_courses)
                for course in created_courses[:limit]:
                    prompt = random.choice(AI_PROMPTS).format(course=course.nome_en or course.nome)
                    try:
                        image_bytes = _generate_ai_image_bytes(prompt, model=ai_model)
                    except OpenAIError as exc:
                        self.stdout.write(self.style.WARNING(f"OpenAI image error: {exc}"))
                        break
                    if not image_bytes:
                        continue
                    dest_name = f"ai-{course.slug}.png"
                    (media_course_dir / dest_name).write_bytes(image_bytes)
                    course.imagem.name = str(Path("cursos/imagens") / dest_name)
                    course.save(update_fields=["imagem"])

        self.stdout.write(self.style.SUCCESS("Investor demo data generated successfully."))

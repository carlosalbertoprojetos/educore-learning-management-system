import hashlib
import math
import re

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from cursos.models import Cursos, Aulas, Materiais, Anuncios
from forum.models import Thread, Reply

from .openai_client import OpenAIError, create_embedding, is_configured
from ..models import AtlasDocument


MAX_CHARS = 2000


def _normalize(text):
    if not text:
        return ""
    return " ".join(text.strip().split())


def _hash_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _trim(text):
    if not text:
        return ""
    text = _normalize(text)
    return text[:MAX_CHARS]


def _simple_tokens(text):
    return set(re.findall(r"[A-Za-z0-9_]+", text.lower()))


def _simple_score(query, doc):
    query_tokens = _simple_tokens(query)
    if not query_tokens:
        return 0.0
    doc_tokens = _simple_tokens(doc)
    if not doc_tokens:
        return 0.0
    overlap = query_tokens.intersection(doc_tokens)
    return len(overlap) / float(len(query_tokens))


def _cosine_similarity(vector_a, vector_b):
    if not vector_a or not vector_b:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vector_a, vector_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def build_atlas(embed=True):
    documents = []
    for curso in Cursos.objects.all():
        content = _trim("\n".join([curso.descricao or "", curso.sobre or ""]))
        documents.append(
            {
                "source_type": "curso",
                "source_id": curso.id,
                "course": curso,
                "title": curso.nome,
                "content": content,
                "source_url": curso.get_absolute_url(),
            }
        )

    for aula in Aulas.objects.select_related("curso").all():
        content = _trim(aula.descricao or "")
        documents.append(
            {
                "source_type": "aula",
                "source_id": aula.id,
                "course": aula.curso,
                "title": aula.nome,
                "content": content,
                "source_url": reverse("cursos:aula", args=[aula.curso.slug, aula.pk]),
            }
        )

    for material in Materiais.objects.select_related("aula", "aula__curso").all():
        content = _trim(material.embutido or "")
        documents.append(
            {
                "source_type": "material",
                "source_id": material.id,
                "course": material.aula.curso,
                "title": material.nome,
                "content": content,
                "source_url": reverse(
                    "cursos:aula", args=[material.aula.curso.slug, material.aula.pk]
                ),
            }
        )

    for anuncio in Anuncios.objects.select_related("curso").all():
        content = _trim("\n".join([anuncio.titulo, anuncio.conteudo or ""]))
        documents.append(
            {
                "source_type": "anuncio",
                "source_id": anuncio.id,
                "course": anuncio.curso,
                "title": anuncio.titulo,
                "content": content,
                "source_url": reverse(
                    "cursos:anuncio", args=[anuncio.curso.slug, anuncio.pk]
                ),
            }
        )

    for thread in Thread.objects.select_related("author").all():
        content = _trim(thread.body or "")
        documents.append(
            {
                "source_type": "forum_thread",
                "source_id": thread.id,
                "course": None,
                "title": thread.title,
                "content": content,
                "source_url": thread.get_absolute_url(),
            }
        )

    for reply in Reply.objects.select_related("thread").all():
        content = _trim(reply.reply or "")
        documents.append(
            {
                "source_type": "forum_reply",
                "source_id": reply.id,
                "course": None,
                "title": reply.thread.title,
                "content": content,
                "source_url": reply.thread.get_absolute_url(),
            }
        )

    now = timezone.now()
    seen_ids = []
    with transaction.atomic():
        for doc in documents:
            content = doc["content"]
            source_hash = _hash_text(content)
            atlas_doc, created = AtlasDocument.objects.get_or_create(
                source_type=doc["source_type"],
                source_id=doc["source_id"],
                defaults={
                    "title": doc["title"],
                    "content": content,
                    "course": doc["course"],
                    "source_url": doc["source_url"],
                    "source_hash": source_hash,
                    "active": True,
                },
            )
            if not created and atlas_doc.source_hash == source_hash:
                atlas_doc.active = True
                atlas_doc.updated_at = now
                atlas_doc.save(update_fields=["active", "updated_at"])
                seen_ids.append(atlas_doc.pk)
                continue

            atlas_doc.title = doc["title"]
            atlas_doc.content = content
            atlas_doc.course = doc["course"]
            atlas_doc.source_url = doc["source_url"]
            atlas_doc.source_hash = source_hash
            atlas_doc.active = True
            if embed and is_configured() and content:
                try:
                    response = create_embedding(content)
                    data = response.get("data", [])
                    if data and "embedding" in data[0]:
                        atlas_doc.embedding = data[0]["embedding"]
                        atlas_doc.embedding_model = response.get(
                            "model", atlas_doc.embedding_model
                        )
                except OpenAIError:
                    atlas_doc.embedding = None
            atlas_doc.save()
            seen_ids.append(atlas_doc.pk)

        if seen_ids:
            AtlasDocument.objects.exclude(pk__in=seen_ids).update(
                active=False, updated_at=now
            )
        else:
            AtlasDocument.objects.update(active=False, updated_at=now)


def search_atlas(query, course=None, limit=6):
    docs = AtlasDocument.objects.filter(active=True)
    if course:
        docs = docs.filter(Q(course=course) | Q(course__isnull=True))
    docs = list(docs)
    if not docs:
        return []

    query_embedding = None
    if is_configured():
        try:
            response = create_embedding(query)
            data = response.get("data", [])
            if data and "embedding" in data[0]:
                query_embedding = data[0]["embedding"]
        except OpenAIError:
            query_embedding = None

    scored = []
    for doc in docs:
        if query_embedding and doc.embedding:
            score = _cosine_similarity(query_embedding, doc.embedding)
        else:
            score = _simple_score(query, doc.content)
        scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for score, doc in scored[:limit] if score > 0]

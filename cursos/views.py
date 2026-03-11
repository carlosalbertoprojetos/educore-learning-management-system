from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ai.services.radar import log_event

from .forms import ComentariosForm, FormContatoCurso
from .models import Anuncios, Cursos, Enrollment, Aulas, Materiais
from .decorators import inscricao_required



def lista_cursos_view(request):
    lista_cursos = Cursos.objects.all()
    context = {
        'lista_cursos': lista_cursos,
    }
    template_name = 'cursos/lista_cursos.html'
    return render(request, template_name, context)


# forma simples
# def detalhes_CursoView(request, slug):
#     curso = get_object_or_404(Cursos, slug=slug)
#     context = {
#         'curso': curso,
#         }
#     template_name = 'cursos/detalhes_curso.html'
#     return render(request, template_name, context)


def detalhes_curso_view(request, slug):
    curso = get_object_or_404(Cursos, slug=slug)
    if request.user.is_authenticated:
        log_event(request, 'view_course', course=curso, metadata={'slug': curso.slug})
    context = {}
    if request.method == 'POST':
        form = FormContatoCurso(request.POST, request.FILES)
        if form.is_valid():
            context['is_valid'] = True  # aciona a mensagem
            form.send_email(curso)
            form = FormContatoCurso()
    else:
        form = FormContatoCurso()
    context['curso'] = curso
    context['form'] = form
    template_name = 'cursos/detalhes_curso.html'
    return render(request, template_name, context)


def contato_curso_view(request):
    send = False
    form = FormContatoCurso(request.POST or None)
    if form.is_valid():
        # enviar e-mail
        nome = request.POST.get('nome', '')
        email = request.POST.get('email', '')
        mensagem = request.POST.get('mensagem', '')
        email = EmailMessage(
            _("Mensagem de Cursos Online"),
            _("De {} <{}> escreveu:\n\n{}").format(nome, email, mensagem),
            "nao-responder@inbox.mailtrap.io",
            ["cursos_online@cursos_online.com"],
            reply_to=[email]
        )
        try:
            email.send()
            send = True
        except:
            send = False
        form = FormContatoCurso()
    context = {
        'form': form,
        'success': send
    }
    return render(request, 'cursos/contato_curso.html', context)


# faz inscrição
@login_required
def enrollment(request, slug):
    curso = get_object_or_404(Cursos, slug=slug)
    enrollment, created = Enrollment.objects.get_or_create(
        usuario=request.user,
        curso=curso
    )
    if created:
        enrollment.ativo()
        messages.success(request, _('Inscrição realizada com sucesso!!!'))
    else:
        messages.info(request, _('Usuário já inscrito neste curso.'))
    return redirect('accounts:painel')


# cancelar inscrição
@login_required
def cancelar_enrollment(request, slug):
    curso = get_object_or_404(Cursos, slug=slug)
    enrollment = get_object_or_404(
        Enrollment,
        usuario=request.user,
        curso=curso
    )
    if request.method == 'POST':
        enrollment.delete()
        messages.success(request, _('Inscrição cancelada com sucesso!!!'))
        return redirect('accounts:painel')
    template_name = 'cursos/cancelar_inscricao.html'
    context = {
        'enrollment': enrollment,
        'curso': curso,
    }
    return render(request, template_name, context)


@login_required
@inscricao_required
def anuncios(request, slug):
    curso = request.curso
    if request.user.is_authenticated:
        log_event(request, 'view_announcements', course=curso)
    template_name = 'cursos/anuncios.html' 
    context = {
        'curso': curso,
        'anuncios': curso.anuncios.all()
    }
    return render(request, template_name, context)


@login_required
@inscricao_required
def painel_anuncio(request, slug, pk):
    curso = request.curso
    if request.user.is_authenticated:
        log_event(request, 'view_announcements', course=curso)
    anuncio = get_object_or_404(curso.anuncios.all(), pk=pk)
    form = ComentariosForm(request.POST or None)
    if form.is_valid():
        comentario = form.save(commit=False)
        comentario.usuario = request.user
        comentario.anuncio = anuncio
        comentario.save()
        form = ComentariosForm()
        messages.success(request, _('Seu comentário foi salvo com sucesso!!!'))

    template_name = 'cursos/anuncio.html'
    context = {
        'curso': curso,
        'anuncio': anuncio,
        'form': form,
    }
    return render(request, template_name, context)


@login_required
@inscricao_required
def aulas(request, slug):
    curso = request.curso
    if request.user.is_authenticated:
        log_event(request, 'view_course', course=curso)
    aulas = curso.aulas_disponiveis()
    if not request.user.is_staff:
        aulas = curso.aula.all()
    template_name = 'cursos/aulas.html'
    context = {
        'curso': curso,
        'aulas' : aulas
    }
    return render(request, template_name, context)


@login_required
@inscricao_required
def aula(request, slug, pk):
    curso = request.curso
    aula = get_object_or_404(Aulas, pk=pk, curso=curso)
    if not request.user.is_staff or not aula.is_disponivel():
        messages.error(request, _('Esta aula não está disponível'))
        return redirect('cursos:aulas', slug=curso.slug)
    if request.user.is_authenticated:
        log_event(
            request,
            'view_lesson',
            course=curso,
            metadata={'aula_id': aula.pk, 'aula_nome': aula.nome},
        )
    template_name = 'cursos/aula.html'
    context = {
        'curso': curso,
        'aula' : aula
    }
    return render(request, template_name, context)


@login_required
@inscricao_required
def material(request, slug, pk):
    curso = request.curso
    aula = get_object_or_404(Aulas, pk=pk, curso=curso)
    material = get_object_or_404(Materiais, pk=pk, aula__curso=curso)
    if not request.user.is_staff or not aula.is_disponivel():
        messages.error(request, _('Este material não está disponível para download.'))
        return redirect('cursos:aula', slug=curso.slug, pk=aula.pk)
    if request.user.is_authenticated:
        log_event(
            request,
            'view_material',
            course=curso,
            metadata={'material_id': material.pk, 'material_nome': material.nome},
        )
    if not material.is_embutido():
        return redirect(material.arquivo.url)
    template_name = 'cursos/material.html'
    context = {
        'curso': curso,
        'aula' : aula, 
        'material': material
    }
    return render(request, template_name, context)


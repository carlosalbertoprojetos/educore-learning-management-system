from datetime import timezone

from accounts.mail import send_email_template
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



class CursosManager(models.Manager):

    def search(self, query):
        return self.get_queryset().filter(
            models.Q(nome__icontains=query) |
            models.Q(descricao__icontains=query)
        )
# o models.Q() é uma espécie de filtro ( | sgnifica 'OU' e & significa 'E')


class Cursos(models.Model):
    nome = models.CharField(_('Nome'), max_length=100)
    slug = models.SlugField(_('Atalho'))
    descricao = models.TextField(_('Descrição Simples'), blank=True)
    sobre = models.TextField(_('Sobre o Curso'), blank=True)
    data_inicial = models.DateField(
        _('Data de início'), null=True, blank=True,
    )
    imagem = models.ImageField(
        upload_to='cursos/imagens', verbose_name=_('Imagem'),
        null=True, blank=True
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    objects = CursosManager()

    def __str__(self):
        return str(self.nome)

    def get_absolute_url(self):
        return reverse('cursos:detalhes_curso', args=[self.slug])

    def aulas_disponiveis(self):
        hoje = timezone.now().date()
        return self.aula.filter(inicio__lte=hoje)

    class Meta:
        verbose_name = _('Curso')
        verbose_name_plural = _('Cursos')
        ordering = ['nome']  # ['-name'] ordem decrescente


class Aulas(models.Model):
    curso = models.ForeignKey(
        Cursos, verbose_name=_('Curso'), related_name='aula', on_delete=models.DO_NOTHING)
    nome = models.CharField(_('Nome'), max_length=100)
    descricao = models.TextField(_('Descrição'), blank=True)
    numero = models.IntegerField(_('Número (ordem)'), blank=True, default=0)
    inicio = models.DateField(_('Disponível em'), blank=True, null=True)

    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    def __str__(self):
        return self.nome

    # verifica se a aula foi disponibilizada - se seu início é >= a hoje
    def is_disponivel(self):
        if self.inicio:
            hoje = timezone.now().date()
            return self.inicio >= hoje
        return False

    class Meta:
        verbose_name = _('Aula')
        verbose_name_plural = _('Aulas')
        ordering = ['-numero']


class Materiais(models.Model):
    aula = models.ForeignKey(
        Aulas, verbose_name=_('Aulas'), related_name='material', on_delete=models.DO_NOTHING)
    nome = models.CharField(_('Nome'), max_length=100)
    embutido = models.TextField(_('Vídeo da aula'), blank=True)
    arquivo = models.FileField(
        upload_to='aulas/materiais', blank=True, null=True)

    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    def is_embutido(self):
        return bool(self.embutido)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = _('Material')
        verbose_name_plural = _('Materiais')


class Enrollment(models.Model):

    STATUS_CHOICES = (
        (0, _('Pendente')),
        (1, _('Aprovado')),
        (2, _('Cancelado')),
        (3, _('Recusado')),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Usuário'),
        related_name='enrollments',
        on_delete=models.DO_NOTHING
    )
    curso = models.ForeignKey(
        Cursos, verbose_name=_('Curso'),
        related_name='enrollments',
        on_delete=models.DO_NOTHING
    )
    status = models.IntegerField(
        _('Situação'),
        choices=STATUS_CHOICES,
        default=0,
        blank=True
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Inscrição')
        verbose_name_plural = _('Inscrições')
        """ 
        unique_together/unicidade - combina a unicidade entre cursos e usuário,
        ou seja, cada usuário se increve apenas uma vez para cada curso.
        """
        unique_together = (('usuario', 'curso'),)

    def ativo(self):
        self.status = 1
        self.save()

    def aprovado(self):
        return self.status == 1

    def __str__(self):
        return self.usuario


class Anuncios(models.Model):
    curso = models.ForeignKey(
        Cursos,
        verbose_name=_('Curso'),
        related_name='anuncios',
        on_delete=models.DO_NOTHING
    )
    titulo = models.CharField(_('Título'), max_length=100)
    conteudo = models.TextField(_('Conteúdo'), blank=True)

    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = _('Anúncio')
        verbose_name_plural = _('Anúncios')
        ordering = ['-criado_em']


class Comentarios(models.Model):
    anuncio = models.ForeignKey(
        Anuncios, verbose_name=_('Anúncio'), related_name='comentarios',
        on_delete=models.DO_NOTHING
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Usuário'),
        on_delete=models.DO_NOTHING
    )
    comentario = models.TextField(_('Comentário'), blank=True)

    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now_add=True)

    class Meta:
        verbose_name = _('Comentário')
        verbose_name_plural = _('Comentários')
        ordering = ['-criado_em']

    def __str__(self):
        return str(self.anuncio.curso)

# ao registrar novo curso um email é disparado aos alunos cadastrados


def post_save_anuncio(instance, created, **kwargs):
    if created:
        subject = instance.titulo
        context = {
            'anuncio': instance
        }
        template_name = 'cursos/anuncio_email.html'
        enrollments = Enrollment.objects.filter(
            curso=instance.curso,
            status=1
        )
        for enrollment in enrollments:
            recipient_list = [enrollment.usuario.email]
            send_email_template(subject, template_name,
                                context, recipient_list)


models.signals.post_save.connect(
    receiver=post_save_anuncio, sender=Anuncios,
    dispatch_uid='envio_anuncio_email'
)

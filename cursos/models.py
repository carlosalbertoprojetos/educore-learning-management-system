from datetime import timezone

from accounts.mail import send_email_template
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone



class CursosManager(models.Manager):

    def search(self, query):
        return self.get_queryset().filter(
            models.Q(nome__icontains=query) |
            models.Q(descricao__icontains=query)
        )
# o models.Q() é uma espécie de filtro ( | sgnifica 'OU' e & significa 'E')


class Cursos(models.Model):
    nome = models.CharField('Nome', max_length=100)
    slug = models.SlugField('Atalho')
    descricao = models.TextField('Descrição Simples', blank=True)
    sobre = models.TextField('Sobre o Curso', blank=True)
    data_inicial = models.DateField(
        'Data de início', null=True, blank=True,
    )
    imagem = models.ImageField(
        upload_to='cursos/imagens', verbose_name='Imagem',
        null=True, blank=True
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em ', auto_now_add=True)

    objects = CursosManager()

    def __str__(self):
        return str(self.nome)

    def get_absolute_url(self):
        return reverse('cursos:detalhes_curso', args=[self.slug])

    def aulas_disponiveis(self):
        hoje = timezone.now().date()
        return self.aula.filter(inicio__lte=hoje)

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['nome']  # ['-name'] ordem decrescente


class Aulas(models.Model):
    curso = models.ForeignKey(
        Cursos, verbose_name='Curso', related_name='aula', on_delete=models.DO_NOTHING)
    nome = models.CharField('Nome', max_length=100)
    descricao = models.TextField('Descrição', blank=True)
    numero = models.IntegerField('Número (ordem)', blank=True, default=0)
    inicio = models.DateField('Disponível em', blank=True, null=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now_add=True)

    def __str__(self):
        return self.nome

    # verifica se a aula foi disponibilizada - se seu início é >= a hoje
    def is_disponivel(self):
        if self.inicio:
            hoje = timezone.now().date()
            return self.inicio >= hoje
        return False

    class Meta:
        verbose_name = 'Aula'
        verbose_name_plural = 'Aulas'
        ordering = ['-numero']


class Materiais(models.Model):
    aula = models.ForeignKey(
        Aulas, verbose_name='Aulas', related_name='material', on_delete=models.DO_NOTHING)
    nome = models.CharField('Nome', max_length=100)
    embutido = models.TextField('Vídeo da aula', blank=True)
    arquivo = models.FileField(
        upload_to='aulas/materiais', blank=True, null=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now_add=True)

    def is_embutido(self):
        return bool(self.embutido)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiais'


class Enrollment(models.Model):

    STATUS_CHOICES = (
        (0, 'Pendente'),
        (1, 'Aprovado'),
        (2, 'Cancelado'),
        (3, 'Recusado'),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Usuário',
        related_name='enrollments',
        on_delete=models.DO_NOTHING
    )
    curso = models.ForeignKey(
        Cursos, verbose_name='Curso',
        related_name='enrollments',
        on_delete=models.DO_NOTHING
    )
    status = models.ImageField(
        'Situação',
        choices=STATUS_CHOICES,
        default=0,
        blank=True
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em ', auto_now_add=True)

    class Meta:
        verbose_name = 'Inscrição'
        verbose_name_plural = 'Inscrições'
        """ 
        unique_together/unicidade - combina a unicidade entre cursos e usuário,
        ou seja, cada usuário se increve apenas uma vez para cada curso.
        """
        unique_together = (('usuario', 'curso'),)

    def ativo(self):
        self.status = '1'
        self.save()

    def aprovado(self):
        return self.status == '1'

    def __str__(self):
        return self.usuario


class Anuncios(models.Model):
    curso = models.ForeignKey(
        Cursos,
        verbose_name='Curso',
        related_name='anuncios',
        on_delete=models.DO_NOTHING
    )
    titulo = models.CharField('Título', max_length=100)
    conteudo = models.TextField('Conteúdo', blank=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now_add=True)

    def __str__(self):
        return self.titulo

    class Meta:
        verbose_name = 'Anúncio'
        verbose_name_plural = 'Anúncios'
        ordering = ['-criado_em']


class Comentarios(models.Model):
    anuncio = models.ForeignKey(
        Anuncios, verbose_name='Anúncio', related_name='comentarios',
        on_delete=models.DO_NOTHING
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Usuário',
        on_delete=models.DO_NOTHING
    )
    comentario = models.TextField('Comentário', blank=True)

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
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

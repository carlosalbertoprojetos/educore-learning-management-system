from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from taggit.managers import TaggableManager



class Thread(models.Model):
    
    title = models.CharField(_('Título'), max_length=100)
    slug = models.SlugField(_('Identificador'), max_length=100, unique=True)
    body = models.TextField(_('Mensagem'))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Autor'), related_name='threads'
    )
    views = models.IntegerField(_('Visualizações'), blank=True, default=0)
    answers = models.IntegerField(_('Respostas'), blank=True, default=0)
    
    tags = TaggableManager()
    
    created = models.DateTimeField(_('Criado em'), auto_now_add=True)
    modified = models.DateTimeField(_('Modificado em'), auto_now=True)
   
    
    class Meta:
        verbose_name = _('Tópico')
        verbose_name_plural = _('Tópicos')
        ordering = ['-modified']
        
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('forum:thread', args=[self.slug])

class Reply(models.Model):
    
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, verbose_name=_('Tópico'), related_name='replies'
        )
    reply = models.TextField(_('Resposta'))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Autor'), related_name='replies'
    )
    correct = models.BooleanField(_('Correta?'), blank=True, default=False)
    
    created = models.DateTimeField(_('Criado em'), auto_now_add=True)
    modified = models.DateTimeField(_('Modificado em'), auto_now=True)
 
    def __str__(self):
        return self.reply[:100]
 
    class Meta:
        verbose_name = _('Resposta')
        verbose_name_plural = _('Respostas')
        ordering = ['-correct', 'created']


def post_save_reply(instance, **kwargs):
    instance.thread.answers = instance.thread.replies.count()
    instance.thread.save()
    # apenas uma resposta correta
    if instance.correct:
        instance.thread.replies.exclude(pk=instance.pk).update(
            correct=False
            )

def post_delete_reply(instance, **kwargs):
    instance.thread.answers = instance.thread.replies.count()
    instance.thread.save()

models.signals.post_save.connect (
    post_save_reply, sender=Reply, dispatch_uid='post_save_reply'
)
        
models.signals.post_delete.connect (
    post_delete_reply, sender=Reply, dispatch_uid='post_delete_reply'
)
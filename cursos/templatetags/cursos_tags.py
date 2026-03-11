from django.template import Library

register = Library()  


from cursos.models import Enrollment

# faz com que todos os cursos sejam listados em todas as dependências/referenciadas no dashboard
@register.inclusion_tag('cursos/templatetags/meus_cursos.html')
def meus_cursos(user):
    enrollments = Enrollment.objects.filter(usuario=user)
    context = {
        'enrollments': enrollments,
    }
    return context


@register.simple_tag
def listar_meus_cursos(user):
    return Enrollment.objects.filter(usuario=user)



from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import Cursos, Enrollment


def inscricao_required(view_func):
    def _wrapper(request, *args, **kwargs):
        slug = kwargs["slug"]
        curso = get_object_or_404(Cursos, slug=slug)
        has_permission = request.user.is_staff
        if not has_permission:
            try:
                enrollment = Enrollment.objects.get(
                    usuario=request.user, curso=curso
                )
            except Enrollment.DoesNotExist:
                message = "Desculpe, voce ainda nao esta inscrito para este curso."
            else:
                if enrollment.aprovado():
                    has_permission = True
                else:
                    message = "A sua inscricao no curso ainda esta pendente"
        if not has_permission:
            messages.error(request, message)
            return redirect("accounts:painel")
        request.curso = curso
        return view_func(request, *args, **kwargs)
    return _wrapper

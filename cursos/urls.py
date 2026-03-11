from django.urls import path

from . import views

app_name = 'cursos'


urlpatterns = [
    path('', views.lista_cursos_view, name='lista_cursos'),
    path('contato/', views.contato_curso_view, name='contato'),
    path('<slug:slug>/', views.detalhes_curso_view, name='detalhes_curso'),
    path('<slug:slug>/inscricao/', views.enrollment, name='enrollment'),
    path('<slug:slug>/cancelar-inscricao/', views.cancelar_enrollment, name='cancelar_enrollment'),
    path('<slug:slug>/anuncios/', views.anuncios, name='anuncios'),
    path('<slug:slug>/anuncio/<int:pk>/', views.painel_anuncio, name='anuncio'),
    
    path('<slug:slug>/aulas/', views.aulas, name='aulas'),
    path('<slug:slug>/<int:pk>/aula/', views.aula, name='aula'),
    
    path('<slug:slug>/<int:pk>/material/', views.material, name='material'),
]



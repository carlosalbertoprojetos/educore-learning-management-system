from django.urls import path
from django.contrib.auth import views as auth_views


from . import views


app_name = 'accounts'

urlpatterns = [
    path('entrar/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('painel/', views.painel, name='painel'),
    path('cadastrar/', views.CadastrarUsuarioView.as_view(), name='cadastrar_usuario'),
    path('editar/usuario/', views.editar_usuario, name='editar_usuario'),
    path('editar/senha/', views.editar_senha, name='editar_senha'),
    path('novasenha/senha/', views.resetar_senha, name='resetar_senha'),
    path('confirmar/novasenha/<str:key>/', views.confirmar_resetar_senha, name='confirmar_resetar_senha'),
]


# condirmar_reset_senha



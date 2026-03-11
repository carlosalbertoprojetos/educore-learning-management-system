from django.contrib import admin

from .models import Cursos, Enrollment, Anuncios, Comentarios, Aulas, Materiais


class CursosAdmin(admin.ModelAdmin):
    list_display = ['nome', 'slug', 'data_inicial', 'criado_em']
    search_fields = ['nome', 'slug']
    prepopulated_fields = {'slug':('nome',)}
    
    
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'curso', 'status', 'criado_em']
    search_fields = ['usuario', 'curso']


class MateriaisAdmin(admin.StackedInline):
    model = Materiais
    extra = 1


class AulasAdmin(admin.ModelAdmin):
    model = Aulas
    list_display = ['nome', 'numero', 'curso', 'inicio', 'criado_em', 'atualizado_em']
    search_fields = ['nome', 'descricao', 'inicio']
    list_filter = ['criado_em',]
    
    inlines = [
        MateriaisAdmin
    ]


    
admin.site.register(Cursos, CursosAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)    
admin.site.register([Anuncios, Comentarios, Materiais])
admin.site.register(Aulas, AulasAdmin) 
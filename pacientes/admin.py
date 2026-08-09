from django.contrib import admin
from .models import Paciente, HitoClinico

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre_completo', 'nivel_dependencia')
    search_fields = ('rut', 'nombre_completo')
    list_filter = ('nivel_dependencia',)

@admin.register(HitoClinico)
class HitoClinicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'responsable', 'fecha')
    list_filter = ('fecha',)

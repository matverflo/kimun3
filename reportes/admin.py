from django.contrib import admin
from .models import RegistroSesionArt33

@admin.register(RegistroSesionArt33)
class RegistroSesionArt33Admin(admin.ModelAdmin):
    list_display = ('usuario', 'modulo_visitado', 'fecha_entrada', 'direccion_ip')
    list_filter = ('fecha_entrada', 'modulo_visitado')
    search_fields = ('usuario__username', 'direccion_ip')
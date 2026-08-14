from django.db import models
from django.conf import settings

class RegistroSesionArt33(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registros_sesion'
    )
    modulo_visitado = models.CharField(max_length=200, verbose_name='Módulo Visitado')
    fecha_entrada = models.DateTimeField(verbose_name='Fecha/Hora de Entrada')
    fecha_salida = models.DateTimeField(null=True, blank=True, verbose_name='Fecha/Hora de Salida')
    direccion_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Dirección IP')

    class Meta:
        verbose_name = 'Registro Sesión (Art. 33)'
        verbose_name_plural = 'Registros de Sesión (Art. 33)'
        ordering = ['-fecha_entrada']

    def __str__(self):
        return f"{self.usuario} - {self.modulo_visitado} - {self.fecha_entrada.strftime('%d/%m/%Y')}"

class ReporteUpskilling(models.Model):
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    datos_json = models.JSONField()

    class Meta:
        ordering = ['-fecha_generacion']

class ReporteNuevosCursos(models.Model):
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    datos_json = models.JSONField()

    class Meta:
        ordering = ['-fecha_generacion']

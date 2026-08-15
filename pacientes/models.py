from django.db import models
from django.conf import settings

class Paciente(models.Model):
    NIVEL_DEPENDENCIA_CHOICES = [
        ('leve', 'Leve'),
        ('moderada', 'Moderada'),
        ('severa', 'Severa'),
        ('postrado', 'Postrado'),
    ]

    rut = models.CharField(max_length=12, unique=True, verbose_name='RUT')
    nombre_completo = models.CharField(max_length=200, verbose_name='Nombre Completo')
    edad = models.PositiveIntegerField(verbose_name='Edad')
    nivel_dependencia = models.CharField(max_length=20, choices=NIVEL_DEPENDENCIA_CHOICES, verbose_name='Nivel de Dependencia')
    patologias = models.TextField(verbose_name='Patologías Diagnósticas', blank=True)
    requerimientos_especiales = models.TextField(verbose_name='Requerimientos Especiales', blank=True)
    
    colaboradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='pacientes_asignados',
        blank=True,
        verbose_name='Colaboradores Asignados'
    )
    
    fecha_ingreso = models.DateField(auto_now_add=True, verbose_name='Fecha de Ingreso')
    activo = models.BooleanField(default=True, verbose_name='Paciente Activo')
    
    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'

    def __str__(self):
        return f"{self.nombre_completo} - {self.get_nivel_dependencia_display()}"


class HitoClinico(models.Model):
    IMPORTANCIA_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
    ]

    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='hitos_clinicos')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='hitos_creados')
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha del Hito')
    descripcion = models.TextField(verbose_name='Descripción del Hito')
    importancia = models.CharField(max_length=10, choices=IMPORTANCIA_CHOICES, default='baja', verbose_name='Nivel de Importancia')

    class Meta:
        verbose_name = 'Hito Clínico'
        verbose_name_plural = 'Hitos Clínicos'
        ordering = ['-fecha']

    def __str__(self):
        return f"Hito {self.paciente.nombre_completo} - {self.fecha.strftime('%d/%m/%Y')}"


class RecetaMedica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='recetas')
    colaborador_encargado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='rutinas_asignadas', verbose_name='Colaborador Titular')
    titulo = models.CharField(max_length=200, verbose_name='Tarea o Medicamento')
    detalles = models.TextField(verbose_name='Detalles / Dosis', blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True, verbose_name='Receta Activa')

    class Meta:
        verbose_name = 'Receta / Tarea Diaria'
        verbose_name_plural = 'Recetas / Tareas Diarias'

    def __str__(self):
        return f"{self.titulo} - {self.paciente.nombre_completo}"


class RegistroRutinaDiaria(models.Model):
    receta = models.ForeignKey(RecetaMedica, on_delete=models.CASCADE, related_name='registros')
    fecha_completada = models.DateTimeField(auto_now_add=True, verbose_name='Fecha Completada')
    completada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='rutinas_completadas', verbose_name='Realizado por')

    class Meta:
        verbose_name = 'Registro de Rutina'
        verbose_name_plural = 'Registros de Rutinas'

    def __str__(self):
        return f"Completado: {self.receta.titulo} - {self.fecha_completada.strftime('%d/%m/%Y')}"

class ReporteAsignacionIA(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='reportes_ia')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    datos_json = models.JSONField()

    class Meta:
        ordering = ['-fecha_generacion']

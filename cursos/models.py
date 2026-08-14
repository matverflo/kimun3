from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from ckeditor.fields import RichTextField


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#6366f1', help_text='Color en formato hex, ej: #6366f1')
    descripcion = models.TextField(blank=True, default='')
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Curso(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('publicado', 'Publicado'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cursos'
    )
    docente_creador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cursos_creados'
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    horas_exigidas = models.PositiveIntegerField(default=0, help_text='Horas totales exigidas para completar el curso')
    horas_por_semana = models.PositiveIntegerField(default=0, help_text='Horas de dedicación semanal esperada')
    exige_tiempo_minimo = models.BooleanField(default=False, help_text='Evita que el alumno complete el curso en menos tiempo del exigido')
    duracion_minutos = models.PositiveIntegerField(default=0, help_text='Duración estimada en minutos')

    # --- CAMPOS EXIGIDOS POR PROTOCOLO SENAMA ---
    responsable = models.CharField(max_length=200, blank=True, help_text='Nombre o cargo del responsable de impartir el curso')
    fundamentacion = RichTextField(blank=True, help_text='Justificación del curso según necesidades detectadas')
    objetivo_general = RichTextField(blank=True, help_text='Objetivo general de aprendizaje')
    metodologia = RichTextField(blank=True, help_text='Metodología de enseñanza (ej: E-learning, Mixto)')
    formato_evaluacion = RichTextField(blank=True, help_text='Cómo se evaluarán los conocimientos adquiridos')

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    def __str__(self):
        return self.titulo

    @property
    def duracion_horas(self):
        """Retorna la duración estimada en horas (float)"""
        return round(self.duracion_minutos / 60.0, 1) if self.duracion_minutos else 0

    @property
    def semanas_estimadas(self):
        import math
        if self.horas_exigidas > 0 and self.horas_por_semana > 0:
            return math.ceil(self.horas_exigidas / self.horas_por_semana)
        return 0


class Material(models.Model):
    TIPO_CHOICES = [
        ('pdf', 'PDF'),
        ('video', 'Video URL'),
    ]

    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='materiales')
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    archivo = models.FileField(upload_to='materiales/', null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"


class InscripcionCurso(models.Model):
    ESTADO_CHOICES = [
        ('asignado', 'Asignado'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscripciones'
    )
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='inscripciones')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='asignado')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Inicio Real')
    fecha_termino = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Término')
    fecha_limite = models.DateTimeField(null=True, blank=True, verbose_name='Fecha Límite')
    inicio_atrasado = models.BooleanField(default=False, help_text='Indica si el alumno inició el curso con retraso y se le otorgó prórroga')

    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        unique_together = ['usuario', 'curso']

    def __str__(self):
        return f"{self.usuario} - {self.curso} ({self.get_estado_display()})"


class Modulo(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='modulos')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, default='')
    orden = models.PositiveIntegerField(default=1, help_text='Orden del módulo en el curso')

    class Meta:
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
        ordering = ['orden']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(orden__gte=1),
                name='modulo_orden_minimo'
            ),
        ]

    def __str__(self):
        return f"Módulo {self.orden}: {self.titulo}"


class Clase(models.Model):
    """Clase/Lección dentro de un curso - contenido rico con CKEditor"""
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='clases')
    modulo = models.ForeignKey(Modulo, on_delete=models.SET_NULL, null=True, blank=True, related_name='clases')
    titulo = models.CharField(max_length=200)
    contenido = RichTextField(verbose_name='Contenido de la clase')
    orden = models.PositiveIntegerField(default=1, help_text='Orden de la clase en el curso')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        ordering = ['orden']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(orden__gte=1),
                name='clase_orden_minimo'
            ),
        ]

    def __str__(self):
        return f"{self.orden}. {self.titulo}"

    def clean(self):
        super().clean()
        if self.orden is not None and self.orden < 1:
            raise ValidationError({'orden': 'El orden debe ser mayor a 0.'})

    def get_clase_anterior(self):
        """Retorna la clase anterior en el orden, o None si es la primera"""
        return Clase.objects.filter(
            curso=self.curso,
            orden__lt=self.orden
        ).order_by('-orden').first()

    def get_siguiente_clase(self):
        """Retorna la siguiente clase en el orden, o None si es la última"""
        return Clase.objects.filter(
            curso=self.curso,
            orden__gt=self.orden
        ).order_by('orden').first()


class ClaseCompletado(models.Model):
    """Registro de completación de una clase por un usuario"""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clases_completadas'
    )
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='completados')
    fecha_completado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Clase Completada'
        verbose_name_plural = 'Clases Completadas'
        unique_together = ['usuario', 'clase']

    def __str__(self):
        return f"{self.usuario} - {self.clase.titulo} ({self.fecha_completado.strftime('%d/%m/%Y')})"
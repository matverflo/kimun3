from django.db import models
from django.contrib.auth.models import AbstractUser


class AreaCargo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    limite_pacientes = models.PositiveIntegerField(
        default=0, 
        help_text='Límite máximo de pacientes asignables para este rol. 0 significa sin límite.'
    )

    class Meta:
        verbose_name = 'Área/Cargo'
        verbose_name_plural = 'Áreas/Cargos'

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('docente', 'Docente'),
        ('colaborador', 'Colaborador'),
    ]

    rut = models.CharField(max_length=12, unique=True, verbose_name='RUT')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='colaborador')
    cargo = models.ForeignKey(
        AreaCargo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    fecha_ingreso = models.DateField(null=True, blank=True, verbose_name='Fecha de Ingreso')
    telefono = models.CharField(max_length=20, null=True, blank=True, verbose_name='Teléfono')
    especialidades_externas = models.TextField(
        null=True, 
        blank=True, 
        help_text='Especialidades, conocimientos o habilidades adquiridas fuera de Kimün.',
        verbose_name='Especialidades Externas'
    )
    limite_pacientes_personalizado = models.IntegerField(
        null=True, 
        blank=True, 
        help_text='Si se define, sobreescribe el límite del cargo del usuario.'
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"


class Recordatorio(models.Model):
    TIPO_CHOICES = [
        ('7_dias', '7 días antes'),
        ('3_dias', '3 días antes'),
        ('1_dia', '1 día antes'),
        ('vencimiento', 'Día del vencimiento'),
    ]

    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='recordatorios'
    )
    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.CASCADE,
        related_name='recordatorios'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recordatorio'
        verbose_name_plural = 'Recordatorios'
        unique_together = ['usuario', 'curso', 'tipo']

    def __str__(self):
        return f"{self.usuario} - {self.curso.titulo} ({self.get_tipo_display()})"
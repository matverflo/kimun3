import os
import django
from cursos.models import Curso
from evaluaciones.models import Evaluacion, Pregunta, BancoPreguntas
from usuarios.models import Usuario

creador = Usuario.objects.filter(rol__in=['docente', 'admin']).first()
if not creador:
    creador = Usuario.objects.first()

curso = Curso.objects.filter(titulo__icontains="Cuidado Integral del Adulto Mayor").first()
if curso:
    if not Evaluacion.objects.filter(curso=curso, titulo="Evaluación Final: Certificación de Cuidados").exists():
        banco = BancoPreguntas.objects.create(
            nombre="Banco Evaluación Final",
            curso=curso,
            creado_por=creador,
            es_publico=False
        )
        eval_final = Evaluacion.objects.create(
            curso=curso,
            titulo="Evaluación Final: Certificación de Cuidados",
            porcentaje_aprobacion=80,
            max_intentos=3,
            orden=6
        )
        Pregunta.objects.create(
            evaluacion=eval_final, banco=banco,
            texto="1. Ante un paciente con demencia que afirma que 'le robaron su dinero', la mejor respuesta es: a) Discutirle y probarle que lo gastó. b) Validar su preocupación y ayudarle a 'buscarlo' amablemente para calmarlo. c) Ignorarlo. d) Enojarte con él."
        )
        Pregunta.objects.create(
            evaluacion=eval_final, banco=banco,
            texto="2. ¿Cuál es la regla de oro para prevenir las escaras en pacientes postrados? a) Cambios posturales cada 2 horas. b) Baños con agua fría. c) Dar masajes fuertes. d) Mantenerlos inmovilizados."
        )
        print("Evaluación final agregada al curso con éxito.")
    else:
        print("La evaluación final ya existe.")

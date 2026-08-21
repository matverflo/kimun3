from django.core.management.base import BaseCommand
from cursos.models import Curso, Categoria, Modulo, Clase
from evaluaciones.models import Evaluacion, Pregunta, Alternativa
from usuarios.models import Usuario
from cursos.models import InscripcionCurso

class Command(BaseCommand):
    help = 'Crea un curso de prueba 100% completo y un colaborador demo'

    def handle(self, *args, **kwargs):
        # 1. Crear el usuario Docente/Admin si no existe
        docente, created = Usuario.objects.get_or_create(
            email='docente_demo@kimun.cl',
            defaults={
                'username': 'docente_demo',
                'first_name': 'Profesor',
                'last_name': 'Demo',
                'rol': 'docente',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            docente.set_password('kimun2024')
            docente.save()

        # 2. Crear un Colaborador para que tome el curso
        colaborador, created = Usuario.objects.get_or_create(
            email='colaborador_demo@kimun.cl',
            defaults={
                'username': 'colaborador_demo',
                'first_name': 'Juan',
                'last_name': 'Pérez (Demo)',
                'rol': 'colaborador',
                'is_active': True,
            }
        )
        if created:
            colaborador.set_password('kimun2024')
            colaborador.save()

        # 3. Crear Categoría y Curso
        cat, _ = Categoria.objects.get_or_create(nombre="Salud Geriátrica", defaults={'color': '#10b981'})
        
        curso_titulo = "Curso Demo: Manejo Integral (100% Completo)"
        curso = Curso.objects.filter(titulo=curso_titulo).first()
        if curso:
            self.stdout.write("El curso ya existe. Recreándolo...")
            curso.delete()

        curso = Curso.objects.create(
            titulo=curso_titulo,
            descripcion="Este curso contiene módulos, clases y una evaluación final para probar la plataforma.",
            categoria=cat,
            docente_creador=docente,
            estado='publicado',
            horas_exigidas=10,
            horas_por_semana=2,
            duracion_minutos=600,
            responsable="Profesor Demo",
            fundamentacion="<p>Demostración de un curso completo.</p>",
            objetivo_general="<p>Probar el flujo del estudiante.</p>",
            metodologia="<p>E-learning.</p>",
            formato_evaluacion="<p>Prueba teórica con alternativas.</p>"
        )

        # 4. Crear Módulo y Clase (Contenido)
        modulo = Modulo.objects.create(
            curso=curso,
            titulo="Módulo 1: Introducción a los Cuidados",
            descripcion="Fundamentos básicos",
            orden=1
        )

        Clase.objects.create(
            curso=curso,
            modulo=modulo,
            titulo="1.1 Principios Básicos",
            contenido="<h3>Bienvenido a la Clase 1</h3><p>Esta es una clase de prueba con texto e información esencial.</p>",
            orden=1
        )
        
        Clase.objects.create(
            curso=curso,
            modulo=modulo,
            titulo="1.2 Procedimientos Diarios",
            contenido="<h3>Clase 2</h3><p>Aquí se detallan los procedimientos diarios para los residentes.</p>",
            orden=2
        )

        # 5. Crear Evaluación (Prueba Final)
        evaluacion = Evaluacion.objects.create(
            curso=curso,
            titulo="Prueba Final del Curso",
            porcentaje_aprobacion=70,
            max_intentos=3,
            orden=1
        )

        # Pregunta 1
        p1 = Pregunta.objects.create(evaluacion=evaluacion, texto="¿Cuál es el objetivo principal del cuidado geriátrico?")
        Alternativa.objects.create(pregunta=p1, texto="Mantener la calidad de vida e independencia", es_correcta=True)
        Alternativa.objects.create(pregunta=p1, texto="Solo administrar medicamentos", es_correcta=False)
        Alternativa.objects.create(pregunta=p1, texto="Aislar al paciente", es_correcta=False)

        # Pregunta 2
        p2 = Pregunta.objects.create(evaluacion=evaluacion, texto="En caso de fiebre sobre 38°C, ¿Qué se debe hacer primero?")
        Alternativa.objects.create(pregunta=p2, texto="Dar antibióticos por cuenta propia", es_correcta=False)
        Alternativa.objects.create(pregunta=p2, texto="Avisar a la enfermera o médico de turno", es_correcta=True)
        Alternativa.objects.create(pregunta=p2, texto="Ignorarlo si el paciente se siente bien", es_correcta=False)

        # 6. Inscribir al Colaborador en el curso
        InscripcionCurso.objects.get_or_create(
            usuario=colaborador,
            curso=curso,
            defaults={'estado': 'asignado'}
        )

        self.stdout.write(self.style.SUCCESS('¡Éxito! Curso 100% completo creado y asignado al colaborador.'))
        self.stdout.write(self.style.SUCCESS(f'Usuario Colaborador: {colaborador.email} / Clave: kimun2024'))
        self.stdout.write(self.style.SUCCESS(f'Usuario Profesor: {docente.email} / Clave: kimun2024'))

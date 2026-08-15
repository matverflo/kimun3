import random
from django.core.management.base import BaseCommand
from cursos.models import Curso, Categoria
from usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Puebla la base de datos con ~20 cursos realistas'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Limpiando cursos anteriores...'))
        Curso.objects.all().delete()
        
        # Categorías
        categorias_data = [
            ("Cuidado Integral", "#3b82f6"),
            ("Salud y Enfermería", "#ef4444"),
            ("Salud Mental", "#10b981"),
            ("Nutrición y Dietética", "#f59e0b"),
            ("Prevención de Riesgos", "#f97316"),
            ("Administración ELEAM", "#6366f1")
        ]
        
        cats = []
        for nombre, color in categorias_data:
            cat, _ = Categoria.objects.get_or_create(nombre=nombre, defaults={'color': color})
            cats.append(cat)
            
        docente = Usuario.objects.filter(rol__in=['docente', 'admin']).first()
        if not docente:
            self.stdout.write(self.style.ERROR('No hay usuarios docentes o admin. Crea uno primero.'))
            return
            
        cursos_data = [
            ("Manejo de Pacientes con Alzheimer Etapa Avanzada", 0),
            ("Prevención de Úlceras por Presión (UPP) en Pacientes Postrados", 1),
            ("Técnicas de Movilización y Transferencia Segura", 0),
            ("Nutrición Geriátrica: Dietas Blandas y Papillas", 3),
            ("Higiene y Confort en el Adulto Mayor", 0),
            ("Administración Segura de Medicamentos Vía Oral", 1),
            ("Primeros Auxilios y RCP Básica en Geriatría", 1),
            ("Estimulación Cognitiva a Través del Juego", 2),
            ("Cuidados Paliativos y Acompañamiento Espiritual", 0),
            ("Protocolo de Prevención de Caídas", 4),
            ("Manejo de Conductas Agresivas en Demencia", 2),
            ("Control de Signos Vitales y Reconocimiento de Alarmas", 1),
            ("Bioseguridad y Control de IAAS", 1),
            ("Manejo de Incontinencia y Cuidado de Sondas", 1),
            ("Atención Centrada en la Persona: Trato Digno", 0),
            ("Uso y Mantención de Equipos Clínicos Menores", 1),
            ("Técnicas de Relajación para Cuidadores (Burnout)", 2),
            ("Alimentación por Sonda Nasogástrica y Gastrostomía", 3),
            ("Normativa SENAMA y Ley de Derechos del Adulto Mayor", 5),
            ("Protocolo de Manejo de Urgencias Médicas ELEAM", 4)
        ]
        
        for titulo, cat_index in cursos_data:
            cat = cats[cat_index]
            Curso.objects.create(
                titulo=titulo,
                descripcion=f"Curso integral sobre {titulo.lower()}. Diseñado para dotar al personal clínico y de apoyo de las herramientas necesarias para enfrentar los desafíos diarios.",
                categoria=cat,
                docente_creador=docente,
                estado='publicado',
                horas_exigidas=random.choice([10, 20, 30, 40]),
                horas_por_semana=random.choice([2, 4, 5]),
                duracion_minutos=random.randint(600, 2400),
                responsable="Dirección Técnica ELEAM",
                fundamentacion="<p>Responde a la necesidad crítica de actualizar conocimientos según la normativa vigente y el perfil epidemiológico de los residentes.</p>",
                objetivo_general=f"<p>Capacitar a los colaboradores en {titulo.lower()} para mejorar la calidad de vida de los residentes.</p>",
                metodologia="<p>E-learning asincrónico con evaluación final de selección múltiple.</p>",
                formato_evaluacion="<p>Prueba teórica de 20 preguntas (70% exigencia mínima).</p>"
            )
            
        self.stdout.write(self.style.SUCCESS('¡20 cursos creados exitosamente!'))

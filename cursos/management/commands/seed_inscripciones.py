import random
from django.core.management.base import BaseCommand
from cursos.models import Curso, InscripcionCurso
from usuarios.models import Usuario
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Asigna aleatoriamente cursos a los cuidadores (pendiente, en progreso, terminados)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Eliminando inscripciones anteriores...'))
        InscripcionCurso.objects.all().delete()
        
        cursos = list(Curso.objects.all())
        if not cursos:
            self.stdout.write(self.style.ERROR('No hay cursos. Ejecuta python manage.py seed_cursos primero.'))
            return
            
        cuidadores = Usuario.objects.filter(rol='colaborador')
        if not cuidadores:
            self.stdout.write(self.style.ERROR('No hay colaboradores.'))
            return
            
        estados = ['asignado', 'en_progreso', 'completado']
        now = timezone.now()
        total_asignados = 0
        
        for cuidador in cuidadores:
            # Asignar entre 2 a 6 cursos a cada uno
            num_cursos = random.randint(2, 6)
            cursos_asignados = random.sample(cursos, min(num_cursos, len(cursos)))
            
            for curso in cursos_asignados:
                estado = random.choices(estados, weights=[0.4, 0.3, 0.3])[0]
                
                # Fechas aleatorias en los últimos 45 días
                dias_atras = random.randint(1, 45)
                fecha_asig = now - datetime.timedelta(days=dias_atras)
                
                insc = InscripcionCurso(
                    usuario=cuidador,
                    curso=curso,
                    estado=estado
                )
                insc.save()
                
                # Actualizar fecha de asignación ya que tiene auto_now_add
                InscripcionCurso.objects.filter(id=insc.id).update(fecha_asignacion=fecha_asig)
                
                # Si completado o en progreso, simular fechas de inicio real y fin
                if estado in ['en_progreso', 'completado']:
                    fecha_inicio = fecha_asig + datetime.timedelta(days=random.randint(1, 5))
                    InscripcionCurso.objects.filter(id=insc.id).update(fecha_inicio_real=fecha_inicio)
                
                total_asignados += 1
                
        self.stdout.write(self.style.SUCCESS(f'¡{total_asignados} inscripciones de cursos asignadas a los colaboradores!'))

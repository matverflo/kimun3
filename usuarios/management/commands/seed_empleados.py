import random
import string
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from usuarios.models import Usuario, AreaCargo
from pacientes.models import Paciente

class Command(BaseCommand):
    help = 'Puebla la base de datos con empleados realistas basados en los datos de la ONG Alumco (2023)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Eliminando colaboradores anteriores (manteniendo admins y docentes)...'))
        Usuario.objects.filter(rol='colaborador').delete()

        cargos_data = [
            {'nombre': 'Trabajador Social', 'cantidad': 1},
            {'nombre': 'Cuidador de personas mayores', 'cantidad': 28},
            {'nombre': 'Enfermero', 'cantidad': 1},
            {'nombre': 'Kinesiólogo', 'cantidad': 1},
            {'nombre': 'Nutricionista', 'cantidad': 1},
            {'nombre': 'TENS', 'cantidad': 4},
            {'nombre': 'Terapeuta Ocupacional', 'cantidad': 1},
        ]

        nombres = [
            "María", "Juan", "Pedro", "Camila", "Valentina", "Sebastián", "Diego", 
            "Catalina", "José", "Daniela", "Matías", "Javiera", "Felipe", "Constanza",
            "Carlos", "Andrea", "Nicolás", "Antonia", "Luis", "Fernanda", "Cristóbal"
        ]
        apellidos = [
            "González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", 
            "Silva", "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López", 
            "Fuentes", "Hernández", "Torres", "Araya", "Flores", "Espinoza", "Valenzuela"
        ]

        def generar_rut():
            # Random RUT generation without verification digit accuracy (not strictly needed for dummy data unless validated)
            return f"{random.randint(10, 25)}{random.randint(100, 999)}{random.randint(100, 999)}-{random.choice('0123456789K')}"

        password = make_password('Kimun2024!')
        total_creados = 0

        for cd in cargos_data:
            cargo, created = AreaCargo.objects.get_or_create(nombre=cd['nombre'])
            if created:
                self.stdout.write(f'Cargo creado: {cargo.nombre}')

            for i in range(cd['cantidad']):
                nombre = random.choice(nombres)
                apellido = random.choice(apellidos)
                rut = generar_rut()
                username = f"{nombre.lower()[0]}{apellido.lower()}{random.randint(1,999)}"
                email = f"{username}@kimun.cl"

                # Ensure unique username and rut
                while Usuario.objects.filter(username=username).exists():
                    username = f"{nombre.lower()[0]}{apellido.lower()}{random.randint(1000,9999)}"
                while Usuario.objects.filter(rut=rut).exists():
                    rut = generar_rut()

                usuario = Usuario(
                    username=username,
                    email=email,
                    first_name=nombre,
                    last_name=apellido,
                    rut=rut,
                    password=password,
                    rol='colaborador',
                    cargo=cargo,
                    telefono=f"+569{random.randint(11111111, 99999999)}"
                )
                usuario.save()
                total_creados += 1

        self.stdout.write(self.style.SUCCESS(f'Se crearon {total_creados} colaboradores exitosamente.'))

        # Asignar aleatoriamente algunos pacientes a los nuevos cuidadores para que los dashboards no estén vacíos
        pacientes = list(Paciente.objects.all())
        cuidadores = list(Usuario.objects.filter(cargo__nombre__icontains='cuidador'))
        
        if pacientes and cuidadores:
            self.stdout.write('Asignando pacientes a cuidadores...')
            asignaciones_creadas = 0
            for paciente in pacientes:
                # Assign 1 to 3 caregivers per patient
                num_asignaciones = random.randint(1, 3)
                cuidadores_asignados = random.sample(cuidadores, min(num_asignaciones, len(cuidadores)))
                for cuidador in cuidadores_asignados:
                    # check if already assigned
                    if not paciente.colaboradores.filter(id=cuidador.id).exists():
                        paciente.colaboradores.add(cuidador)
                        asignaciones_creadas += 1
            
            self.stdout.write(self.style.SUCCESS(f'Se generaron {asignaciones_creadas} asignaciones cuidador-paciente.'))

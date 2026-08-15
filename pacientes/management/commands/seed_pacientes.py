import random
from django.core.management.base import BaseCommand
from pacientes.models import Paciente
from usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Puebla la base de datos con 60 pacientes realistas basados en los datos del ELEAM 2025'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Eliminando pacientes anteriores...'))
        Paciente.objects.all().delete()

        nombres_mujeres = ["María", "Rosa", "Margarita", "Carmen", "Ana", "Teresa", "Juana", "Marta", "Gladys", "Silvia", "Elena", "Alicia", "Sonia", "Eliana"]
        nombres_hombres = ["José", "Juan", "Luis", "Carlos", "Manuel", "Pedro", "Jorge", "Héctor", "Mario", "Víctor", "Sergio", "Julio"]
        apellidos = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Hernández"]

        patologias_base = [
            ("Demencia", 0.64),
            ("Incontinencia Urinaria", 0.58),
            ("Hipertensión Arterial", 0.55),
            ("Trastorno de la Marcha", 0.48),
            ("Dolor Crónico", 0.28),
            ("Artrosis", 0.27),
            ("Insuficiencia Renal Crónica", 0.26),
            ("Hipotiroidismo", 0.25),
            ("Constipación", 0.25),
            ("Osteoporosis", 0.25),
            ("Patologías de Salud Mental", 0.24),
            ("Diabetes", 0.23),
            ("Infecciones urinarias recurrentes", 0.14),
            ("Patologías Oncológicas", 0.09),
            ("Lesiones por Presión", 0.03)
        ]

        def generar_rut():
            return f"{random.randint(2, 9)}{random.randint(100, 999)}{random.randint(100, 999)}-{random.choice('0123456789K')}"

        def generar_edad():
            # 60-69 (15%), 70-79 (26%), 80-89 (37%), 90+ (22%)
            r = random.random()
            if r < 0.15: return random.randint(60, 69)
            elif r < 0.41: return random.randint(70, 79)
            elif r < 0.78: return random.randint(80, 89)
            else: return random.randint(90, 102)

        def generar_dependencia():
            # Leve (21.5%), Moderada (28.3%), Severa (25.1%), Postrado (25.1%)
            r = random.random()
            if r < 0.22: return 'leve'
            elif r < 0.50: return 'moderada'
            elif r < 0.75: return 'severa'
            else: return 'postrado'

        cuidadores = list(Usuario.objects.filter(rol='colaborador'))

        for i in range(60):
            es_mujer = random.random() < 0.69
            if es_mujer:
                nombre = f"{random.choice(nombres_mujeres)} {random.choice(nombres_mujeres)}"
            else:
                nombre = f"{random.choice(nombres_hombres)} {random.choice(nombres_hombres)}"
            
            nombre_completo = f"{nombre} {random.choice(apellidos)} {random.choice(apellidos)}"
            
            # Generar patologías
            pats = []
            for pat, prob in patologias_base:
                if random.random() < prob:
                    pats.append(pat)
            
            if len(pats) == 0:
                pats.append(random.choice(["Hipertensión Arterial", "Demencia", "Osteoporosis"]))
            
            rut = generar_rut()
            while Paciente.objects.filter(rut=rut).exists():
                rut = generar_rut()

            p = Paciente.objects.create(
                rut=rut,
                nombre_completo=nombre_completo,
                edad=generar_edad(),
                nivel_dependencia=generar_dependencia(),
                patologias=", ".join(pats),
                requerimientos_especiales="Asistencia en AVD básica." if random.random() < 0.3 else ""
            )

            # Asignar 1-2 cuidadores
            if cuidadores:
                asignados = random.sample(cuidadores, min(len(cuidadores), random.randint(1, 2)))
                for c in asignados:
                    p.colaboradores.add(c)
        
        self.stdout.write(self.style.SUCCESS('¡60 pacientes creados exitosamente basados en la estadística ELEAM 2025!'))

from django.core.management.base import BaseCommand
from cursos.models import Curso, Categoria, Modulo, Clase, InscripcionCurso
from evaluaciones.models import Evaluacion, Pregunta, Alternativa, BancoPreguntas
from tareas.models import Tarea
from usuarios.models import Usuario
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Crea un curso de prueba 100% completo (Adulto Mayor) y un colaborador demo'

    def handle(self, *args, **kwargs):
        # 1. Crear el usuario Docente/Admin si no existe
        docente, created = Usuario.objects.get_or_create(
            email='docente_demo@kimun.cl',
            defaults={
                'username': 'docente_demo',
                'rut': '99999999-9',
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
                'rut': '88888888-8',
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
        cat, _ = Categoria.objects.get_or_create(
            nombre="Salud y Asistencia Social",
            defaults={'color': '#10b981', 'descripcion': 'Cursos de salud y cuidados.'}
        )

        curso_titulo = "Cuidado Integral del Adulto Mayor: Salud, Bienestar y Trato Digno"
        curso = Curso.objects.filter(titulo=curso_titulo).first()
        if curso:
            self.stdout.write("El curso ya existe. Recreándolo...")
            curso.delete()

        curso = Curso.objects.create(
            titulo=curso_titulo,
            descripcion="Nuestros adultos mayores merecen vivir su etapa de madurez con dignidad, respeto y la mejor calidad de vida posible. Este curso está diseñado para capacitar a familiares, voluntarios y cuidadores iniciales en las mejores prácticas de asistencia geriátrica.",
            categoria=cat,
            docente_creador=docente,
            estado='publicado',
            horas_exigidas=25,
            horas_por_semana=6,
            duracion_minutos=1500,
            exige_tiempo_minimo=False,  # Sin límite de tiempo para el demo
            responsable="Profesor Demo",
        )

        # 4. Crear Módulo y Clases
        modulo = Modulo.objects.create(
            curso=curso,
            titulo="Módulo 1: Fundamentos y Cuidados",
            descripcion="Clases completas del curso",
            orden=1
        )

        clases_data = [
            {
                "titulo": "1. Psicología del Envejecimiento y Trato Digno",
                "contenido": "<h2>Introducción</h2><p>El envejecimiento no es solo un proceso físico; viene acompañado de profundos cambios psicológicos y sociales. Muchas veces, la pérdida de amigos, la jubilación, y la disminución de capacidades físicas generan frustración o aislamiento.</p><h3>1. El Duelo por la Pérdida de Autonomía</h3><p>Cuando una persona nota que ya no puede realizar las mismas actividades que antes, experimenta un proceso de duelo. Es fundamental que el cuidador:</p><ul><li><strong>Escuche activamente:</strong> Valide los sentimientos de tristeza o enojo del adulto mayor. No minimice sus emociones diciendo 'no es para tanto'.</li><li><strong>Evite la infantilización:</strong> Un adulto mayor NO es un niño grande. Hablarle con voz de bebé o tratarlo como incapaz daña su autoestima y acelera el deterioro cognitivo.</li></ul><h3>2. Paciencia y Empatía Activa</h3><p>El ritmo de procesamiento de información puede disminuir, al igual que los reflejos físicos.</p><ul><li><strong>Técnica del tiempo de espera:</strong> Después de hacer una pregunta, cuente hasta 5 mentalmente antes de repetir o responder por ellos.</li><li><strong>Validación biográfica:</strong> Preguntarles sobre sus logros pasados refuerza su identidad y sentido de valía.</li></ul><h2>Conclusión</h2><p>Un buen cuidado comienza por la mente. Si logramos que el adulto mayor se sienta respetado, escuchado y útil, su salud física responderá mucho mejor a los tratamientos y rutinas.</p>"
            },
            {
                "titulo": "2. Fomento de la Autonomía vs Asistencialismo",
                "contenido": "<h2>Introducción</h2><p>Una trampa común en el cuidado de ancianos es el <em>asistencialismo excesivo</em>: hacer todo por ellos para 'ahorrarles esfuerzo' o para hacerlo más rápido. A largo plazo, esto atrofia sus capacidades.</p><h3>1. ¿Qué es el Síndrome por Desuso?</h3><p>Cuando dejamos de usar un músculo o una habilidad mental, el cuerpo y el cerebro la desactivan. Si usted abrocha siempre los botones de la camisa del adulto mayor, él olvidará cómo hacerlo.</p><h3>2. Estrategias de Fomento de Autonomía</h3><ul><li><strong>Ayuda Gradual:</strong> Si al adulto mayor le cuesta comer, no le dé en la boca inmediatamente. Primero, acérquele el plato. Si no puede, ayúdele a sostener la cuchara. Intervenga solo lo estrictamente necesario.</li><li><strong>Tareas Adaptadas:</strong> Involúcrelos en la dinámica del hogar. Pueden doblar toallas, pelar verduras o regar plantas pequeñas. Sentirse útiles es vital para la salud mental.</li><li><strong>Modificación de Ropa y Utensilios:</strong> Use zapatos con velcro, pantalones con elástico, y cubiertos con mangos gruesos para que puedan seguir manejándose solos por más tiempo.</li></ul><h2>Reflexión Final</h2><p>'Cuidar bien' no significa 'hacer por el otro', sino 'ayudar al otro a que pueda seguir haciendo'. Su rol es ser un facilitador, no un sustituto.</p>"
            },
            {
                "titulo": "3. Movilidad y Prevención de Caídas",
                "contenido": "<h2>Introducción</h2><p>Las caídas son la principal causa de hospitalización en la tercera edad y a menudo marcan el inicio del declive físico severo (por ejemplo, tras una fractura de cadera). La prevención es su mejor herramienta.</p><h3>1. Modificación del Entorno</h3><p>La mayoría de las caídas ocurren dentro del hogar.</p><ul><li><strong>Pisos y alfombras:</strong> Retire las alfombras pequeñas sueltas. Mantenga el piso seco.</li><li><strong>Iluminación:</strong> Instale luces de noche (sensor de movimiento) en el pasillo entre el dormitorio y el baño.</li><li><strong>Baño:</strong> Instale barras de apoyo dentro de la ducha y junto al inodoro. Use sillas de ducha y pisos antideslizantes.</li></ul><h3>2. Ergonomía para el Cuidador</h3><p>Cuidar de su propia espalda es fundamental para poder seguir ayudando.</p><ul><li><strong>Para levantar a una persona:</strong> Nunca doble la cintura. Doble las rodillas, mantenga la espalda recta y use la fuerza de sus piernas.</li><li><strong>Traslados (Cama a Silla):</strong> Acerque la silla lo más posible. Pídale al adulto mayor que se apoye en sus hombros (nunca en su cuello) mientras usted lo toma por la cintura.</li></ul><h3>3. Uso de Aparatos de Apoyo</h3><ul><li>Asegúrese de que andadores y bastones tengan las gomas inferiores (regatones) en buen estado y no gastadas.</li><li>Ajuste la altura del bastón para que quede al nivel del hueso de la cadera.</li></ul>"
            },
            {
                "titulo": "4. Alimentación e Higiene Personal",
                "contenido": "<h2>Introducción</h2><p>Las rutinas de aseo y alimentación son momentos muy íntimos. Una mala técnica puede generar rechazo, desnutrición o infecciones, pero un buen manejo convierte estos momentos en espacios de conexión.</p><h3>1. Higiene y Prevención de Escaras</h3><p>Para pacientes postrados (en cama):</p><ul><li><strong>Aseo en Cama:</strong> Hágalo por partes para evitar enfriamientos. Siempre de lo más limpio a lo más sucio (cara primero, genitales al final).</li><li><strong>Prevención de Escaras (Úlceras por presión):</strong> La regla de oro es el <em>cambio postural cada 2 horas</em>. Use almohadas bajo pantorrillas y espalda para evitar que los talones y el coxis rocen contra el colchón.</li><li>Piel seca e hidratada: Seque dando toques suaves, nunca frotando con la toalla.</li></ul><h3>2. Alimentación Segura</h3><ul><li>Pacientes con disfagia (dificultad para tragar): Deben comer sentados a 90 grados. No recline la cama hasta 30 minutos después de comer.</li><li>Espesar líquidos si hay riesgo de que el paciente se ahogue (broncoaspiración).</li><li>Fomente la masticación lenta. No apure al adulto mayor.</li></ul>"
            },
            {
                "titulo": "5. Salud Mental, Alzheimer y Demencia",
                "contenido": "<h2>Introducción</h2><p>El deterioro cognitivo no debe verse como un proceso aislado. Enfermedades como el Alzheimer presentan retos enormes para el cuidador, pero existen técnicas para reducir la ansiedad del paciente.</p><h3>1. Trato en Casos de Demencia</h3><ul><li><strong>No discuta la realidad del paciente:</strong> Si un anciano con demencia pide ver a su madre (ya fallecida), decirle 'tu mamá murió hace 30 años' solo le causará un dolor innecesario. Utilice la técnica de 'terapia de validación' (desviar amablemente el tema: <em>'¿La extrañas mucho? Cuéntame cómo hacía tu pastel favorito'</em>).</li><li><strong>Evitar la sobreestimulación:</strong> Ambientes muy ruidosos o con mucha gente pueden provocar irritabilidad o ataques de pánico (fenómeno conocido como 'sundowning' o síndrome del ocaso al atardecer).</li></ul><h3>2. Estimulación Cognitiva (Gimnasia Mental)</h3><p>Dedique 15 minutos al día para realizar ejercicios simples que mantienen activo el cerebro:</p><ul><li>Reconocer objetos por el tacto.</li><li>Escuchar canciones de su juventud y pedir que complete la letra.</li><li>Clasificar objetos por color o forma (botones, cartas, frijoles).</li></ul>"
            }
        ]

        for i, cl in enumerate(clases_data, 1):
            Clase.objects.create(
                curso=curso,
                modulo=modulo,
                titulo=cl['titulo'],
                contenido=cl['contenido'],
                orden=i
            )

        # 5. Crear Evaluacion
        banco = BancoPreguntas.objects.create(
            nombre="Banco de Cuidado Físico",
            curso=curso,
            creado_por=docente,
            es_publico=False
        )
        evaluacion = Evaluacion.objects.create(
            curso=curso,
            titulo="Evaluación Final del Curso",
            porcentaje_aprobacion=70,
            max_intentos=0,
            orden=1
        )
        
        # Preguntas con alternativas
        p1 = Pregunta.objects.create(evaluacion=evaluacion, banco=banco, texto="1. Al tratar con un adulto mayor que está experimentando pérdida de autonomía, la mejor actitud del cuidador es:")
        Alternativa.objects.create(pregunta=p1, texto="Hacer absolutamente todo por él.", es_correcta=False)
        Alternativa.objects.create(pregunta=p1, texto="Escuchar activamente sus frustraciones y fomentar que haga lo que aún puede hacer.", es_correcta=True)
        Alternativa.objects.create(pregunta=p1, texto="Tratarlo como a un niño.", es_correcta=False)
        Alternativa.objects.create(pregunta=p1, texto="Ignorar sus quejas.", es_correcta=False)

        p2 = Pregunta.objects.create(evaluacion=evaluacion, banco=banco, texto="2. ¿Cuál de las siguientes es una medida clave para prevenir caídas en el hogar?")
        Alternativa.objects.create(pregunta=p2, texto="Usar calcetines gruesos en lugar de zapatos.", es_correcta=False)
        Alternativa.objects.create(pregunta=p2, texto="Instalar alfombras pequeñas decorativas.", es_correcta=False)
        Alternativa.objects.create(pregunta=p2, texto="Mantener iluminación adecuada e instalar barras de sujeción en el baño.", es_correcta=True)
        Alternativa.objects.create(pregunta=p2, texto="Pedirle que nunca se levante.", es_correcta=False)

        p3 = Pregunta.objects.create(evaluacion=evaluacion, banco=banco, texto="3. Para prevenir las úlceras por presión (escaras) en un paciente postrado, es fundamental:")
        Alternativa.objects.create(pregunta=p3, texto="Bañarlo con agua muy caliente.", es_correcta=False)
        Alternativa.objects.create(pregunta=p3, texto="Realizar cambios posturales cada 2 o 3 horas.", es_correcta=True)
        Alternativa.objects.create(pregunta=p3, texto="Frotar la piel fuertemente al secarlo.", es_correcta=False)
        Alternativa.objects.create(pregunta=p3, texto="Dejarlo en la misma posición toda la noche.", es_correcta=False)

        # 6. Crear Tarea
        tarea = Tarea.objects.create(
            curso=curso,
            titulo="Tarea Final: Plan de Cuidados y Adaptación del Entorno",
            descripcion="<p><strong>Caso Práctico: Don Luis</strong></p><p>Don Luis tiene 82 años. Vive con usted. Recientemente sufrió una leve caída sin fracturas, pero ahora camina con un andador y se siente muy inseguro al ir al baño. Además, presenta olvidos frecuentes (ej: a veces olvida si almorzó o dónde dejó sus lentes). Él disfruta mucho conversar sobre su antigua profesión (carpintero).</p><h3>Instrucciones</h3><ol><li><strong>Adaptación Física:</strong> Menciona al menos tres adaptaciones concretas que harías en el trayecto desde el dormitorio de Don Luis hasta el baño para evitar futuras caídas.</li><li><strong>Fomento de Autonomía:</strong> Menciona dos actividades del hogar en las que podrías involucrar a Don Luis para que se sienta útil sin ponerlo en riesgo.</li><li><strong>Manejo Cognitivo:</strong> Si Don Luis te dice a las 3:00 PM: <em>'No me han dado de comer en todo el día'</em>, a pesar de que almorzó hace una hora. ¿Cómo le responderías aplicando lo aprendido para no generar ansiedad ni discutir?</li></ol>",
            fecha_limite=timezone.now() + timedelta(days=30),
            puntaje_maximo=100,
            creado_por=docente
        )

        # 7. Inscribir al Colaborador en el curso
        InscripcionCurso.objects.get_or_create(
            usuario=colaborador,
            curso=curso,
            defaults={'estado': 'asignado'}
        )

        self.stdout.write(self.style.SUCCESS(f"¡Éxito! Curso '{curso.titulo}' creado sin límite de tiempo y asignado al colaborador."))
        self.stdout.write(self.style.SUCCESS(f"Usuario Colaborador: {colaborador.email} / Clave: kimun2024"))
        self.stdout.write(self.style.SUCCESS(f"Usuario Profesor: {docente.email} / Clave: kimun2024"))

import os
import json
from openai import OpenAI
from django.conf import settings
from pacientes.models import Paciente
from cursos.models import Curso
from usuarios.models import Usuario

def obtener_analisis_institucional(tipo_analisis):
    """
    Analiza el estado general de la institución según el tipo de análisis solicitado.
    tipo_analisis puede ser 'upskilling' o 'nuevos_cursos'.
    """
    pacientes = Paciente.objects.all()
    cursos = Curso.objects.filter(estado='publicado')
    colaboradores = Usuario.objects.filter(rol='colaborador')
    
    if not pacientes.exists():
        return {"error": "No hay pacientes registrados para analizar."}
        
    # Agrupar patologías (Escalabilidad: contar frecuencias en lugar de concatenar texto infinito)
    from collections import Counter
    todas_patologias = []
    for p in pacientes:
        if p.patologias:
            # Separamos por coma y normalizamos a minúsculas
            pats = [pat.strip().capitalize() for pat in p.patologias.split(',')]
            todas_patologias.extend(pats)
            
    conteo_patologias = Counter(todas_patologias)
    top_patologias = conteo_patologias.most_common(20) # Tomamos las 20 más frecuentes
    
    resumen_patologias = "\n".join([f"- {pat}: presente en {count} paciente(s)" for pat, count in top_patologias])
    
    resumen_pacientes = f"Total Pacientes: {pacientes.count()}\nPrincipales patologías en la residencia:\n{resumen_patologias}"
    
    # Agrupar cursos actuales
    cursos_list = [f"- {c.titulo} (ID: {c.id})" for c in cursos]
    resumen_cursos = "Cursos actualmente disponibles en la plataforma:\n" + "\n".join(cursos_list)
    
    if not cursos.exists():
        resumen_cursos = "Actualmente no hay cursos publicados en la plataforma."

    # Agrupar colaboradores y sus faltas
    colab_list = []
    for c in colaboradores:
        cargo = c.cargo.nombre if c.cargo else "Sin cargo"
        cursos_hechos = []
        if hasattr(c, 'inscripciones'):
            from cursos.models import InscripcionCurso
            insc = c.inscripciones.filter(estado__in=['completado', 'en_progreso'])
            cursos_hechos = [i.curso.titulo for i in insc]
            
        pacientes_asignados = c.pacientes_asignados.all()
        patologias_cuidadas = set()
        for p in pacientes_asignados:
            if p.patologias:
                for pat in p.patologias.split(','):
                    patologias_cuidadas.add(pat.strip().capitalize())
                    
        pat_str = ", ".join(patologias_cuidadas) if patologias_cuidadas else "Ninguna"
        
        colab_list.append(f"- ID: {c.id} | {c.get_full_name()} ({cargo}) | Patologías a cargo: {pat_str} | Cursos: {', '.join(cursos_hechos) if cursos_hechos else 'Ninguno'}")
        
    resumen_colaboradores = "Personal actual, patologías de los pacientes que cuidan directamente, y cursos ya realizados:\n" + "\n".join(colab_list)

    # Inicializar cliente
    api_key = os.getenv('OPENAI_API_KEY')
    model_name = os.getenv('MODEL_API', 'gpt-3.5-turbo')
    
    if not api_key:
        return {"error": "No se ha configurado la API KEY en el archivo .env"}
        
    client_kwargs = {'api_key': api_key}
    if 'qwen' in model_name.lower():
        client_kwargs['base_url'] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        
    client = OpenAI(**client_kwargs)
    
    if tipo_analisis == 'upskilling':
        system_prompt = """
        Eres un Consultor Estratégico de Recursos Humanos (IA Médica) de una organización gerontológica.
        Tu tarea es evaluar qué cursos YA EXISTENTES en el catálogo deben ser reforzados, basándote en las patologías reales de los pacientes.
        
        INSTRUCCIONES CLAVES:
        1. Analiza qué patologías son críticas actualmente en la institución.
        2. Selecciona un curso existente que aborde directamente esa patología.
        3. En lugar de sugerir cuidadores, debes indicar claramente cuál es la "patología objetivo" principal que este curso ayuda a tratar (ej: "Demencia", "Incontinencia urinaria"). El sistema automáticamente asignará el curso a los cuidadores que atienden a esos pacientes.
        4. Solo sugiere cursos donde haya un déficit real de capacitación.
        
        Devuelve EXACTAMENTE un objeto JSON válido con este esquema, sin texto extra:
        {
          "resumen_general": "Resumen narrativo sobre por qué es necesario priorizar estos cursos basándose en las patologías actuales.",
          "upskilling": [
            {
              "curso_id": "El número de ID del curso (entero)",
              "curso_existente": "Nombre del curso",
              "justificacion": "Justificación clínica detallada (ej: 'Tenemos 35 pacientes con Incontinencia Urinaria, es vital capacitar a sus cuidadores directos').",
              "patologias_objetivo": ["Incontinencia urinaria", "Demencia"] // Array de strings con las patologías que este curso ataca
            }
          ]
        }
        """
    else:
        system_prompt = """
        Eres un Consultor Estratégico de Recursos Humanos (IA Médica) de una organización gerontológica.
        Tu tarea es identificar qué habilidades clínicas y de cuidado FALTAN totalmente en el catálogo de cursos actual basándote en las patologías reales de los pacientes.
        
        INSTRUCCIONES CLAVES:
        Tu justificación debe ser extremadamente específica, empírica y basada en los datos provistos.
        Debes seguir esta estructura de pensamiento para justificar: "Actualmente no contamos con ningún curso sobre [Tema]. Tenemos [N] residentes que sufren de [Patología/Condición], por lo que este curso ayudaría específicamente a [Acción clínica o beneficio concreto]."
        No des respuestas genéricas. Cruza la falta de cursos con las necesidades médicas de la población.
        
        Devuelve EXACTAMENTE un objeto JSON válido con este esquema, sin texto extra:
        {
          "resumen_general": "Resumen narrativo y cuantitativo sobre las brechas detectadas y el volumen de pacientes afectados por la falta de capacitación.",
          "nuevos_cursos": [
            {
              "titulo_sugerido": "Nombre de un curso nuevo altamente específico",
              "habilidad_faltante": "Técnica, protocolo o habilidad clínica exacta que falta en el catálogo",
              "justificacion": "Justificación basada en datos (ej: 'No hay curso sobre manejo de gastrostomía. 12 residentes requieren alimentación enteral, y esto ayudaría a reducir IAAS...')"
            }
          ]
        }
        """
    
    user_prompt = f"1. DATOS PACIENTES:\n{resumen_pacientes}\n\n2. CATÁLOGO CURSOS:\n{resumen_cursos}\n\n3. PERSONAL:\n{resumen_colaboradores}"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith('```json'):
            content = content.replace('```json', '', 1)
        if content.endswith('```'):
            content = content[:-3]
            
        data = json.loads(content)
        return data
        
    except Exception as e:
        return {"error": f"Error de conexión con la IA: {str(e)}"}

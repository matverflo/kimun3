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
            insc = c.inscripciones.filter(estado='completado')
            cursos_hechos = [i.curso.titulo for i in insc]
        
        colab_list.append(f"- {c.get_full_name()} ({cargo}): Ha completado: {', '.join(cursos_hechos) if cursos_hechos else 'Ninguno'}")
        
    resumen_colaboradores = "Personal actual y sus capacitaciones completadas:\n" + "\n".join(colab_list)

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
        Tu tarea es evaluar qué cursos YA EXISTENTES en el catálogo deben ser reforzados y enseñados al personal, basándote estrictamente en las patologías clínicas actuales de los pacientes.
        
        IMPORTANTE: Revisa el listado de PERSONAL ACTUAL. ¡NO sugieras un curso si todos los colaboradores de los roles relevantes ya lo completaron o lo tienen en curso! Solo sugiere cursos donde haya un déficit real de capacitación.
        
        Devuelve EXACTAMENTE un objeto JSON válido con este esquema, sin texto extra:
        {
          "resumen_general": "Resumen narrativo sobre por qué es necesario priorizar estos cursos basándose en las patologías actuales.",
          "upskilling": [
            {
              "curso_id": "El número de ID del curso (entero)",
              "curso_existente": "Nombre del curso",
              "justificacion": "Justificación clínica detallada de por qué se necesita más personal capacitado en esto.",
              "roles_ideales": ["Enfermero/a", "Cuidador/a", "Tens"]
            }
          ]
        }
        """
    else:
        system_prompt = """
        Eres un Consultor Estratégico de Recursos Humanos (IA Médica) de una organización gerontológica.
        Tu tarea es identificar qué habilidades críticas FALTAN totalmente en el catálogo de cursos actual basándote en las patologías de los pacientes, y sugerir la creación de nuevos cursos.
        
        Devuelve EXACTAMENTE un objeto JSON válido con este esquema, sin texto extra:
        {
          "resumen_general": "Resumen narrativo sobre las brechas detectadas.",
          "nuevos_cursos": [
            {
              "titulo_sugerido": "Nombre de un curso nuevo",
              "habilidad_faltante": "Qué habilidad falta",
              "justificacion": "Por qué es necesario."
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

from django import forms
from django.conf import settings
from .models import Curso, Material, Categoria, Clase


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'categoria', 'estado', 'horas_exigidas', 'horas_por_semana', 'exige_tiempo_minimo', 'duracion_minutos']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Primeros Auxilios'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 4,
                'placeholder': 'Describe el contenido y objetivos del curso...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'estado': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'horas_exigidas': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: 20'
            }),
            'horas_por_semana': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: 4'
            }),
            'exige_tiempo_minimo': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            }),
            'duracion_minutos': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: 30'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['horas_exigidas'].required = False
        self.fields['horas_por_semana'].required = False
        self.fields['exige_tiempo_minimo'].required = False
        if self.user and self.user.rol == 'admin':
            from usuarios.models import Usuario
            self.fields['docente_creador'] = forms.ModelChoiceField(
                queryset=Usuario.objects.filter(rol='docente').order_by('first_name', 'last_name'),
                required=True,
                label='Docente Instructor',
                widget=forms.Select(attrs={
                    'class': 'input-field w-full px-4 py-3 rounded-xl'
                })
            )
            self.order_fields(['titulo', 'descripcion', 'categoria', 'estado', 'docente_creador', 'horas_exigidas', 'horas_por_semana', 'exige_tiempo_minimo', 'duracion_minutos'])


class CursoCreateForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'categoria']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Primeros Auxilios'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 4,
                'placeholder': 'Describe el contenido y objetivos del curso...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        if self.user and self.user.rol == 'admin':
            from usuarios.models import Usuario
            self.fields['docente_creador'] = forms.ModelChoiceField(
                queryset=Usuario.objects.filter(rol='docente').order_by('first_name', 'last_name'),
                required=True,
                label='Docente Instructor',
                widget=forms.Select(attrs={
                    'class': 'input-field w-full px-4 py-3 rounded-xl'
                })
            )
            self.order_fields(['titulo', 'descripcion', 'categoria', 'docente_creador'])


class CursoPublishForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['titulo', 'descripcion', 'categoria', 'horas_exigidas', 'horas_por_semana', 'exige_tiempo_minimo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Primeros Auxilios'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 4,
                'placeholder': 'Describe el contenido y objetivos del curso...'
            }),
            'categoria': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'horas_exigidas': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: 20'
            }),
            'horas_por_semana': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: 4'
            }),
            'exige_tiempo_minimo': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['horas_exigidas'].required = True
        self.fields['horas_por_semana'].required = True
        self.fields['exige_tiempo_minimo'].required = False


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['titulo', 'tipo', 'archivo', 'url']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Manual de Primeros Auxilios'
            }),
            'tipo': forms.Select(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl'
            }),
            'archivo': forms.FileInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'accept': '.pdf'
            }),
            'url': forms.URLInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        archivo = cleaned_data.get('archivo')
        url = cleaned_data.get('url')

        if tipo == 'pdf' and not archivo:
            self.add_error('archivo', 'Debes subir un archivo PDF para este tipo de material.')

        if tipo == 'video' and not url:
            self.add_error('url', 'Debes ingresar una URL de video para este tipo de material.')

        return cleaned_data


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'color', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Seguridad Laboral'
            }),
            'color': forms.TextInput(attrs={
                'class': 'w-12 h-12 rounded-lg cursor-pointer border-0',
                'type': 'color'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'rows': 3,
                'placeholder': 'Descripción breve de la categoría...'
            }),
        }


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['titulo', 'contenido', 'orden']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': 'Ej: Introducción a los Primeros Auxilios'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'input-field w-full px-4 py-3 rounded-xl text-lg',
                'placeholder': '1',
                'min': '1'
            }),
        }

    def clean_orden(self):
        orden = self.cleaned_data.get('orden')
        if orden is not None and orden < 1:
            raise forms.ValidationError('El orden debe ser mayor a 0.')
        return orden

    def clean(self):
        cleaned_data = super().clean()
        titulo = cleaned_data.get('titulo')
        orden = cleaned_data.get('orden')
        curso_obj = cleaned_data.get('curso')
        if not curso_obj:
            curso_obj = getattr(self.instance, 'curso', None)
        curso_id = curso_obj.pk if curso_obj else None

        if titulo and orden and curso_id:
            qs = Clase.objects.filter(curso_id=curso_id, orden=orden)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
                
            from evaluaciones.models import Evaluacion
            qs_eval = Evaluacion.objects.filter(curso_id=curso_id, orden=orden)

            if qs.exists() or qs_eval.exists():
                raise forms.ValidationError(
                    {'orden': f'Ya existe un elemento (Clase o Evaluación) con orden {orden} en este curso.'}
                )

        return cleaned_data

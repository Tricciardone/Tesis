from django import forms
from .models import CV, SavedCriterion
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class CVUploadForm(forms.ModelForm):
    class Meta:
        model = CV
        fields = ['candidate_name', 'pdf_file']
        labels = {
            'candidate_name': 'Nombre del perfil',
            'pdf_file': 'Documento PDF',
        }
        widgets = {
            'candidate_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: Juan Pérez',
                'autocomplete': 'off'
            }),
            'pdf_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf,.pdf'
            }),
        }
        help_texts = {
            'candidate_name': 'Ingresá el nombre completo del candidato o perfil profesional.',
            'pdf_file': 'Solo se permiten archivos PDF de hasta 5 MB.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.add_input(
            Submit(
                'submit',
                'Cargar y analizar perfil',
                css_class='btn btn-primary btn-lg rounded-pill px-4'
            )
        )

    def clean_candidate_name(self):
        candidate_name = self.cleaned_data.get('candidate_name', '').strip()

        if len(candidate_name) < 3:
            raise forms.ValidationError('El nombre del perfil debe tener al menos 3 caracteres.')

        return candidate_name

    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')

        if not pdf_file:
            raise forms.ValidationError('Debés seleccionar un archivo PDF.')

        filename = pdf_file.name.lower()

        if not filename.endswith('.pdf'):
            raise forms.ValidationError('Solo se permiten archivos con extensión PDF.')

        if getattr(pdf_file, 'content_type', None) not in ['application/pdf', 'application/x-pdf']:
            raise forms.ValidationError('El archivo seleccionado no parece ser un PDF válido.')

        max_size = 5 * 1024 * 1024

        if pdf_file.size > max_size:
            raise forms.ValidationError('El archivo no puede superar los 5 MB.')

        return pdf_file


class QueryForm(forms.Form):
    query = forms.CharField(
        label='Consulta sobre el perfil',
        min_length=5,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': (
                'Ejemplo: ¿Este candidato menciona experiencia en Python, SQL o bases de datos?\n'
                'Ejemplo: ¿Qué fortalezas tiene para un puesto administrativo?\n'
                'Ejemplo: ¿Qué riesgos o vacíos presenta el perfil?'
            )
        }),
        help_text='La respuesta se generará únicamente con información presente en el perfil cargado.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit(
                'submit',
                'Analizar con IA',
                css_class='btn btn-success btn-lg rounded-pill px-4'
            )
        )

    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()

        if len(query) < 5:
            raise forms.ValidationError('La consulta debe tener al menos 5 caracteres.')

        return query


class BulkQueryForm(forms.Form):
    query = forms.CharField(
        label='Consulta comparativa',
        min_length=10,
        max_length=1500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': (
                'Ejemplos:\n'
                '- Ordená los perfiles según su adecuación para un puesto de Data Analyst con Python, SQL y bases de datos.\n'
                '- ¿Qué candidato tiene mejor perfil para atención al cliente?\n'
                '- Compará los perfiles según experiencia laboral, formación y habilidades técnicas.'
            )
        }),
        help_text='La consulta se aplicará a los perfiles procesados y devolverá un ranking comparativo.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit(
                'submit',
                'Generar comparativa IA',
                css_class='btn btn-primary btn-lg rounded-pill px-4'
            )
        )

    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()

        if len(query) < 10:
            raise forms.ValidationError('La consulta comparativa debe tener al menos 10 caracteres.')

        return query
    
class JobDescriptionMatchForm(forms.Form):
    job_description = forms.CharField(
        label='Descripción del puesto',
        min_length=20,
        max_length=3000,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': (
                'Pegá acá la descripción del puesto.\n\n'
                'Ejemplo:\n'
                'Buscamos Analista de Datos con experiencia en SQL, Power BI, '
                'elaboración de reportes, análisis de información y comunicación con áreas de negocio.'
            )
        }),
        help_text='TalentScan IA comparará esta descripción contra los perfiles procesados.'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit(
                'submit',
                'Calcular matching IA',
                css_class='btn btn-primary btn-lg rounded-pill px-4'
            )
        )

    def clean_job_description(self):
        job_description = self.cleaned_data.get('job_description', '').strip()

        if len(job_description) < 20:
            raise forms.ValidationError('La descripción del puesto debe tener al menos 20 caracteres.')

        return job_description


class SavedCriterionForm(forms.ModelForm):
    class Meta:
        model = SavedCriterion
        fields = ['name', 'criterion_type', 'content']
        labels = {
            'name': 'Nombre',
            'criterion_type': 'Tipo',
            'content': 'Criterio / descripción',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: Backend Python Semi Senior',
            }),
            'criterion_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 7,
                'placeholder': (
                    'Pegá una descripción de puesto, criterio de búsqueda o consulta comparativa reutilizable.'
                ),
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit(
                'submit',
                'Guardar criterio',
                css_class='btn btn-primary btn-lg px-4'
            )
        )

    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()

        if len(content) < 10:
            raise forms.ValidationError('El criterio debe tener al menos 10 caracteres.')

        return content

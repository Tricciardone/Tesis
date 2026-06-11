from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets


class Organization(models.Model):
    name = models.CharField(max_length=160, unique=True, verbose_name="Organizacion")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creacion")

    class Meta:
        verbose_name = "Organizacion"
        verbose_name_plural = "Organizaciones"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("recruiter", "Recruiter"),
        ("viewer", "Viewer"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="talentscan_profile")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Organizacion",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="recruiter", verbose_name="Rol")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de alta")

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"


class CV(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('error', 'Error'),
    ]

    PIPELINE_STATUS_CHOICES = [
        ('new', 'Nuevo'),
        ('review', 'Revisar'),
        ('shortlist', 'Shortlist'),
        ('interview', 'Entrevista'),
        ('discarded', 'Descartado'),
    ]

    candidate_name = models.CharField(
        max_length=200,
        verbose_name="Nombre del candidato"
    )

    pdf_file = models.FileField(
        upload_to='cvs/',
        verbose_name="Archivo PDF"
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Cargado por"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de carga"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Estado"
    )

    analysis_result = models.TextField(
        blank=True,
        null=True,
        verbose_name="Resultado del análisis inicial"
    )

    extracted_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="Texto extraído del perfil"
    )

    text_length = models.PositiveIntegerField(
        default=0,
        verbose_name="Longitud del texto extraído"
    )

    processed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de procesamiento"
    )

    processing_error = models.TextField(
        blank=True,
        null=True,
        verbose_name="Detalle del error de procesamiento"
    )
    structured_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos estructurados del perfil"
    )

    detected_skills = models.TextField(
        blank=True,
        null=True,
        verbose_name="Habilidades detectadas"
    )

    detected_education = models.TextField(
        blank=True,
        null=True,
        verbose_name="Educación detectada"
    )

    detected_experience = models.TextField(
        blank=True,
        null=True,
        verbose_name="Experiencia detectada"
    )

    detected_roles = models.TextField(
        blank=True,
        null=True,
        verbose_name="Puestos detectados"
    )

    detected_institutions = models.TextField(
        blank=True,
        null=True,
        verbose_name="Instituciones detectadas"
    )

    pipeline_status = models.CharField(
        max_length=20,
        choices=PIPELINE_STATUS_CHOICES,
        default='new',
        verbose_name="Estado de selección"
    )

    is_shortlisted = models.BooleanField(
        default=False,
        verbose_name="En shortlist"
    )

    recruiter_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notas internas del recruiter"
    )

    class Meta:
        verbose_name = "Perfil profesional"
        verbose_name_plural = "Perfiles profesionales"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Perfil de {self.candidate_name}"

    def has_valid_text(self):
        return bool(self.extracted_text and len(self.extracted_text.strip()) >= 50)

    def get_short_analysis(self):
        if not self.analysis_result:
            return "Sin análisis disponible"
        return self.analysis_result[:150] + "..." if len(self.analysis_result) > 150 else self.analysis_result


class AnalysisQuery(models.Model):
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        related_name='queries',
        verbose_name="Perfil profesional"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )

    query = models.TextField(
        verbose_name="Consulta"
    )

    response = models.TextField(
        verbose_name="Respuesta del motor IA"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de consulta"
    )
    structured_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos estructurados IA"
    )

    detected_skills = models.TextField(
        blank=True,
        null=True,
        verbose_name="Skills detectadas"
    )

    detected_roles = models.TextField(
        blank=True,
        null=True,
        verbose_name="Roles detectados"
    )

    detected_education = models.TextField(
        blank=True,
        null=True,
        verbose_name="Educación detectada"
    )

    detected_universities = models.TextField(
        blank=True,
        null=True,
        verbose_name="Universidades detectadas"
    )

    detected_languages = models.TextField(
        blank=True,
        null=True,
        verbose_name="Idiomas detectados"
    )

    seniority = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Seniority detectado"
    )

    class Meta:
        verbose_name = "Consulta individual"
        verbose_name_plural = "Consultas individuales"
        ordering = ['-created_at']

    def __str__(self):
        return f"Consulta sobre {self.cv.candidate_name} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

    def get_short_query(self):
        return self.query[:100] + "..." if len(self.query) > 100 else self.query

    def get_short_response(self):
        return self.response[:150] + "..." if len(self.response) > 150 else self.response


class BulkAnalysisQuery(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )

    query = models.TextField(
        verbose_name="Consulta comparativa"
    )

    response = models.TextField(
        verbose_name="Respuesta comparativa del motor IA"
    )

    cvs_analyzed = models.ManyToManyField(
        CV,
        verbose_name="Perfiles analizados"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de consulta"
    )

    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de procesamiento en segundos"
    )

    class Meta:
        verbose_name = "Comparativa IA"
        verbose_name_plural = "Comparativas IA"
        ordering = ['-created_at']

    def __str__(self):
        return f"Comparativa IA - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

    def get_cvs_count(self):
        return self.cvs_analyzed.count()

    def get_short_query(self):
        return self.query[:100] + "..." if len(self.query) > 100 else self.query

    def get_short_response(self):
        return self.response[:150] + "..." if len(self.response) > 150 else self.response
    
class JobMatchQuery(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )

    job_description = models.TextField(
        verbose_name="Descripción del puesto"
    )

    response = models.TextField(
        verbose_name="Resultado del matching IA"
    )

    cvs_analyzed = models.ManyToManyField(
        CV,
        verbose_name="Perfiles evaluados"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de evaluación"
    )

    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Tiempo de procesamiento en segundos"
    )

    class Meta:
        verbose_name = "Matching contra puesto"
        verbose_name_plural = "Matchings contra puestos"
        ordering = ['-created_at']

    def __str__(self):
        return f"Matching JD - {self.created_at.strftime('%d/%m/%Y %H:%M')}"

    def get_cvs_count(self):
        return self.cvs_analyzed.count()

    def get_short_description(self):
        return self.job_description[:120] + "..." if len(self.job_description) > 120 else self.job_description


class SavedCriterion(models.Model):
    TYPE_CHOICES = [
        ('job_match', 'Matching contra puesto'),
        ('bulk_analysis', 'Comparativa IA'),
        ('search', 'Búsqueda de perfiles'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )

    name = models.CharField(
        max_length=120,
        verbose_name="Nombre del criterio"
    )

    criterion_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='job_match',
        verbose_name="Tipo de criterio"
    )

    content = models.TextField(
        verbose_name="Contenido del criterio"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    last_used_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Último uso"
    )

    class Meta:
        verbose_name = "Criterio guardado"
        verbose_name_plural = "Criterios guardados"
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def get_short_content(self):
        return self.content[:140] + "..." if len(self.content) > 140 else self.content


def generate_share_token():
    return secrets.token_urlsafe(32)


class SharedReportLink(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name="shared_links")
    token = models.CharField(max_length=96, unique=True, default=generate_share_token)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_report_links")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Link seguro de informe"
        verbose_name_plural = "Links seguros de informes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Informe compartido - {self.cv.candidate_name}"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True


class AuditEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="audit_events",
        blank=True,
        null=True,
    )
    cv = models.ForeignKey(CV, on_delete=models.SET_NULL, blank=True, null=True, related_name="audit_events")
    action = models.CharField(max_length=80)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de auditoria"
        verbose_name_plural = "Eventos de auditoria"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.created_at:%d/%m/%Y %H:%M}"

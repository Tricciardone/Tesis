from django.contrib import admin
from .models import (
    AuditEvent,
    CV,
    AnalysisQuery,
    BulkAnalysisQuery,
    JobMatchQuery,
    Organization,
    SavedCriterion,
    SharedReportLink,
    UserProfile,
)


admin.site.site_header = "TalentScan IA"
admin.site.site_title = "Administración TalentScan IA"
admin.site.index_title = "Panel de administración"


@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = [
        'candidate_name',
        'uploaded_by',
        'status',
        'pipeline_status',
        'is_shortlisted',
        'text_length',
        'uploaded_at',
        'processed_at',
    ]

    list_filter = [
        'status',
        'pipeline_status',
        'is_shortlisted',
        'uploaded_at',
        'processed_at',
        'uploaded_by',
    ]

    search_fields = [
        'candidate_name',
        'uploaded_by__username',
        'uploaded_by__first_name',
        'uploaded_by__last_name',
        'analysis_result',
        'extracted_text',
    ]

    readonly_fields = [
        'uploaded_at',
        'processed_at',
        'text_length',
        'analysis_result',
        'extracted_text',
        'processing_error',
    ]

    fieldsets = (
        ('Información del perfil', {
            'fields': (
                'candidate_name',
                'pdf_file',
                'uploaded_by',
                'status',
                'pipeline_status',
                'is_shortlisted',
                'recruiter_notes',
            )
        }),
        ('Procesamiento IA', {
            'fields': (
                'analysis_result',
                'extracted_text',
                'text_length',
                'processed_at',
                'processing_error',
            )
        }),
        ('Auditoría', {
            'fields': (
                'uploaded_at',
            )
        }),
    )

    ordering = ['-uploaded_at']

    def has_valid_text(self, obj):
        return obj.has_valid_text()

    has_valid_text.boolean = True
    has_valid_text.short_description = "Texto válido"


@admin.register(AnalysisQuery)
class AnalysisQueryAdmin(admin.ModelAdmin):
    list_display = [
        'cv',
        'user',
        'created_at',
        'query_preview',
        'response_preview',
    ]

    list_filter = [
        'created_at',
        'user',
        'cv__status',
    ]

    search_fields = [
        'cv__candidate_name',
        'user__username',
        'query',
        'response',
    ]

    readonly_fields = [
        'cv',
        'user',
        'query',
        'response',
        'created_at',
    ]

    ordering = ['-created_at']

    def query_preview(self, obj):
        return obj.get_short_query()

    query_preview.short_description = 'Consulta'

    def response_preview(self, obj):
        return obj.get_short_response()

    response_preview.short_description = 'Respuesta IA'


@admin.register(BulkAnalysisQuery)
class BulkAnalysisQueryAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'created_at',
        'cvs_count',
        'processing_time',
        'query_preview',
        'response_preview',
    ]

    list_filter = [
        'created_at',
        'user',
    ]

    search_fields = [
        'user__username',
        'query',
        'response',
        'cvs_analyzed__candidate_name',
    ]

    readonly_fields = [
        'user',
        'query',
        'response',
        'created_at',
        'processing_time',
    ]

    filter_horizontal = [
        'cvs_analyzed',
    ]

    ordering = ['-created_at']

    def query_preview(self, obj):
        return obj.get_short_query()

    query_preview.short_description = 'Consulta comparativa'

    def response_preview(self, obj):
        return obj.get_short_response()

    response_preview.short_description = 'Respuesta IA'

    def cvs_count(self, obj):
        return obj.get_cvs_count()

    cvs_count.short_description = 'Perfiles'


@admin.register(SavedCriterion)
class SavedCriterionAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'user',
        'criterion_type',
        'updated_at',
        'last_used_at',
    ]

    list_filter = [
        'criterion_type',
        'updated_at',
        'last_used_at',
        'user',
    ]

    search_fields = [
        'name',
        'content',
        'user__username',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'last_used_at',
    ]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'created_at']
    list_filter = ['organization', 'role']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'organization__name']


@admin.register(JobMatchQuery)
class JobMatchQueryAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'processing_time']
    list_filter = ['created_at', 'user']
    search_fields = ['user__username', 'job_description', 'response', 'cvs_analyzed__candidate_name']
    filter_horizontal = ['cvs_analyzed']
    readonly_fields = ['user', 'job_description', 'response', 'created_at', 'processing_time']


@admin.register(SharedReportLink)
class SharedReportLinkAdmin(admin.ModelAdmin):
    list_display = ['cv', 'created_by', 'created_at', 'expires_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['cv__candidate_name', 'created_by__username', 'token']


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'organization', 'cv', 'created_at']
    list_filter = ['action', 'organization', 'created_at']
    search_fields = ['description', 'user__username', 'cv__candidate_name']
    readonly_fields = ['user', 'organization', 'cv', 'action', 'description', 'metadata', 'created_at']

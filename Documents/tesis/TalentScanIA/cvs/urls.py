from django.urls import path
from . import views

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views.recruiter_dashboard, name='recruiter_dashboard'),
    path('', views.cv_list, name='cv_list'),

    # Perfiles profesionales
    path('upload/', views.cv_upload, name='cv_upload'),
    path('history/', views.analysis_history, name='analysis_history'),
    path('normalize-existing/', views.normalize_existing_profiles, name='normalize_existing_profiles'),
    path('selection-kanban/', views.selection_kanban, name='selection_kanban'),
    path('shortlist/export/', views.export_shortlist, name='export_shortlist'),
    path('criteria/', views.saved_criteria, name='saved_criteria'),
    path('criteria/<int:criterion_id>/delete/', views.delete_saved_criterion, name='delete_saved_criterion'),
    path('team/', views.team_settings, name='team_settings'),
    path('audit/', views.audit_log, name='audit_log'),
    path('shared/report/<str:token>/', views.shared_cv_report, name='shared_cv_report'),

    # Estado del motor IA
    path('status/', views.ollama_status, name='ollama_status'),

    # Comparativas IA
    path('bulk-analysis/', views.bulk_analysis, name='bulk_analysis'),
    path('bulk-analysis/history/', views.bulk_analysis_history, name='bulk_analysis_history'),
    path('bulk-analysis/<int:query_id>/', views.bulk_analysis_detail, name='bulk_analysis_detail'),
    path('job-match/', views.job_match, name='job_match'),
    path('job-match/<int:match_id>/', views.job_match_detail, name='job_match_detail'),
    path(
    '<int:cv_id>/interview-questions/',
    views.generate_interview_questions,
    name='generate_interview_questions'
    ),
    # Detalle de perfil
    path('<int:cv_id>/', views.cv_detail, name='cv_detail'),
    path('<int:cv_id>/report/', views.cv_report, name='cv_report'),
    path('<int:cv_id>/document/', views.cv_document, name='cv_document'),
    path('<int:cv_id>/share-report/', views.create_shared_report_link, name='create_shared_report_link'),
    path('<int:cv_id>/reprocess/', views.cv_reprocess, name='cv_reprocess'),
    path('<int:cv_id>/pipeline/', views.update_cv_pipeline, name='update_cv_pipeline'),
    path('<int:cv_id>/query/', views.cv_query, name='cv_query'),
    path('<int:cv_id>/delete/', views.cv_delete, name='cv_delete'),
]

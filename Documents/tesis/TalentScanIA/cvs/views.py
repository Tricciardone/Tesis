import csv
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import FileResponse, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from collections import Counter
import logging
import time
from collections import Counter
from django.http import JsonResponse
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
from .forms import CVUploadForm, QueryForm, BulkQueryForm, JobDescriptionMatchForm, SavedCriterionForm
from .services import (
    INSTITUTION_ALIASES,
    OllamaService,
    UNIVERSITY_CATALOG,
    normalize_structured_profile,
    normalize_text,
)
from .utils import extract_text_from_pdf, validate_pdf_file, get_pdf_info
from django.db import models

logger = logging.getLogger(__name__)


def get_user_profile(user):
    profile = getattr(user, "talentscan_profile", None)
    if profile:
        return profile

    organization, _ = Organization.objects.get_or_create(
        name=f"Equipo {user.username}",
    )
    role = "admin" if user.is_superuser else "recruiter"
    return UserProfile.objects.create(user=user, organization=organization, role=role)


def get_user_organization(user):
    return get_user_profile(user).organization


def get_user_role(user):
    if user.is_superuser:
        return "admin"
    return get_user_profile(user).role


def can_write(user):
    return user.is_superuser or get_user_role(user) in {"admin", "recruiter"}


def can_admin(user):
    return user.is_superuser or get_user_role(user) == "admin"


def require_write_access(request):
    if can_write(request.user):
        return True

    messages.warning(request, "Tu rol actual es Viewer: podés consultar perfiles, pero no modificar datos.")
    return False


def require_admin_access(request):
    if can_admin(request.user):
        return True

    messages.warning(request, "Solo un usuario Admin puede gestionar equipo y auditoría.")
    return False


def get_accessible_cvs(user):
    if user.is_superuser:
        return CV.objects.all()

    organization = get_user_organization(user)
    return CV.objects.filter(uploaded_by__talentscan_profile__organization=organization)


def get_accessible_users(user):
    if user.is_superuser:
        return User.objects.all()

    organization = get_user_organization(user)
    return User.objects.filter(talentscan_profile__organization=organization)


def get_accessible_saved_criteria(user):
    return SavedCriterion.objects.filter(user__in=get_accessible_users(user))


def log_audit(user, action, description, cv=None, metadata=None):
    organization = None
    if user and user.is_authenticated:
        organization = get_user_organization(user)

    AuditEvent.objects.create(
        user=user if user and user.is_authenticated else None,
        organization=organization,
        cv=cv,
        action=action,
        description=description,
        metadata=metadata or {},
    )


def get_search_variants(value):
    normalized = normalize_text(value)
    variants = {value.strip(), normalized}

    for alias, canonical in INSTITUTION_ALIASES.items():
        canonical_normalized = normalize_text(canonical)
        if normalized == alias or normalized in canonical_normalized or canonical_normalized in normalized:
            variants.update({
                alias,
                alias.upper(),
                canonical,
                canonical_normalized,
            })

    return [variant for variant in variants if variant]


def get_institution_search_variants(value):
    normalized = normalize_text(value)
    variants = {value.strip(), normalized}

    for alias, canonical in INSTITUTION_ALIASES.items():
        canonical_normalized = normalize_text(canonical)
        if normalized == alias or normalized in canonical_normalized or canonical_normalized in normalized:
            variants.update({
                alias,
                alias.upper(),
                canonical,
                canonical_normalized,
            })

    return [variant for variant in variants if len(variant) >= 4 or variant.lower() in INSTITUTION_ALIASES]


def get_institution_filter_target(value):
    normalized = normalize_text(value)

    for acronym, canonical in UNIVERSITY_CATALOG:
        acronym_normalized = normalize_text(acronym)
        canonical_normalized = normalize_text(canonical)

        if normalized in {acronym_normalized, canonical_normalized}:
            return acronym, canonical, canonical_normalized

    return value.strip(), value.strip(), normalized


def get_canonical_institution_name_variants(name):
    variants = {name}
    normalized_name = normalize_text(name)
    compact_name = re.sub(r"\b(de|del|la|las|el|los)\b", " ", normalized_name)
    compact_name = re.sub(r"\s+", " ", compact_name).strip()

    if compact_name and compact_name != normalized_name:
        variants.add(compact_name)

    return [variant for variant in variants if variant]


def build_profile_search_q(value, *fields):
    query = models.Q()

    for variant in get_search_variants(value):
        for field in fields:
            query |= models.Q(**{f"{field}__icontains": variant})

    return query


def build_institution_search_q(value):
    query = models.Q()
    acronym, canonical, _ = get_institution_filter_target(value)
    acronym_boundary = rf"(^|[^A-Za-z0-9]){re.escape(acronym)}([^A-Za-z0-9]|$)"

    for name_variant in get_canonical_institution_name_variants(canonical):
        query |= models.Q(detected_institutions__icontains=name_variant)

    if acronym:
        query |= models.Q(detected_institutions__iregex=acronym_boundary)

    return query


def join_structured_values(values):
    if not values:
        return ""

    if isinstance(values, str):
        return values

    cleaned = []
    for value in values:
        if isinstance(value, dict):
            value = value.get("name") or value.get("title") or value.get("value")

        if value:
            cleaned.append(str(value).strip())

    return ", ".join(item for item in cleaned if item)


def structured_data_from_cv_fields(cv):
    return {
        "skills": cv.detected_skills,
        "education": cv.detected_education,
        "institutions": cv.detected_institutions,
        "experience": cv.detected_experience,
        "roles": cv.detected_roles,
        "languages": (cv.structured_data or {}).get("languages", []),
        "seniority": (cv.structured_data or {}).get("seniority", "No informado"),
        "areas": (cv.structured_data or {}).get("areas", []),
    }


def apply_structured_data_to_cv(cv, structured_data, save=True):
    normalized_data = normalize_structured_profile(structured_data)

    cv.structured_data = normalized_data
    cv.detected_skills = join_structured_values(normalized_data.get("skills", []))
    cv.detected_education = join_structured_values(normalized_data.get("education", []))
    cv.detected_experience = join_structured_values(normalized_data.get("experience", []))
    cv.detected_roles = join_structured_values(normalized_data.get("roles", []))
    cv.detected_institutions = join_structured_values(normalized_data.get("institutions", []))

    if save:
        cv.save(update_fields=[
            "structured_data",
            "detected_skills",
            "detected_education",
            "detected_experience",
            "detected_roles",
            "detected_institutions",
        ])

    return cv


def text_matches_variants(text, variants):
    normalized_text = normalize_text(text)
    return any(normalize_text(variant) in normalized_text for variant in variants if variant)


def split_search_terms(value):
    stopwords = {
        "con",
        "del",
        "los",
        "las",
        "una",
        "uno",
        "para",
        "por",
        "que",
        "perfil",
        "perfiles",
        "experiencia",
    }
    return [
        term
        for term in normalize_text(value).split()
        if (len(term) > 2 or any(symbol in term for symbol in ["#", "+", "."])) and term not in stopwords
    ]


def get_cv_search_text(cv):
    return " ".join([
        cv.candidate_name or "",
        cv.analysis_result or "",
        cv.detected_skills or "",
        cv.detected_education or "",
        cv.detected_experience or "",
        cv.detected_roles or "",
        cv.detected_institutions or "",
    ])


def institution_matches_cv(cv, institution):
    acronym, canonical, _ = get_institution_filter_target(institution)
    institution_text = cv.detected_institutions or ""

    for name_variant in get_canonical_institution_name_variants(canonical):
        if text_matches_variants(institution_text, [name_variant]):
            return True

    if acronym:
        acronym_boundary = rf"(^|[^A-Za-z0-9]){re.escape(acronym)}([^A-Za-z0-9]|$)"
        return bool(re.search(acronym_boundary, institution_text, re.IGNORECASE))

    return False


def score_cv_for_search(cv, q="", skill="", role="", education="", institution=""):
    weights = {}
    score = 0
    reasons = []

    if q:
        terms = split_search_terms(q)
        if terms:
            weights["q"] = 40
            searchable_text = normalize_text(get_cv_search_text(cv))
            matched_terms = [
                term
                for term in terms
                if any(
                    normalize_text(variant) in searchable_text
                    for variant in (
                        get_search_variants(term)
                        if term.lower() in INSTITUTION_ALIASES
                        else [term]
                    )
                )
            ]

            if matched_terms:
                score += weights["q"] * (len(matched_terms) / len(terms))
                reasons.append(f"Coincide con {len(matched_terms)} término(s) de búsqueda")

    if skill:
        weights["skill"] = 20
        if text_matches_variants(cv.detected_skills or "", get_search_variants(skill)):
            score += weights["skill"]
            reasons.append("Skill detectada")
        else:
            return 0, []

    if role:
        weights["role"] = 15
        if text_matches_variants(cv.detected_roles or "", get_search_variants(role)):
            score += weights["role"]
            reasons.append("Puesto compatible")
        else:
            return 0, []

    if education:
        weights["education"] = 15
        if text_matches_variants(cv.detected_education or "", get_search_variants(education)):
            score += weights["education"]
            reasons.append("Formación compatible")
        else:
            return 0, []

    if institution:
        weights["institution"] = 20
        if institution_matches_cv(cv, institution):
            score += weights["institution"]
            reasons.append("Universidad compatible")
        else:
            return 0, []

    total_weight = sum(weights.values())
    if not total_weight or score <= 0:
        return 0, []

    normalized_score = round((score / total_weight) * 100)
    return min(normalized_score, 100), reasons[:3]


def build_profile_scorecard(cv):
    data = cv.structured_data or {}
    languages = data.get("languages") or []
    seniority = data.get("seniority") or "No informado"

    missing = []
    if not cv.detected_skills:
        missing.append("skills")
    if not cv.detected_roles:
        missing.append("puestos")
    if not cv.detected_education:
        missing.append("formación")
    if not cv.detected_institutions:
        missing.append("institución")

    ready_for_matching = (
        cv.status == "completed"
        and cv.has_valid_text()
        and bool(cv.detected_skills or cv.detected_roles)
    )

    strengths = []
    if cv.detected_skills:
        strengths.append("Skills detectadas")
    if cv.detected_roles:
        strengths.append("Puestos identificados")
    if cv.detected_institutions:
        strengths.append("Institución normalizada")
    if seniority and seniority != "No informado":
        strengths.append("Seniority informado")

    return {
        "seniority": seniority,
        "languages": languages,
        "ready_for_matching": ready_for_matching,
        "missing": missing,
        "strengths": strengths,
        "completeness_score": calculate_profile_completeness(cv),
    }


def get_saved_criterion_for_request(request, allowed_types):
    criterion_id = request.GET.get('criterion')
    if not criterion_id:
        return None

    criterion = get_object_or_404(
        get_accessible_saved_criteria(request.user),
        id=criterion_id,
        criterion_type__in=allowed_types,
    )
    criterion.last_used_at = timezone.now()
    criterion.save(update_fields=['last_used_at'])
    return criterion


def calculate_profile_completeness(cv):
    checks = [
        cv.status == "completed",
        cv.has_valid_text(),
        bool(cv.detected_skills),
        bool(cv.detected_roles),
        bool(cv.detected_education),
        bool(cv.detected_institutions),
        bool((cv.structured_data or {}).get("seniority") and (cv.structured_data or {}).get("seniority") != "No informado"),
        bool((cv.structured_data or {}).get("languages")),
    ]

    return round((sum(1 for check in checks if check) / len(checks)) * 100)


@login_required
def cv_list(request):
    cvs = get_accessible_cvs(request.user).order_by('-uploaded_at')

    q = request.GET.get('q', '').strip()
    skill = request.GET.get('skill', '').strip()
    role = request.GET.get('role', '').strip()
    education = request.GET.get('education', '').strip()
    institution = request.GET.get('institution', '').strip()
    has_search = any([q, skill, role, education, institution])

    if has_search:
        ranked_cvs = []

        for cv in cvs:
            match_score, match_reasons = score_cv_for_search(
                cv,
                q=q,
                skill=skill,
                role=role,
                education=education,
                institution=institution,
            )

            if match_score > 0:
                cv.match_score = match_score
                cv.match_reasons = match_reasons
                ranked_cvs.append(cv)

        cvs = sorted(ranked_cvs, key=lambda cv: (cv.match_score, cv.uploaded_at), reverse=True)

    paginator = Paginator(cvs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for cv in page_obj.object_list:
        cv.completeness_score = calculate_profile_completeness(cv)

    context = {
        'page_obj': page_obj,
        'total_cvs': len(cvs) if has_search else cvs.count(),
        'has_search': has_search,
        'filters': {
            'q': q,
            'skill': skill,
            'role': role,
            'education': education,
            'institution': institution,
        },
        'university_options': UNIVERSITY_CATALOG,
        'can_write_profiles': can_write(request.user),
    }

    return render(request, 'cvs/cv_list.html', context)


@login_required
def cv_upload(request):
    """Subir un nuevo CV"""
    if not require_write_access(request):
        return redirect('cv_list')

    if request.method == 'POST':
        form = CVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                cv = form.save(commit=False)
                cv.uploaded_by = request.user
                
                # Validar el archivo PDF
                pdf_file = request.FILES['pdf_file']
                is_valid, error_message = validate_pdf_file(pdf_file)
                
                if not is_valid:
                    messages.error(request, f"Error en el archivo PDF: {error_message}")
                    return render(request, 'cvs/cv_upload.html', {'form': form})
                
                cv.status = 'processing'
                cv.save()
                log_audit(request.user, 'cv_upload', f'Cargo el perfil {cv.candidate_name}', cv=cv)
                
                # Procesar el PDF en background (simulado)
                try:
                    # Extraer texto del PDF
                    pdf_text = extract_text_from_pdf(pdf_file)

                    if not pdf_text or len(pdf_text.strip()) < 50:
                        cv.status = 'error'
                        cv.processing_error = 'No se pudo extraer texto suficiente del PDF.'
                        cv.text_length = len(pdf_text.strip()) if pdf_text else 0
                        cv.save()
                        messages.error(request, 'El PDF se cargó, pero no contiene texto suficiente para analizar.')
                        return redirect('cv_detail', cv_id=cv.id)

                    ollama_service = OllamaService()
                    analysis_result = ollama_service.summarize_cv(pdf_text)
                    
                    structured_data = ollama_service.extract_structured_profile(pdf_text)

                    apply_structured_data_to_cv(cv, structured_data, save=False)
                    cv.extracted_text = pdf_text
                    cv.text_length = len(pdf_text.strip())
                    cv.analysis_result = analysis_result
                    cv.status = 'completed'
                    cv.save()
                    
                    messages.success(request, f'CV de {cv.candidate_name} subido y procesado exitosamente!')
                    
                except Exception as e:
                    logger.error(f"Error procesando CV: {e}")
                    cv.status = 'error'
                    cv.processing_error = str(e)
                    cv.analysis_result = f"Error procesando el CV: {str(e)}"
                    cv.save()
                    messages.error(request, 'El CV se subió pero hubo un error en el procesamiento.')
                
                return redirect('cv_detail', cv_id=cv.id)
                
            except Exception as e:
                logger.error(f"Error subiendo CV: {e}")
                messages.error(request, f'Error subiendo el CV: {str(e)}')
    else:
        form = CVUploadForm()
    
    return render(request, 'cvs/cv_upload.html', {'form': form})


@login_required
def cv_detail(request, cv_id):
    """Detalle de un CV con posibilidad de hacer consultas"""
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)
    queries = AnalysisQuery.objects.filter(cv=cv).order_by('-created_at')
    
    query_form = QueryForm()
    
    context = {
        'cv': cv,
        'queries': queries,
        'query_form': query_form,
        'scorecard': build_profile_scorecard(cv),
        'can_write_profiles': can_write(request.user),
    }
    
    return render(request, 'cvs/cv_detail.html', context)


@login_required
def cv_report(request, cv_id):
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)

    context = {
        'cv': cv,
        'scorecard': build_profile_scorecard(cv),
        'generated_at': timezone.now(),
    }

    return render(request, 'cvs/cv_report.html', context)


@login_required
def cv_document(request, cv_id):
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)
    return FileResponse(
        cv.pdf_file.open('rb'),
        content_type='application/pdf',
        filename=cv.pdf_file.name.split('/')[-1],
    )


@login_required
def cv_reprocess(request, cv_id):
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)

    if request.method != 'POST':
        return redirect('cv_detail', cv_id=cv.id)

    if not require_write_access(request):
        return redirect('cv_detail', cv_id=cv.id)

    try:
        cv.status = 'processing'
        cv.processing_error = ''
        cv.save(update_fields=['status', 'processing_error'])

        if cv.has_valid_text():
            pdf_text = cv.extracted_text
        else:
            pdf_text = extract_text_from_pdf(cv.pdf_file)

        if not pdf_text or len(pdf_text.strip()) < 50:
            cv.status = 'error'
            cv.processing_error = 'No se pudo extraer texto suficiente del PDF.'
            cv.text_length = len(pdf_text.strip()) if pdf_text else 0
            cv.save(update_fields=['status', 'processing_error', 'text_length'])
            messages.error(request, 'No se pudo extraer texto suficiente para reprocesar el perfil.')
            return redirect('cv_detail', cv_id=cv.id)

        ollama_service = OllamaService()
        analysis_result = ollama_service.summarize_cv(pdf_text)
        structured_data = ollama_service.extract_structured_profile(pdf_text)

        apply_structured_data_to_cv(cv, structured_data, save=False)
        cv.extracted_text = pdf_text
        cv.text_length = len(pdf_text.strip())
        cv.analysis_result = analysis_result
        cv.status = 'completed'
        cv.processed_at = timezone.now()
        cv.processing_error = ''
        cv.save()
        log_audit(request.user, 'cv_reprocess', f'Reproceso el perfil {cv.candidate_name}', cv=cv)

        messages.success(request, f'Perfil de {cv.candidate_name} reprocesado y normalizado correctamente.')

    except Exception as e:
        logger.error(f"Error reprocesando CV {cv.id}: {e}")
        cv.status = 'error'
        cv.processing_error = str(e)
        cv.save(update_fields=['status', 'processing_error'])
        messages.error(request, f'Error reprocesando el perfil: {str(e)}')

    return redirect('cv_detail', cv_id=cv.id)


@login_required
def normalize_existing_profiles(request):
    if request.method != 'POST':
        return redirect('cv_list')

    if not require_write_access(request):
        return redirect('cv_list')

    cvs = get_accessible_cvs(request.user)
    updated = 0

    for cv in cvs:
        source_data = cv.structured_data or structured_data_from_cv_fields(cv)
        apply_structured_data_to_cv(cv, source_data, save=True)
        updated += 1

    messages.success(request, f'{updated} perfil{"" if updated == 1 else "es"} normalizado{"" if updated == 1 else "s"} contra el catálogo actual.')
    log_audit(request.user, 'profiles_normalized', f'Normalizo {updated} perfiles existentes')
    return redirect('cv_list')


@login_required
def update_cv_pipeline(request, cv_id):
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)

    if request.method != 'POST':
        return redirect('cv_detail', cv_id=cv.id)

    if not require_write_access(request):
        return redirect('cv_detail', cv_id=cv.id)

    pipeline_status = request.POST.get('pipeline_status', cv.pipeline_status)
    recruiter_notes = request.POST.get('recruiter_notes', cv.recruiter_notes or '').strip()
    is_shortlisted = request.POST.get('is_shortlisted') == 'on'

    valid_statuses = {choice[0] for choice in CV.PIPELINE_STATUS_CHOICES}
    if pipeline_status not in valid_statuses:
        messages.error(request, 'Estado de selección inválido.')
        return redirect('cv_detail', cv_id=cv.id)

    if pipeline_status == 'shortlist':
        is_shortlisted = True

    cv.pipeline_status = pipeline_status
    cv.recruiter_notes = recruiter_notes
    cv.is_shortlisted = is_shortlisted
    cv.save(update_fields=['pipeline_status', 'recruiter_notes', 'is_shortlisted'])
    log_audit(request.user, 'pipeline_update', f'Actualizo pipeline de {cv.candidate_name}', cv=cv)

    messages.success(request, 'Estado de selección actualizado.')
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)

    return redirect('cv_detail', cv_id=cv.id)


@login_required
def selection_kanban(request):
    cvs = get_accessible_cvs(request.user).order_by('-uploaded_at')
    columns = []

    for status_value, status_label in CV.PIPELINE_STATUS_CHOICES:
        items = []
        for cv in cvs:
            if cv.pipeline_status == status_value:
                cv.completeness_score = calculate_profile_completeness(cv)
                items.append(cv)

        columns.append({
            'status': status_value,
            'label': status_label,
            'items': items,
        })

    return render(request, 'cvs/selection_kanban.html', {
        'columns': columns,
        'total_cvs': cvs.count(),
        'can_write_profiles': can_write(request.user),
    })


@login_required
def export_shortlist(request):
    cvs = get_accessible_cvs(request.user).filter(
        models.Q(is_shortlisted=True) | models.Q(pipeline_status='shortlist')
    ).order_by('candidate_name')
    log_audit(request.user, 'shortlist_export', 'Exporto la shortlist')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="shortlist_talentscan.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Candidato',
        'Estado selección',
        'Completitud',
        'Skills',
        'Puestos',
        'Formación',
        'Instituciones',
        'Notas internas',
    ])

    for cv in cvs:
        writer.writerow([
            cv.candidate_name,
            cv.get_pipeline_status_display(),
            f'{calculate_profile_completeness(cv)}%',
            cv.detected_skills or '',
            cv.detected_roles or '',
            cv.detected_education or '',
            cv.detected_institutions or '',
            cv.recruiter_notes or '',
        ])

    return response


@login_required
def saved_criteria(request):
    if request.method == 'POST':
        if not require_write_access(request):
            return redirect('saved_criteria')

        form = SavedCriterionForm(request.POST)

        if form.is_valid():
            criterion = form.save(commit=False)
            criterion.user = request.user
            criterion.save()
            log_audit(request.user, 'criterion_created', f'Creo el criterio {criterion.name}')
            messages.success(request, 'Criterio guardado correctamente.')
            return redirect('saved_criteria')
    else:
        form = SavedCriterionForm()

    criteria = get_accessible_saved_criteria(request.user)
    grouped_counts = {
        'job_match': criteria.filter(criterion_type='job_match').count(),
        'bulk_analysis': criteria.filter(criterion_type='bulk_analysis').count(),
        'search': criteria.filter(criterion_type='search').count(),
    }

    return render(request, 'cvs/saved_criteria.html', {
        'form': form,
        'criteria': criteria,
        'grouped_counts': grouped_counts,
    })


@login_required
def delete_saved_criterion(request, criterion_id):
    criterion = get_object_or_404(get_accessible_saved_criteria(request.user), id=criterion_id)

    if request.method == 'POST':
        if not require_write_access(request):
            return redirect('saved_criteria')

        criterion_name = criterion.name
        criterion.delete()
        log_audit(request.user, 'criterion_deleted', f'Elimino el criterio {criterion_name}')
        messages.success(request, 'Criterio eliminado correctamente.')

    return redirect('saved_criteria')


@login_required
def cv_query(request, cv_id):
    """Procesar una consulta sobre un CV específico"""
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)
    
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            query_text = form.cleaned_data['query']
            
            try:
                # Extraer texto del PDF si no está disponible
                if cv.status != 'completed':
                    error_message = 'El perfil todavía no está disponible para consultas.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_message})
                    messages.error(request, error_message)
                    return redirect('cv_detail', cv_id=cv.id)

                if cv.has_valid_text():
                    pdf_text = cv.extracted_text
                else:
                    pdf_text = extract_text_from_pdf(cv.pdf_file)
                    cv.extracted_text = pdf_text
                    cv.text_length = len(pdf_text.strip()) if pdf_text else 0
                    cv.save(update_fields=['extracted_text', 'text_length'])

                if not pdf_text or len(pdf_text.strip()) < 50:
                    error_message = 'No hay texto suficiente para analizar este perfil.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': error_message})
                    messages.error(request, error_message)
                    return redirect('cv_detail', cv_id=cv.id)
                
                # Realizar consulta a Ollama
                ollama_service = OllamaService()
                response = ollama_service.analyze_cv(pdf_text, query_text)
                
                # Guardar la consulta y respuesta
                analysis_query = AnalysisQuery.objects.create(
                    cv=cv,
                    user=request.user,
                    query=query_text,
                    response=response
                )
                log_audit(request.user, 'cv_query', f'Consulto el perfil {cv.candidate_name}', cv=cv)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    # Respuesta AJAX
                    return JsonResponse({
                        'success': True,
                        'response': response,
                        'query_id': analysis_query.id,
                        'created_at': analysis_query.created_at.strftime('%d/%m/%Y %H:%M')
                    })
                else:
                    messages.success(request, 'Consulta procesada exitosamente!')
                    return redirect('cv_detail', cv_id=cv.id)
                    
            except Exception as e:
                logger.error(f"Error procesando consulta: {e}")
                error_message = f"Error procesando la consulta: {str(e)}"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    })
                else:
                    messages.error(request, error_message)
                    return redirect('cv_detail', cv_id=cv.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Formulario inválido'
                })
    
    return redirect('cv_detail', cv_id=cv.id)


@login_required
def cv_delete(request, cv_id):
    """Eliminar un CV"""
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)

    if not require_write_access(request):
        return redirect('cv_detail', cv_id=cv.id)
    
    if request.method == 'POST':
        candidate_name = cv.candidate_name
        log_audit(request.user, 'cv_delete', f'Elimino el perfil {candidate_name}', cv=cv)
        cv.delete()
        messages.success(request, f'CV de {candidate_name} eliminado exitosamente!')
        return redirect('cv_list')
    
    return render(request, 'cvs/cv_confirm_delete.html', {'cv': cv})


@login_required
def analysis_history(request):
    """Historial de todas las consultas del usuario"""
    queries = AnalysisQuery.objects.filter(cv__in=get_accessible_cvs(request.user)).select_related('cv').order_by('-created_at')
    paginator = Paginator(queries, 20)  # 20 consultas por página
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_queries': queries.count()
    }
    return render(request, 'cvs/analysis_history.html', context)


@login_required
def ollama_status(request):
    try:
        ai_service = OllamaService()
        connected = ai_service.check_connection()

        return JsonResponse({
            'connected': connected,
            'target_model': 'OpenAI gpt-4o-mini'
        })

    except Exception as e:
        logger.error(f"Error verificando estado IA: {e}")

        return JsonResponse({
            'connected': False,
            'target_model': 'OpenAI gpt-4o-mini'
        })


@login_required
def bulk_analysis(request):
    """Vista para análisis comparativo de perfiles profesionales"""
    user_cvs = get_accessible_cvs(request.user).filter(status='completed').order_by('-uploaded_at')

    # Quitar duplicados por nombre de candidato
    unique_cvs = []
    seen_names = set()

    for cv in user_cvs:
        normalized_name = cv.candidate_name.strip().lower()

        if normalized_name not in seen_names:
            unique_cvs.append(cv)
            seen_names.add(normalized_name)

    if request.method == 'POST':
        if not require_write_access(request):
            return redirect('bulk_analysis')

        form = BulkQueryForm(request.POST)

        if form.is_valid():
            query_text = form.cleaned_data['query']

            if len(unique_cvs) == 0:
                messages.error(request, 'No tenés perfiles procesados para analizar.')
                return redirect('bulk_analysis')

            if len(unique_cvs) < 2:
                messages.error(request, 'Se requieren al menos 2 perfiles distintos para realizar una comparativa.')
                return redirect('bulk_analysis')

            try:
                start_time = time.time()

                cvs_data = []

                for cv in unique_cvs:
                    try:
                        if cv.has_valid_text():
                            pdf_text = cv.extracted_text
                        else:
                            pdf_text = extract_text_from_pdf(cv.pdf_file)
                            cv.extracted_text = pdf_text
                            cv.text_length = len(pdf_text.strip()) if pdf_text else 0
                            cv.save(update_fields=['extracted_text', 'text_length'])

                        if not pdf_text or len(pdf_text.strip()) < 50:
                            logger.warning(f"Texto insuficiente en el perfil {cv.id}")
                            continue

                        cvs_data.append({
                            'name': cv.candidate_name,
                            'text': pdf_text,
                            'cv_id': cv.id
                        })

                    except Exception as e:
                        logger.error(f"Error extrayendo texto del perfil {cv.id}: {e}")
                        continue

                if len(cvs_data) < 2:
                    messages.error(
                        request,
                        'No se pudo extraer texto suficiente de al menos 2 perfiles distintos.'
                    )
                    return redirect('bulk_analysis')

                ollama_service = OllamaService()
                response = ollama_service.bulk_analyze_cvs(cvs_data, query_text)

                processing_time = time.time() - start_time

                with transaction.atomic():
                    bulk_query = BulkAnalysisQuery.objects.create(
                        user=request.user,
                        query=query_text,
                        response=response,
                        processing_time=processing_time
                    )

                    # guardar solo los CVs realmente analizados
                    analyzed_ids = [item['cv_id'] for item in cvs_data]
                    analyzed_cvs = get_accessible_cvs(request.user).filter(id__in=analyzed_ids)
                    bulk_query.cvs_analyzed.set(analyzed_cvs)
                    log_audit(request.user, 'bulk_analysis', 'Genero una comparativa IA')

                messages.success(
                    request,
                    f'Comparativa generada correctamente en {processing_time:.2f} segundos.'
                )
                return redirect('bulk_analysis_detail', query_id=bulk_query.id)

            except Exception as e:
                logger.error(f"Error en análisis comparativo: {e}")
                messages.error(request, f'Error procesando la comparativa: {str(e)}')
                return redirect('bulk_analysis')

        else:
            messages.error(request, 'Formulario inválido.')
    else:
        criterion = get_saved_criterion_for_request(request, ['bulk_analysis', 'search'])
        form = BulkQueryForm(initial={'query': criterion.content} if criterion else None)

    bulk_queries = BulkAnalysisQuery.objects.filter(user__in=get_accessible_users(request.user)).order_by('-created_at')[:5]
    saved_criteria = get_accessible_saved_criteria(request.user).filter(
        criterion_type__in=['bulk_analysis', 'search'],
    )[:5]

    context = {
        'form': form,
        'cvs_count': len(unique_cvs),
        'user_cvs': unique_cvs[:10],
        'bulk_queries': bulk_queries,
        'saved_criteria': saved_criteria,
    }

    return render(request, 'cvs/bulk_analysis.html', context)


@login_required
def bulk_analysis_detail(request, query_id):
    """Vista de detalle para una consulta masiva"""
    bulk_query = get_object_or_404(BulkAnalysisQuery.objects.filter(user__in=get_accessible_users(request.user)), id=query_id)
    
    context = {
        'bulk_query': bulk_query,
        'cvs_analyzed': bulk_query.cvs_analyzed.all(),
    }
    
    return render(request, 'cvs/bulk_analysis_detail.html', context)


@login_required
def bulk_analysis_history(request):
    """Historial de consultas masivas"""
    bulk_queries = BulkAnalysisQuery.objects.filter(user__in=get_accessible_users(request.user)).order_by('-created_at')
    paginator = Paginator(bulk_queries, 10)
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_queries': bulk_queries.count()
    }
    
    return render(request, 'cvs/bulk_analysis_history.html', context)

@login_required
def job_match(request):
    user_cvs = get_accessible_cvs(request.user).filter(status='completed').order_by('-uploaded_at')

    unique_cvs = []
    seen_names = set()

    for cv in user_cvs:
        normalized_name = cv.candidate_name.strip().lower()
        if normalized_name not in seen_names:
            unique_cvs.append(cv)
            seen_names.add(normalized_name)

    if request.method == 'POST':
        if not require_write_access(request):
            return redirect('job_match')

        form = JobDescriptionMatchForm(request.POST)

        if form.is_valid():
            job_description = form.cleaned_data['job_description']

            if len(unique_cvs) < 2:
                messages.error(request, 'Se requieren al menos 2 perfiles procesados para calcular matching.')
                return redirect('job_match')

            try:
                start_time = time.time()
                cvs_data = []

                for cv in unique_cvs:
                    if cv.has_valid_text():
                        pdf_text = cv.extracted_text
                    else:
                        pdf_text = extract_text_from_pdf(cv.pdf_file)
                        cv.extracted_text = pdf_text
                        cv.text_length = len(pdf_text.strip()) if pdf_text else 0
                        cv.save(update_fields=['extracted_text', 'text_length'])

                    if pdf_text and len(pdf_text.strip()) >= 50:
                        cvs_data.append({
                            'name': cv.candidate_name,
                            'text': pdf_text,
                            'cv_id': cv.id
                        })

                if len(cvs_data) < 2:
                    messages.error(request, 'No hay suficiente texto extraído para evaluar perfiles.')
                    return redirect('job_match')

                ia_service = OllamaService()
                response = ia_service.match_job_description(cvs_data, job_description)

                processing_time = time.time() - start_time

                with transaction.atomic():
                    match_query = JobMatchQuery.objects.create(
                        user=request.user,
                        job_description=job_description,
                        response=response,
                        processing_time=processing_time
                    )

                    analyzed_ids = [item['cv_id'] for item in cvs_data]
                    analyzed_cvs = get_accessible_cvs(request.user).filter(id__in=analyzed_ids)
                    match_query.cvs_analyzed.set(analyzed_cvs)
                    log_audit(request.user, 'job_match', 'Genero un matching contra puesto')

                messages.success(request, f'Matching generado correctamente en {processing_time:.2f} segundos.')
                return redirect('job_match_detail', match_id=match_query.id)

            except Exception as e:
                logger.error(f"Error en matching contra puesto: {e}")
                messages.error(request, f'Error procesando matching: {str(e)}')
                return redirect('job_match')

    else:
        criterion = get_saved_criterion_for_request(request, ['job_match'])
        form = JobDescriptionMatchForm(initial={'job_description': criterion.content} if criterion else None)

    recent_matches = JobMatchQuery.objects.filter(user__in=get_accessible_users(request.user)).order_by('-created_at')[:5]
    saved_criteria = get_accessible_saved_criteria(request.user).filter(criterion_type='job_match')[:5]

    context = {
        'form': form,
        'cvs_count': len(unique_cvs),
        'user_cvs': unique_cvs[:10],
        'recent_matches': recent_matches,
        'saved_criteria': saved_criteria,
    }

    return render(request, 'cvs/job_match.html', context)


@login_required
def job_match_detail(request, match_id):
    match_query = get_object_or_404(JobMatchQuery.objects.filter(user__in=get_accessible_users(request.user)), id=match_id)

    context = {
        'match_query': match_query,
        'cvs_analyzed': match_query.cvs_analyzed.all(),
    }

    return render(request, 'cvs/job_match_detail.html', context)

@login_required
def generate_interview_questions(request, cv_id):
    cv = get_object_or_404(
        get_accessible_cvs(request.user),
        id=cv_id
    )

    try:
        ia_service = OllamaService()

        response = ia_service.generate_interview_questions(
            cv.extracted_text
        )

        return JsonResponse({
            'success': True,
            'response': response
        })

    except Exception as e:
        logger.error(f"Error generando preguntas: {e}")

        return JsonResponse({
            'success': False,
            'error': 'Error generando preguntas'
        })


@login_required
def team_settings(request):
    if not require_admin_access(request):
        return redirect('cv_list')

    profile = get_user_profile(request.user)
    organization = profile.organization

    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        role = request.POST.get('role', 'viewer').strip()

        valid_roles = {choice[0] for choice in UserProfile.ROLE_CHOICES}
        if action in {'add', 'update_role'} and role not in valid_roles:
            messages.error(request, 'Rol invalido.')
            return redirect('team_settings')

        if action == 'add':
            username = request.POST.get('username', '').strip()
            member = User.objects.filter(username=username).first()
            if not member:
                messages.error(request, 'No existe un usuario con ese username.')
                return redirect('team_settings')

            member_profile, _ = UserProfile.objects.get_or_create(
                user=member,
                defaults={'organization': organization, 'role': role},
            )
            member_profile.organization = organization
            member_profile.role = role
            member_profile.save(update_fields=['organization', 'role'])

            log_audit(request.user, 'team_member_added', f'Agrego {member.username} como {role}')
            messages.success(request, f'{member.username} ahora pertenece a {organization.name} como {role}.')
            return redirect('team_settings')

        member_profile = get_object_or_404(
            UserProfile.objects.select_related('user'),
            id=request.POST.get('profile_id'),
            organization=organization,
        )

        if member_profile.user == request.user:
            messages.warning(request, 'No podés modificar o quitar tu propio rol desde esta pantalla.')
            return redirect('team_settings')

        if action == 'update_role':
            member_profile.role = role
            member_profile.save(update_fields=['role'])
            log_audit(request.user, 'team_member_role_updated', f'Actualizo rol de {member_profile.user.username} a {role}')
            messages.success(request, f'Rol de {member_profile.user.username} actualizado.')
            return redirect('team_settings')

        if action == 'remove':
            username = member_profile.user.username
            member_profile.delete()
            log_audit(request.user, 'team_member_removed', f'Quito a {username} del equipo')
            messages.success(request, f'{username} fue quitado del equipo.')
            return redirect('team_settings')

        messages.error(request, 'Accion invalida.')
        return redirect('team_settings')

    members = UserProfile.objects.filter(organization=organization).select_related('user').order_by('user__username')

    return render(request, 'cvs/team_settings.html', {
        'organization': organization,
        'members': members,
        'roles': UserProfile.ROLE_CHOICES,
    })


@login_required
def audit_log(request):
    if not require_admin_access(request):
        return redirect('cv_list')

    organization = get_user_organization(request.user)
    events = AuditEvent.objects.filter(organization=organization).select_related('user', 'cv')
    paginator = Paginator(events, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'cvs/audit_log.html', {
        'page_obj': page_obj,
        'total_events': events.count(),
    })


@login_required
def create_shared_report_link(request, cv_id):
    cv = get_object_or_404(get_accessible_cvs(request.user), id=cv_id)

    if request.method != 'POST':
        return redirect('cv_detail', cv_id=cv.id)

    if not require_write_access(request):
        return redirect('cv_detail', cv_id=cv.id)

    shared_link = SharedReportLink.objects.create(
        cv=cv,
        created_by=request.user,
        expires_at=timezone.now() + timezone.timedelta(days=30),
    )
    log_audit(request.user, 'report_shared', f'Creo link seguro para {cv.candidate_name}', cv=cv)

    public_url = request.build_absolute_uri(
        reverse('shared_cv_report', kwargs={'token': shared_link.token})
    )

    return render(request, 'cvs/shared_report_link.html', {
        'cv': cv,
        'shared_link': shared_link,
        'public_url': public_url,
    })


def shared_cv_report(request, token):
    shared_link = get_object_or_404(
        SharedReportLink.objects.select_related('cv', 'created_by'),
        token=token,
    )

    if not shared_link.is_valid():
        messages.error(request, 'El link del informe ya no esta disponible.')
        return redirect('login')

    cv = shared_link.cv
    return render(request, 'cvs/cv_report.html', {
        'cv': cv,
        'scorecard': build_profile_scorecard(cv),
        'generated_at': timezone.now(),
        'shared_link': shared_link,
    })


def split_values(value):
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(',')
        if item.strip()
    ]


@login_required
def recruiter_dashboard(request):
    cvs = get_accessible_cvs(request.user)

    total_cvs = cvs.count()
    completed_cvs = cvs.filter(status='completed').count()
    processing_cvs = cvs.filter(status='processing').count()
    error_cvs = cvs.filter(status='error').count()

    completed_percent = round((completed_cvs / total_cvs) * 100) if total_cvs else 0
    processing_percent = round((processing_cvs / total_cvs) * 100) if total_cvs else 0
    error_percent = round((error_cvs / total_cvs) * 100) if total_cvs else 0

    skills_counter = Counter()
    institutions_counter = Counter()
    roles_counter = Counter()
    education_counter = Counter()
    seniority_counter = Counter()
    languages_counter = Counter()
    top_candidates = []

    for cv in cvs:
        cv.completeness_score = calculate_profile_completeness(cv)
        top_candidates.append(cv)

        skills_counter.update(split_values(cv.detected_skills))
        institutions_counter.update(split_values(cv.detected_institutions))
        roles_counter.update(split_values(cv.detected_roles))
        education_counter.update(split_values(cv.detected_education))

        data = cv.structured_data or {}

        seniority = data.get('seniority')
        if seniority and seniority.strip().lower() != 'no informado':
            seniority_counter.update([seniority])

        languages = data.get('languages', [])
        if isinstance(languages, list):
            clean_languages = [
                lang.strip()
                for lang in languages
                if lang and lang.strip().lower() != 'no informado'
            ]
            languages_counter.update(clean_languages)

    top_candidates = sorted(
        top_candidates,
        key=lambda item: (item.completeness_score, item.is_shortlisted, item.uploaded_at),
        reverse=True
    )[:5]

    ready_for_matching_count = sum(
        1 for cv in cvs
        if cv.status == 'completed' and cv.has_valid_text() and bool(cv.detected_skills or cv.detected_roles)
    )
    missing_skills_count = cvs.filter(status='completed').filter(
        models.Q(detected_skills__isnull=True) | models.Q(detected_skills='')
    ).count()
    missing_institutions_count = cvs.filter(status='completed').filter(
        models.Q(detected_institutions__isnull=True) | models.Q(detected_institutions='')
    ).count()
    shortlisted_count = cvs.filter(models.Q(is_shortlisted=True) | models.Q(pipeline_status='shortlist')).count()
    interview_count = cvs.filter(pipeline_status='interview').count()
    review_count = cvs.filter(pipeline_status='review').count()

    quality_alerts = [
        {
            'label': 'Sin skills detectadas',
            'value': missing_skills_count,
            'icon': 'fa-code',
            'tone': 'warning',
        },
        {
            'label': 'Sin universidad',
            'value': missing_institutions_count,
            'icon': 'fa-university',
            'tone': 'warning',
        },
        {
            'label': 'Listos para matching',
            'value': ready_for_matching_count,
            'icon': 'fa-bullseye',
            'tone': 'success',
        },
        {
            'label': 'En revisión',
            'value': review_count,
            'icon': 'fa-eye',
            'tone': 'primary',
        },
    ]

    pipeline_summary = [
        {
            'label': label,
            'count': cvs.filter(pipeline_status=value).count(),
            'status': value,
        }
        for value, label in CV.PIPELINE_STATUS_CHOICES
    ]

    context = {
        'total_cvs': total_cvs,
        'completed_cvs': completed_cvs,
        'processing_cvs': processing_cvs,
        'error_cvs': error_cvs,
        'completed_percent': completed_percent,
        'processing_percent': processing_percent,
        'error_percent': error_percent,
        'top_skills': skills_counter.most_common(10),
        'top_institutions': institutions_counter.most_common(10),
        'top_roles': roles_counter.most_common(10),
        'top_education': education_counter.most_common(10),
        'top_seniority': seniority_counter.most_common(10),
        'top_languages': languages_counter.most_common(10),
        'top_candidates': top_candidates,
        'quality_alerts': quality_alerts,
        'pipeline_summary': pipeline_summary,
        'ready_for_matching_count': ready_for_matching_count,
        'shortlisted_count': shortlisted_count,
        'interview_count': interview_count,
    }

    return render(request, 'cvs/recruiter_dashboard.html', context)

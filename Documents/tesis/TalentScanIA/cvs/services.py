import json
import logging
import re
import unicodedata

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


UNIVERSITY_CATALOG = [
    ("UBA", "Universidad de Buenos Aires"),
    ("UTN", "Universidad Tecnológica Nacional"),
    ("UNC", "Universidad Nacional de Córdoba"),
    ("UNLP", "Universidad Nacional de La Plata"),
    ("UNR", "Universidad Nacional de Rosario"),
    ("UNL", "Universidad Nacional del Litoral"),
    ("UNCUYO", "Universidad Nacional de Cuyo"),
    ("UNS", "Universidad Nacional del Sur"),
    ("UNNE", "Universidad Nacional del Nordeste"),
    ("UNT", "Universidad Nacional de Tucumán"),
    ("UNSA", "Universidad Nacional de Salta"),
    ("UNJU", "Universidad Nacional de Jujuy"),
    ("UNSE", "Universidad Nacional de Santiago del Estero"),
    ("UNCA", "Universidad Nacional de Catamarca"),
    ("UNLAR", "Universidad Nacional de La Rioja"),
    ("UNRC", "Universidad Nacional de Río Cuarto"),
    ("UNCOMA", "Universidad Nacional del Comahue"),
    ("UNPSJB", "Universidad Nacional de la Patagonia San Juan Bosco"),
    ("UNPA", "Universidad Nacional de la Patagonia Austral"),
    ("UNAM", "Universidad Nacional de Misiones"),
    ("UNER", "Universidad Nacional de Entre Ríos"),
    ("UNVM", "Universidad Nacional de Villa María"),
    ("UNNOBA", "Universidad Nacional del Noroeste de la Provincia de Buenos Aires"),
    ("UNGS", "Universidad Nacional de General Sarmiento"),
    ("UNQ", "Universidad Nacional de Quilmes"),
    ("UNLA", "Universidad Nacional de Lanús"),
    ("UNAJ", "Universidad Nacional Arturo Jauretche"),
    ("UNM", "Universidad Nacional de Moreno"),
    ("UNIPE", "Universidad Pedagógica Nacional"),
    ("UNTREF", "Universidad Nacional de Tres de Febrero"),
    ("UNDEF", "Universidad de la Defensa Nacional"),
    ("UNAHUR", "Universidad Nacional de Hurlingham"),
    ("UNO", "Universidad Nacional del Oeste"),
    ("UNAB", "Universidad Nacional Guillermo Brown"),
    ("UNPAZ", "Universidad Nacional de José C. Paz"),
    ("UNRAF", "Universidad Nacional de Rafaela"),
    ("UNVIME", "Universidad Nacional de Villa Mercedes"),
    ("UNCAUS", "Universidad Nacional del Chaco Austral"),
    ("UNRN", "Universidad Nacional de Río Negro"),
    ("UNSAM", "Universidad Nacional de San Martín"),
    ("UNLZ", "Universidad Nacional de Lomas de Zamora"),
    ("UNMDP", "Universidad Nacional de Mar del Plata"),
    ("UNLU", "Universidad Nacional de Luján"),
    ("UNSADA", "Universidad Nacional de San Antonio de Areco"),
    ("UNADA", "Universidad Nacional de Avellaneda"),
    ("UNA", "Universidad Nacional de las Artes"),
    ("UCA", "Universidad Católica Argentina"),
    ("UADE", "Universidad Argentina de la Empresa"),
    ("UB", "Universidad de Belgrano"),
    ("USAL", "Universidad del Salvador"),
    ("UAI", "Universidad Abierta Interamericana"),
    ("UCES", "Universidad de Ciencias Empresariales y Sociales"),
    ("UP", "Universidad de Palermo"),
    ("UM", "Universidad de Morón"),
    ("UFLO", "Universidad de Flores"),
    ("UCALP", "Universidad Católica de La Plata"),
    ("UCC", "Universidad Católica de Córdoba"),
    ("UCU", "Universidad de Concepción del Uruguay"),
    ("UCSF", "Universidad Católica de Santa Fe"),
    ("UCSE", "Universidad Católica de Santiago del Estero"),
    ("UFASTA", "Universidad FASTA"),
    ("UBP", "Universidad Blas Pascal"),
    ("UES21", "Universidad Empresarial Siglo 21"),
    ("UMAZA", "Universidad Juan Agustín Maza"),
    ("UTDT", "Universidad Torcuato Di Tella"),
    ("ITBA", "Instituto Tecnológico de Buenos Aires"),
    ("UCEMA", "Universidad del CEMA"),
    ("UDESA", "Universidad de San Andrés"),
    ("UF", "Universidad Favaloro"),
    ("UISALUD", "Universidad ISALUD"),
    ("UK", "Universidad Kennedy"),
    ("UCASAL", "Universidad Católica de Salta"),
    ("UCCUYO", "Universidad Católica de Cuyo"),
    ("UMSA", "Universidad del Museo Social Argentino"),
    ("UNAU", "Universidad Notarial Argentina"),
    ("UCH", "Universidad Champagnat"),
    ("UNSTA", "Universidad del Norte Santo Tomás de Aquino"),
    ("UCAMI", "Universidad Católica de las Misiones"),
    ("UGR", "Universidad del Gran Rosario"),
    ("UDA", "Universidad del Aconcagua"),
    ("UGD", "Universidad Gastón Dachary"),
    ("UCP", "Universidad de la Cuenca del Plata"),
    ("UAP", "Universidad Adventista del Plata"),
    ("UDEMM", "Universidad de la Marina Mercante"),
    ("UMENDOZA", "Universidad de Mendoza"),
    ("UPC", "Universidad Provincial de Córdoba"),
    ("UPSO", "Universidad Provincial del Sudoeste"),
    ("UADER", "Universidad Autónoma de Entre Ríos"),
    ("UPE", "Universidad Provincial de Ezeiza"),
    ("UPRO", "Universidad Provincial de Oficios Eva Perón"),
    ("UPCH", "Universidad Provincial del Chubut"),
    ("UPATECO", "Universidad Provincial de Administración, Tecnología y Oficios de Salta"),
]


INSTITUTION_ALIASES = {
    acronym.lower(): name
    for acronym, name in UNIVERSITY_CATALOG
}


UNIVERSITY_CATALOG_PROMPT = "\n".join(
    f"- {acronym} — {name}"
    for acronym, name in UNIVERSITY_CATALOG
)


def normalize_text(value):
    value = str(value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9+#.]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def institution_match_key(value):
    stopwords = {
        "universidad",
        "instituto",
        "nacional",
        "provincial",
        "catolica",
        "de",
        "del",
        "la",
        "las",
        "el",
        "los",
    }
    return " ".join(
        token
        for token in normalize_text(value).split()
        if token not in stopwords
    )


def clean_list(values):
    if not values:
        return []

    if isinstance(values, str):
        values = re.split(r"[,;\n|]+", values)

    cleaned = []
    seen = set()

    for value in values:
        if isinstance(value, dict):
            value = value.get("name") or value.get("title") or value.get("value")

        text = str(value or "").strip(" \t\r\n-•")
        if not text or normalize_text(text) == "no informado":
            continue

        key = normalize_text(text)
        if key and key not in seen:
            cleaned.append(text)
            seen.add(key)

    return cleaned


def build_institution_record(value):
    raw_name = str(value or "").strip()
    normalized = normalize_text(raw_name)
    aliases = set()
    canonical_name = raw_name

    for alias, canonical in INSTITUTION_ALIASES.items():
        canonical_normalized = normalize_text(canonical)
        canonical_key = institution_match_key(canonical)
        normalized_key = institution_match_key(raw_name)
        if (
            normalized == alias
            or normalized == canonical_normalized
            or alias in normalized.split()
            or canonical_normalized in normalized
            or normalized in canonical_normalized
            or (normalized_key and normalized_key == canonical_key)
        ):
            canonical_name = canonical
            aliases.add(alias.upper())
            aliases.add(canonical)
            break

    if raw_name != canonical_name:
        aliases.add(raw_name)

    search_terms = sorted({
        canonical_name,
        normalize_text(canonical_name),
        raw_name,
        normalize_text(raw_name),
        *aliases,
        *(normalize_text(alias) for alias in aliases),
    })

    return {
        "name": canonical_name,
        "raw": raw_name,
        "aliases": sorted(aliases),
        "search_terms": [term for term in search_terms if term],
    }


def normalize_structured_profile(data):
    if not isinstance(data, dict):
        data = {}

    skills = clean_list(data.get("skills"))
    education = clean_list(data.get("education"))
    experience = clean_list(data.get("experience"))
    roles = clean_list(data.get("roles"))
    languages = clean_list(data.get("languages"))
    areas = clean_list(data.get("areas"))

    institution_names = clean_list(data.get("institutions"))
    institution_records = []
    seen_institutions = set()

    for institution_name in institution_names:
        record = build_institution_record(institution_name)
        key = normalize_text(record["name"])
        if key and key not in seen_institutions:
            institution_records.append(record)
            seen_institutions.add(key)

    institution_search_terms = []
    for record in institution_records:
        institution_search_terms.extend(record.get("search_terms", []))

    search_terms = {
        "skills": sorted({term for skill in skills for term in {skill, normalize_text(skill)} if term}),
        "education": sorted({term for item in education for term in {item, normalize_text(item)} if term}),
        "institutions": sorted({term for term in institution_search_terms if term}),
        "roles": sorted({term for role in roles for term in {role, normalize_text(role)} if term}),
        "languages": sorted({term for lang in languages for term in {lang, normalize_text(lang)} if term}),
    }

    seniority = str(data.get("seniority") or "No informado").strip() or "No informado"

    return {
        "skills": skills,
        "education": education,
        "institutions": [record["name"] for record in institution_records],
        "institution_details": institution_records,
        "institution_search_terms": search_terms["institutions"],
        "experience": experience,
        "roles": roles,
        "languages": languages,
        "seniority": seniority,
        "areas": areas,
        "search_terms": search_terms,
    }


class OllamaService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def check_connection(self):
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY no configurada.")
            return False

        try:
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"Error conectando con OpenAI: {e}")
            return False

    def list_models(self):
        return [self.model]

    def generate_response(
        self,
        prompt,
        timeout=60,
        num_predict=400,
        temperature=0.05,
        top_p=0.8,
    ):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                timeout=timeout,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Sos TalentScan IA, un motor profesional de análisis de perfiles. "
                            "Tu tarea es asistir procesos de selección con respuestas breves, "
                            "claras, basadas solo en evidencia explícita del CV. "
                            "No inventes experiencia, habilidades, tecnologías, estudios ni idiomas. "
                            "Si un dato no aparece, indicá 'No informado'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
                top_p=top_p,
                max_tokens=num_predict,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error OpenAI: {e}")
            error_text = str(e)

            if (
                "insufficient_quota" in error_text
                or "exceeded your current quota" in error_text
            ):
                return "Error: la cuenta de OpenAI no tiene cuota o crédito disponible."

            if "rate_limit" in error_text or "429" in error_text:
                return (
                    "Error: se alcanzó el límite temporal de uso de OpenAI. "
                    "Intentá nuevamente en unos segundos."
                )

            if "api_key" in error_text.lower() or "authentication" in error_text.lower():
                return "Error: la API key de OpenAI no es válida o no está configurada."

            return "Error procesando la consulta."

    def analyze_cv(self, cv_text, query):
        cv_text = cv_text[:4000]

        prompt = f"""
Analizá el siguiente perfil profesional y respondé la consulta del usuario.

REGLAS:
- Usá únicamente información explícita del perfil.
- No inventes experiencia, habilidades, tecnologías, estudios, idiomas ni años.
- No hagas inferencias optimistas.
- Si el dato no aparece, escribí: No informado.
- Respondé en español profesional.
- Sé breve y concreto.

CONSULTA DEL USUARIO:
{query}

PERFIL:
{cv_text}

FORMATO EXACTO:
RECOMIENDO:
[Aca decime si o no recomendarías este perfil para el criterio consultado, basado solo en evidencia]

RESUMEN DEL PERFIL:
[2 líneas máximo]

RESPUESTA:
[respuesta directa a la consulta]

EVIDENCIA UTILIZADA:
[lista breve de datos concretos del perfil]
"""

        return self.generate_response(
            prompt=prompt,
            timeout=60,
            num_predict=350,
            temperature=0.03,
            top_p=0.7,
        )

    def summarize_cv(self, cv_text):
        cv_text = cv_text[:5000]

        prompt = f"""
Generá una evaluación inicial del siguiente CV.

REGLAS:
- Extraé solo información explícita.
- No inventes datos.
- No uses "No informado" si el dato sí aparece en el CV.
- Si hay experiencia laboral, listala.
- Si hay habilidades, listalas.
- Si hay educación, listala.
- Respondé en español profesional, claro y breve.

CV:
{cv_text}

FORMATO EXACTO:

RESUMEN DEL PERFIL:
[1 o 2 líneas]

EXPERIENCIA DETECTADA:
- [cargo / área / empresa / período si aparece]

HABILIDADES DETECTADAS:
- [habilidad explícita]

FORMACIÓN:
- [formación explícita]

OBSERVACIONES:
[datos faltantes o aclaraciones relevantes en 1 línea]
"""

        return self.generate_response(
            prompt=prompt,
            timeout=60,
            num_predict=500,
            temperature=0.03,
            top_p=0.7,
        )

    def bulk_analyze_cvs(self, cvs_data, query):
        if not cvs_data:
            return "No hay perfiles para analizar."

        if len(cvs_data) < 2:
            return "Se requieren al menos 2 perfiles."

        cvs_text = ""

        for cv_data in cvs_data:
            candidate_name = cv_data.get("name", "Sin nombre")
            candidate_text = cv_data.get("text", "")[:2500]

            cvs_text += f"""
CANDIDATO: {candidate_name}
{candidate_text}

"""

        prompt = f"""
Compará los siguientes candidatos según la consulta del usuario.

CONSULTA:
{query}

REGLAS:
- Usá solo evidencia explícita de los CVs.
- No inventes experiencia, habilidades, tecnologías, estudios ni años.
- Evaluá la coincidencia directa con el puesto o criterio solicitado.
- No conviertas habilidades generales en experiencia específica.
- No consideres marketing, ventas, administración o gestión como relevantes salvo que la consulta pida explícitamente esos perfiles.
- Si ningún candidato cumple claramente, indicá que ninguno presenta evidencia suficiente.
- El score debe reflejar el ajuste real al criterio consultado.
- Respondé breve.

CRITERIO DE SCORE:
0-20: sin evidencia relevante.
21-40: baja coincidencia.
41-60: coincidencia parcial.
61-80: buena coincidencia.
81-100: alta coincidencia.

FORMATO EXACTO:

RANKING:
1. [Nombre] — XX/100
Motivo: [motivo breve basado en evidencia]
Gaps: [faltantes principales]

2. [Nombre] — XX/100
Motivo: [motivo breve basado en evidencia]
Gaps: [faltantes principales]

CONCLUSIÓN FINAL:
[máximo 2 líneas]

CANDIDATOS:
{cvs_text}
"""

        return self.generate_response(
            prompt=prompt,
            timeout=90,
            num_predict=600,
            temperature=0.03,
            top_p=0.7,
        )

    def match_job_description(self, cvs_data, job_description):
        if not cvs_data:
            return "No hay perfiles para analizar."

        if len(cvs_data) < 2:
            return "Se requieren al menos 2 perfiles."

        cvs_text = ""

        for cv_data in cvs_data:
            candidate_name = cv_data.get("name", "Sin nombre")
            candidate_text = cv_data.get("text", "")[:2500]

            cvs_text += f"""
CANDIDATO: {candidate_name}
{candidate_text}

"""

        prompt = f"""
Compará los candidatos contra la siguiente descripción de puesto.

DESCRIPCIÓN DEL PUESTO:
{job_description}

REGLAS:
- Usá solo evidencia explícita de los CVs.
- No inventes experiencia, habilidades, tecnologías, estudios, certificaciones, idiomas ni años.
- Calculá un Matching Score de 0 a 100 para cada candidato.
- El score debe reflejar coincidencia directa con la descripción del puesto.
- No conviertas habilidades generales en experiencia específica.
- Separá fortalezas, gaps y evidencia concreta.
- Si ningún candidato encaja claramente, indicá que ninguno presenta evidencia suficiente.
- Respondé en español profesional y claro.
- El TOP CANDIDATO RECOMENDADO debe ser el candidato con mayor Match Score.
- Si ningún candidato supera 40/100, indicar: "Ningún candidato recomendado".

CRITERIO DE MATCHING:
0-20: sin evidencia relevante para el puesto.
21-40: baja coincidencia.
41-60: coincidencia parcial.
61-80: buena coincidencia.
81-100: alta coincidencia.

FORMATO EXACTO:

🏆 TOP CANDIDATO RECOMENDADO:
[Nombre] — Match: XX/100
Motivo: [por qué queda primero, basado en evidencia explícita]

MATCHING CONTRA PUESTO:

1. [Nombre] — Match: XX/100
Fortalezas:
- [fortaleza alineada al puesto]
Gaps:
- [faltante contra el puesto]
Evidencia:
- [dato concreto del CV]

2. [Nombre] — Match: XX/100
Fortalezas:
- [fortaleza alineada al puesto]
Gaps:
- [faltante contra el puesto]
Evidencia:
- [dato concreto del CV]

CONCLUSIÓN FINAL:
[máximo 3 líneas]

CANDIDATOS:
{cvs_text}
"""

        return self.generate_response(
            prompt=prompt,
            timeout=90,
            num_predict=800,
            temperature=0.03,
            top_p=0.7,
        )

    def generate_interview_questions(self, cv_text):
        cv_text = cv_text[:4000]

        prompt = f"""
Generá preguntas de entrevista para este candidato.

REGLAS:
- Usá SOLO información explícita del CV.
- No inventes tecnologías, experiencia ni proyectos.
- Generá preguntas útiles para validar experiencia real.
- Incluí preguntas técnicas y de experiencia.
- Si faltan datos importantes, generá preguntas para validar esos gaps.
- Respondé breve y profesional.

CV:
{cv_text}

FORMATO EXACTO:

PREGUNTAS TÉCNICAS:
1. [pregunta]
2. [pregunta]
3. [pregunta]

PREGUNTAS SOBRE EXPERIENCIA:
1. [pregunta]
2. [pregunta]

PREGUNTAS PARA VALIDAR GAPS:
1. [pregunta]
2. [pregunta]
"""

        return self.generate_response(
            prompt=prompt,
            timeout=60,
            num_predict=500,
            temperature=0.05,
            top_p=0.7,
        )

    def extract_structured_profile(self, cv_text):
        cv_text = cv_text[:5000]

        prompt = f"""
Extraé datos estructurados del siguiente CV.

REGLAS:
- Usá SOLO información explícita.
- No inventes datos.
- Si un dato no aparece, usá lista vacía [] o "No informado".
- Clasificá instituciones argentinas usando el catálogo provisto.
- Si aparece una sigla o nombre del catálogo, guardá EXACTAMENTE el nombre completo del catálogo en institutions.
- Si aparece una institución fuera del catálogo, guardala solo si está explícita.
- No mezcles carrera/título con institución: carrera va en education, universidad/instituto va en institutions.
- Separá skills, roles, formación, instituciones e idiomas en elementos individuales.
- Evitá duplicados y variantes del mismo dato.
- Respondé únicamente JSON válido.
- No agregues markdown.
- No agregues explicación.

CV:
{cv_text}

CATÁLOGO DE UNIVERSIDADES ARGENTINAS:
{UNIVERSITY_CATALOG_PROMPT}

JSON esperado:
{{
  "skills": [],
  "education": ["títulos, carreras, cursos o certificaciones explícitas"],
  "institutions": ["universidades, institutos, academias o plataformas educativas explícitas"],
  "experience": [],
  "roles": [],
  "languages": [],
  "seniority": "No informado",
  "areas": []
}}
"""

        response = self.generate_response(
            prompt=prompt,
            timeout=60,
            num_predict=700,
            temperature=0.01,
            top_p=0.5,
        )

        try:
            cleaned = response.strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1

            if start == -1 or end == 0:
                raise ValueError("No se encontró JSON válido en la respuesta.")

            clean_json = cleaned[start:end]
            return normalize_structured_profile(json.loads(clean_json))

        except Exception as e:
            logger.error(f"Error parseando structured profile: {e}")

            return normalize_structured_profile({})

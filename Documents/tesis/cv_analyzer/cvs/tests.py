from django.test import SimpleTestCase

from .services import build_institution_record, normalize_structured_profile, normalize_text
from .views import get_institution_filter_target, get_institution_search_variants, get_search_variants


class StructuredProfileNormalizationTests(SimpleTestCase):
    def test_normalize_text_removes_accents_and_symbols(self):
        self.assertEqual(
            normalize_text("Universidad Tecnológica Nacional"),
            "universidad tecnologica nacional",
        )

    def test_normalize_structured_profile_deduplicates_and_canonicalizes_institutions(self):
        profile = normalize_structured_profile({
            "skills": ["Python", "python", " SQL "],
            "education": ["Licenciatura en Sistemas"],
            "institutions": ["UBA", "Universidad de Buenos Aires", "UTN"],
            "roles": ["Developer"],
            "languages": ["Español"],
            "seniority": "Semi Senior",
        })

        self.assertEqual(profile["skills"], ["Python", "SQL"])
        self.assertEqual(
            profile["institutions"],
            ["Universidad de Buenos Aires", "Universidad Tecnológica Nacional"],
        )
        self.assertIn("UBA", profile["institution_search_terms"])
        self.assertIn("utn", profile["institution_search_terms"])

    def test_build_institution_record_adds_aliases_and_search_terms(self):
        record = build_institution_record("UBA")

        self.assertEqual(record["name"], "Universidad de Buenos Aires")
        self.assertIn("UBA", record["aliases"])
        self.assertNotIn("buenos", record["search_terms"])

    def test_search_variants_expand_known_institution_aliases(self):
        variants = get_search_variants("UBA")

        self.assertIn("Universidad de Buenos Aires", variants)

    def test_institution_search_does_not_add_weak_tokens(self):
        variants = get_institution_search_variants("UNSAM")

        self.assertIn("Universidad Nacional de San Martín", variants)
        self.assertIn("UNSAM", variants)
        self.assertNotIn("san", variants)
        self.assertNotIn("martin", variants)

    def test_short_acronyms_resolve_to_their_own_university(self):
        ub_acronym, ub_name, _ = get_institution_filter_target("UB")
        uba_acronym, uba_name, _ = get_institution_filter_target("UBA")

        self.assertEqual(ub_acronym, "UB")
        self.assertEqual(ub_name, "Universidad de Belgrano")
        self.assertEqual(uba_acronym, "UBA")
        self.assertEqual(uba_name, "Universidad de Buenos Aires")

    def test_common_missing_connector_still_canonicalizes(self):
        record = build_institution_record("Universidad Belgrano")

        self.assertEqual(record["name"], "Universidad de Belgrano")

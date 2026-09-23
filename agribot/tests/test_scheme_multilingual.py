import unittest

from services.scheme_intent import detect_language, extract_farmer_profile, is_scheme_query
from services.scheme_service import find_schemes, load_schemes
from services.scheme_validator import validate_scheme


class SchemeMultilingualTests(unittest.TestCase):
    def test_dataset_loads_and_has_official_sources(self):
        schemes = load_schemes()
        self.assertGreaterEqual(len(schemes), 20)
        self.assertTrue(all(item["official_source_url"].startswith("https://") for item in schemes))

    def test_all_supported_languages_route_to_same_finder(self):
        queries = {
            "English": "I am a Telangana farmer growing paddy. What government schemes are available?",
            "Telugu": "నేను తెలంగాణ రైతును. వరి పండిస్తున్నాను. నాకు ఏ ప్రభుత్వ పథకాలు ఉన్నాయి?",
            "Hindi": "मैं तेलंगाना का किसान हूँ और धान की खेती करता हूँ। मेरे लिए कौन सी सरकारी योजनाएं हैं?",
            "Tamil": "நான் தெலங்கானா விவசாயி. நெல் பயிரிடுகிறேன். எனக்கு என்ன அரசு திட்டங்கள் உள்ளன?",
            "Kannada": "ನಾನು ತೆಲಂಗಾಣದ ರೈತ. ಭತ್ತ ಬೆಳೆಯುತ್ತಿದ್ದೇನೆ. ನನಗೆ ಯಾವ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಇವೆ?",
            "Malayalam": "ഞാൻ തെലങ്കാനയിലെ കർഷകനാണ്. നെല്ല് കൃഷി ചെയ്യുന്നു. എനിക്ക് എന്തെല്ലാം സർക്കാർ പദ്ധതികൾ ലഭ്യമാണ്?",
        }
        for language, query in queries.items():
            self.assertTrue(is_scheme_query(query), language)
            self.assertEqual(detect_language(query), language)
            result = find_schemes(query, language)
            self.assertEqual(result["language"], language)
            self.assertTrue(result["schemes"], language)
            self.assertIn("Telangana", result["farmer_profile"].get("state", ""), language)
            self.assertEqual(result["farmer_profile"].get("crop"), "Paddy", language)

    def test_profile_extracts_land_size_without_inventing_other_details(self):
        profile = extract_farmer_profile("నేను తెలంగాణలో 2 ఎకరాల్లో వరి పండిస్తున్నాను.")
        self.assertEqual(profile["state"], "Telangana")
        self.assertEqual(profile["crop"], "Paddy")
        self.assertEqual(profile["land_size"], 2.0)
        self.assertNotIn("gender", profile)
        self.assertNotIn("district", profile)

    def test_search_terms_and_no_match(self):
        self.assertTrue(find_schemes("PM-KISAN subsidy", "English")["schemes"])
        self.assertTrue(find_schemes("వరి సబ్సిడీ", "Telugu")["schemes"])
        self.assertFalse(find_schemes("government schemes for polar research", "English")["schemes"])
        insurance = find_schemes("What farmer schemes can help with crop insurance?", "Telugu")["schemes"]
        self.assertEqual(insurance[0]["scheme_name"], "Pradhan Mantri Fasal Bima Yojana")
        self.assertTrue(all("insurance" in " ".join(item["keywords"]).casefold() or "insurance" in item["description"].casefold() for item in insurance))
        self.assertFalse(is_scheme_query("How should I grow paddy in Telangana?"))

    def test_invalid_record_is_rejected(self):
        record = {"scheme_name": "Missing source"}
        self.assertTrue(validate_scheme(record))


if __name__ == "__main__":
    unittest.main()

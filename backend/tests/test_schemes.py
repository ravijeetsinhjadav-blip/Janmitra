import uuid
from datetime import date, datetime, timezone
import pytest
from app.services.eligibility_service import EligibilityEngine
from app.schemas.scheme import EligibilityCondition


def get_auth_headers(client, mobile_number: str) -> dict:
    """Helper to authenticate a citizen via mock OTP."""
    res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": mobile_number})
    otp = res_otp.json()["dev_otp"]
    res_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": mobile_number, "otp": otp},
    )
    token = res_verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestBirthdayBoundaryAndAgeCalculation:
    """Unit tests for exact birthday boundary age calculation, leap years, and cutoff dates."""

    def test_exact_birthday_boundary(self):
        ref_today = date(2026, 10, 31)

        # 1. Birthday is today: exactly 18
        age_today = EligibilityEngine.calculate_age("2008-10-31", reference_date=ref_today)
        assert age_today == 18

        # 2. Birthday is tomorrow (Nov 1): still 17
        age_tomorrow = EligibilityEngine.calculate_age("2008-11-01", reference_date=ref_today)
        assert age_tomorrow == 17

        # 3. Birthday was yesterday (Oct 30): 18
        age_yesterday = EligibilityEngine.calculate_age("2008-10-30", reference_date=ref_today)
        assert age_yesterday == 18

    def test_leap_year_feb_29_statutory_anniversary_convention(self):
        """Under statutory/common law convention, 365 full days elapse on March 1 in common years."""
        dob_leap = "2004-02-29"

        # On Feb 28, 2025 (common year): 20
        age_feb28 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2025, 2, 28), feb29_convention="statutory_anniversary"
        )
        assert age_feb28 == 20

        # On Mar 1, 2025 (common year): 21
        age_mar01 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2025, 3, 1), feb29_convention="statutory_anniversary"
        )
        assert age_mar01 == 21

    def test_leap_year_feb_29_end_of_february_convention(self):
        """Under administrative convention, anniversary is deemed on the final day of February (Feb 28)."""
        dob_leap = "2004-02-29"

        # On Feb 27, 2025 (common year): 20
        age_feb27 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2025, 2, 27), feb29_convention="end_of_february"
        )
        assert age_feb27 == 20

        # On Feb 28, 2025 (common year): 21
        age_feb28 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2025, 2, 28), feb29_convention="end_of_february"
        )
        assert age_feb28 == 21

        # In leap year 2024: both conventions align on Feb 29
        age_leap_feb28 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2024, 2, 28), feb29_convention="end_of_february"
        )
        assert age_leap_feb28 == 19
        age_leap_feb29 = EligibilityEngine.calculate_age(
            dob_leap, reference_date=date(2024, 2, 29), feb29_convention="end_of_february"
        )
        assert age_leap_feb29 == 20

    def test_scheme_specific_official_cutoff_dates(self):
        """Schemes often specify fixed official cutoff dates (e.g. Jan 1 or July 1 of recruitment year)."""
        dob = "2006-05-15"

        # As of Jan 1, 2024: 17 years old
        age_jan1 = EligibilityEngine.calculate_age(dob, reference_date=date(2024, 1, 1))
        assert age_jan1 == 17

        # As of July 1, 2024: 18 years old
        age_jul1 = EligibilityEngine.calculate_age(dob, reference_date=date(2024, 7, 1))
        assert age_jul1 == 18

    def test_invalid_and_future_dates(self):
        ref_today = date(2026, 10, 31)
        # Future date
        assert EligibilityEngine.calculate_age("2030-01-01", reference_date=ref_today) is None
        # Invalid format / strings
        assert EligibilityEngine.calculate_age("not-a-date", reference_date=ref_today) is None
        assert EligibilityEngine.calculate_age(None, reference_date=ref_today) is None
        assert EligibilityEngine.calculate_age("", reference_date=ref_today) is None


class TestEligibilityEngineOperatorsAndSafety:
    """Unit tests for operator evaluations, type validation, and injection prevention."""

    def test_all_comparison_operators(self):
        # 1. eq
        cond_eq = EligibilityCondition(condition_name="State", field="state", operator="eq", expected_value="Maharashtra", explanation="State match")
        assert EligibilityEngine.evaluate_condition(cond_eq, {"state": "Maharashtra"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_eq, {"state": "Gujarat"}).status == "not_satisfied"

        # 2. neq
        cond_neq = EligibilityCondition(condition_name="Not Urban", field="residence_type", operator="neq", expected_value="urban", explanation="Non-urban")
        assert EligibilityEngine.evaluate_condition(cond_neq, {"residence_type": "rural"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_neq, {"residence_type": "urban"}).status == "not_satisfied"

        # 3. gte & lte
        cond_gte = EligibilityCondition(condition_name="Min Age", field="age", operator="gte", expected_value=18, explanation="Adult")
        assert EligibilityEngine.evaluate_condition(cond_gte, {"age": 25}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_gte, {"age": 18}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_gte, {"age": 17}).status == "not_satisfied"

        cond_lte = EligibilityCondition(condition_name="Max Income", field="annual_family_income", operator="lte", expected_value=250000, explanation="Income ceiling")
        assert EligibilityEngine.evaluate_condition(cond_lte, {"annual_family_income": 200000}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_lte, {"annual_family_income": 250000}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_lte, {"annual_family_income": 300000}).status == "not_satisfied"

        # 4. gt & lt
        cond_gt = EligibilityCondition(condition_name="Income Above Zero", field="annual_family_income", operator="gt", expected_value=0, explanation="Income > 0")
        assert EligibilityEngine.evaluate_condition(cond_gt, {"annual_family_income": 100}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_gt, {"annual_family_income": 0}).status == "not_satisfied"

        cond_lt = EligibilityCondition(condition_name="Income Below", field="annual_family_income", operator="lt", expected_value=100000, explanation="Income < 100k")
        assert EligibilityEngine.evaluate_condition(cond_lt, {"annual_family_income": 80000}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_lt, {"annual_family_income": 100000}).status == "not_satisfied"

        # 5. in
        cond_in = EligibilityCondition(condition_name="Category", field="category", operator="in", expected_value=["SC", "ST", "OBC"], explanation="Reserved category")
        assert EligibilityEngine.evaluate_condition(cond_in, {"category": "SC"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_in, {"category": "ST"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_in, {"category": "General"}).status == "not_satisfied"

        # 6. contains
        cond_cont = EligibilityCondition(condition_name="Occupation", field="occupation", operator="contains", expected_value="farmer", explanation="Farming occupation")
        assert EligibilityEngine.evaluate_condition(cond_cont, {"occupation": "Farmer"}).status == "satisfied"
        # Controlled fields use normalized exact matching: ambiguous partial substrings do not match
        assert EligibilityEngine.evaluate_condition(cond_cont, {"occupation": "Small farmer"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_cont, {"occupation": "Software Engineer"}).status == "not_satisfied"

    def test_contains_edge_cases_and_empty_string_safety(self):
        """Empty expected string must never match in contains operator."""
        cond_empty = EligibilityCondition(condition_name="Occupation", field="occupation", operator="contains", expected_value="", explanation="Empty")
        result = EligibilityEngine.evaluate_condition(cond_empty, {"occupation": "Farmer"})
        assert result.status == "not_satisfied"

        cond_whitespace = EligibilityCondition(condition_name="Occupation", field="occupation", operator="contains", expected_value="   ", explanation="Spaces")
        result_ws = EligibilityEngine.evaluate_condition(cond_whitespace, {"occupation": "Farmer"})
        assert result_ws.status == "not_satisfied"

    def test_contains_operator_controlled_fields_prevent_substring_false_positives(self):
        """Ambiguous substring matching must be prevented for controlled fields (residence_type, state, category, occupation)."""
        # 1. 'ur' in 'rural' or 'urban'
        cond_ur = EligibilityCondition(condition_name="Res", field="residence_type", operator="contains", expected_value="ur", explanation="Check")
        assert EligibilityEngine.evaluate_condition(cond_ur, {"residence_type": "rural"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_ur, {"residence_type": "urban"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_ur, {"residence_type": "ur"}).status == "satisfied"

        # 2. 'art' in 'Cart driver' or 'Farmer'
        cond_art = EligibilityCondition(condition_name="Occ", field="occupation", operator="contains", expected_value="art", explanation="Art")
        assert EligibilityEngine.evaluate_condition(cond_art, {"occupation": "Cart driver"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_art, {"occupation": "Farmer"}).status == "not_satisfied"

        # 3. 'SC' in 'MISC'
        cond_sc = EligibilityCondition(condition_name="Cat", field="category", operator="contains", expected_value="SC", explanation="Cat")
        assert EligibilityEngine.evaluate_condition(cond_sc, {"category": "MISC"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_sc, {"category": "SC"}).status == "satisfied"

        # 4. 'Goa' in 'Goan'
        cond_goa = EligibilityCondition(condition_name="State", field="state", operator="contains", expected_value="Goa", explanation="State")
        assert EligibilityEngine.evaluate_condition(cond_goa, {"state": "Goan"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_goa, {"state": "Goa"}).status == "satisfied"

    def test_contains_operator_retains_justified_substring_matching_on_freeform_fields(self):
        """Free-form descriptive text fields retain justified substring matching."""
        cond_free = EligibilityCondition(condition_name="Disability", field="disability_description", operator="contains", expected_value="locomotor", explanation="Check")
        assert EligibilityEngine.evaluate_condition(cond_free, {"disability_description": "Severe locomotor impairment"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_free, {"disability_description": "Visual impairment"}).status == "not_satisfied"

    def test_in_operator_rejects_plain_string_and_prevents_substring_false_positives(self):
        """The 'in' operator must accept only collections (list, tuple, set) and reject strings to prevent false positives."""
        # 1. Plain string rejected as expected collection
        cond_str_exp = {"condition_name": "Category In", "field": "category", "operator": "in", "expected_value": "SC, ST", "explanation": "Bad string"}
        res_str = EligibilityEngine.evaluate_condition(cond_str_exp, {"category": "SC"})
        assert res_str.status == "unknown"
        assert "Invalid scheme rule configuration" in res_str.explanation

        # 2. Non-collection type (int, dict) rejected
        cond_int_exp = {"condition_name": "Int In", "field": "category", "operator": "in", "expected_value": 12345, "explanation": "Bad int"}
        res_int = EligibilityEngine.evaluate_condition(cond_int_exp, {"category": "SC"})
        assert res_int.status == "unknown"
        assert "Invalid scheme rule configuration" in res_int.explanation

        # 3. Valid collection prevents substring false positive ('SC' is in 'MISC', but collection requires exact item)
        cond_valid_in = EligibilityCondition(condition_name="Category Valid", field="category", operator="in", expected_value=["SC", "ST"], explanation="Valid")
        assert EligibilityEngine.evaluate_condition(cond_valid_in, {"category": "MISC"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_valid_in, {"category": "SC"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_valid_in, {"category": "General"}).status == "not_satisfied"

        # 4. State substring: 'Maha' does not match 'Maharashtra'
        cond_state_in = EligibilityCondition(condition_name="State Valid", field="state", operator="in", expected_value=["Maharashtra", "Gujarat"], explanation="Valid states")
        assert EligibilityEngine.evaluate_condition(cond_state_in, {"state": "Maha"}).status == "not_satisfied"
        assert EligibilityEngine.evaluate_condition(cond_state_in, {"state": "Maharashtra"}).status == "satisfied"

    def test_invalid_actual_values_for_numeric_operators(self):
        """Invalid actual citizen profile values (non-numeric string, NaN, Inf) must return unknown, never not_satisfied."""
        cond_num = EligibilityCondition(
            condition_name="Income Limit",
            field="annual_family_income",
            operator="lte",
            expected_value=200000,
            explanation="Income limit",
        )

        # 1. Non-numeric string in profile
        res_str = EligibilityEngine.evaluate_condition(cond_num, {"annual_family_income": "invalid_number_abc"})
        assert res_str.status == "unknown"
        assert "Cannot evaluate condition" in res_str.explanation

        # 2. NaN in profile
        res_nan = EligibilityEngine.evaluate_condition(cond_num, {"annual_family_income": float("nan")})
        assert res_nan.status == "unknown"
        assert "Cannot evaluate condition" in res_nan.explanation

        # 3. Infinity in profile
        res_inf = EligibilityEngine.evaluate_condition(cond_num, {"annual_family_income": float("inf")})
        assert res_inf.status == "unknown"
        assert "Cannot evaluate condition" in res_inf.explanation

    def test_invalid_expected_values_for_numeric_operators(self):
        """Invalid scheme rule expected values (None, non-numeric, NaN, Inf) must return unknown rule error, never not_satisfied."""
        # 1. Null expected value
        cond_null = {"condition_name": "Test Null", "field": "age", "operator": "gte", "expected_value": None, "explanation": "Null rule"}
        res_null = EligibilityEngine.evaluate_condition(cond_null, {"age": 25})
        assert res_null.status == "unknown"
        assert "Invalid scheme rule configuration" in res_null.explanation

        # 2. Non-numeric string expected value for numeric op
        cond_str = {"condition_name": "Test Str", "field": "age", "operator": "gte", "expected_value": "not_a_number", "explanation": "Bad rule"}
        res_str = EligibilityEngine.evaluate_condition(cond_str, {"age": 25})
        assert res_str.status == "unknown"
        assert "Invalid scheme rule configuration" in res_str.explanation

        # 3. NaN expected value
        cond_nan = {"condition_name": "Test NaN", "field": "age", "operator": "gte", "expected_value": float("nan"), "explanation": "NaN rule"}
        res_nan = EligibilityEngine.evaluate_condition(cond_nan, {"age": 25})
        assert res_nan.status == "unknown"
        assert "Invalid scheme rule configuration" in res_nan.explanation

        # 4. Infinity expected value
        cond_inf = {"condition_name": "Test Inf", "field": "age", "operator": "gte", "expected_value": float("inf"), "explanation": "Inf rule"}
        res_inf = EligibilityEngine.evaluate_condition(cond_inf, {"age": 25})
        assert res_inf.status == "unknown"
        assert "Invalid scheme rule configuration" in res_inf.explanation

    def test_unsupported_operator(self):
        """Unsupported operator returns unknown status."""
        cond_bad_op = {"condition_name": "Test", "field": "age", "operator": "regex", "expected_value": "^18$", "explanation": "Regex"}
        res_op = EligibilityEngine.evaluate_condition(cond_bad_op, {"age": 18})
        assert res_op.status == "unknown"
        assert "Unsupported operator" in res_op.explanation

    def test_missing_profile_field_classified_as_unknown(self):
        """A missing profile field must be classified as unknown, not automatically failed."""
        cond = EligibilityCondition(condition_name="Income", field="annual_family_income", operator="lte", expected_value=200000, explanation="Income limit")
        result = EligibilityEngine.evaluate_condition(cond, {})
        assert result.status == "unknown"
        assert result.actual_value is None
        assert "cannot be verified" in result.explanation


class TestCriteriaMatchScoreInterpretation:
    """Test Criteria Match Percentage calculation and mixed condition outcomes."""

    def test_mixed_satisfied_failed_unknown_conditions(self):
        from app.models.scheme import Scheme
        from app.models.profile import UserProfile

        # Scheme with 3 conditions: Age >= 18, Residence == rural, Income <= 200,000
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Test Mixed Scheme",
            description="Testing mixed evaluation",
            department="Test Ministry",
            state_applicability="All India",
            eligibility_summary="Test summary",
            official_source_url="https://test.gov.in",
            official_application_url="https://test.gov.in/apply",
            eligibility_criteria=[
                {"condition_name": "Min Age", "field": "age", "operator": "gte", "expected_value": 18, "explanation": "Age 18+"},
                {"condition_name": "Rural Area", "field": "residence_type", "operator": "eq", "expected_value": "rural", "explanation": "Rural area"},
                {"condition_name": "Income Limit", "field": "annual_family_income", "operator": "lte", "expected_value": 200000, "explanation": "Income limit"},
            ],
            status="active",
            is_active=True,
            is_demo_data=True,
        )

        # Profile: Age=25 (satisfied), Residence=urban (FAILED), Income=None (UNKNOWN)
        profile = UserProfile(
            user_id=uuid.uuid4(),
            full_name="Mixed Citizen",
            date_of_birth=date(2000, 1, 1),
            state="Maharashtra",
            district="Pune",
            residence_type="urban",  # Fails rural condition
            annual_family_income=None,  # Missing -> unknown
        )

        result = EligibilityEngine.evaluate_scheme(scheme, profile)
        assert result["satisfied_count"] == 1
        assert result["not_satisfied_count"] == 1
        assert result["unknown_count"] == 1
        # Failed condition forces overall status to Not Eligible Based on Available Information
        assert result["overall_status"] == "Not Eligible Based on Available Information"
        # Match percentage: 1 / 3 = 33.3%
        assert result["criteria_match_percentage"] == 33.3
        # Ensure score interpretation explicitly denies government approval guarantee
        assert "NOT represent an official approval likelihood" in result["score_interpretation"]


class TestSchemeDiscoveryEndpoints:
    """Test API endpoints for scheme discovery, filtering, search, and details."""

    def test_list_schemes_and_pagination(self, client):
        res = client.get("/api/v1/schemes?page=1&page_size=2")
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 5

        # Verify demo flag and advisory nature
        first_item = data["items"][0]
        assert first_item["is_demo_data"] is True
        assert first_item["status"] == "active"
        assert "advisory_notice" in first_item

    def test_search_schemes_by_keyword(self, client):
        res = client.get("/api/v1/schemes?q=kisan")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        names = [s["scheme_name"] for s in data["items"]]
        assert any("Kisan" in n for n in names)

        # Search for non-matching term
        res_empty = client.get("/api/v1/schemes?q=nonexistentkeywordxyz")
        assert res_empty.status_code == 200
        data_empty = res_empty.json()
        assert data_empty["total"] == 0

    def test_filter_by_category_and_state(self, client):
        res = client.get("/api/v1/schemes?category=Healthcare")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for s in data["items"]:
            assert s["category"] == "Healthcare"

    def test_get_categories_aggregation(self, client):
        res = client.get("/api/v1/schemes/categories")
        assert res.status_code == 200
        data = res.json()
        categories = {item["category"]: item["count"] for item in data}
        assert "Agriculture" in categories
        assert "Healthcare" in categories

    def test_get_scheme_by_id_and_source_verification(self, client):
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"
        res = client.get(f"/api/v1/schemes/{pm_kisan_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == pm_kisan_id
        assert "PM-KISAN" in data["scheme_name"]
        assert data["official_source_url"] == "https://pmkisan.gov.in/"
        assert data["official_application_url"].startswith("https://pmkisan.gov.in/")
        assert data["is_demo_data"] is True
        assert data["source_last_verified_at"] is not None
        assert "pmkisan.gov.in" in data["source_verification_details"]


class TestSchemeAssessmentAndRecommendations:
    """Test authenticated assessment, recommendations, and history isolation."""

    def test_recommendations_exclude_failed_mandatory_conditions(self, client):
        headers = get_auth_headers(client, "9222233333")

        # Set up citizen profile as a software engineer living in an urban area with high income
        # Fails PM-KISAN (not farmer), PMAY-G (urban), NSP (not student)
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Dev High Income",
                "date_of_birth": "1990-01-01",
                "state": "Gujarat",
                "district": "Ahmedabad",
                "residence_type": "urban",
                "annual_family_income": 900000.0,
                "occupation": "Software Engineer",
            },
            headers=headers,
        )

        res = client.get("/api/v1/schemes/recommendations", headers=headers)
        assert res.status_code == 200
        data = res.json()
        # Verify that failed schemes (PM-KISAN, PMAY-G, NSP) are NOT recommended
        recommended_names = [r["scheme"]["scheme_name"] for r in data]
        for name in recommended_names:
            assert "PM-KISAN" not in name
            assert "PMAY-G" not in name

    def test_run_assessment_criteria_match_percentage(self, client):
        headers = get_auth_headers(client, "9333344444")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Kisan Lal",
                "date_of_birth": "1980-01-01",
                "state": "Uttar Pradesh",
                "district": "Varanasi",
                "residence_type": "rural",
                "occupation": "Farmer",
            },
            headers=headers,
        )

        res = client.post(f"/api/v1/schemes/{pm_kisan_id}/assess", headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["scheme_id"] == pm_kisan_id
        assert data["overall_status"] == "Potentially Eligible"
        assert data["criteria_match_percentage"] == 100.0
        assert data["overall_readiness_score"] == 100.0
        assert "NOT represent an official approval likelihood" in data["score_interpretation"]
        assert data["satisfied_count"] >= 2
        assert data["not_satisfied_count"] == 0
        assert data["unknown_count"] == 0

    def test_run_assessment_missing_fields_yields_insufficient_info(self, client):
        headers = get_auth_headers(client, "9444455555")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        res = client.post(f"/api/v1/schemes/{pm_kisan_id}/assess", headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["overall_status"] == "Insufficient Information"
        assert data["unknown_count"] > 0
        assert "occupation" in data["missing_fields"]
        assert data["criteria_match_percentage"] == 0.0

    def test_assessment_history_and_citizen_isolation(self, client):
        headers_a = get_auth_headers(client, "9666677777")
        headers_b = get_auth_headers(client, "9777788888")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        # Citizen A runs assessment
        res_a = client.post(f"/api/v1/schemes/{pm_kisan_id}/assess", headers=headers_a)
        assert res_a.status_code == 201
        assessment_a_id = res_a.json()["assessment_id"]

        # Citizen A checks their history
        res_hist_a = client.get("/api/v1/schemes/assessments/history", headers=headers_a)
        assert res_hist_a.status_code == 200
        history_a = res_hist_a.json()
        assert len(history_a) >= 1
        assert any(item["assessment_id"] == assessment_a_id for item in history_a)
        assert "criteria_match_percentage" in history_a[0]

        # Citizen B checks history -> should be 0, cannot see Citizen A's record
        res_hist_b = client.get("/api/v1/schemes/assessments/history", headers=headers_b)
        assert res_hist_b.status_code == 200
        history_b = res_hist_b.json()
        assert not any(item["assessment_id"] == assessment_a_id for item in history_b)

        # Citizen B attempts to access Citizen A's assessment detail -> must be 404
        res_cross = client.get(f"/api/v1/schemes/assessments/{assessment_a_id}", headers=headers_b)
        assert res_cross.status_code == 404


class TestSchemeSourceMetadataVerification:
    """Verify official sources, application URLs, references, freshness, and demo markers."""

    def test_seeded_schemes_source_metadata_completeness(self):
        from app.services.scheme_service import DEMO_SCHEMES_SEED

        assert len(DEMO_SCHEMES_SEED) == 5

        for s in DEMO_SCHEMES_SEED:
            # 1. Marked as DEMO data
            assert s["is_demo_data"] is True
            assert "[DEMO]" in s["scheme_name"]

            # 2. Official URLs present and valid
            assert s["official_source_url"].startswith("https://")
            assert s["official_application_url"].startswith("https://")

            # 3. Source references present and non-empty
            assert s["eligibility_source_reference"] is not None
            assert len(s["eligibility_source_reference"].strip()) > 10

            assert s["benefits_source_reference"] is not None
            assert len(s["benefits_source_reference"].strip()) > 10

            # 4. Freshness and verification details
            assert s["source_freshness_status"] == "Verified Official Source (Demo Seed)"
            assert isinstance(s["source_last_verified_at"], datetime)
            assert "DEMO / TEST DATA" in s["source_verification_details"]

    def test_scheme_detail_api_exposes_source_verification_metadata(self, client):
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"
        res = client.get(f"/api/v1/schemes/{pm_kisan_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["id"] == pm_kisan_id
        assert data["is_demo_data"] is True
        assert data["official_source_url"] == "https://pmkisan.gov.in/"
        assert data["official_application_url"] == "https://pmkisan.gov.in/RegistrationFormNew.aspx"
        assert data["source_freshness_status"] == "Verified Official Source (Demo Seed)"
        assert "PM-KISAN Operational Guidelines" in data["eligibility_source_reference"]
        assert "PM-KISAN Operational Guidelines" in data["benefits_source_reference"]
        assert "DEMO / TEST DATA" in data["source_verification_details"]
        assert data["source_last_verified_at"] is not None
        assert "JanMitra Assist is an advisory preparation platform" in data["advisory_notice"]

    def test_new_scheme_defaults_to_pending_verification_without_invented_timestamp(self):
        """Newly created schemes must default to 'Pending Verification' with null verified timestamp."""
        from app.models.scheme import Scheme

        new_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Unverified State Welfare Scheme",
            description="Newly drafted scheme pending verification",
            department="State Department",
            eligibility_summary="Pending guidelines check",
            official_source_url="https://state.gov.in/scheme",
            official_application_url="https://state.gov.in/apply",
        )
        assert new_scheme.source_freshness_status == "Pending Verification"
        assert new_scheme.source_last_verified_at is None

    def test_stale_and_review_required_freshness_states(self):
        """Scheme sources can be marked as 'Review Required' or 'Stale' when guidelines change."""
        from app.models.scheme import Scheme

        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Existing Scheme",
            description="Scheme requiring verification review",
            department="Department",
            eligibility_summary="Summary",
            official_source_url="https://gov.in",
            official_application_url="https://gov.in/apply",
            source_freshness_status="Review Required",
        )
        assert scheme.source_freshness_status == "Review Required"

        scheme.source_freshness_status = "Stale"
        assert scheme.source_freshness_status == "Stale"

    def test_age_calculation_no_unsupported_general_clauses_act_claim(self):
        """Docstring and comments must not claim General Clauses Act Section 9 mandates leap-year birthdays."""
        doc_normalized = " ".join((EligibilityEngine.calculate_age.__doc__ or "").split())
        assert "Section 9 of the General Clauses Act, 1897 governs commencement and termination of time periods" in doc_normalized
        assert "does not establish a direct legal rule for leap-year birthdays" in doc_normalized
        assert "Scheme-specific official age cutoff rules must always take priority" in doc_normalized

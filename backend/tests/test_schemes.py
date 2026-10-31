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
    """Unit tests for exact birthday boundary age calculation."""

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

    def test_leap_year_feb_29_boundary(self):
        # Born on Feb 29, 2004 (leap year)
        # Evaluated in non-leap year 2025
        dob_leap = "2004-02-29"

        # On Feb 28, 2025 (day before anniversary month): 20
        age_feb28 = EligibilityEngine.calculate_age(dob_leap, reference_date=date(2025, 2, 28))
        assert age_feb28 == 20

        # On Mar 1, 2025 (anniversary month arrived): 21
        age_mar01 = EligibilityEngine.calculate_age(dob_leap, reference_date=date(2025, 3, 1))
        assert age_mar01 == 21

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
        assert EligibilityEngine.evaluate_condition(cond_cont, {"occupation": "Small farmer"}).status == "satisfied"
        assert EligibilityEngine.evaluate_condition(cond_cont, {"occupation": "Software Engineer"}).status == "not_satisfied"

    def test_contains_edge_cases_and_empty_string_safety(self):
        """Empty expected string must never match in contains operator."""
        cond_empty = EligibilityCondition(condition_name="Occupation", field="occupation", operator="contains", expected_value="", explanation="Empty")
        result = EligibilityEngine.evaluate_condition(cond_empty, {"occupation": "Farmer"})
        assert result.status == "not_satisfied"

        cond_whitespace = EligibilityCondition(condition_name="Occupation", field="occupation", operator="contains", expected_value="   ", explanation="Spaces")
        result_ws = EligibilityEngine.evaluate_condition(cond_whitespace, {"occupation": "Farmer"})
        assert result_ws.status == "not_satisfied"

    def test_invalid_types_for_numeric_operators(self):
        """Non-numeric string values with numeric operators must fail safely without crash."""
        cond_num = EligibilityCondition(condition_name="Income", field="annual_family_income", operator="lte", expected_value=200000, explanation="Limit")
        # Actual is invalid string
        res = EligibilityEngine.evaluate_condition(cond_num, {"annual_family_income": "invalid_number_abc"})
        assert res.status == "not_satisfied"
        assert "Non-numeric" in res.explanation

    def test_unsupported_operator_and_missing_expected(self):
        """Unsupported operator or missing expected value returns unknown status."""
        # Unsupported operator
        cond_bad_op = {"condition_name": "Test", "field": "age", "operator": "regex", "expected_value": "^18$", "explanation": "Regex"}
        res_op = EligibilityEngine.evaluate_condition(cond_bad_op, {"age": 18})
        assert res_op.status == "unknown"
        assert "Unsupported operator" in res_op.explanation

        # None expected value
        cond_none_exp = {"condition_name": "Test", "field": "age", "operator": "gte", "expected_value": None, "explanation": "Null expected"}
        res_none = EligibilityEngine.evaluate_condition(cond_none_exp, {"age": 18})
        assert res_none.status == "unknown"
        assert "Invalid rule" in res_none.explanation

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

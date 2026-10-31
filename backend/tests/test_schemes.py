import uuid
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


class TestEligibilityEngineOperators:
    """Unit tests for structured eligibility rules and operators."""

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

    def test_missing_profile_field_classified_as_unknown(self):
        """A missing profile field must be classified as unknown, not automatically failed."""
        cond = EligibilityCondition(condition_name="Income", field="annual_family_income", operator="lte", expected_value=200000, explanation="Income limit")
        result = EligibilityEngine.evaluate_condition(cond, {})
        assert result.status == "unknown"
        assert result.actual_value is None
        assert "cannot be verified" in result.explanation


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
        assert data["total_pages"] >= 3

        # Verify demo flag and advisory nature
        first_item = data["items"][0]
        assert first_item["is_demo_data"] is True
        assert first_item["status"] == "active"

    def test_search_schemes_by_keyword(self, client):
        # Search for PM-KISAN
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
        assert len(data_empty["items"]) == 0

    def test_filter_by_category_and_state(self, client):
        # Healthcare category
        res = client.get("/api/v1/schemes?category=Healthcare")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for s in data["items"]:
            assert s["category"] == "Healthcare"

        # Maharashtra state
        res_mh = client.get("/api/v1/schemes?state=Maharashtra")
        assert res_mh.status_code == 200
        data_mh = res_mh.json()
        assert data_mh["total"] >= 2
        states = [s["state_applicability"] for s in data_mh["items"]]
        assert any("Maharashtra" in st or st == "All India" for st in states)

    def test_get_categories_aggregation(self, client):
        res = client.get("/api/v1/schemes/categories")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        categories = {item["category"]: item["count"] for item in data}
        assert "Agriculture" in categories
        assert "Healthcare" in categories
        assert "Housing" in categories
        assert "Education" in categories

    def test_get_scheme_by_id(self, client):
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"
        res = client.get(f"/api/v1/schemes/{pm_kisan_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == pm_kisan_id
        assert "PM-KISAN" in data["scheme_name"]
        assert len(data["benefits"]) > 0
        assert len(data["eligibility_criteria"]) > 0
        assert len(data["required_documents"]) > 0
        assert data["official_source_url"].startswith("https://")
        assert data["is_demo_data"] is True

        # Non-existent ID
        random_id = str(uuid.uuid4())
        res_404 = client.get(f"/api/v1/schemes/{random_id}")
        assert res_404.status_code == 404


class TestSchemeAssessmentAndRecommendations:
    """Test authenticated assessment, recommendations, and history isolation."""

    def test_recommendations_for_user(self, client):
        headers = get_auth_headers(client, "9222233333")

        # Set up citizen profile as a farmer in Maharashtra
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Suresh Patel",
                "date_of_birth": "1988-06-12",
                "state": "Maharashtra",
                "district": "Pune",
                "residence_type": "rural",
                "annual_family_income": 120000.0,
                "occupation": "Agricultural farmer",
            },
            headers=headers,
        )

        res = client.get("/api/v1/schemes/recommendations", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) > 0
        first_rec = data[0]
        assert "scheme" in first_rec
        assert "id" in first_rec["scheme"]
        assert "match_score" in first_rec
        assert "recommendation_reason" in first_rec

    def test_run_assessment_eligible_citizen(self, client):
        headers = get_auth_headers(client, "9333344444")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        # Complete profile satisfying PM-KISAN
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
        assert data["overall_readiness_score"] == 100
        assert data["satisfied_count"] >= 2
        assert data["not_satisfied_count"] == 0
        assert data["unknown_count"] == 0
        assert len(data["missing_fields"]) == 0
        assert data["official_application_url"].startswith("https://")

    def test_run_assessment_missing_fields_yields_insufficient_info(self, client):
        headers = get_auth_headers(client, "9444455555")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        # User has empty profile (no occupation, no DOB)
        res = client.post(f"/api/v1/schemes/{pm_kisan_id}/assess", headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["overall_status"] == "Insufficient Information"
        assert data["unknown_count"] > 0
        assert "occupation" in data["missing_fields"]

    def test_run_assessment_failing_criterion_yields_not_eligible(self, client):
        headers = get_auth_headers(client, "9555566666")
        pm_kisan_id = "11111111-1111-1111-1111-111111111111"

        # User is a software engineer (not a farmer)
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Dev User",
                "date_of_birth": "1995-01-01",
                "state": "Karnataka",
                "district": "Bengaluru",
                "occupation": "Software Engineer",
            },
            headers=headers,
        )

        res = client.post(f"/api/v1/schemes/{pm_kisan_id}/assess", headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["overall_status"] == "Not Eligible Based on Available Information"
        assert data["not_satisfied_count"] >= 1

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

        # Citizen B checks history -> should be 0, cannot see Citizen A's record
        res_hist_b = client.get("/api/v1/schemes/assessments/history", headers=headers_b)
        assert res_hist_b.status_code == 200
        history_b = res_hist_b.json()
        assert not any(item["assessment_id"] == assessment_a_id for item in history_b)

        # Citizen B attempts to access Citizen A's assessment detail -> must be 404
        res_cross = client.get(f"/api/v1/schemes/assessments/{assessment_a_id}", headers=headers_b)
        assert res_cross.status_code == 404

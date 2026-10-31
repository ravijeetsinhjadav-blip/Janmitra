from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.schemas.scheme import (
    ConditionEvaluation,
    EligibilityCondition,
    SchemeRecommendation,
    SchemeResponse,
)


class EligibilityEngine:
    """Deterministic, configurable rule-based eligibility assessment engine.
    
    Evaluates citizen demographics against structured scheme conditions without
    relying on arbitrary code execution or ungrounded model hallucinations.
    """

    SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"}

    @staticmethod
    def calculate_age(dob_str: Optional[str]) -> Optional[int]:
        """Derive citizen age from YYYY-MM-DD date of birth string."""
        if not dob_str:
            return None
        try:
            dob = datetime.strptime(str(dob_str), "%Y-%m-%d").date()
            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except (ValueError, TypeError):
            return None

    @classmethod
    def extract_profile_facts(cls, profile: Optional[UserProfile]) -> Dict[str, Any]:
        """Extract evaluation facts dictionary from Citizen UserProfile."""
        if not profile:
            return {
                "age": None,
                "state": None,
                "district": None,
                "residence_type": None,
                "annual_family_income": None,
                "occupation": None,
                "education_level": None,
            }

        age = cls.calculate_age(str(profile.date_of_birth) if profile.date_of_birth else None)
        return {
            "age": age,
            "state": profile.state.strip() if profile.state else None,
            "district": profile.district.strip() if profile.district else None,
            "residence_type": profile.residence_type.strip().lower() if profile.residence_type else None,
            "annual_family_income": float(profile.annual_family_income) if profile.annual_family_income is not None else None,
            "occupation": profile.occupation.strip() if profile.occupation else None,
            "education_level": profile.education_level.strip() if profile.education_level else None,
        }

    @classmethod
    def evaluate_condition(
        cls,
        condition: Any,
        facts: Dict[str, Any],
    ) -> ConditionEvaluation:
        """Evaluate a single rule condition against extracted citizen facts."""
        if hasattr(condition, "model_dump"):
            condition = condition.model_dump()
        elif not isinstance(condition, dict):
            condition = dict(condition)

        cond_name = condition.get("condition_name", "Eligibility Criterion")
        field = condition.get("field", "")
        op = condition.get("operator", "eq").lower()
        expected = condition.get("expected_value")
        base_explanation = condition.get("explanation", "")

        actual = facts.get(field)

        # 1. Missing or undefined profile fact -> Classified as UNKNOWN, never auto-failed
        if actual is None:
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=None,
                status="unknown",
                explanation=f"{base_explanation} (Missing from citizen profile; cannot be verified).",
            )

        # 2. Operator evaluation
        is_satisfied = False
        try:
            if op == "eq":
                if isinstance(actual, str) and isinstance(expected, str):
                    is_satisfied = actual.strip().lower() == expected.strip().lower()
                else:
                    is_satisfied = actual == expected

            elif op == "neq":
                if isinstance(actual, str) and isinstance(expected, str):
                    is_satisfied = actual.strip().lower() != expected.strip().lower()
                else:
                    is_satisfied = actual != expected

            elif op in ("gt", "gte", "lt", "lte"):
                num_actual = float(actual)
                num_expected = float(expected)
                if op == "gt":
                    is_satisfied = num_actual > num_expected
                elif op == "gte":
                    is_satisfied = num_actual >= num_expected
                elif op == "lt":
                    is_satisfied = num_actual < num_expected
                elif op == "lte":
                    is_satisfied = num_actual <= num_expected

            elif op == "in":
                # Expected is a list of allowed values
                if isinstance(expected, list):
                    lowered_expected = [str(e).strip().lower() for e in expected]
                    actual_str = str(actual).strip().lower()
                    # Universal state check
                    if field == "state" and ("all india" in lowered_expected or "all" in lowered_expected):
                        is_satisfied = True
                    else:
                        is_satisfied = actual_str in lowered_expected
                else:
                    is_satisfied = str(actual).strip().lower() == str(expected).strip().lower()

            elif op == "contains":
                actual_str = str(actual).strip().lower()
                expected_str = str(expected).strip().lower()
                is_satisfied = expected_str in actual_str

            else:
                # Unsupported operator falls back to unknown
                return ConditionEvaluation(
                    condition_name=cond_name,
                    field=field,
                    operator=op,
                    expected_value=expected,
                    actual_value=actual,
                    status="unknown",
                    explanation=f"Unsupported operator '{op}'.",
                )

        except (ValueError, TypeError):
            is_satisfied = False

        if is_satisfied:
            detail_msg = f"{base_explanation} (Satisfied: your {field} is '{actual}')."
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=actual,
                status="satisfied",
                explanation=detail_msg,
            )
        else:
            detail_msg = f"{base_explanation} (Not satisfied: your {field} is '{actual}', expected {op} '{expected}')."
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=actual,
                status="not_satisfied",
                explanation=detail_msg,
            )

    @classmethod
    def evaluate_scheme(
        cls,
        scheme: Scheme,
        profile: Optional[UserProfile],
    ) -> Dict[str, Any]:
        """Perform comprehensive deterministic assessment of a scheme for a citizen profile."""
        facts = cls.extract_profile_facts(profile)
        criteria: List[Dict[str, Any]] = scheme.eligibility_criteria or []

        # If scheme has geographical state applicability and no state rule, add default state check
        if scheme.state_applicability and scheme.state_applicability.lower() != "all india":
            has_state_rule = any(c.get("field") == "state" for c in criteria)
            if not has_state_rule:
                criteria = list(criteria) + [{
                    "condition_name": "State of Residence",
                    "field": "state",
                    "operator": "eq",
                    "expected_value": scheme.state_applicability,
                    "explanation": f"Scheme is restricted to residents of {scheme.state_applicability}.",
                }]

        evaluations: List[ConditionEvaluation] = []
        missing_fields: List[str] = []

        for condition in criteria:
            ev = cls.evaluate_condition(condition, facts)
            evaluations.append(ev)
            if ev.status == "unknown" and ev.field not in missing_fields:
                missing_fields.append(ev.field)

        satisfied_count = sum(1 for e in evaluations if e.status == "satisfied")
        not_satisfied_count = sum(1 for e in evaluations if e.status == "not_satisfied")
        unknown_count = sum(1 for e in evaluations if e.status == "unknown")
        total_conditions = len(evaluations)

        # Determine overall category
        if not_satisfied_count > 0:
            overall_status = "Not Eligible Based on Available Information"
        elif unknown_count > 0:
            overall_status = "Insufficient Information"
        else:
            overall_status = "Potentially Eligible"

        # Calculate readiness score (percentage of criteria verified as satisfied)
        if total_conditions == 0:
            readiness_score = 100.0
        else:
            readiness_score = round((satisfied_count / total_conditions) * 100.0, 1)

        return {
            "overall_status": overall_status,
            "overall_readiness_score": readiness_score,
            "conditions_breakdown": evaluations,
            "satisfied_count": satisfied_count,
            "not_satisfied_count": not_satisfied_count,
            "unknown_count": unknown_count,
            "missing_fields": missing_fields,
            "evaluated_at": datetime.now(timezone.utc),
        }

    @classmethod
    def generate_recommendations(
        cls,
        schemes: List[Scheme],
        profile: Optional[UserProfile],
    ) -> List[SchemeRecommendation]:
        """Generate tailored scheme recommendations for authenticated citizen."""
        recommendations: List[SchemeRecommendation] = []

        for scheme in schemes:
            if not scheme.is_active or scheme.status != "active":
                continue

            assessment = cls.evaluate_scheme(scheme, profile)
            status = assessment["overall_status"]

            # Exclude definitively not eligible schemes from recommendations
            if status == "Not Eligible Based on Available Information":
                continue

            # Build human-readable recommendation explanation
            satisfied = assessment["satisfied_count"]
            unknown = assessment["unknown_count"]
            missing = assessment["missing_fields"]
            score = assessment["overall_readiness_score"]

            if not profile:
                reason = "National welfare scheme. Complete your citizen profile to verify specific criteria."
            elif status == "Potentially Eligible":
                matched_traits = []
                if profile.state and (scheme.state_applicability == "All India" or scheme.state_applicability == profile.state):
                    matched_traits.append(f"state ({profile.state})")
                if profile.occupation and any("occupation" in str(c) for c in (scheme.eligibility_criteria or [])):
                    matched_traits.append(f"occupation ({profile.occupation})")
                if profile.residence_type and any("residence" in str(c) for c in (scheme.eligibility_criteria or [])):
                    matched_traits.append(f"residence ({profile.residence_type})")
                
                if matched_traits:
                    reason = f"Strong match based on your {', '.join(matched_traits)} and age criteria."
                else:
                    reason = f"You satisfy all {satisfied} evaluated eligibility conditions."
            else:
                # Insufficient Information
                missing_str = ", ".join(m.replace("_", " ").title() for m in missing)
                reason = f"Satisfies {satisfied} criteria. Provide {missing_str} in your profile to confirm eligibility."

            recommendations.append(
                SchemeRecommendation(
                    scheme=SchemeResponse.model_validate(scheme),
                    recommendation_reason=reason,
                    match_score=score,
                    satisfied_count=satisfied,
                    unknown_count=unknown,
                    missing_profile_fields=missing,
                )
            )

        # Sort recommendations: highest match score first, then by satisfied count
        recommendations.sort(key=lambda r: (r.match_score, r.satisfied_count), reverse=True)
        return recommendations

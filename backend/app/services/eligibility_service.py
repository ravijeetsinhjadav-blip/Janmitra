import math
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.schemas.scheme import (
    ConditionEvaluation,
    SchemeRecommendation,
    SchemeResponse,
)


class EligibilityEngine:
    """Deterministic, configurable rule-based eligibility assessment engine.
    
    Evaluates citizen demographics against structured scheme conditions without
    relying on arbitrary code execution (eval/exec) or ungrounded model hallucinations.
    """

    SUPPORTED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "in", "contains"}
    CONTROLLED_FIELDS = {"residence_type", "state", "gender", "category"}

    @staticmethod
    def calculate_age(
        dob_val: Any,
        reference_date: Optional[date] = None,
    ) -> Optional[int]:
        """Derive citizen age from YYYY-MM-DD date of birth or date object.
        
        Correctly accounts for leap years, future dates, and birthday boundaries:
        - On the birthday anniversary, age increments by 1.
        - The day before the birthday anniversary, age is still (years - 1).
        """
        if not dob_val:
            return None
        try:
            if isinstance(dob_val, date) and not isinstance(dob_val, datetime):
                dob = dob_val
            elif isinstance(dob_val, datetime):
                dob = dob_val.date()
            else:
                dob = datetime.strptime(str(dob_val).strip()[:10], "%Y-%m-%d").date()

            today = reference_date or date.today()
            if dob > today:
                return None  # Future birth date is invalid

            # Statutory anniversary calculation:
            # ((today.month, today.day) < (dob.month, dob.day)) is True if birthday has not yet occurred this year
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            if age < 0 or age > 130:
                return None
            return age
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
                "category": None,
            }

        age = cls.calculate_age(profile.date_of_birth)
        return {
            "age": age,
            "state": profile.state.strip() if profile.state else None,
            "district": profile.district.strip() if profile.district else None,
            "residence_type": profile.residence_type.strip().lower() if profile.residence_type else None,
            "annual_family_income": float(profile.annual_family_income) if profile.annual_family_income is not None else None,
            "occupation": profile.occupation.strip() if profile.occupation else None,
            "education_level": profile.education_level.strip() if profile.education_level else None,
            "category": getattr(profile, "category", None),
        }

    @classmethod
    def evaluate_condition(
        cls,
        condition: Any,
        facts: Dict[str, Any],
    ) -> ConditionEvaluation:
        """Evaluate a single rule condition against extracted citizen facts.
        
        Requirements:
        - Safely handle null and missing profile values (classified as unknown).
        - Safely validate expected types and prevent arbitrary code execution.
        - Prefer normalized exact matching for controlled fields (residence_type, state).
        - Handle invalid types gracefully without throwing unhandled exceptions.
        """
        if hasattr(condition, "model_dump"):
            condition = condition.model_dump()
        elif not isinstance(condition, dict):
            condition = dict(condition)

        cond_name = condition.get("condition_name", "Eligibility Criterion")
        field = condition.get("field", "")
        op = str(condition.get("operator", "eq")).strip().lower()
        expected = condition.get("expected_value")
        base_explanation = condition.get("explanation", "")

        actual = facts.get(field)

        # 1. Validate operator support
        if op not in cls.SUPPORTED_OPERATORS:
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=actual,
                status="unknown",
                explanation=f"Unsupported operator '{op}'. Condition cannot be deterministically evaluated.",
            )

        # 2. Validate expected value presence
        if expected is None:
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=actual,
                status="unknown",
                explanation=f"Invalid rule definition: expected value for '{cond_name}' is not defined.",
            )

        # 3. Missing or undefined profile fact -> Classified as UNKNOWN, never auto-failed
        if actual is None:
            return ConditionEvaluation(
                condition_name=cond_name,
                field=field,
                operator=op,
                expected_value=expected,
                actual_value=None,
                status="unknown",
                explanation=f"{base_explanation} (Missing from citizen profile: '{field}'; cannot be verified).",
            )

        # 4. Operator evaluation with strict type safety
        is_satisfied = False
        eval_note = ""

        try:
            if op == "eq":
                # String comparison: normalized case-insensitive stripped equality
                if isinstance(actual, str) and isinstance(expected, str):
                    act_norm = actual.strip().casefold()
                    exp_norm = expected.strip().casefold()
                    # Universal state check
                    if field == "state" and exp_norm in ("all india", "all"):
                        is_satisfied = True
                    else:
                        is_satisfied = act_norm == exp_norm
                elif isinstance(actual, (int, float)) and isinstance(expected, (int, float, str)):
                    try:
                        is_satisfied = float(actual) == float(expected)
                    except (ValueError, TypeError):
                        is_satisfied = False
                else:
                    is_satisfied = actual == expected

            elif op == "neq":
                if isinstance(actual, str) and isinstance(expected, str):
                    is_satisfied = actual.strip().casefold() != expected.strip().casefold()
                elif isinstance(actual, (int, float)) and isinstance(expected, (int, float, str)):
                    try:
                        is_satisfied = float(actual) != float(expected)
                    except (ValueError, TypeError):
                        is_satisfied = True
                else:
                    is_satisfied = actual != expected

            elif op in ("gt", "gte", "lt", "lte"):
                # Validate numeric types safely
                try:
                    num_actual = float(actual)
                    num_expected = float(expected)
                    if math.isnan(num_actual) or math.isnan(num_expected) or math.isinf(num_actual) or math.isinf(num_expected):
                        is_satisfied = False
                        eval_note = "Invalid numeric value (NaN/Infinity)."
                    elif op == "gt":
                        is_satisfied = num_actual > num_expected
                    elif op == "gte":
                        is_satisfied = num_actual >= num_expected
                    elif op == "lt":
                        is_satisfied = num_actual < num_expected
                    elif op == "lte":
                        is_satisfied = num_actual <= num_expected
                except (ValueError, TypeError):
                    is_satisfied = False
                    eval_note = f"Non-numeric comparison: cannot compare actual '{actual}' with expected '{expected}'."

            elif op == "in":
                # Expected must be a collection of valid values
                if isinstance(expected, (list, tuple, set)):
                    lowered_expected = [str(e).strip().casefold() for e in expected if e is not None]
                    actual_str = str(actual).strip().casefold()
                    if field == "state" and ("all india" in lowered_expected or "all" in lowered_expected):
                        is_satisfied = True
                    else:
                        is_satisfied = actual_str in lowered_expected
                elif isinstance(expected, str):
                    is_satisfied = str(actual).strip().casefold() == expected.strip().casefold()
                else:
                    is_satisfied = actual == expected

            elif op == "contains":
                # Substring or token matching
                actual_str = str(actual).strip().casefold()
                expected_str = str(expected).strip().casefold()
                # Empty expected string must never match
                if not expected_str or not actual_str:
                    is_satisfied = False
                    eval_note = "Empty substring or target."
                elif isinstance(actual, (list, tuple, set)):
                    is_satisfied = any(expected_str == str(item).strip().casefold() for item in actual)
                else:
                    is_satisfied = expected_str in actual_str

        except Exception as ex:
            is_satisfied = False
            eval_note = f"Evaluation error: {str(ex)}"

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
            suffix = f" [{eval_note}]" if eval_note else ""
            detail_msg = f"{base_explanation} (Not satisfied: your {field} is '{actual}', expected {op} '{expected}'){suffix}."
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
        """Perform comprehensive deterministic assessment of a scheme for a citizen profile.
        
        Calculates Criteria Match Percentage representing the proportion of verified conditions satisfied.
        This is an advisory metric and NOT an official government approval likelihood.
        """
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

        # Categorize overall status strictly:
        # 1. Any failed condition -> 'Not Eligible Based on Available Information'
        # 2. Any unknown condition (with zero failures) -> 'Insufficient Information'
        # 3. All conditions satisfied -> 'Potentially Eligible'
        if not_satisfied_count > 0:
            overall_status = "Not Eligible Based on Available Information"
        elif unknown_count > 0:
            overall_status = "Insufficient Information"
        else:
            overall_status = "Potentially Eligible"

        # Calculate Criteria Match Percentage (proportion of satisfied conditions)
        if total_conditions == 0:
            match_percentage = 100.0
        else:
            match_percentage = round((satisfied_count / total_conditions) * 100.0, 1)

        score_interpretation = (
            f"Criteria Match Percentage indicates that {satisfied_count} of {total_conditions} conditions "
            f"({match_percentage}%) are satisfied based on provided profile facts. "
            f"It represents verified condition compliance and does NOT represent an official approval likelihood."
        )

        return {
            "overall_status": overall_status,
            "criteria_match_percentage": match_percentage,
            "overall_readiness_score": match_percentage,  # backward compatibility alias
            "score_interpretation": score_interpretation,
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
        """Generate tailored scheme recommendations for authenticated citizen.
        
        Rules:
        - Match percentage is NOT represented as eligibility probability.
        - Schemes with clearly failed mandatory conditions are EXCLUDED from recommendations.
        - Missing profile fields are classified as unknown, not treated as confirmed matches.
        - Recommendations include clear citizen explanations and an explicit advisory notice.
        """
        recommendations: List[SchemeRecommendation] = []

        for scheme in schemes:
            if not scheme.is_active or scheme.status != "active":
                continue

            assessment = cls.evaluate_scheme(scheme, profile)
            status = assessment["overall_status"]
            satisfied = assessment["satisfied_count"]
            not_satisfied = assessment["not_satisfied_count"]
            unknown = assessment["unknown_count"]
            missing = assessment["missing_fields"]
            match_percentage = assessment["criteria_match_percentage"]

            # Exclude schemes with any clearly failed mandatory condition
            if not_satisfied > 0 or status == "Not Eligible Based on Available Information":
                continue

            # Build human-readable recommendation explanation
            if not profile:
                reason = "National welfare scheme. Complete your citizen profile to check eligibility."
                match_percentage = 0.0  # Missing fields are not treated as matches
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
                    criteria_match_percentage=match_percentage,
                    match_score=match_percentage,
                    satisfied_count=satisfied,
                    unknown_count=unknown,
                    missing_profile_fields=missing,
                )
            )

        # Sort recommendations: highest criteria match percentage first, then by satisfied count
        recommendations.sort(key=lambda r: (r.criteria_match_percentage, r.satisfied_count), reverse=True)
        return recommendations

"""
Comprehensive verification script for all supported roles.
Tests both value-based matching (from frontend) and keyword-based matching.
"""

from app.utils.skill_map_selector import get_skill_map_for_role


def verify_all_roles():
    print("=" * 60)
    print("Testing Value-Based Matching (Frontend Dropdown Values)")
    print("=" * 60)

    # Test all frontend dropdown values
    test_cases = [
        ("frontend", "js_fundamentals"),
        ("backend", "api_design"),
        ("fullstack", "fullstack_fundamentals"),
        ("data", "data_modeling"),
        ("ml", "ml_fundamentals"),
        ("devops", "linux_fundamentals"),
    ]

    for role_value, expected_skill in test_cases:
        skills = get_skill_map_for_role(role_value)
        skill_ids = [s.id for s in skills]
        assert expected_skill in skill_ids, f"Failed for {role_value}"
        print(f"  ✓ {role_value:12} -> {skill_ids[:2]}")

    print("\n" + "=" * 60)
    print("Testing Keyword-Based Matching (Backward Compatibility)")
    print("=" * 60)

    # Test keyword-based matching
    keyword_tests = [
        ("Frontend Engineer", "js_fundamentals"),
        ("Backend Developer", "api_design"),
        ("Full-Stack Developer", "fullstack_fundamentals"),
        ("Data Engineer", "data_modeling"),
        ("Machine Learning Engineer", "ml_fundamentals"),
        ("DevOps Engineer", "linux_fundamentals"),
        ("QA Engineer", "testing_fundamentals"),
        ("SDET", "programming_for_testing"),
    ]

    for role_name, expected_skill in keyword_tests:
        skills = get_skill_map_for_role(role_name)
        skill_ids = [s.id for s in skills]
        assert expected_skill in skill_ids, f"Failed for {role_name}"
        print(f"  ✓ {role_name:30} -> {skill_ids[:2]}")

    print("\n" + "=" * 60)
    print("Testing Edge Cases")
    print("=" * 60)

    # Test case sensitivity
    skills = get_skill_map_for_role("BACKEND")
    assert "api_design" in [s.id for s in skills]
    print("  ✓ Case insensitivity works")

    # Test default fallback
    skills = get_skill_map_for_role("Product Manager")
    assert "js_fundamentals" in [s.id for s in skills]
    print("  ✓ Unknown roles default to frontend")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print("\nSupported Roles (Frontend Dropdown Values):")
    print("  - frontend  : Frontend Developer")
    print("  - backend   : Backend Developer")
    print("  - fullstack : Full-Stack Developer")
    print("  - data      : Data Engineer")
    print("  - ml        : Machine Learning Engineer")
    print("  - devops    : DevOps Engineer")
    print("\nAlso supports: QA Engineer, SDET (via keyword matching)")


if __name__ == "__main__":
    verify_all_roles()

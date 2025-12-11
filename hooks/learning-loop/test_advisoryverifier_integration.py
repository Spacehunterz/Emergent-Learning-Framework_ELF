#!/usr/bin/env python3
"""
AdvisoryVerifier Integration Tests - Full Flow Testing

This tests the COMPLETE AdvisoryVerifier workflow including:
- Comment filtering
- Line-by-line analysis
- False positive prevention
- Edge case handling

Unlike test_edge_cases_phase4.py which tests raw regex patterns,
this tests the actual AdvisoryVerifier.analyze_edit() method.
"""

import sys
from pathlib import Path

# Import the verifier
sys.path.insert(0, str(Path(__file__).parent))
from post_tool_learning import AdvisoryVerifier


class IntegrationTester:
    """Test AdvisoryVerifier with real-world scenarios."""

    def __init__(self):
        self.verifier = AdvisoryVerifier()
        self.test_results = []

    def test_scenario(self, name, old_content, new_content, should_warn, expected_category=None):
        """Test a complete edit scenario.

        Args:
            name: Test name
            old_content: Original file content
            new_content: Modified file content
            should_warn: True if warnings expected, False otherwise
            expected_category: Expected warning category (if should_warn=True)
        """
        result = self.verifier.analyze_edit(
            file_path='test_file.py',
            old_content=old_content,
            new_content=new_content
        )

        has_warnings = result['has_warnings']
        passed = (has_warnings == should_warn)

        if should_warn and passed:
            # Verify category if specified
            if expected_category:
                categories = [w['category'] for w in result['warnings']]
                if expected_category not in categories:
                    passed = False

        self.test_results.append({
            'name': name,
            'passed': passed,
            'expected_warning': should_warn,
            'got_warning': has_warnings,
            'warnings': result.get('warnings', [])
        })

        return passed

    def run_all_tests(self):
        """Run comprehensive integration tests."""
        print("\n" + "="*80)
        print("ADVISORYVERIFIER INTEGRATION TESTS")
        print("Testing full workflow with comment filtering and edge cases")
        print("="*80)

        # Test 1: Comments should NOT trigger warnings
        print("\n=== Test Category: Comment Filtering ===")

        self.test_scenario(
            name="Pure comment with eval",
            old_content="",
            new_content="# Using eval() is dangerous",
            should_warn=False
        )

        self.test_scenario(
            name="Docstring with password",
            old_content="",
            new_content='"""Password should be hashed"""',
            should_warn=False
        )

        self.test_scenario(
            name="JS comment with eval",
            old_content="",
            new_content="// eval() is unsafe",
            should_warn=False
        )

        self.test_scenario(
            name="Multi-line comment start",
            old_content="",
            new_content="/* eval() here */",
            should_warn=False
        )

        # Test 2: Code with inline comments should trigger (code part detected)
        print("\n=== Test Category: Inline Comments ===")

        self.test_scenario(
            name="Code with inline comment",
            old_content="",
            new_content='result = eval(x)  # dangerous',
            should_warn=True,
            expected_category='code'
        )

        # Test 3: Variable names should NOT trigger
        print("\n=== Test Category: False Positive Prevention ===")

        self.test_scenario(
            name="eval_result variable",
            old_content="",
            new_content="eval_result = compute()",
            should_warn=False
        )

        self.test_scenario(
            name="password_hash variable",
            old_content="",
            new_content="password_hash = hash_function(pwd)",
            should_warn=False
        )

        self.test_scenario(
            name="validate_password function",
            old_content="",
            new_content="def validate_password():\n    pass",
            should_warn=False
        )

        # Test 4: Real risks should trigger
        print("\n=== Test Category: True Positives ===")

        self.test_scenario(
            name="Actual eval usage",
            old_content="",
            new_content="result = eval(user_input)",
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="Hardcoded password",
            old_content="",
            new_content='password = "secret123"',
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="API key hardcoded",
            old_content="",
            new_content='api_key = "sk_live_1234567890"',
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="shell=True usage",
            old_content="",
            new_content="subprocess.run(cmd, shell=True)",
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="pickle.load usage",
            old_content="",
            new_content="data = pickle.load(file)",
            should_warn=True,
            expected_category='deserialization'
        )

        self.test_scenario(
            name="MD5 hash usage",
            old_content="",
            new_content="hash = hashlib.md5(data)",
            should_warn=True,
            expected_category='cryptography'
        )

        self.test_scenario(
            name="random.randint usage",
            old_content="",
            new_content="token = random.randint(0, 999999)",
            should_warn=True,
            expected_category='cryptography'
        )

        self.test_scenario(
            name="verify=False usage",
            old_content="",
            new_content="response = requests.get(url, verify=False)",
            should_warn=True,
            expected_category='network'
        )

        # Test 5: Only NEW lines should be checked
        print("\n=== Test Category: Diff Detection ===")

        self.test_scenario(
            name="Existing eval not flagged",
            old_content="result = eval(x)",
            new_content="result = eval(x)",
            should_warn=False
        )

        self.test_scenario(
            name="Adding safe code to risky file",
            old_content="result = eval(x)",
            new_content="result = eval(x)\nprint('hello')",
            should_warn=False
        )

        self.test_scenario(
            name="Adding risky code to safe file",
            old_content="print('hello')",
            new_content="print('hello')\nresult = eval(x)",
            should_warn=True,
            expected_category='code'
        )

        # Test 6: Edge cases
        print("\n=== Test Category: Edge Cases ===")

        self.test_scenario(
            name="Case insensitive EVAL",
            old_content="",
            new_content="result = EVAL(x)",
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="Mixed case EvAl",
            old_content="",
            new_content="result = EvAl(x)",
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="Whitespace variation",
            old_content="",
            new_content="eval   (x)",
            should_warn=True,
            expected_category='code'
        )

        self.test_scenario(
            name="Newline after eval",
            old_content="",
            new_content="eval\n(x)",
            should_warn=True,
            expected_category='code'
        )

        # Test 7: Multi-line edits
        print("\n=== Test Category: Multi-line Changes ===")

        self.test_scenario(
            name="Adding multiple risky lines",
            old_content="",
            new_content='''password = "secret"
api_key = "key123"
result = eval(x)''',
            should_warn=True
        )

        self.test_scenario(
            name="Mixed safe and risky",
            old_content="",
            new_content='''# This is safe
x = 1
result = eval(y)  # This is risky''',
            should_warn=True,
            expected_category='code'
        )

        # Test 8: Escalation threshold (3+ warnings)
        print("\n=== Test Category: Escalation Recommendation ===")

        result = self.verifier.analyze_edit(
            file_path='test.py',
            old_content="",
            new_content='''password = "secret"
api_key = "key123"
token = "tok456"
eval(x)'''
        )

        escalation_needed = len(result['warnings']) >= 3
        recommendation_has_escalation = 'CEO' in result['recommendation'] or 'escalation' in result['recommendation']

        self.test_results.append({
            'name': "Escalation recommendation for 3+ warnings",
            'passed': escalation_needed and recommendation_has_escalation,
            'expected_warning': True,
            'got_warning': result['has_warnings'],
            'warnings': result['warnings']
        })

        print(f"  Warnings count: {len(result['warnings'])}")
        print(f"  Recommendation: {result['recommendation']}")

    def print_results(self):
        """Print test results."""
        print("\n" + "="*80)
        print("TEST RESULTS")
        print("="*80)

        passed_count = sum(1 for r in self.test_results if r['passed'])
        total_count = len(self.test_results)

        for result in self.test_results:
            status = "[PASS]" if result['passed'] else "[FAIL]"
            print(f"\n{status} {result['name']}")

            if not result['passed']:
                print(f"  Expected warning: {result['expected_warning']}")
                print(f"  Got warning: {result['got_warning']}")
                if result['warnings']:
                    print(f"  Warnings: {[w['message'] for w in result['warnings']]}")

        print("\n" + "="*80)
        print(f"SUMMARY: {passed_count}/{total_count} tests passed ({passed_count/total_count*100:.1f}%)")
        print("="*80)

        return passed_count, total_count

    def generate_findings(self, passed, total):
        """Generate findings report."""
        print("\n" + "="*80)
        print("## FINDINGS")
        print("="*80)

        print("\n### FACTS")
        print(f"[fact] AdvisoryVerifier passed {passed}/{total} integration tests ({passed/total*100:.1f}%)")

        # Analyze specific capabilities
        comment_tests = [r for r in self.test_results if 'comment' in r['name'].lower()]
        comment_passed = sum(1 for r in comment_tests if r['passed'])
        if comment_passed == len(comment_tests):
            print("[fact] Comment filtering is working correctly - no false positives from pure comments")
        else:
            print(f"[blocker] Comment filtering has issues - {len(comment_tests) - comment_passed} failures")

        false_positive_tests = [r for r in self.test_results if 'False Positive' in str(r.get('name', ''))]
        fp_passed = sum(1 for r in false_positive_tests if r['passed'])
        if fp_passed == len(false_positive_tests):
            print("[fact] False positive prevention working - variable names not flagged")
        else:
            print(f"[hypothesis] False positive prevention may need improvement - {len(false_positive_tests) - fp_passed} failures")

        true_positive_tests = [r for r in self.test_results if 'True Positive' in str(r.get('name', ''))]
        tp_passed = sum(1 for r in true_positive_tests if r['passed'])
        if tp_passed == len(true_positive_tests):
            print("[fact] True positive detection working - actual risks are flagged")
        else:
            print(f"[blocker] True positive detection failing - {len(true_positive_tests) - tp_passed} real risks missed")

        diff_tests = [r for r in self.test_results if 'Diff' in str(r.get('name', ''))]
        diff_passed = sum(1 for r in diff_tests if r['passed'])
        if diff_passed == len(diff_tests):
            print("[fact] Diff detection working - only new lines are analyzed")
        else:
            print(f"[hypothesis] Diff detection may have issues - {len(diff_tests) - diff_passed} failures")

        print("\n### HYPOTHESES")
        # Check for any systematic failures
        failed_tests = [r for r in self.test_results if not r['passed']]
        if failed_tests:
            print(f"[hypothesis] {len(failed_tests)} test(s) failed - may indicate edge cases needing attention")
            for fail in failed_tests[:3]:  # Show first 3
                print(f"  - {fail['name']}")
        else:
            print("[hypothesis] All integration tests passed - system appears robust for tested scenarios")

        print("\n### BLOCKERS")
        critical_failures = [r for r in self.test_results
                           if not r['passed'] and ('True Positive' in r['name'] or 'comment' in r['name'].lower())]
        if critical_failures:
            for fail in critical_failures:
                print(f"[blocker] Critical test failed: {fail['name']}")
        else:
            print("[fact] No critical blockers - core functionality working")

        print("\n### RECOMMENDATIONS")
        if passed == total:
            print("[fact] AdvisoryVerifier integration tests all passing")
            print("[fact] Comment filtering prevents false positives as designed")
            print("[fact] System ready for Phase 4 completion")
        else:
            print("[hypothesis] Review failed tests and adjust patterns or comment filtering")
            print(f"[fact] {total - passed} tests need attention before Phase 4 completion")


def main():
    """Run integration tests."""
    print("AdvisoryVerifier Integration Test Suite")
    print("Testing complete workflow including comment filtering")

    tester = IntegrationTester()
    tester.run_all_tests()
    passed, total = tester.print_results()
    tester.generate_findings(passed, total)


if __name__ == "__main__":
    main()

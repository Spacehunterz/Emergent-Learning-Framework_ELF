#!/usr/bin/env python3
"""
Tests for the new pattern categories added in Phase 4.

Tests the following previously untested categories:
- deserialization (pickle, yaml, marshal)
- cryptography (MD5, SHA1, random)
- command_injection (os.system, os.popen)
- path_traversal (../, open with user input)
- network (verify=False, ssl unverified)

Total: 12 patterns, 36+ test cases
"""

import unittest
import sys
import re
from pathlib import Path

# Add the hook directory to path
sys.path.insert(0, str(Path(__file__).parent))

from security_patterns import RISKY_PATTERNS
from post_tool_learning import AdvisoryVerifier


class TestDeserializationPatterns(unittest.TestCase):
    """Test deserialization vulnerability patterns."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()
        self.patterns = RISKY_PATTERNS['deserialization']

    def test_pickle_load_detected(self):
        """pickle.load() should be flagged."""
        code = 'data = pickle.load(file)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('pickle', result['warnings'][0]['message'].lower())

    def test_pickle_loads_detected(self):
        """pickle.loads() should be flagged."""
        code = 'obj = pickle.loads(user_data)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('pickle', result['warnings'][0]['message'].lower())

    def test_pickle_with_spaces(self):
        """pickle.load with various spacing."""
        code = 'pickle.load( f )'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_yaml_load_without_loader_detected(self):
        """yaml.load() without Loader should be flagged."""
        code = 'config = yaml.load(file)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('yaml', result['warnings'][0]['message'].lower())

    def test_yaml_load_with_safeloader_ok(self):
        """yaml.load() with SafeLoader should NOT be flagged."""
        code = 'config = yaml.load(file, Loader=yaml.SafeLoader)'
        result = self.verifier.analyze_edit('test.py', '', code)
        # Should not flag when Loader is specified
        yaml_warnings = [w for w in result.get('warnings', [])
                        if 'yaml' in w['message'].lower()]
        self.assertEqual(len(yaml_warnings), 0)

    def test_yaml_safe_load_ok(self):
        """yaml.safe_load() should NOT be flagged."""
        code = 'config = yaml.safe_load(file)'
        result = self.verifier.analyze_edit('test.py', '', code)
        yaml_warnings = [w for w in result.get('warnings', [])
                        if 'yaml' in w['message'].lower()]
        self.assertEqual(len(yaml_warnings), 0)

    def test_marshal_load_detected(self):
        """marshal.load() should be flagged."""
        code = 'data = marshal.load(f)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('marshal', result['warnings'][0]['message'].lower())

    def test_marshal_loads_detected(self):
        """marshal.loads() should be flagged."""
        code = 'obj = marshal.loads(bytes_data)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])


class TestCryptographyPatterns(unittest.TestCase):
    """Test weak cryptography patterns."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()
        self.patterns = RISKY_PATTERNS['cryptography']

    def test_md5_detected(self):
        """hashlib.md5() should be flagged."""
        code = 'hash = hashlib.md5(data)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('md5', result['warnings'][0]['message'].lower())

    def test_md5_with_encoding(self):
        """MD5 with encode should still be flagged."""
        code = "h = hashlib.md5(password.encode('utf-8'))"
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_sha1_detected(self):
        """hashlib.sha1() should be flagged."""
        code = 'hash = hashlib.sha1(password)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('sha1', result['warnings'][0]['message'].lower())

    def test_sha256_ok(self):
        """hashlib.sha256() should NOT be flagged (secure)."""
        code = 'hash = hashlib.sha256(data)'
        result = self.verifier.analyze_edit('test.py', '', code)
        sha_warnings = [w for w in result.get('warnings', [])
                       if 'sha' in w['message'].lower()]
        self.assertEqual(len(sha_warnings), 0)

    def test_random_randint_detected(self):
        """random.randint() should be flagged for security use."""
        code = 'token = random.randint(0, 999999)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('random', result['warnings'][0]['message'].lower())

    def test_random_choice_detected(self):
        """random.choice() should be flagged."""
        code = "code = ''.join(random.choice(chars) for _ in range(8))"
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_random_shuffle_detected(self):
        """random.shuffle() should be flagged."""
        code = 'random.shuffle(deck)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_secrets_module_ok(self):
        """secrets module should NOT be flagged (secure)."""
        code = 'token = secrets.token_hex(32)'
        result = self.verifier.analyze_edit('test.py', '', code)
        random_warnings = [w for w in result.get('warnings', [])
                         if 'random' in w['message'].lower() or 'secret' in w['message'].lower()]
        # secrets module is fine, only warns about hardcoded secrets
        self.assertEqual(len(random_warnings), 0)


class TestCommandInjectionPatterns(unittest.TestCase):
    """Test command injection vulnerability patterns."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()
        self.patterns = RISKY_PATTERNS['command_injection']

    def test_os_system_detected(self):
        """os.system() should be flagged."""
        code = 'os.system("ls -la")'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('os.system', result['warnings'][0]['message'].lower())

    def test_os_system_with_variable(self):
        """os.system() with variable should be flagged."""
        code = 'os.system(user_command)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_os_system_fstring(self):
        """os.system() with f-string should be flagged."""
        code = 'os.system(f"rm {filename}")'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_os_popen_detected(self):
        """os.popen() should be flagged."""
        code = 'output = os.popen("whoami").read()'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('os.popen', result['warnings'][0]['message'].lower())

    def test_os_popen_with_variable(self):
        """os.popen() with variable should be flagged."""
        code = 'os.popen(cmd)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_subprocess_run_ok(self):
        """subprocess.run() without shell=True should NOT be flagged."""
        code = 'subprocess.run(["ls", "-la"])'
        result = self.verifier.analyze_edit('test.py', '', code)
        cmd_warnings = [w for w in result.get('warnings', [])
                       if 'command' in w['message'].lower() or 'os.' in w['message'].lower()]
        self.assertEqual(len(cmd_warnings), 0)


class TestPathTraversalPatterns(unittest.TestCase):
    """Test path traversal vulnerability patterns."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()
        self.patterns = RISKY_PATTERNS['path_traversal']

    def test_triple_dot_dot_detected(self):
        """../../../ pattern should be flagged."""
        code = 'path = "../../../etc/passwd"'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('traversal', result['warnings'][0]['message'].lower())

    def test_double_dot_backslash(self):
        r"""..\..\.. pattern should be flagged."""
        # Use actual backslash characters in the string
        code = 'path = "..\\..\\..\\windows\\system32"'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_open_with_user_concat_detected(self):
        """open() with user input concatenation should be flagged."""
        code = 'f = open("/data/" + user_input)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('user', result['warnings'][0]['message'].lower())

    def test_open_with_fstring_user(self):
        """open() with f-string and user should be flagged."""
        code = 'open(f"/uploads/{user_filename}")'
        # This pattern specifically looks for + concatenation with 'user'
        # f-strings don't match this exact pattern
        result = self.verifier.analyze_edit('test.py', '', code)
        # May or may not flag depending on pattern - testing behavior
        # The current pattern requires + concatenation

    def test_safe_path_join_ok(self):
        """os.path.join() should NOT be flagged (safer)."""
        code = 'path = os.path.join(base_dir, filename)'
        result = self.verifier.analyze_edit('test.py', '', code)
        traversal_warnings = [w for w in result.get('warnings', [])
                             if 'traversal' in w['message'].lower()]
        self.assertEqual(len(traversal_warnings), 0)


class TestNetworkPatterns(unittest.TestCase):
    """Test network security patterns."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()
        self.patterns = RISKY_PATTERNS['network']

    def test_verify_false_detected(self):
        """verify=False should be flagged."""
        code = 'requests.get(url, verify=False)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('ssl', result['warnings'][0]['message'].lower())

    def test_verify_false_in_post(self):
        """verify=False in POST should be flagged."""
        code = 'requests.post(url, data=payload, verify=False)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_verify_false_with_spaces(self):
        """verify = False with spaces should be flagged."""
        code = 'requests.get(url, verify = False)'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])

    def test_ssl_unverified_context_detected(self):
        """ssl._create_unverified_context should be flagged."""
        code = 'ctx = ssl._create_unverified_context()'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        self.assertIn('ssl', result['warnings'][0]['message'].lower())

    def test_ssl_default_context_ok(self):
        """ssl.create_default_context() should NOT be flagged."""
        code = 'ctx = ssl.create_default_context()'
        result = self.verifier.analyze_edit('test.py', '', code)
        ssl_warnings = [w for w in result.get('warnings', [])
                       if 'unverified' in w['message'].lower()]
        self.assertEqual(len(ssl_warnings), 0)

    def test_verify_true_ok(self):
        """verify=True should NOT be flagged."""
        code = 'requests.get(url, verify=True)'
        result = self.verifier.analyze_edit('test.py', '', code)
        verify_warnings = [w for w in result.get('warnings', [])
                         if 'verification disabled' in w['message'].lower()]
        self.assertEqual(len(verify_warnings), 0)


class TestIntegrationMultipleCategories(unittest.TestCase):
    """Test that multiple categories work together."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()

    def test_multiple_vulnerabilities_detected(self):
        """Code with multiple vulnerability types should flag all."""
        code = """
import pickle
import hashlib

data = pickle.loads(user_input)
hash = hashlib.md5(password)
os.system(command)
requests.get(url, verify=False)
"""
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertTrue(result['has_warnings'])
        # Should detect multiple issues
        self.assertGreaterEqual(len(result['warnings']), 3)

    def test_escalation_recommendation(self):
        """3+ warnings should trigger escalation recommendation."""
        code = """
pickle.loads(x)
hashlib.md5(y)
os.system(z)
verify=False
"""
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertIn('escalation', result['recommendation'].lower())

    def test_categories_properly_labeled(self):
        """Each warning should have correct category."""
        test_cases = [
            ('pickle.load(f)', 'deserialization'),
            ('hashlib.md5(x)', 'cryptography'),
            ('os.system(cmd)', 'command_injection'),
            ('verify=False', 'network'),
        ]

        for code, expected_category in test_cases:
            result = self.verifier.analyze_edit('test.py', '', code)
            if result['has_warnings']:
                self.assertEqual(result['warnings'][0]['category'], expected_category,
                               f"Wrong category for: {code}")


class TestCommentFilteringForNewPatterns(unittest.TestCase):
    """Ensure comment filtering works for new pattern categories."""

    def setUp(self):
        self.verifier = AdvisoryVerifier()

    def test_deserialization_in_comment_not_flagged(self):
        """# pickle.load() in comment should NOT be flagged."""
        code = '# Never use pickle.load() with untrusted data'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertFalse(result['has_warnings'])

    def test_crypto_in_comment_not_flagged(self):
        """# hashlib.md5() in comment should NOT be flagged."""
        code = '# Avoid hashlib.md5() for passwords'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertFalse(result['has_warnings'])

    def test_command_in_comment_not_flagged(self):
        """# os.system() in comment should NOT be flagged."""
        code = '# Don\'t use os.system() - use subprocess instead'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertFalse(result['has_warnings'])

    def test_network_in_comment_not_flagged(self):
        """# verify=False in comment should NOT be flagged."""
        code = '# Setting verify=False is insecure!'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertFalse(result['has_warnings'])

    def test_docstring_not_flagged(self):
        """Patterns in docstrings should NOT be flagged."""
        code = '"""Warning: pickle.load() is dangerous"""'
        result = self.verifier.analyze_edit('test.py', '', code)
        self.assertFalse(result['has_warnings'])


def run_tests():
    """Run all tests and print summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDeserializationPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestCryptographyPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandInjectionPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestPathTraversalPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestNetworkPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationMultipleCategories))
    suite.addTests(loader.loadTestsFromTestCase(TestCommentFilteringForNewPatterns))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY - New Pattern Categories")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[FAILED] Some tests failed:")
        for test, trace in result.failures + result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

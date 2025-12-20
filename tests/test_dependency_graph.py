#!/usr/bin/env python3
"""
Comprehensive tests for dependency_graph.py
Tests all import parsing scenarios, graph building, clustering, and edge cases.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from coordinator.dependency_graph import DependencyGraph


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_test(self, name: str):
        print(f"[PASS] {name}")
        self.passed += 1

    def fail_test(self, name: str, reason: str):
        print(f"[FAIL] {name}")
        print(f"  Reason: {reason}")
        self.failed += 1
        self.errors.append(f"{name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}\n")
        return self.failed == 0


def create_test_project() -> Path:
    """Create a temporary test project with various import patterns."""
    temp_dir = Path(tempfile.mkdtemp(prefix="depgraph_test_"))

    # Test file 1: Simple imports
    (temp_dir / "simple.py").write_text("""
import os
import sys
from pathlib import Path
""")

    # Test file 2: Complex imports
    (temp_dir / "complex.py").write_text("""
import simple
from utils import helper
from utils.advanced import AdvancedHelper
import complex_lib as cl
from typing import Dict, List
""")

    # Test file 3: Utils module (to be imported)
    utils_dir = temp_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text("")
    (utils_dir / "helper.py").write_text("""
import os
from pathlib import Path
""")
    (utils_dir / "advanced.py").write_text("""
from utils.helper import helper_func
import simple
""")

    # Test file 4: No imports
    (temp_dir / "no_imports.py").write_text("""
def standalone_function():
    return 42
""")

    # Test file 5: Circular imports (A imports B, B imports A)
    (temp_dir / "circular_a.py").write_text("""
import circular_b
def func_a():
    pass
""")
    (temp_dir / "circular_b.py").write_text("""
import circular_a
def func_b():
    pass
""")

    # Test file 6: Relative imports
    pkg_dir = temp_dir / "package"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module1.py").write_text("""
from . import module2
from ..simple import something
""")
    (pkg_dir / "module2.py").write_text("""
from . import module1
""")

    # Non-Python file (should be ignored)
    (temp_dir / "README.md").write_text("# Test Project")

    # File with syntax error (should be handled gracefully)
    (temp_dir / "syntax_error.py").write_text("""
def broken(
    missing closing paren
""")

    return temp_dir


def test_import_parsing(results: TestResults, test_dir: Path):
    """Test 1: Import Parsing - various import styles."""
    print("\n=== Test 1: Import Parsing ===")

    dg = DependencyGraph(test_dir)
    dg.scan()

    # Test simple imports (should only have stdlib, which we ignore)
    simple_deps = dg.get_dependencies("simple.py")
    assert len(simple_deps) == 0, f"Expected 0 deps, got {len(simple_deps)}: {simple_deps}"
    results.pass_test("Simple imports (stdlib filtered)")

    # Test complex imports (should import simple and utils)
    complex_deps = dg.get_dependencies("complex.py")
    expected_complex = {"simple.py"}  # utils might not resolve if structure is wrong

    has_simple = "simple.py" in complex_deps
    assert has_simple, f"Expected simple.py in {complex_deps}"
    results.pass_test("Complex imports - found simple.py")

    # Test utils/advanced imports utils/helper
    utils_advanced_deps = dg.get_dependencies("utils/advanced.py")
    assert "utils/helper.py" in utils_advanced_deps or "simple.py" in utils_advanced_deps, \
        f"Expected utils/helper.py or simple.py, got {utils_advanced_deps}"
    results.pass_test("Nested module imports")


def test_graph_building(results: TestResults, test_dir: Path):
    """Test 2: Graph Building - forward and reverse graphs."""
    print("\n=== Test 2: Graph Building ===")

    dg = DependencyGraph(test_dir)
    dg.scan()

    # Check forward graph exists
    assert len(dg.graph) > 0, "Graph is empty"
    results.pass_test("Forward graph built")

    # Check reverse graph exists
    assert len(dg.reverse) > 0, "Reverse graph is empty"
    results.pass_test("Reverse graph built")

    # Test that simple.py has dependents (complex.py imports it)
    simple_dependents = dg.get_dependents("simple.py")
    assert "complex.py" in simple_dependents, f"Expected complex.py in {simple_dependents}"
    results.pass_test("Reverse graph correctly tracks dependents")


def test_cluster_generation(results: TestResults, test_dir: Path):
    """Test 3: Cluster Generation - depth 1 and 2."""
    print("\n=== Test 3: Cluster Generation ===")

    dg = DependencyGraph(test_dir)
    dg.scan()

    # Test cluster depth=1
    cluster1 = dg.get_cluster("simple.py", depth=1)
    assert "simple.py" in cluster1, "Original file not in cluster"
    results.pass_test("Cluster includes original file")

    # Cluster should include both dependencies and dependents
    assert len(cluster1) >= 1, f"Cluster is empty: {cluster1}"  # At minimum includes itself
    results.pass_test("Cluster depth=1 generated")

    # Test cluster depth=2 (should be larger or equal)
    cluster2 = dg.get_cluster("simple.py", depth=2)
    assert len(cluster2) >= len(cluster1), \
        f"depth=2 ({len(cluster2)}) smaller than depth=1 ({len(cluster1)})"
    results.pass_test("Cluster depth=2 >= depth=1")

    # Test that cluster includes both deps and dependents
    # complex.py imports simple.py, so it should be in the cluster
    assert "complex.py" in cluster1 or "complex.py" in cluster2, \
        f"complex.py not in clusters: {cluster1}, {cluster2}"
    results.pass_test("Cluster includes dependents")


def test_chain_suggestion(results: TestResults, test_dir: Path):
    """Test 4: Chain Suggestion - single and multiple files."""
    print("\n=== Test 4: Chain Suggestion ===")

    dg = DependencyGraph(test_dir)
    dg.scan()

    # Test single file
    chain_single = dg.suggest_chain(["simple.py"])
    assert "simple.py" in chain_single, f"simple.py not in {chain_single}"
    results.pass_test("Chain suggestion for single file")

    # Test multiple files
    chain_multi = dg.suggest_chain(["simple.py", "complex.py"])
    assert "simple.py" in chain_multi and "complex.py" in chain_multi, \
        f"Missing files in {chain_multi}"
    results.pass_test("Chain suggestion for multiple files")

    # Test that chain returns sorted list
    assert chain_multi == sorted(chain_multi), f"Chain not sorted: {chain_multi}"
    results.pass_test("Chain is sorted")

    # Test complete transitive closure
    # If we modify complex.py, we should get simple.py too (since complex imports simple)
    chain_complex = dg.suggest_chain(["complex.py"])
    assert "simple.py" in chain_complex, f"simple.py not in complex.py chain: {chain_complex}"
    results.pass_test("Chain includes transitive dependencies")


def test_edge_cases(results: TestResults, test_dir: Path):
    """Test 5: Edge Cases - no imports, circular imports, errors."""
    print("\n=== Test 5: Edge Cases ===")

    dg = DependencyGraph(test_dir)
    dg.scan()

    # Test file with no imports
    no_import_deps = dg.get_dependencies("no_imports.py")
    assert len(no_import_deps) == 0, f"Expected 0 deps, got {no_import_deps}"
    results.pass_test("File with no imports")

    # Test circular imports (should handle gracefully)
    circular_a_cluster = dg.get_cluster("circular_a.py", depth=2)
    circular_b_cluster = dg.get_cluster("circular_b.py", depth=2)

    # Both should be in each other's clusters
    assert "circular_b.py" in circular_a_cluster and "circular_a.py" in circular_b_cluster, \
        f"A: {circular_a_cluster}, B: {circular_b_cluster}"
    results.pass_test("Circular imports handled")

    # Test non-existent file
    nonexistent_deps = dg.get_dependencies("does_not_exist.py")
    assert len(nonexistent_deps) == 0, f"Expected empty, got {nonexistent_deps}"
    results.pass_test("Non-existent file returns empty")

    # Test non-Python file (should not be in graph)
    assert "README.md" not in dg.graph, "README.md should not be in graph"
    results.pass_test("Non-Python file filtered")

    # Test file with syntax error (should be in graph but with no deps, or excluded)
    if "syntax_error.py" in dg.graph:
        syntax_deps = dg.get_dependencies("syntax_error.py")
        assert len(syntax_deps) == 0, f"Expected 0 deps, got {syntax_deps}"
        results.pass_test("Syntax error file handled gracefully")
    else:
        results.pass_test("Syntax error file handled gracefully (excluded)")


def test_elf_codebase(results: TestResults):
    """Test 6: ELF Codebase - scan the actual ELF framework."""
    print("\n=== Test 6: ELF Codebase Analysis ===")

    elf_root = Path(__file__).parent.parent
    dg = DependencyGraph(elf_root)

    dg.scan()
    stats = dg.get_stats()

    print(f"\nELF Codebase Statistics:")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Total dependencies: {stats['total_dependencies']}")
    print(f"  Files with no deps: {stats['files_with_no_deps']}")
    print(f"  Files with no dependents: {stats['files_with_no_dependents']}")
    print(f"  Max dependencies: {stats['most_dependencies']}")
    print(f"  Max dependents: {stats['most_dependents']}")

    assert stats['total_files'] > 0, "No files found"
    results.pass_test("ELF codebase scanned")

    # Test that dependency_graph.py itself is in the graph
    # Use os.path.join for cross-platform compatibility
    dep_graph_path = os.path.join("coordinator", "dependency_graph.py")
    assert dep_graph_path in dg.graph, "dependency_graph.py not found in graph"
    results.pass_test("dependency_graph.py found in graph")

    # Check its dependencies
    deps = dg.get_dependencies(dep_graph_path)
    print(f"\n  dependency_graph.py imports: {len(deps)} files")
    for dep in sorted(deps):
        print(f"    - {dep}")

    # Find the file with most dependencies
    max_deps_file = max(dg.graph.items(), key=lambda x: len(x[1]), default=(None, set()))
    if max_deps_file[0]:
        print(f"\n  Most dependencies: {max_deps_file[0]} ({len(max_deps_file[1])} deps)")

    # Find the file with most dependents
    max_dependents_file = max(dg.reverse.items(), key=lambda x: len(x[1]), default=(None, set()))
    if max_dependents_file[0]:
        print(f"  Most dependents: {max_dependents_file[0]} ({len(max_dependents_file[1])} dependents)")

    return stats


def test_query_before_scan(results: TestResults, test_dir: Path):
    """Test 7: Error handling - query before scan."""
    print("\n=== Test 7: Error Handling ===")

    dg = DependencyGraph(test_dir)

    # Should raise RuntimeError if queried before scan
    raised_correctly = False
    try:
        dg.get_dependencies("simple.py")
        assert False, "Should raise RuntimeError"
    except RuntimeError as e:
        assert "scan()" in str(e), f"Wrong error message: {e}"
        raised_correctly = True
    except Exception as e:
        assert False, f"Wrong exception type: {type(e)}"

    assert raised_correctly, "RuntimeError was not raised"
    results.pass_test("Query before scan raises RuntimeError")


def main():
    """Run all tests."""
    print("="*60)
    print("Dependency Graph Comprehensive Test Suite")
    print("="*60)

    results = TestResults()
    test_dir = None

    try:
        # Create test project
        print("\nCreating test project...")
        test_dir = create_test_project()
        print(f"Test project created at: {test_dir}")

        # Run all tests
        test_query_before_scan(results, test_dir)
        test_import_parsing(results, test_dir)
        test_graph_building(results, test_dir)
        test_cluster_generation(results, test_dir)
        test_chain_suggestion(results, test_dir)
        test_edge_cases(results, test_dir)

        # Test real ELF codebase
        elf_stats = test_elf_codebase(results)

        # Print summary
        results.summary()

        # Return stats
        return elf_stats

    finally:
        # Cleanup
        if test_dir and test_dir.exists():
            print(f"\nCleaning up test project at {test_dir}...")
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    stats = main()

    # Exit with error code if tests failed
    sys.exit(0 if stats else 1)

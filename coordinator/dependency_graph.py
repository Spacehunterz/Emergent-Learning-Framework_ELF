#!/usr/bin/env python3
"""
Dependency Graph: Static analysis of file dependencies for smart claim chains.

Analyzes Python imports to build a dependency graph, enabling agents to:
- Discover what files are related to their target files
- Claim complete dependency clusters atomically
- Avoid breaking imports by editing interdependent files independently

Supports: Python (via ast), with extensibility for other languages.
"""

import ast
import os
from pathlib import Path
from typing import Set, List, Dict, Optional
from collections import deque


class DependencyGraph:
    """Build and query dependency relationships between files.

    This class scans Python files to build:
    - Forward graph: file -> what it imports
    - Reverse graph: file -> what imports it

    Used to suggest complete claim chains when agents want to edit files.
    """

    def __init__(self, project_root: str):
        """Initialize dependency graph for a project.

        Args:
            project_root: Root directory of the project to analyze
        """
        self.root = Path(project_root).resolve()
        self.graph: Dict[str, Set[str]] = {}  # file -> files it depends on
        self.reverse: Dict[str, Set[str]] = {}  # file -> files that depend on it
        self._scanned = False

    def scan(self, include_patterns: Optional[List[str]] = None) -> None:
        """Scan project and build import/dependency graph.

        Args:
            include_patterns: Optional list of glob patterns to include (e.g., ["*.py", "src/**/*.py"])
                             If None, scans all .py files in project
        """
        self.graph = {}
        self.reverse = {}

        # Default to scanning all Python files
        if include_patterns is None:
            include_patterns = ["**/*.py"]

        # Collect all files to scan
        files_to_scan: Set[Path] = set()
        for pattern in include_patterns:
            for file_path in self.root.glob(pattern):
                if file_path.is_file():
                    files_to_scan.add(file_path)

        # Build dependency graph
        for file_path in files_to_scan:
            rel_path = str(file_path.relative_to(self.root))
            dependencies = self._extract_python_imports(file_path)

            # Store dependencies
            self.graph[rel_path] = set()
            for dep in dependencies:
                # Try to resolve import to actual file
                resolved = self._resolve_import_to_file(dep, file_path)
                if resolved:
                    self.graph[rel_path].add(resolved)

        # Build reverse graph
        for file_path, deps in self.graph.items():
            for dep in deps:
                if dep not in self.reverse:
                    self.reverse[dep] = set()
                self.reverse[dep].add(file_path)

        self._scanned = True

    def _extract_python_imports(self, file_path: Path) -> Set[str]:
        """Extract import statements from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Set of module names imported (e.g., {"os", "pathlib.Path", "mymodule.utils"})
        """
        imports: Set[str] = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        # Also add full paths for "from X import Y"
                        for alias in node.names:
                            imports.add(f"{node.module}.{alias.name}")

        except (SyntaxError, UnicodeDecodeError, OSError):
            # Skip files that can't be parsed
            pass

        return imports

    def _resolve_import_to_file(self, import_name: str, importing_file: Path) -> Optional[str]:
        """Resolve an import statement to an actual file path.

        Args:
            import_name: Import string (e.g., "mymodule.utils" or "os")
            importing_file: The file doing the importing

        Returns:
            Relative path to the imported file, or None if not found
        """
        # Skip standard library and external packages (heuristic: no dot or common stdlib names)
        stdlib_modules = {
            'os', 'sys', 'pathlib', 'json', 'time', 'datetime', 'collections',
            'typing', 'io', 'ast', 'subprocess', 'shutil', 'glob', 're',
            'random', 'hashlib', 'base64', 'tempfile', 'unittest', 'pytest',
            'logging', 'threading', 'multiprocessing', 'queue', 'argparse'
        }

        base_module = import_name.split('.')[0]
        if base_module in stdlib_modules:
            return None

        # Try to resolve relative to project root
        # Convert module path to file path (e.g., "mymodule.utils" -> "mymodule/utils.py")
        module_parts = import_name.split('.')

        # Try multiple possible file locations
        # Use Path.joinpath to properly handle path construction
        base_path = Path(*module_parts) if len(module_parts) > 1 else Path(module_parts[0])

        candidates = [
            self.root / (str(base_path) + '.py'),  # Direct file
            self.root / base_path / '__init__.py',  # Package
            self.root / 'src' / (str(base_path) + '.py'),  # In src/
            self.root / 'src' / base_path / '__init__.py',
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    rel_path = str(candidate.relative_to(self.root))
                    return rel_path
                except ValueError:
                    # Not relative to project root
                    pass

        return None

    def get_dependencies(self, file_path: str) -> Set[str]:
        """Get files that this file depends on (imports).

        Args:
            file_path: Relative path to file from project root

        Returns:
            Set of file paths this file imports
        """
        if not self._scanned:
            raise RuntimeError("Must call scan() before querying dependencies")

        # Normalize path
        file_path = str(Path(file_path))
        return self.graph.get(file_path, set())

    def get_dependents(self, file_path: str) -> Set[str]:
        """Get files that depend on this file (import it).

        Args:
            file_path: Relative path to file from project root

        Returns:
            Set of file paths that import this file
        """
        if not self._scanned:
            raise RuntimeError("Must call scan() before querying dependents")

        # Normalize path
        file_path = str(Path(file_path))
        return self.reverse.get(file_path, set())

    def get_cluster(self, file_path: str, depth: int = 2) -> Set[str]:
        """Get file + dependencies + dependents up to specified depth.

        This performs a bidirectional BFS to find all related files within
        the specified number of hops.

        Args:
            file_path: Relative path to file from project root
            depth: How many levels deep to traverse (default: 2)

        Returns:
            Set of all related file paths (including the original file)
        """
        if not self._scanned:
            raise RuntimeError("Must call scan() before querying clusters")

        # Normalize path
        file_path = str(Path(file_path))

        cluster: Set[str] = {file_path}
        visited: Set[str] = {file_path}
        queue: deque = deque([(file_path, 0)])  # (file, current_depth)

        while queue:
            current_file, current_depth = queue.popleft()

            if current_depth >= depth:
                continue

            # Explore dependencies (forward)
            for dep in self.graph.get(current_file, set()):
                if dep not in visited:
                    visited.add(dep)
                    cluster.add(dep)
                    queue.append((dep, current_depth + 1))

            # Explore dependents (reverse)
            for dependent in self.reverse.get(current_file, set()):
                if dependent not in visited:
                    visited.add(dependent)
                    cluster.add(dependent)
                    queue.append((dependent, current_depth + 1))

        return cluster

    def suggest_chain(self, files: List[str], depth: int = 2) -> List[str]:
        """Given files agent wants to modify, suggest complete chain needed.

        This combines clusters for all input files and returns a sorted list.

        Args:
            files: List of file paths the agent wants to modify
            depth: Cluster depth for each file (default: 2)

        Returns:
            Sorted list of all files that should be claimed together
        """
        if not self._scanned:
            raise RuntimeError("Must call scan() before suggesting chains")

        all_files: Set[str] = set()

        for file_path in files:
            cluster = self.get_cluster(file_path, depth=depth)
            all_files.update(cluster)

        return sorted(all_files)

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the dependency graph.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_files": len(self.graph),
            "total_dependencies": sum(len(deps) for deps in self.graph.values()),
            "files_with_no_deps": sum(1 for deps in self.graph.values() if not deps),
            "files_with_no_dependents": sum(1 for deps in self.reverse.values() if not deps),
            "most_dependencies": max((len(deps) for deps in self.graph.values()), default=0),
            "most_dependents": max((len(deps) for deps in self.reverse.values()), default=0),
        }


# CLI interface for testing
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("""Usage: dependency_graph.py <command> [args]

Commands:
  scan <project_root>               Scan project and show stats
  deps <project_root> <file>        Show dependencies of a file
  dependents <project_root> <file>  Show what depends on a file
  cluster <project_root> <file> [depth]  Show dependency cluster
  suggest <project_root> <file1> [file2 ...]  Suggest claim chain

Examples:
  dependency_graph.py scan .
  dependency_graph.py deps . coordinator/blackboard.py
  dependency_graph.py cluster . coordinator/blackboard.py 3
  dependency_graph.py suggest . coordinator/blackboard.py scripts/record-failure.sh
""")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "scan" and len(sys.argv) >= 3:
        root = sys.argv[2]
        dg = DependencyGraph(root)
        print(f"Scanning {root}...")
        dg.scan()
        stats = dg.get_stats()
        print("\nDependency Graph Statistics:")
        print(json.dumps(stats, indent=2))

    elif cmd == "deps" and len(sys.argv) >= 4:
        root = sys.argv[2]
        file_path = sys.argv[3]
        dg = DependencyGraph(root)
        dg.scan()
        deps = dg.get_dependencies(file_path)
        print(f"\nDependencies of {file_path}:")
        for dep in sorted(deps):
            print(f"  - {dep}")

    elif cmd == "dependents" and len(sys.argv) >= 4:
        root = sys.argv[2]
        file_path = sys.argv[3]
        dg = DependencyGraph(root)
        dg.scan()
        dependents = dg.get_dependents(file_path)
        print(f"\nFiles that depend on {file_path}:")
        for dep in sorted(dependents):
            print(f"  - {dep}")

    elif cmd == "cluster" and len(sys.argv) >= 4:
        root = sys.argv[2]
        file_path = sys.argv[3]
        depth = int(sys.argv[4]) if len(sys.argv) > 4 else 2
        dg = DependencyGraph(root)
        dg.scan()
        cluster = dg.get_cluster(file_path, depth=depth)
        print(f"\nCluster for {file_path} (depth={depth}):")
        for f in sorted(cluster):
            print(f"  - {f}")

    elif cmd == "suggest" and len(sys.argv) >= 4:
        root = sys.argv[2]
        files = sys.argv[3:]
        dg = DependencyGraph(root)
        dg.scan()
        chain = dg.suggest_chain(files)
        print(f"\nSuggested claim chain for: {', '.join(files)}")
        print(f"Total files to claim: {len(chain)}\n")
        for f in chain:
            print(f"  - {f}")

    else:
        print("Invalid command or missing arguments. Run without args for help.")
        sys.exit(1)

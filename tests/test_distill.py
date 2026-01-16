"""
Tests for ELF Distillation module - Pattern decay, promotion, and golden rules.
"""
import json
import tempfile
import pytest
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observe.elf_distill import (
    calculate_decay_factor,
    is_promotion_candidate,
    estimate_tokens,
    format_pattern_for_golden_rules,
    select_patterns_for_promotion,
    DECAY_HALF_LIFE_DAYS,
    PROMOTION_THRESHOLDS,
    TOKEN_BUDGET,
)


class TestDecayCalculation:
    """Tests for pattern strength decay."""

    def test_decay_at_zero_days(self):
        """No decay at age 0."""
        factor = calculate_decay_factor(0)
        assert factor == 1.0, "Factor should be 1.0 at age 0"

    def test_decay_at_half_life(self):
        """Strength should halve at half-life."""
        factor = calculate_decay_factor(DECAY_HALF_LIFE_DAYS)
        assert abs(factor - 0.5) < 0.01, f"Factor should be ~0.5 at half-life, got {factor}"

    def test_decay_at_two_half_lives(self):
        """Strength should quarter at two half-lives."""
        factor = calculate_decay_factor(DECAY_HALF_LIFE_DAYS * 2)
        assert abs(factor - 0.25) < 0.01, f"Factor should be ~0.25 at 2x half-life, got {factor}"

    def test_decay_monotonic_decrease(self):
        """Decay factor should monotonically decrease."""
        factors = [calculate_decay_factor(d) for d in range(0, 30)]
        for i in range(1, len(factors)):
            assert factors[i] <= factors[i-1], "Decay should be monotonically decreasing"

    def test_decay_never_zero(self):
        """Decay factor should never reach zero."""
        factor = calculate_decay_factor(365)  # One year
        assert factor > 0, "Decay factor should never be exactly zero"


class MockPattern:
    """Mock pattern object for testing promotion candidates."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 1)
        self.strength = kwargs.get('strength', 0.5)
        self.occurrence_count = kwargs.get('occurrence_count', 1)
        self.first_seen = kwargs.get('first_seen', datetime.utcnow() - timedelta(days=7))
        self.last_seen = kwargs.get('last_seen', datetime.utcnow())
        self.session_ids = kwargs.get('session_ids', '[]')
        self.promoted_to_heuristic_id = kwargs.get('promoted_to_heuristic_id', None)
        self.pattern_text = kwargs.get('pattern_text', 'Test pattern')
        self.domain = kwargs.get('domain', 'general')
        self.signature = kwargs.get('signature', 'test_sig')


class TestPromotionCandidates:
    """Tests for promotion candidate selection."""

    def test_meets_all_thresholds(self):
        """Pattern meeting all thresholds should be candidate."""
        pattern = MockPattern(
            strength=0.8,
            occurrence_count=5,
            first_seen=datetime.utcnow() - timedelta(days=3),
            session_ids=json.dumps(['s1', 's2', 's3']),
        )
        assert is_promotion_candidate(pattern) is True

    def test_already_promoted(self):
        """Already promoted pattern should not be candidate."""
        pattern = MockPattern(
            strength=0.9,
            occurrence_count=10,
            session_ids=json.dumps(['s1', 's2', 's3']),
            promoted_to_heuristic_id=42,
        )
        assert is_promotion_candidate(pattern) is False

    def test_strength_too_low(self):
        """Pattern with low strength should not be candidate."""
        pattern = MockPattern(
            strength=0.5,  # Below 0.7 threshold
            occurrence_count=10,
            session_ids=json.dumps(['s1', 's2', 's3']),
        )
        assert is_promotion_candidate(pattern) is False

    def test_occurrence_count_too_low(self):
        """Pattern with low occurrence count should not be candidate."""
        pattern = MockPattern(
            strength=0.9,
            occurrence_count=1,  # Below 3 threshold
            session_ids=json.dumps(['s1', 's2', 's3']),
        )
        assert is_promotion_candidate(pattern) is False

    def test_too_young(self):
        """Pattern that is too young should not be candidate."""
        pattern = MockPattern(
            strength=0.9,
            occurrence_count=5,
            first_seen=datetime.utcnow() - timedelta(hours=1),  # Less than 1 day
            session_ids=json.dumps(['s1', 's2', 's3']),
        )
        assert is_promotion_candidate(pattern) is False

    def test_low_session_diversity(self):
        """Pattern from single session should not be candidate."""
        pattern = MockPattern(
            strength=0.9,
            occurrence_count=5,
            session_ids=json.dumps(['s1']),  # Only 1 session
        )
        assert is_promotion_candidate(pattern) is False


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_tokens_empty(self):
        """Empty string should have 0 tokens."""
        assert estimate_tokens("") == 0

    def test_estimate_tokens_short(self):
        """Short string should have few tokens."""
        tokens = estimate_tokens("Hello world")
        assert tokens >= 1
        assert tokens < 10

    def test_estimate_tokens_proportional(self):
        """Longer strings should have proportionally more tokens."""
        short = estimate_tokens("abc")
        long = estimate_tokens("abcdefghijklmnopqrstuvwxyz")
        assert long > short


class TestGoldenRulesFormatting:
    """Tests for formatting patterns as golden rules."""

    def test_format_basic_pattern(self):
        """Should format pattern as markdown."""
        pattern = MockPattern(
            pattern_text='Always check file exists before reading',
            occurrence_count=5,
            session_ids=json.dumps(['s1', 's2']),
            domain='filesystem',
            strength=0.85,
        )
        formatted = format_pattern_for_golden_rules(pattern, 1)

        assert '## 1.' in formatted
        assert 'Always check file exists' in formatted
        assert 'filesystem' in formatted
        assert '0.85' in formatted
        assert 'Observed 5x' in formatted

    def test_format_truncates_long_text(self):
        """Should truncate very long pattern text in heading."""
        long_text = "This is a very long pattern text that should be truncated " * 10
        pattern = MockPattern(pattern_text=long_text)
        formatted = format_pattern_for_golden_rules(pattern, 1)

        # Heading should be truncated but full text in blockquote
        lines = formatted.split('\n')
        heading = [l for l in lines if l.startswith('## 1.')][0]
        assert len(heading) < len(long_text)


class TestPatternSelection:
    """Tests for selecting patterns within token budget."""

    def test_select_highest_strength_first(self):
        """Should select highest strength patterns first."""
        patterns = [
            MockPattern(id=1, strength=0.7, occurrence_count=3, pattern_text='Low strength'),
            MockPattern(id=2, strength=0.95, occurrence_count=5, pattern_text='High strength'),
            MockPattern(id=3, strength=0.8, occurrence_count=4, pattern_text='Medium strength'),
        ]
        selected = select_patterns_for_promotion(patterns, token_budget=TOKEN_BUDGET)

        if len(selected) >= 2:
            # First selected should be highest strength
            assert selected[0].strength >= selected[1].strength

    def test_respects_token_budget(self):
        """Should not exceed token budget."""
        patterns = [
            MockPattern(id=i, strength=0.9, pattern_text=f'Pattern {i} ' * 50)
            for i in range(100)
        ]
        selected = select_patterns_for_promotion(patterns, token_budget=500)

        total_tokens = sum(estimate_tokens(format_pattern_for_golden_rules(p, i))
                         for i, p in enumerate(selected))
        assert total_tokens <= 500 + 100  # Allow small overflow from estimation

    def test_empty_candidates(self):
        """Should handle empty candidate list."""
        selected = select_patterns_for_promotion([], token_budget=TOKEN_BUDGET)
        assert selected == []


class TestGoldenRulesFile:
    """Tests for appending to golden-rules.md file."""

    def test_append_creates_section(self):
        """Should create auto-distilled section if not present."""
        from src.observe.elf_distill import append_to_golden_rules

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Golden Rules\n\n## 1. Existing Rule\n> Some existing rule\n\n")
            f.flush()
            rules_path = Path(f.name)

        try:
            patterns = [MockPattern(
                pattern_text='New auto-distilled pattern',
                occurrence_count=5,
                session_ids=json.dumps(['s1', 's2']),
            )]

            count = append_to_golden_rules(patterns, rules_path)

            assert count == 1
            content = rules_path.read_text()
            assert 'Auto-Distilled Patterns' in content
            assert 'New auto-distilled pattern' in content
        finally:
            rules_path.unlink()

    def test_append_no_patterns(self):
        """Should handle empty pattern list."""
        from src.observe.elf_distill import append_to_golden_rules

        count = append_to_golden_rules([], None)
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

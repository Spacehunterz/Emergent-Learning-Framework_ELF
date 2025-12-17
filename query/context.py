"""
Context builder mixin - builds agent context from the knowledge base (async).
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

try:
    from query.models import Heuristic, Learning, get_manager
    from query.utils import AsyncTimeoutHandler
    from query.exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
    from query.config_loader import get_config, load_custom_golden_rules, get_always_load_categories
except ImportError:
    from models import Heuristic, Learning, get_manager
    from utils import AsyncTimeoutHandler
    from exceptions import TimeoutError, ValidationError, DatabaseError, QuerySystemError
    from config_loader import get_config, load_custom_golden_rules, get_always_load_categories

# MetaObserver is optional
META_OBSERVER_AVAILABLE = False
try:
    from meta_observer import MetaObserver
    META_OBSERVER_AVAILABLE = True
except ImportError:
    pass

# Plan-postmortem is optional
PLAN_POSTMORTEM_AVAILABLE = False
try:
    try:
        from query.plan_postmortem import (
            get_active_plans, get_recent_postmortems,
            format_plans_for_context, format_postmortems_for_context
        )
    except ImportError:
        from plan_postmortem import (
            get_active_plans, get_recent_postmortems,
            format_plans_for_context, format_postmortems_for_context
        )
    PLAN_POSTMORTEM_AVAILABLE = True
except ImportError:
    pass

# Project context support (optional)
PROJECT_CONTEXT_AVAILABLE = False
try:
    try:
        from query.project import detect_project_context, ProjectContext, format_project_status
    except ImportError:
        from project import detect_project_context, ProjectContext, format_project_status
    PROJECT_CONTEXT_AVAILABLE = True
except ImportError:
    pass


def get_depth_limits(depth: str) -> dict:
    """Get query limits based on depth level."""
    if depth == 'deep':
        return {
            'heuristics': 25,
            'learnings': 25,
            'decisions': 10,
            'invariants': 10,
            'assumptions': 10,
            'spikes': 10,
            'recent_context': 10,
            'summary_truncate': 200,  # More detail in summaries
        }
    elif depth == 'minimal':
        return {
            'heuristics': 0,
            'learnings': 0,
            'decisions': 0,
            'invariants': 0,
            'assumptions': 0,
            'spikes': 0,
            'recent_context': 0,
            'summary_truncate': 50,
        }
    else:  # standard
        return {
            'heuristics': 10,
            'learnings': 10,
            'decisions': 5,
            'invariants': 5,
            'assumptions': 5,
            'spikes': 5,
            'recent_context': 5,
            'summary_truncate': 100,
        }


class ContextBuilderMixin:
    """Mixin for building agent context from the knowledge base (async)."""

    async def build_context(
        self,
        task: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_tokens: int = 5000,
        timeout: int = None,
        depth: str = 'standard'
    ) -> str:
        """
        Build a context string for agents with tiered retrieval (async).

        Tier 1: Golden rules (always included)
        Tier 2: Domain-specific heuristics and tag-matched learnings
        Tier 3: Recent context if tokens remain

        Depth levels control how much context is loaded:
        - minimal: Golden rules only (~500 tokens) - for quick tasks
        - standard: + domain heuristics and learnings (default)
        - deep: + experiments, ADRs, all recent learnings (~5k tokens)

        Args:
            task: Description of the task for context
            domain: Optional domain to focus on
            tags: Optional tags to match
            max_tokens: Maximum tokens to use (approximate, based on ~4 chars/token)
            timeout: Query timeout in seconds (default: 30)
            depth: Context depth level ('minimal', 'standard', 'deep')

        Returns:
            Formatted context string for agent consumption

        Raises:
            ValidationError: If inputs are invalid
            TimeoutError: If query times out
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        result = None

        # Track counts for logging
        golden_rules_returned = 0
        heuristics_count = 0
        learnings_count = 0
        experiments_count = 0
        ceo_reviews_count = 0
        decisions_count = 0

        try:
            # Validate inputs
            task = self._validate_query(task)
            if domain:
                domain = self._validate_domain(domain)
            if tags:
                tags = self._validate_tags(tags)
            if max_tokens > self.MAX_TOKENS:
                max_tokens = self.MAX_TOKENS
            timeout = timeout or self.DEFAULT_TIMEOUT * 2  # Context building may take longer

            # Validate depth parameter
            if depth not in ('minimal', 'standard', 'deep'):
                depth = 'standard'

            # Get depth-aware limits
            limits = get_depth_limits(depth)

            self._log_debug(f"Building context (domain={domain}, tags={tags}, max_tokens={max_tokens}, depth={depth})")
            async with AsyncTimeoutHandler(timeout):
                context_parts = []
                approx_tokens = 0
                max_chars = max_tokens * 4  # Rough approximation

                # Tier 0: Project Context (if in an ELF-initialized project)
                project_ctx = None
                if PROJECT_CONTEXT_AVAILABLE:
                    try:
                        project_ctx = detect_project_context()
                        if project_ctx.has_project_context():
                            self._log_debug(f"Detected project: {project_ctx.project_name} at {project_ctx.elf_root}")

                            # Add project header
                            context_parts.append("# TIER 0: Project Context\n\n")
                            context_parts.append(f"**Project:** {project_ctx.project_name}\n")
                            context_parts.append(f"**Root:** {project_ctx.elf_root}\n")

                            if project_ctx.domains:
                                context_parts.append(f"**Domains:** {', '.join(project_ctx.domains)}\n")
                                # Use project domains if no explicit domain provided
                                if not domain and project_ctx.domains:
                                    domain = project_ctx.domains[0]
                                    self._log_debug(f"Using project domain: {domain}")

                            if project_ctx.inheritance_chain:
                                parents = [p.name for p in project_ctx.inheritance_chain]
                                context_parts.append(f"**Inherits from:** {' -> '.join(parents)}\n")

                            context_parts.append("\n")

                            # Load project context.md content
                            project_description = project_ctx.get_context_md_content()
                            if project_description:
                                context_parts.append("## Project Description\n\n")
                                if len(project_description) > 2000:
                                    project_description = project_description[:2000] + "\n...(truncated)"
                                context_parts.append(project_description)
                                context_parts.append("\n\n")
                                approx_tokens += len(project_description) // 4

                            context_parts.append("---\n\n")
                        else:
                            self._log_debug("No .elf/ found - global-only mode")
                    except Exception as e:
                        self._log_debug(f"Project context detection failed: {e}")

                # Tier 1: Golden Rules
                # For minimal depth, only load configured always_load_categories
                if depth == 'minimal':
                    always_cats = get_always_load_categories()
                    golden_rules = await self.get_golden_rules(categories=always_cats)
                    context_parts.append(f"# TIER 1: Golden Rules ({', '.join(always_cats)})\n")
                else:
                    golden_rules = await self.get_golden_rules()
                    context_parts.append("# TIER 1: Golden Rules\n")

                # Append custom golden rules if they exist
                custom_rules = load_custom_golden_rules()
                if custom_rules:
                    context_parts.append("\n# Custom Golden Rules\n")
                    context_parts.append(custom_rules)
                    context_parts.append("\n")

                context_parts.append(golden_rules)
                context_parts.append("\n")
                approx_tokens += len(golden_rules) // 4
                golden_rules_returned = 1  # Flag that golden rules were included

                # For minimal depth, return just core golden rules (~300 tokens)
                if depth == 'minimal':
                    building_header = "🏢 Building Status (minimal)\n━━━━━━━━━━━━━━━━━━\n\n"

                    # Add project location to header
                    if PROJECT_CONTEXT_AVAILABLE:
                        try:
                            project_ctx = detect_project_context()
                            project_info = format_project_status(project_ctx)
                            building_header += f"{project_info}\n\n"
                        except Exception:
                            pass

                    context_parts.insert(0, f"{building_header}# Task Context\n\n{task}\n\n---\n\n")
                    result = "".join(context_parts)
                    self._log_debug(f"Built minimal context with ~{len(result)//4} tokens")
                    return result

                # Check for similar failures (early warning system)
                similar_failures = await self.find_similar_failures(task)
                if similar_failures:
                    context_parts.append("\n## Similar Failures Detected\n\n")
                    for sf in similar_failures[:3]:  # Top 3 most similar
                        context_parts.append(f"- **[{sf['relevance_score']*100:.0f}% match] {sf['learning'].get('title', 'Unknown')}**\n")
                        if sf.get('matching_words'):
                            context_parts.append(f"  Matching keywords: {sf['matching_words']}\n")
                        summary = sf['learning'].get('summary', '')
                        if summary:
                            summary = summary[:100] + '...' if len(summary) > 100 else summary
                            context_parts.append(f"  Lesson: {summary}\n")
                        context_parts.append("\n")

                # Tier 2: Query-matched content
                context_parts.append("# TIER 2: Relevant Knowledge\n\n")

                if domain:
                    context_parts.append(f"## Domain: {domain}\n\n")
                    domain_data = await self.query_by_domain(domain, limit=limits['heuristics'], timeout=timeout)

                    if domain_data['heuristics']:
                        context_parts.append("### Heuristics:\n")
                        # Apply relevance scoring to heuristics
                        heuristics_with_scores = []
                        for h in domain_data['heuristics']:
                            h['_relevance'] = self._calculate_relevance_score(h, task, domain)
                            heuristics_with_scores.append(h)
                        heuristics_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                        for h in heuristics_with_scores:
                            entry = f"- **{h['rule']}** (confidence: {h['confidence']:.2f}, validated: {h['times_validated']}x)\n"
                            entry += f"  {h['explanation']}\n\n"
                            context_parts.append(entry)
                            approx_tokens += len(entry) // 4
                        heuristics_count += len(domain_data['heuristics'])

                    if domain_data['learnings']:
                        context_parts.append("### Recent Learnings:\n")
                        # Apply relevance scoring to learnings
                        learnings_with_scores = []
                        for l in domain_data['learnings']:
                            l['_relevance'] = self._calculate_relevance_score(l, task, domain)
                            learnings_with_scores.append(l)
                        learnings_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                        for l in learnings_with_scores:
                            entry = f"- **{l['title']}** ({l['type']})\n"
                            if l['summary']:
                                entry += f"  {l['summary']}\n"
                            entry += f"  Tags: {l['tags']}\n\n"
                            context_parts.append(entry)
                            approx_tokens += len(entry) // 4
                        learnings_count += len(domain_data['learnings'])


                # Add project-specific heuristics (if in project mode)
                if PROJECT_CONTEXT_AVAILABLE and project_ctx and project_ctx.has_project_context():
                    try:
                        import sqlite3
                        project_db = project_ctx.project_db_path
                        if project_db and project_db.exists():
                            conn = sqlite3.connect(str(project_db))
                            cursor = conn.cursor()

                            # Query project heuristics
                            cursor.execute("""
                                SELECT rule, explanation, domain, confidence, validation_count
                                FROM heuristics
                                ORDER BY confidence DESC, validation_count DESC
                                LIMIT ?
                            """, (limits['heuristics'],))
                            project_heuristics = cursor.fetchall()

                            if project_heuristics:
                                context_parts.append("\n## Project-Specific Heuristics\n\n")
                                for h in project_heuristics:
                                    rule, explanation, h_domain, confidence, val_count = h
                                    entry = f"- **{rule}** (confidence: {confidence:.2f}"
                                    if val_count:
                                        entry += f", validated: {val_count}x"
                                    entry += ")\n"
                                    if explanation:
                                        expl = explanation[:100] + '...' if len(explanation) > 100 else explanation
                                        entry += f"  {expl}\n"
                                    entry += "\n"
                                    context_parts.append(entry)
                                    approx_tokens += len(entry) // 4
                                heuristics_count += len(project_heuristics)

                            # Query project learnings
                            cursor.execute("""
                                SELECT type, summary, details, domain
                                FROM learnings
                                ORDER BY created_at DESC
                                LIMIT ?
                            """, (limits['learnings'],))
                            project_learnings = cursor.fetchall()

                            if project_learnings:
                                context_parts.append("\n## Project-Specific Learnings\n\n")
                                for l in project_learnings:
                                    l_type, summary, details, l_domain = l
                                    entry = f"- **{summary}** ({l_type})\n"
                                    if details:
                                        det = details[:100] + '...' if len(details) > 100 else details
                                        entry += f"  {det}\n"
                                    entry += "\n"
                                    context_parts.append(entry)
                                    approx_tokens += len(entry) // 4
                                learnings_count += len(project_learnings)

                            conn.close()
                    except Exception as e:
                        self._log_debug(f"Failed to load project-specific content: {e}")

                else:
                    # No domain specified - show recent heuristics across all domains
                    try:
                        m = get_manager()
                        async with m:
                            async with m.connection():
                                # Get recent non-golden heuristics (golden are in TIER 1)
                                recent_heuristics_query = (Heuristic
                                    .select()
                                    .where((Heuristic.is_golden == False) | (Heuristic.is_golden.is_null()))
                                    .order_by(Heuristic.created_at.desc(), Heuristic.confidence.desc())
                                    .limit(limits['heuristics']))

                                recent_heuristics = []
                                async for h in recent_heuristics_query:
                                    recent_heuristics.append({
                                        'rule': h.rule,
                                        'domain': h.domain,
                                        'confidence': h.confidence,
                                        'explanation': h.explanation
                                    })

                                if recent_heuristics:
                                    context_parts.append("## Recent Heuristics (all domains)\n\n")
                                    for h in recent_heuristics:
                                        h_domain = h.get('domain', 'general')
                                        entry = f"- **{h['rule']}** (domain: {h_domain}, confidence: {h['confidence']:.2f})\n"
                                        if h.get('explanation'):
                                            expl = h['explanation'][:100] + '...' if len(h['explanation']) > 100 else h['explanation']
                                            entry += f"  {expl}\n"
                                        entry += "\n"
                                        context_parts.append(entry)
                                        approx_tokens += len(entry) // 4
                                    heuristics_count += len(recent_heuristics)

                                # Get recent learnings across all domains
                                recent_learnings_query = (Learning
                                    .select()
                                    .order_by(Learning.created_at.desc())
                                    .limit(limits['learnings']))

                                recent_learnings = []
                                async for l in recent_learnings_query:
                                    recent_learnings.append({
                                        'title': l.title,
                                        'type': l.type,
                                        'domain': l.domain,
                                        'summary': l.summary
                                    })

                                if recent_learnings:
                                    context_parts.append("## Recent Learnings (all domains)\n\n")
                                    for l in recent_learnings:
                                        l_domain = l.get('domain', 'general')
                                        entry = f"- **{l['title']}** ({l['type']}, domain: {l_domain})\n"
                                        if l.get('summary'):
                                            summary = l['summary'][:100] + '...' if len(l['summary']) > 100 else l['summary']
                                            entry += f"  {summary}\n"
                                        entry += "\n"
                                        context_parts.append(entry)
                                        approx_tokens += len(entry) // 4
                                    learnings_count += len(recent_learnings)

                    except Exception as e:
                        self._log_debug(f"Failed to fetch recent heuristics/learnings: {e}")

                if tags:
                    context_parts.append(f"## Tag Matches: {', '.join(tags)}\n\n")
                    tag_results = await self.query_by_tags(tags, limit=limits['learnings'], timeout=timeout)

                    # Apply relevance scoring to tag results
                    tag_results_with_scores = []
                    for l in tag_results:
                        l['_relevance'] = self._calculate_relevance_score(l, task, domain)
                        tag_results_with_scores.append(l)
                    tag_results_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                    for l in tag_results_with_scores:
                        entry = f"- **{l['title']}** ({l['type']}, domain: {l['domain']})\n"
                        if l['summary']:
                            entry += f"  {l['summary']}\n"
                        entry += f"  Tags: {l['tags']}\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4
                    learnings_count += len(tag_results)

                # Add decisions (ADRs) in Tier 2
                decisions = await self.get_decisions(domain=domain, status='accepted', limit=limits['decisions'], timeout=timeout)
                if decisions:
                    context_parts.append("\n## Decisions (ADRs)\n\n")
                    for dec in decisions:
                        entry = f"- **{dec['title']}**"
                        if dec.get('domain'):
                            entry += f" (domain: {dec['domain']})"
                        entry += "\n"
                        if dec.get('decision'):
                            decision_text = dec['decision'][:150] + '...' if len(dec['decision']) > 150 else dec['decision']
                            entry += f"  Decision: {decision_text}\n"
                        if dec.get('rationale'):
                            rationale_text = dec['rationale'][:150] + '...' if len(dec['rationale']) > 150 else dec['rationale']
                            entry += f"  Rationale: {rationale_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4
                    decisions_count = len(decisions)

                # Add active plans and recent postmortems (plan-postmortem learning)
                if PLAN_POSTMORTEM_AVAILABLE:
                    try:
                        active_plans = get_active_plans(domain=domain, limit=3)
                        if active_plans:
                            plans_output = format_plans_for_context(active_plans)
                            context_parts.append("\n" + plans_output)
                            approx_tokens += len(plans_output) // 4
                        recent_postmortems = get_recent_postmortems(domain=domain, limit=3)
                        if recent_postmortems:
                            postmortems_output = format_postmortems_for_context(recent_postmortems)
                            context_parts.append("\n" + postmortems_output)
                            approx_tokens += len(postmortems_output) // 4
                    except Exception as e:
                        self._log_debug(f"Failed to fetch plans/postmortems: {e}")

                # Add invariants (what must always be true)
                invariants = await self.get_invariants(domain=domain, status='active', limit=limits['invariants'], timeout=timeout)
                violated_invariants = await self.get_invariants(domain=domain, status='violated', limit=limits['invariants'] // 2 + 1, timeout=timeout)

                if violated_invariants:
                    context_parts.append("\n## VIOLATED INVARIANTS\n\n")
                    for inv in violated_invariants:
                        entry = f"- **[VIOLATED {inv.get('violation_count', 0)}x] {inv['statement'][:100]}{'...' if len(inv['statement']) > 100 else ''}**\n"
                        entry += f"  Severity: {inv['severity']} | Scope: {inv['scope']}\n"
                        if inv.get('rationale'):
                            rationale_text = inv['rationale'][:100] + '...' if len(inv['rationale']) > 100 else inv['rationale']
                            entry += f"  Rationale: {rationale_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                if invariants:
                    context_parts.append("\n## Active Invariants\n\n")
                    for inv in invariants:
                        entry = f"- **{inv['statement'][:100]}{'...' if len(inv['statement']) > 100 else ''}**"
                        if inv.get('domain'):
                            entry += f" (domain: {inv['domain']})"
                        entry += f"\n  Severity: {inv['severity']} | Scope: {inv['scope']}"
                        if inv.get('validation_type'):
                            entry += f" | Validation: {inv['validation_type']}"
                        entry += "\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Add high-confidence active assumptions
                assumptions = await self.get_assumptions(domain=domain, status='active', min_confidence=0.6, limit=limits['assumptions'], timeout=timeout)
                if assumptions:
                    context_parts.append("\n## Active Assumptions (High Confidence)\n\n")
                    for assum in assumptions:
                        entry = f"- **{assum['assumption'][:100]}{'...' if len(assum['assumption']) > 100 else ''}**"
                        entry += f" (confidence: {assum['confidence']:.0%}"
                        if assum['verified_count'] > 0:
                            entry += f", verified: {assum['verified_count']}x"
                        entry += ")\n"
                        if assum.get('context'):
                            context_text = assum['context'][:100] + '...' if len(assum['context']) > 100 else assum['context']
                            entry += f"  Context: {context_text}\n"
                        if assum.get('source'):
                            entry += f"  Source: {assum['source']}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Show challenged/invalidated assumptions as warnings
                challenged = await self.get_challenged_assumptions(domain=domain, limit=limits['assumptions'] // 2 + 1, timeout=timeout)
                if challenged:
                    context_parts.append("\n## Challenged/Invalidated Assumptions\n\n")
                    for assum in challenged:
                        status_emoji = "INVALIDATED" if assum['status'] == 'invalidated' else "CHALLENGED"
                        entry = f"- **[{status_emoji}] {assum['assumption'][:80]}{'...' if len(assum['assumption']) > 80 else ''}**\n"
                        entry += f"  Challenged {assum['challenged_count']}x"
                        if assum['verified_count'] > 0:
                            entry += f", verified {assum['verified_count']}x"
                        entry += f" | Confidence: {assum['confidence']:.0%}\n"
                        if assum.get('context'):
                            context_text = assum['context'][:80] + '...' if len(assum['context']) > 80 else assum['context']
                            entry += f"  Original context: {context_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4


                # Add relevant spike reports (hard-won research knowledge)
                spike_reports = await self.get_spike_reports(domain=domain, limit=limits['spikes'], timeout=timeout)
                if spike_reports:
                    context_parts.append("\n## Spike Reports (Research Knowledge)\n\n")
                    for spike in spike_reports:
                        entry = f"- **{spike['title']}**"
                        if spike.get('time_invested_minutes'):
                            entry += f" ({spike['time_invested_minutes']} min invested)"
                        entry += "\n"
                        if spike.get('topic'):
                            entry += f"  Topic: {spike['topic'][:100]}{'...' if len(spike['topic']) > 100 else ''}\n"
                        if spike.get('findings'):
                            findings_text = spike['findings'][:200] + '...' if len(spike['findings']) > 200 else spike['findings']
                            entry += f"  Findings: {findings_text}\n"
                        if spike.get('gotchas'):
                            gotchas_text = spike['gotchas'][:100] + '...' if len(spike['gotchas']) > 100 else spike['gotchas']
                            entry += f"  Gotchas: {gotchas_text}\n"
                        if spike.get('usefulness_score') and spike['usefulness_score'] > 0:
                            entry += f"  Usefulness: {spike['usefulness_score']:.1f}/5\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Tier 3: Recent context if tokens remain
                remaining_tokens = max_tokens - approx_tokens
                if remaining_tokens > 500:
                    context_parts.append("# TIER 3: Recent Context\n\n")
                    recent = await self.query_recent(limit=3, timeout=timeout)

                    for l in recent:
                        entry = f"- **{l['title']}** ({l['type']}, {l['created_at']})\n"
                        if l['summary']:
                            entry += f"  {l['summary']}\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                        if approx_tokens >= max_tokens:
                            break
                    learnings_count += len(recent)

                # Add active experiments
                experiments = await self.get_active_experiments(timeout=timeout)
                if experiments:
                    context_parts.append("\n# Active Experiments\n\n")
                    for exp in experiments:
                        entry = f"- **{exp['name']}** ({exp['cycles_run']} cycles)\n"
                        if exp['hypothesis']:
                            entry += f"  Hypothesis: {exp['hypothesis']}\n\n"
                        context_parts.append(entry)
                    experiments_count = len(experiments)

                # Add pending CEO reviews
                ceo_reviews = await self.get_pending_ceo_reviews(timeout=timeout)
                if ceo_reviews:
                    context_parts.append("\n# Pending CEO Reviews\n\n")
                    for review in ceo_reviews:
                        entry = f"- **{review['title']}**\n"
                        if review['context']:
                            entry += f"  Context: {review['context']}\n"
                        if review['recommendation']:
                            entry += f"  Recommendation: {review['recommendation']}\n\n"
                        context_parts.append(entry)
                    ceo_reviews_count = len(ceo_reviews)

                # Task context with building header (show depth level)
                depth_label = f" ({depth})" if depth != 'standard' else ""
                building_header = f"🏢 Building Status{depth_label}\n━━━━━━━━━━━━━━━━━━\n\n"
                
                # Add project location to header
                if PROJECT_CONTEXT_AVAILABLE:
                    try:
                        project_ctx = detect_project_context()
                        project_info = format_project_status(project_ctx)
                        building_header += f"{project_info}\n\n"
                    except Exception:
                        pass

                context_parts.insert(0, f"{building_header}# Task Context\n\n{task}\n\n---\n\n")

            result = "".join(context_parts)
            self._log_debug(f"Built context with ~{len(result)//4} tokens")
            return result

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            tokens_approx = len(result) // 4 if result else 0
            total_results = heuristics_count + learnings_count + experiments_count + ceo_reviews_count + decisions_count

            await self._log_query(
                query_type='build_context',
                domain=domain,
                tags=','.join(tags) if tags else None,
                max_tokens_requested=max_tokens,
                results_returned=total_results,
                tokens_approximated=tokens_approx,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                golden_rules_returned=golden_rules_returned,
                heuristics_count=heuristics_count,
                learnings_count=learnings_count,
                experiments_count=experiments_count,
                ceo_reviews_count=ceo_reviews_count,
                query_summary=f"Context build for task: {task[:50]}..."
            )

            # Record system metrics for monitoring (non-blocking)
            await self._record_system_metrics(domain=domain)

    async def _record_system_metrics(self, domain: Optional[str] = None):
        """
        Record system health metrics via MetaObserver (async).

        Called after each query to track:
        - avg_confidence: Average confidence of active heuristics
        - validation_velocity: Validations in last 24 hours
        - contradiction_rate: Contradictions / total applications
        - query_count: Incremented on each query

        This is non-blocking - errors are logged but don't propagate.
        """
        if not META_OBSERVER_AVAILABLE:
            return

        try:
            observer = MetaObserver(db_path=self.db_path)

            # Calculate avg confidence using async queries
            m = get_manager()
            async with m:
                async with m.connection():
                    total_confidence = 0.0
                    heuristic_count = 0
                    async for h in Heuristic.select():
                        if domain is None or h.domain == domain:
                            total_confidence += h.confidence or 0.5
                            heuristic_count += 1

                    avg_conf = total_confidence / heuristic_count if heuristic_count > 0 else 0.5

                    if heuristic_count > 0:
                        observer.record_metric('avg_confidence', avg_conf, domain=domain,
                                              metadata={'heuristic_count': heuristic_count})

                    # Validation velocity - sum of times_validated
                    validation_count = 0
                    async for h in Heuristic.select():
                        if domain is None or h.domain == domain:
                            validation_count += h.times_validated or 0
                    observer.record_metric('validation_velocity', validation_count, domain=domain)

                    # Violation rate
                    total_violations = 0
                    total_applications = 0
                    async for h in Heuristic.select():
                        total_violations += h.times_violated or 0
                        total_applications += (h.times_validated or 0) + (h.times_violated or 0)

                    if total_applications > 0:
                        violation_rate = total_violations / total_applications
                        observer.record_metric('violation_rate', violation_rate, domain=domain)

                    # Query count (simple increment)
                    observer.record_metric('query_count', 1, domain=domain)

            self._log_debug("Recorded system metrics to meta_observer")

        except Exception as e:
            # Non-blocking: log the error but don't raise
            self._log_debug(f"Failed to record system metrics: {e}")

    def _check_system_alerts(self) -> list:
        """
        Check for system alerts via MetaObserver.

        Returns list of active alerts, or empty list if unavailable.
        This is non-blocking.
        """
        if not META_OBSERVER_AVAILABLE:
            return []

        try:
            observer = MetaObserver(db_path=self.db_path)
            return observer.check_alerts()
        except Exception as e:
            self._log_debug(f"Failed to check system alerts: {e}")
            return []

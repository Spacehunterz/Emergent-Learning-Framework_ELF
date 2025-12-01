# Heuristics: game-development

Generated from database recovery on 2025-12-01.

---

## H-11: Refactor God Objects before scaling

**Confidence**: 0.85
**Source**: observation

Game.ts at 496 lines with 8+ responsibilities is a God Object antipattern. Extract managers (UIManager, StateManager, CollisionManager) BEFORE adding features. Adding features to a God Object compounds technical debt exponentially.

---

## H-12: Add visual feedback for all player actions

**Confidence**: 0.85
**Source**: success

Every player action should have immediate visual/audio feedback. Barrel roll without particles felt incomplete; adding cyan trail made it satisfying. This is the juice principle - mechanics need sensory payoff.

---

## H-10: Fix build blockers before adding features

**Confidence**: 0.8
**Source**: observation

When analyzing a game project, always check if the build passes first. TypeScript strictness settings (erasableSyntaxOnly, noUnusedLocals) can silently break builds. Fix compilation errors before any feature work - a broken build blocks all progress.

---


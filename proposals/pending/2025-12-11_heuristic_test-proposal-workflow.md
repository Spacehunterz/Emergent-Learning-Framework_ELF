---
type: heuristic
domain: testing
confidence: 0.8
tags: proposals, testing, workflow
source: observation
submitted_by: claude-agent
submitted_at: 2025-12-11 23:50:00
---

# Test Proposal - Always Validate Workflow

## Summary

Before deploying any new workflow system, create a test proposal to verify the entire pipeline works correctly.

## Details

This is a test proposal created to validate the proposals directory structure and approval workflow. It tests:

1. Proposal creation with proper frontmatter
2. list-proposals.sh output
3. review-proposal.sh approve/reject functionality
4. integrate-proposal.py database integration

## Evidence

- Created as part of ELF proposals system implementation
- Date: 2025-12-11

## Recommendation

If approved, this should create a new heuristic in the testing domain with confidence 0.8.

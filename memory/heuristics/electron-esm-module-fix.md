# Electron ESM Module Conflict Fix

## Heuristic
When using Electron with `"type": "module"` in package.json, rename Electron's main entry file from `.js` to `.cjs` extension to avoid module format conflicts.

## Context
- Electron's main process uses CommonJS (require/module.exports)
- Vite/modern projects use `"type": "module"` for ES modules
- Node.js interprets all `.js` files based on package.json type field
- This causes "ERR_REQUIRE_ESM" or similar errors at runtime

## Solution
1. Rename `electron/main.js` → `electron/main.cjs`
2. Update package.json `"main"` field to point to `.cjs` file
3. Rebuild with electron-builder

## Confidence
0.8

## Domain
electron, packaging, javascript-modules

## Recorded
2025-12-02

## Source
Spaceshooter game packaging - user tested, error occurred, fix validated

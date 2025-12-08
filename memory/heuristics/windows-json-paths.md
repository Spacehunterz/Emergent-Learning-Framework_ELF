# Heuristic: Windows Paths in JSON Require Forward Slashes

## Pattern
When Windows paths appear in JSON config files (like `~/.claude/mcp.json`), they must use forward slashes (`/`) instead of backslashes (`\`).

## Why
Backslashes in JSON are escape characters. `C:\Users` becomes invalid because `\U` is interpreted as a unicode escape sequence. The JSON parser will fail silently or with cryptic errors.

## Detection
- MCP servers configured but tools not appearing
- `json.decoder.JSONDecodeError: Invalid \escape`
- Python/Node failing to parse config files

## Fix
Replace `C:\Users\Evede\...` with `C:/Users/Evede/...`

Or double-escape: `C:\Users\Evede\...`

## Confidence
0.9 (validated today - claudex-mcp was configured but not loading due to this exact issue)

## Domain
windows, json, mcp, configuration

## Date
2025-12-06

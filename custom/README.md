# Custom Configuration Layer

This directory contains your personal customizations that **survive framework updates**.

Files here are:
- Gitignored (won't be overwritten when you `git pull`)
- Merged with defaults at runtime
- Yours to modify freely

## Directory Structure

```
custom/
├── README.md           # This file
├── config.yaml         # Your preferences (overrides defaults)
├── golden-rules.md     # Your additional golden rules
├── parties.yaml        # Your custom party definitions
└── agents/             # Custom agent personalities
    └── my-agent/
        └── personality.md
```

## How It Works

1. **ELF loads defaults** from the main directories
2. **ELF loads custom** from this directory
3. **Custom overrides/extends defaults** (merge, not replace)

## config.yaml

Override system defaults:

```yaml
# Your personal preferences
preferences:
  default_depth: standard      # minimal | standard | deep
  default_format: text         # text | json | csv
  default_timeout: 30          # seconds

# Query behavior
query:
  max_results: 20              # default limit for queries
  include_challenged: true     # show challenged assumptions

# Categories to always load (even in minimal depth)
always_load_categories:
  - core
  - git                        # add your critical categories

# Your domains (for better suggestions)
my_domains:
  - react
  - typescript
  - api-design
```

## golden-rules.md

Add your own golden rules (same format as main file):

```markdown
## C1. My Custom Rule
> Always do X before Y.

**Category:** my-category
**Why:** Because reasons.
**Promoted:** 2025-01-01 (personal rule)
**Validations:** N/A
```

These are loaded IN ADDITION to the main golden rules.
Use "C" prefix (C1, C2, etc.) to distinguish from main rules.

## parties.yaml

Add custom party definitions:

```yaml
parties:
  my-review:
    description: "My custom review process"
    lead: skeptic
    agents:
      - researcher
      - skeptic
    workflow: sequential
    triggers:
      - "my review"
```

## agents/

Create custom agents or override existing ones:

```
custom/agents/my-specialist/personality.md
```

Format matches main agent files. Custom agents are available alongside defaults.

## Tips

1. **Start small** - Only customize what you need
2. **Use categories** - Tag your rules for filtering
3. **Version your customs** - Consider backing up this folder separately
4. **Share carefully** - These are YOUR preferences, may not suit others

## Resetting

To reset to defaults, simply delete files from this directory.
The framework will use defaults for anything not customized.

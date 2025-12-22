# Load Building Context

Query the Emergent Learning Framework for institutional knowledge.

## Steps

1. Run the query system to load context:
   ```bash
   python ~/.claude/emergent-learning/query/query.py --context
   ```

2. Summarize for the user:
   - Active golden rules count
   - Relevant heuristics for current work
   - Any pending CEO decisions
   - Active experiments

3. If there are pending CEO decisions, list them and ask if the user wants to address them.

4. If there are active experiments, briefly note their status.

## Domain-Specific Queries

If the user includes a domain (e.g., "/building architecture"), also run:
```bash
python ~/.claude/emergent-learning/query/query.py --domain [domain]
```

## Available Domains
- coordination
- architecture
- debugging
- communication
- other

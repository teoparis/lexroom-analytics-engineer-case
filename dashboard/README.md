# Decision cockpit

The Streamlit app reads only the three dbt marts in `lexroom.duckdb`. It does not load seeds or repeat business metric formulas in Python. The UI keeps the snapshot cutoff, feedback evidence and the boundary of the operational quality proxy visible beside the decision views.

From the repository root:

```bash
make build
make dashboard
```

# Verification of the supplied version

Executed in Python 3.12.14 on Linux. All four pipelines ran successfully and all three tests for this repository passed. The notebook code cells were syntax-checked; the notebooks are supplied without saved execution outputs. SQL queries were executed against their generated SQLite databases. Result charts were visually reviewed.

Verified package versions:

- numpy 2.3.5
- pandas 2.2.3
- scipy 1.17.0
- scikit-learn 1.8.0
- matplotlib 3.10.8

`requirements-verified.txt` records direct dependency versions used here; it is not a lockfile for every transitive dependency. Use `pip install -r requirements-verified.txt` to reproduce the direct environment. Exact bitwise results can still vary by platform or dependency implementation. Dependencies were available in the supplied execution environment; clean pip installation and remote GitHub Actions have not been tested here.

These checks verify the code and selected methodological invariants, not real-world causal validity or commercial performance.

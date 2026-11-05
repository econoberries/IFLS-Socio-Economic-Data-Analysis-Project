# RAPSEM synthetic checks

From the directory containing `IFLS_Project.Rproj`, run:

```bash
python -m pip install -r 02_scripts/20_rapsem_blt2005/requirements.txt
python -m pytest -q tests/test_rapsem_common.py tests/test_rapsem_pipeline_simulated.py
```

These tests use synthetic tables and a mocked Stata reader. They do not validate real IFLS variable codes, poverty-line definitions, historical BLT household attribution, or the RAPSEM causal estimator.

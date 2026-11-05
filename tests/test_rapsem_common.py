"""Small deterministic RAPSEM study checks; no IFLS records needed."""
import importlib.util
from pathlib import Path
import pandas as pd

HERE=Path(__file__).parents[1]/'02_scripts'/'20_rapsem_blt2005'/'common.py'
spec=importlib.util.spec_from_file_location('rapsem_common',HERE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_identifier_normalization():
    assert mod.txt(' 00123 ')=='00123'
    assert mod.txt(3.0)=='3'
    assert mod.txt(float('nan')) is None

def test_reject_duplicate_linkage():
    x=pd.DataFrame({'pidlink':['00001','00001']})
    try:mod.assert_unique(x,'pidlink','test')
    except ValueError:return
    raise AssertionError('Duplicate current member identifiers must fail.')

def test_normalize_keeps_leading_zeros():
    assert list(mod.normalized(pd.Series(['001',' 002 '])))==['001','002']

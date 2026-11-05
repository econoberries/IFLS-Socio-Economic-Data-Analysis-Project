"""Synthetic end-to-end RAPSEM data preparation tests; no real IFLS records."""
import json
import shutil
import sys
import types
import runpy
from pathlib import Path
import pandas as pd

def test_build_panel_synthetic(tmp_path,monkeypatch):
    root=tmp_path/'project'
    root.mkdir()
    (root/'IFLS_Project.Rproj').write_text('Version: 1.0\n')
    (root/'01_data').mkdir()
    sdir=root/'02_scripts'/'20_rapsem_blt2005'
    src=Path(__file__).parents[1]/'02_scripts'/'20_rapsem_blt2005'
    shutil.copytree(src,sdir,ignore=shutil.ignore_patterns('__pycache__'))
    tables={
        ('ifls3','bk_ar1'):pd.DataFrame({'pidlink':['001','002','003'],'hhid00':['H0','H0','H1'],'ar01a':[1,1,3],'ar09':[34,29,30],'ar07':[1,3,1]}),
        ('ifls4','bk_ar1'):pd.DataFrame({'pidlink':['001','002'],'hhid07':['H7','H7'],'ar01a':[1,1],'ar09':[41,36]}),
        ('ifls5','bk_ar1'):pd.DataFrame({'pidlink':['001','002'],'hhid14':['H14','H14'],'ar01a':[1,1],'ar09':[48,43]}),
        ('ifls4','b1_ksr1'):pd.DataFrame({'hhid07':['H7'],'ksr3type':['A'],'ksr17':[1],'ksr18y':[2005]}),
        ('ifls4','b3b_kp'):pd.DataFrame([{'pidlink':p,'kptype':letter,'kp02':(j%4)+1} for p in ['001','002'] for j,letter in enumerate('ABCDEFGHIJ')]),
    }
    for (wave,stem),df in tables.items():
        folder=root/'01_data'/'01_raw_dta'/wave/'household'
        folder.mkdir(parents=True,exist_ok=True)
        (folder/(stem+'.dta')).touch()
    welfare=root/'01_data'/'04_intermediate'/'rapsem_blt2005'
    welfare.mkdir(parents=True)
    pd.DataFrame([
        {'wave':'ifls3','hhid':'H0','monthly_pce':50,'monthly_poverty_line':100},
        {'wave':'ifls5','hhid':'H14','monthly_pce':130,'monthly_poverty_line':100},
    ]).to_csv(welfare/'household_welfare_harmonized.csv',index=False)
    cfg=json.loads((sdir/'study_config.example.json').read_text())
    for wave in ('ifls3','ifls4','ifls5'):
        cfg['rosters'][wave]['approved']=True
        cfg['rosters'][wave]['current_codes']=['1']
    cfg['treatment'].update(approved=True,exposure_assignment_verified=True,
       program_selector_column='ksr3type',program_selector_codes=['A'],
       receipt_column='ksr17',treated_codes=['1'],untreated_codes=['3'],
       receipt_year_column='ksr18y',receipt_year_codes=['2005'])
    cfg['mediator']['approved']=True
    cfg['mediator']['item_code_map']={k:k for k in 'ABCDEFGHIJ'}
    cfg['mediator']['valid_response_codes']=['1','2','3','4']
    cfg['welfare']['approved']=True
    cfg['baseline_covariates']=[{'approved':True,'name':'sex_2000_raw',
     'file':'bk_ar1','level':'person','key':'pidlink','variable':'ar07', 'aggregation':'none'}]
    (sdir/'study_config.json').write_text(json.dumps(cfg))

    fake=types.ModuleType('pyreadstat')
    def fake_read_dta(path,**kwargs):
        p=Path(path); wave=next(x for x in ('ifls3','ifls4','ifls5') if x in p.parts)
        return tables[(wave,p.stem)].copy(),types.SimpleNamespace()
    fake.read_dta=fake_read_dta
    monkeypatch.setitem(sys.modules,'pyreadstat',fake)
    monkeypatch.syspath_prepend(str(sdir))
    monkeypatch.delitem(sys.modules,'common',raising=False)
    monkeypatch.chdir(root)
    runpy.run_path(str(sdir/'04_build_panel.py'),run_name='__main__')
    panel=pd.read_csv(welfare/'person_panel_full.csv',dtype='string')
    assert len(panel)==2
    assert set(panel['pidlink'])=={'001','002'}
    assert set(panel['blt_2005'])=={'1'}
    assert set(panel['poverty_exit_2014'])=={'1'}
    assert set(panel['cesd_observed_items'])=={'10'}
    assert (welfare/'cesd_items_2007.csv').is_file()
    assert (root/'01_data'/'05_analysis'/'rapsem_blt2005'/'baseline_poor_analysis_panel.csv').is_file()
    runpy.run_path(str(sdir/'05_quality_report.py'),run_name='__main__')
    report=root/'05_outputs'/'tables'/'rapsem_blt2005'/'05_variable_completeness.csv'
    assert report.is_file()

def test_welfare_builder_synthetic(tmp_path,monkeypatch):
    root=tmp_path/'project';root.mkdir();(root/'IFLS_Project.Rproj').touch();(root/'01_data').mkdir()
    sdir=root/'02_scripts'/'20_rapsem_blt2005'
    src=Path(__file__).parents[1]/'02_scripts'/'20_rapsem_blt2005'
    shutil.copytree(src,sdir,ignore=shutil.ignore_patterns('__pycache__'))
    tables={}
    for wave,hh in [('ifls3','hhid00'),('ifls5','hhid14')]:
        tables[(wave,'bk_ar1')]=pd.DataFrame({'pidlink':['001','002'],hh:['H'+wave[-1]]*2,'ar01a':[1,1]})
        for stem,amt in [('b1_ks1',50),('b1_ks2',40),('b1_ks3',120)]:
            tables[(wave,stem)]=pd.DataFrame({hh:['H'+wave[-1]],'item':['A'],'amount':[amt]})
        for stem in ['bk_ar1','b1_ks1','b1_ks2','b1_ks3']:
            folder=root/'01_data'/'01_raw_dta'/wave/'household';folder.mkdir(parents=True,exist_ok=True)
            (folder/(stem+'.dta')).touch()
    cfg=json.loads((sdir/'study_config.example.json').read_text())
    for wave in ('ifls3','ifls5'):
        cfg['rosters'][wave]['approved']=True
        cfg['rosters'][wave]['current_codes']=['1']
    (sdir/'study_config.json').write_text(json.dumps(cfg))
    basket=json.loads((sdir/'welfare_basket.example.json').read_text())
    basket['approved']=True
    for wave in ('ifls3','ifls5'):
        basket[f'basket_complete_{wave}']=True
        for comp in basket['components'][wave]:
            comp['all_rows_approved']=True
            comp['amount_columns']=['amount']
            comp['item_column']='item'
    (sdir/'welfare_basket.json').write_text(json.dumps(basket))
    folder=root/'01_data'/'04_intermediate'/'rapsem_blt2005';folder.mkdir(parents=True)
    pd.DataFrame([{'wave':wave,'hhid':'H'+wave[-1],'monthly_poverty_line':50} for wave in ('ifls3','ifls5')]).to_csv(folder/'poverty_lines_household.csv',index=False)
    fake=types.ModuleType('pyreadstat')
    def fake_read_dta(path,**kwargs):
        p=Path(path);wave=next(x for x in ('ifls3','ifls5') if x in p.parts)
        return tables[(wave,p.stem)].copy(),types.SimpleNamespace()
    fake.read_dta=fake_read_dta
    monkeypatch.setitem(sys.modules,'pyreadstat',fake)
    monkeypatch.syspath_prepend(str(sdir));monkeypatch.delitem(sys.modules,'common',raising=False);monkeypatch.chdir(root)
    runpy.run_path(str(sdir/'03_build_welfare.py'),run_name='__main__')
    d=pd.read_csv(folder/'household_welfare_harmonized.csv')
    assert len(d)==2
    assert d['monthly_pce'].between(133,134).all()
    assert d['poor'].eq(0).all()

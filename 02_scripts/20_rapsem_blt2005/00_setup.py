"""Create *missing* folders. Never moves, copies or overwrites source data."""
from common import project_root, REQUIRED, STUDY

root=project_root()
for wave in REQUIRED:
    for part in ('household','community'):
        (root/'01_data'/'01_raw_dta'/wave/part).mkdir(parents=True,exist_ok=True)
        (root/'00_documentation'/wave/'codebooks').mkdir(parents=True,exist_ok=True)
        (root/'00_documentation'/wave/'questionnaires').mkdir(parents=True,exist_ok=True)
        (root/'00_documentation'/wave/'user_guides').mkdir(parents=True,exist_ok=True)
for path in [root/'01_data'/'04_intermediate'/STUDY,
             root/'01_data'/'05_analysis'/STUDY,
             root/'05_outputs'/'tables'/STUDY,
             root/'00_documentation'/'general']:
    path.mkdir(parents=True,exist_ok=True)
print('Created missing folders only. Existing IFLS files are unchanged.')
print('Project root:',root)
print('Next: copy/extract IFLS3, IFLS4, IFLS5 household .dta files into their own wave folders.')

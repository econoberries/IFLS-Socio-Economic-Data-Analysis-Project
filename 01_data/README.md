# Local data

Run `source("02_scripts/00_setup_folders.R")` from the project root to create
all survey and component folders.

| Folder | Content |
| --- | --- |
| `01_raw_dta` | Extracted original Stata datasets; never overwrite or clean them |
| `02_raw_csv` | Generated CSV copies; treat them as read-only |
| `03_metadata` | Generated labels, imported types, missing tags, source checksums |
| `04_intermediate` | Later derived data between construction steps |
| `05_analysis` | Later final datasets ready for estimation |

Dataset files and generated metadata are excluded from Git. Keep a separate backup.

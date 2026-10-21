# Run order

Open `IFLS_Project.Rproj` and run these from the RStudio Console:

```r
source("02_scripts/00_setup_folders.R")
source("02_scripts/01_install_packages.R")
# Copy your extracted .dta datasets into 01_data/01_raw_dta before the next line.
source("02_scripts/02_convert_all_dta_to_csv.R")
```

`02a_convert_one_dta.R` is the helper loaded automatically by step 2.
`checks/check_conversion.R` is an optional synthetic converter check.
These scripts do not clear your R environment or change your working directory.

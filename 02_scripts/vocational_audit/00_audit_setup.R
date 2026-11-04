# 00 — Setup. Run from the IFLS project in RStudio.
project_folder <- "/Users/khaira_abdillah/Documents/IFLS_Causal_Project"
raw_csv_folder <- file.path(project_folder, "01_data", "02_raw_csv")
audit_folder <- file.path(project_folder, "01_data", "04_processed", "vocational_audit")
report_folder <- file.path(project_folder, "03_reports", "vocational_audit")

if (!dir.exists(raw_csv_folder)) stop("Raw CSV folder missing: ", raw_csv_folder)
dir.create(audit_folder, recursive = TRUE, showWarnings = FALSE)
dir.create(report_folder, recursive = TRUE, showWarnings = FALSE)

# Configure these after examining 01_inventory_files.csv.
# Use paths RELATIVE to 01_data/02_raw_csv (not absolute paths).
roster4_file <- NA_character_
roster5_file <- NA_character_

# Set to a verified identifier only after checking both rosters.
# Typically 'pidlink', but do not assume it exists or is unique.
link_id <- "pidlink"

read_raw_csv <- function(relative_path) {
  if (length(relative_path) != 1 || is.na(relative_path) || !nzchar(relative_path)) {
    stop("Set the relative file path after reviewing the inventory.")
  }
  full_path <- file.path(raw_csv_folder, relative_path)
  if (!file.exists(full_path)) stop("File missing: ", full_path)
  read.csv(full_path, stringsAsFactors = FALSE, check.names = FALSE,
           colClasses = "character", na.strings = c("", "NA"))
}

save_audit <- function(data, filename) {
  write.csv(data, file.path(audit_folder, filename), row.names = FALSE, na = "")
}
cat("Audit setup ready. Outputs: ", audit_folder, "\n")

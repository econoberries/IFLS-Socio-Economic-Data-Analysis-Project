# 01 — Inventory converted CSV files without reading their contents.
source("02_scripts/vocational_audit/00_audit_setup.R")
paths <- list.files(raw_csv_folder, pattern = "\\.csv$", recursive = TRUE,
                    full.names = TRUE, ignore.case = TRUE)
if (length(paths) == 0) stop("No CSV files found. Run the existing converter first.")
relative <- substring(paths, nchar(raw_csv_folder) + 2)
normalized <- gsub("\\\\", "/", relative)
# Wave classification requires explicit folder names; uncertain files remain unclassified.
wave <- ifelse(grepl("(^|/)(ifls[ _-]?4|wave[ _-]?4)(/|$)", normalized, ignore.case = TRUE),
               "IFLS4", ifelse(grepl("(^|/)(ifls[ _-]?5|wave[ _-]?5)(/|$)", normalized,
                                     ignore.case = TRUE), "IFLS5", "UNCLASSIFIED"))
inv <- data.frame(wave = wave, relative_path = normalized,
                  file_name = basename(paths), size_bytes = file.info(paths)$size)
save_audit(inv, "01_inventory_files.csv")
print(table(inv$wave))
cat("Roster candidates (inspect and verify):\n")
print(inv[grepl("bk_ar|roster|(^|/)ar", inv$file_name, ignore.case = TRUE),
          c("wave", "relative_path"), drop = FALSE], row.names = FALSE)
cat("Inventory saved. Set roster4_file and roster5_file in 00_audit_setup.R.\n")

# 04 — Find likely education, employment and welfare datasets/columns.
# This is a SEARCH AID, not a validated variable dictionary.
source("02_scripts/vocational_audit/00_audit_setup.R")
inv <- read.csv(file.path(audit_folder, "01_inventory_files.csv"), stringsAsFactors = FALSE)
# Include DL (education), TK (employment), and broad household candidate files.
candidates <- inv[grepl("(^|[_/])(dl|tk|ks|kr|ar|hr)([0-9_./]|$)",
                        tolower(inv$relative_path)), , drop = FALSE]
if (!nrow(candidates)) {
  cat("No files matched. Inspect 01_inventory_files.csv and adjust candidate names.\n")
} else {
  out <- lapply(seq_len(nrow(candidates)), function(i) {
    file <- file.path(raw_csv_folder, candidates$relative_path[i])
    header <- names(read.csv(file, nrows = 0, check.names = FALSE))
    data.frame(wave = candidates$wave[i], file = candidates$relative_path[i],
               variable = header)
  })
  dictionary <- do.call(rbind, out)
  save_audit(dictionary, "04_candidate_variable_inventory.csv")
  print(head(dictionary, 40), row.names = FALSE)
  cat("Now cross-check candidates with questionnaires, codebooks, and skip patterns.\n")
}

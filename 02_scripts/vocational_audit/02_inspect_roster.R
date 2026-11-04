# 02 — Examine roster identifiers and age fields BEFORE linking.
source("02_scripts/vocational_audit/00_audit_setup.R")
inspect_roster <- function(relative_path, wave) {
  x <- read_raw_csv(relative_path)
  dictionary <- data.frame(wave = wave, variable = names(x),
                           nonmissing = vapply(x, function(z) sum(!is.na(z)), integer(1)),
                           examples = vapply(x, function(z) paste(head(unique(na.omit(z)), 5),
                                                                  collapse = " | "), character(1)))
  save_audit(dictionary, paste0("02_roster_dictionary_", wave, ".csv"))
  if (!(link_id %in% names(x))) stop(wave, ": no ", link_id, ". Check dictionary.")
  ids <- trimws(x[[link_id]])
  valid <- !is.na(ids) & nzchar(ids)
  duplicates <- unique(ids[valid & (duplicated(ids) | duplicated(ids, fromLast = TRUE))])
  summary <- data.frame(wave = wave, rows = nrow(x), nonmissing_id = sum(valid),
                        unique_ids = length(unique(ids[valid])),
                        duplicated_id_values = length(duplicates))
  save_audit(summary, paste0("02_roster_summary_", wave, ".csv"))
  if (length(duplicates)) {
    examples <- x[valid & ids %in% duplicates, , drop = FALSE]
    save_audit(head(examples, 200), paste0("02_duplicate_examples_", wave, ".csv"))
  }
  print(summary)
  invisible(x)
}
roster4 <- inspect_roster(roster4_file, "IFLS4")
roster5 <- inspect_roster(roster5_file, "IFLS5")
cat("Inspect age, household membership, and duplicate-ID diagnostics before Step 03.\n")

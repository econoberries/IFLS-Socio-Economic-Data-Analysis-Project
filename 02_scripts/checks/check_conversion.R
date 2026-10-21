# Synthetic integration check: does not read or modify IFLS datasets.
# Run from the project root after installing haven and readr.

(function() {
  source("02_scripts/02a_convert_one_dta.R", local = TRUE)

  test_folder <- tempfile("ifls_conversion_check_")
  dir.create(test_folder)
  on.exit(unlink(test_folder, recursive = TRUE), add = TRUE)

  dta_root <- file.path(test_folder, "dta")
  csv_root <- file.path(test_folder, "csv")
  meta_root <- file.path(test_folder, "metadata")
  source_folder <- file.path(dta_root, "ifls5", "household", "nested")
  dir.create(source_folder, recursive = TRUE)
  source_file <- file.path(source_folder, "example.DTA")

  example <- data.frame(
    hhid = c("001", "002", "003", "004"),
    response = haven::labelled(
      c(1, 3, haven::tagged_na("a"), NA_real_),
      labels = c(Male = 1, Female = 3, Refused = haven::tagged_na("a")),
      label = "Response label"
    ),
    text = c("comma, inside", "quote \"inside\"", "NA", ""),
    visit_date = as.Date(c("2014-01-01", "2014-01-02", NA, "2015-01-01")),
    stringsAsFactors = FALSE
  )
  haven::write_dta(example, source_file)
  original_md5 <- unname(tools::md5sum(source_file))

  result <- convert_one_dta(source_file, dta_root, csv_root, meta_root)
  stopifnot(result$status == "converted", result$rows == 4, result$columns == 4)
  stopifnot(identical(original_md5, unname(tools::md5sum(source_file))))

  csv_file <- file.path(csv_root, "ifls5/household/nested/example.csv")
  meta_stem <- file.path(meta_root, "ifls5/household/nested/example")
  converted <- readr::read_csv(
    csv_file,
    col_types = readr::cols(
      hhid = readr::col_character(), response = readr::col_double(),
      text = readr::col_character(), visit_date = readr::col_date()
    ),
    na = "", show_col_types = FALSE
  )
  stopifnot(identical(names(converted), names(example)))
  stopifnot(identical(converted$hhid, example$hhid))
  stopifnot(identical(converted$response, c(1, 3, NA_real_, NA_real_)))
  stopifnot(identical(converted$text[1:3], example$text[1:3]))
  stopifnot(identical(converted$visit_date, example$visit_date))

  variables <- readr::read_csv(paste0(meta_stem, "__variables.csv"), show_col_types = FALSE)
  labels <- readr::read_csv(paste0(meta_stem, "__value_labels.csv"), show_col_types = FALSE)
  missing <- readr::read_csv(paste0(meta_stem, "__tagged_missing.csv"), show_col_types = FALSE)
  stopifnot(variables$variable_label[variables$variable == "response"] == "Response label")
  stopifnot(labels$label[labels$code == ".a"] == "Refused")
  stopifnot(nrow(missing) == 1L, missing$row_number == 3, missing$stata_missing == ".a")

  repeated <- convert_one_dta(source_file, dta_root, csv_root, meta_root)
  stopifnot(repeated$status == "skipped_existing")

  # A partial export must not be mistaken for a complete, skippable one.
  unlink(paste0(meta_stem, "__variables.csv"))
  incomplete <- try(convert_one_dta(source_file, dta_root, csv_root, meta_root), silent = TRUE)
  stopifnot(inherits(incomplete, "try-error"))
  repaired <- convert_one_dta(source_file, dta_root, csv_root, meta_root, overwrite = TRUE)
  stopifnot(repaired$status == "converted")

  example$hhid[1] <- "099"
  haven::write_dta(example, source_file)
  changed <- try(convert_one_dta(source_file, dta_root, csv_root, meta_root), silent = TRUE)
  stopifnot(inherits(changed, "try-error"))
  replaced <- convert_one_dta(source_file, dta_root, csv_root, meta_root, overwrite = TRUE)
  stopifnot(replaced$status == "converted")

  message("All synthetic conversion checks passed.")
})()

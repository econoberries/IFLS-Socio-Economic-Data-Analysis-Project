# STEP 2: create CSV copies of selected IFLS source datasets.
# Existing complete exports are checked and SKIPPED when overwrite_csv is FALSE.
# Original .dta files are never changed.

# 1. Choose which surveys to check.
# "all" checks every survey currently present in 01_data/01_raw_dta.
surveys_to_convert <- "all"

# To process only the earlier waves after adding their source files, use:
# surveys_to_convert <- c("ifls1", "ifls2", "ifls3")

# To process only one wave, use:
# surveys_to_convert <- "ifls3"


# 2. Prepare folders and check packages.
source("02_scripts/00_setup_folders.R", local = TRUE)
source("02_scripts/02a_convert_one_dta.R", local = TRUE)

for (package in c("haven", "readr")) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Run source('02_scripts/01_install_packages.R') first.")
  }
}

if (!is.character(surveys_to_convert) || length(surveys_to_convert) == 0L ||
    anyNA(surveys_to_convert)) {
  stop("Choose 'all' or survey names such as c('ifls1', 'ifls2', 'ifls3').")
}

if (!identical(surveys_to_convert, "all") &&
    any(!surveys_to_convert %in% survey_folders)) {
  stop("Use 'all' by itself, or names from: ", paste(survey_folders, collapse = ", "))
}


# 3. Find the original Stata files and identify their surveys.
all_dta_files <- sort(list.files(
  raw_dta_folder, pattern = "\\.dta$", ignore.case = TRUE,
  recursive = TRUE, full.names = TRUE
))

relative_files <- substring(all_dta_files, nchar(raw_dta_folder) + 2L)
path_parts <- strsplit(relative_files, "/", fixed = TRUE)

survey_names <- vapply(path_parts, function(parts) {
  if (length(parts) >= 2L) parts[1] else "(root)"
}, character(1))

component_names <- vapply(path_parts, function(parts) {
  if (length(parts) >= 3L) parts[2] else "(unspecified)"
}, character(1))

# Selecting earlier waves excludes IFLS4 and IFLS5 entirely.
selected <- rep(TRUE, length(all_dta_files))
if (!identical(surveys_to_convert, "all")) {
  selected <- survey_names %in% surveys_to_convert
}

dta_files <- all_dta_files[selected]
relative_files <- relative_files[selected]
survey_names <- survey_names[selected]
component_names <- component_names[selected]

if (length(dta_files) == 0L) {
  stop(
    "No .dta files found for the chosen surveys: ",
    paste(surveys_to_convert, collapse = ", "),
    ". Check your selection and source folders inside: ", raw_dta_folder
  )
}

output_stems <- tolower(tools::file_path_sans_ext(dta_files))
if (anyDuplicated(output_stems)) {
  stop("Some source paths would produce the same CSV filename. Check duplicate paths.")
}


# 4. Show exactly what this run will check.
message("Source folder: ", raw_dta_folder)
message("CSV folder: ", raw_csv_folder)
message("Survey selection: ", paste(surveys_to_convert, collapse = ", "))
message("Selected source files: ", length(dta_files))
message("Source files outside this selection: ", sum(!selected))

if (overwrite_csv) {
  message("Overwrite mode: ON. Existing exports in this selection will be recreated.")
} else {
  message("Overwrite mode: OFF. Complete exports with unchanged sources will be SKIPPED.")
}

message("Files selected by survey and component:")
source_summary <- as.data.frame(table(
  survey = survey_names,
  component = component_names
))
source_summary <- source_summary[source_summary$Freq > 0L, ]
names(source_summary)[3] <- "source_files"
print(source_summary, row.names = FALSE)

if (!identical(surveys_to_convert, "all")) {
  empty_surveys <- setdiff(surveys_to_convert, unique(survey_names))
  if (length(empty_surveys) > 0L) {
    message("No source files found for: ", paste(empty_surveys, collapse = ", "))
  }
}

message("Progress counts checked files, including files that will be skipped.")
message("Each file receives a CONVERTED, SKIPPED, or FAILED result.")


# 5. Check each selected file and report the actual result.
results <- vector("list", length(dta_files))

for (i in seq_along(dta_files)) {
  message("[", i, "/", length(dta_files), "] CHECKING: ", relative_files[i])

  results[[i]] <- tryCatch(
    convert_one_dta(
      source_file = dta_files[i],
      raw_dta_folder = raw_dta_folder,
      raw_csv_folder = raw_csv_folder,
      metadata_folder = metadata_folder,
      overwrite = overwrite_csv
    ),
    error = function(error) {
      data.frame(
        source_file = relative_files[i],
        status = "failed", rows = NA_real_, columns = NA_real_,
        message = conditionMessage(error), stringsAsFactors = FALSE
      )
    }
  )

  file_result <- results[[i]]

  if (file_result$status == "converted") {
    message(
      "  CONVERTED: ", relative_files[i],
      " (", file_result$rows, " rows, ", file_result$columns, " columns)"
    )
  } else if (file_result$status == "skipped_existing") {
    message(
      "  SKIPPED: ", relative_files[i],
      " -- complete export exists; source checksum matches; no output rewritten."
    )
  } else {
    message("  FAILED: ", relative_files[i], " -- ", file_result$message)
  }
}


# 6. Save the results and show a summary for each survey.
conversion_inventory <- do.call(rbind, results)
conversion_inventory$survey <- survey_names
conversion_inventory$component <- component_names

run_name <- paste0(
  "conversion_", format(Sys.time(), "%Y%m%d_%H%M%S", tz = "UTC"),
  "_", Sys.getpid()
)

inventory_file <- file.path(logs_folder, paste0(run_name, ".csv"))
readr::write_csv(conversion_inventory, inventory_file, na = "")
writeLines(
  capture.output(sessionInfo()),
  file.path(logs_folder, paste0(run_name, "_session.txt"))
)

status_order <- factor(
  conversion_inventory$status,
  levels = c("converted", "skipped_existing", "failed")
)
message("Results by survey:")
print(table(survey = conversion_inventory$survey, result = status_order))

message("Files converted: ", sum(conversion_inventory$status == "converted"))
message("Existing exports skipped: ", sum(conversion_inventory$status == "skipped_existing"))
message("Files failed: ", sum(conversion_inventory$status == "failed"))
message("Detailed conversion inventory: ", inventory_file)

if (any(conversion_inventory$status == "failed")) {
  stop("Some files failed. Read the inventory's message column before retrying.")
}

message("Finished. All selected sources were converted or skipped as complete existing exports.")

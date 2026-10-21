# STEP 2: export every .dta file inside 01_data/01_raw_dta.
# Run after copying your source datasets into their survey folders.
# No filtering, recoding of survey responses, merging, or cleaning takes place.

# 1. Prepare folders and check packages.
source("02_scripts/00_setup_folders.R", local = TRUE)
source("02_scripts/02a_convert_one_dta.R", local = TRUE)

for (package in c("haven", "readr")) {
  if (!requireNamespace(package, quietly = TRUE)) {
    stop("Run source('02_scripts/01_install_packages.R') first.")
  }
}

# 2. Find all Stata files, including files in nested source folders.
dta_files <- sort(list.files(
  raw_dta_folder, pattern = "\\.dta$", ignore.case = TRUE,
  recursive = TRUE, full.names = TRUE
))

if (length(dta_files) == 0L) {
  stop("No .dta files found. Put your original datasets in: ", raw_dta_folder)
}

# Avoid overwriting when filenames differ only in letter case or extension.
output_stems <- tolower(tools::file_path_sans_ext(dta_files))
if (anyDuplicated(output_stems)) {
  stop("Some source paths would produce the same CSV filename. Check duplicate paths.")
}

# 3. Process one file at a time and record failures without losing other results.
results <- vector("list", length(dta_files))

for (i in seq_along(dta_files)) {
  message("[", i, "/", length(dta_files), "] ", basename(dta_files[i]))

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
        source_file = substring(dta_files[i], nchar(raw_dta_folder) + 2L),
        status = "failed", rows = NA_real_, columns = NA_real_,
        message = conditionMessage(error), stringsAsFactors = FALSE
      )
    }
  )
}

# 4. Save a run inventory and package / R version details.
conversion_inventory <- do.call(rbind, results)
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

print(table(conversion_inventory$status))
message("Conversion inventory: ", inventory_file)

if (any(conversion_inventory$status == "failed")) {
  stop("Some exports failed. Open the inventory and read the message column.")
}

message("All source files have a CSV export or were skipped as existing exports.")

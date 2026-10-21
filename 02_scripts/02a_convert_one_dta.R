# Helper for 02_convert_all_dta_to_csv.R. Sourcing this file only defines a function.
# It never edits a source .dta file. Rows and variable order are preserved.

convert_one_dta <- function(source_file, raw_dta_folder, raw_csv_folder,
                            metadata_folder, overwrite = FALSE) {

  # 1. Keep the source folder structure in both destinations.
  source_file <- normalizePath(source_file, winslash = "/", mustWork = TRUE)
  source_root <- normalizePath(raw_dta_folder, winslash = "/", mustWork = TRUE)
  source_prefix <- paste0(source_root, "/")

  if (!startsWith(source_file, source_prefix)) {
    stop("The source file must be inside 01_raw_dta.")
  }

  relative_file <- substring(source_file, nchar(source_prefix) + 1L)
  relative_stem <- tools::file_path_sans_ext(relative_file)
  csv_file <- file.path(raw_csv_folder, paste0(relative_stem, ".csv"))
  metadata_stem <- file.path(metadata_folder, relative_stem)

  variable_file <- paste0(metadata_stem, "__variables.csv")
  value_file <- paste0(metadata_stem, "__value_labels.csv")
  missing_file <- paste0(metadata_stem, "__tagged_missing.csv")
  info_file <- paste0(metadata_stem, "__file_info.csv")
  output_files <- c(csv_file, variable_file, value_file, missing_file, info_file)

  # A source checksum lets a repeated run detect changes to a .dta file.
  source_md5 <- unname(tools::md5sum(source_file))
  if (is.na(source_md5)) stop("Could not calculate the source checksum.")

  if (any(file.exists(output_files)) && !overwrite) {
    if (!all(file.exists(output_files))) {
      stop("Incomplete export exists. Set overwrite_csv <- TRUE to recreate it.")
    }

    previous_info <- readr::read_csv(
      info_file, col_types = readr::cols(.default = readr::col_character()),
      show_col_types = FALSE, progress = FALSE
    )

    if (nrow(previous_info) != 1L ||
        !identical(previous_info$source_md5, source_md5)) {
      stop("Source changed or metadata are invalid. Set overwrite_csv <- TRUE.")
    }

    return(data.frame(
      source_file = relative_file, status = "skipped_existing",
      rows = as.numeric(previous_info$rows),
      columns = as.numeric(previous_info$columns), message = "",
      stringsAsFactors = FALSE
    ))
  }

  # 2. Read one dataset at a time; do not load all IFLS data into memory.
  dataset <- haven::read_dta(source_file, .name_repair = "minimal")

  # 3. Record variable labels and imported types before exporting values.
  variable_metadata <- data.frame(
    position = seq_along(dataset),
    variable = names(dataset),
    variable_label = vapply(dataset, function(x) {
      label <- attr(x, "label", exact = TRUE)
      if (is.null(label)) "" else as.character(label)
    }, character(1)),
    r_class = vapply(dataset, function(x) paste(class(x), collapse = ";"), character(1)),
    r_storage_type = vapply(dataset, typeof, character(1)),
    stata_format = vapply(dataset, function(x) {
      format <- attr(x, "format.stata", exact = TRUE)
      if (is.null(format)) "" else as.character(format)
    }, character(1)),
    stringsAsFactors = FALSE
  )

  # 4. Keep numeric value codes and their labels in a separate table.
  value_labels <- data.frame(
    variable = character(), code = character(), label = character(),
    stringsAsFactors = FALSE
  )
  tagged_missing <- data.frame(
    variable = character(), row_number = integer(), stata_missing = character(),
    stringsAsFactors = FALSE
  )

  for (variable in names(dataset)) {
    values <- dataset[[variable]]
    labels <- attr(values, "labels", exact = TRUE)

    if (length(labels) > 0L) {
      codes <- as.character(unname(labels))
      if (is.double(labels)) {
        tagged <- haven::is_tagged_na(labels)
        codes[tagged] <- paste0(".", haven::na_tag(labels[tagged]))
        codes[is.na(labels) & !tagged] <- "."
      }
      value_labels <- rbind(value_labels, data.frame(
        variable = variable, code = codes, label = names(labels),
        stringsAsFactors = FALSE
      ))
    }

    # Record every tagged missing by its original, one-based row position.
    if (is.double(values)) {
      missing_rows <- which(haven::is_tagged_na(values))
      if (length(missing_rows) > 0L) {
        tagged_missing <- rbind(tagged_missing, data.frame(
          variable = variable,
          row_number = missing_rows,
          stata_missing = paste0(".", haven::na_tag(values[missing_rows])),
          stringsAsFactors = FALSE
        ))
      }
    }
  }

  # 5. Write CSV values. Labels are not substituted for numeric codes.
  # Dates imported by haven are written as readable dates / UTC timestamps.
  # Missing values are blank fields. Empty Stata strings also remain blank.
  csv_dataset <- haven::zap_labels(dataset)
  file_info <- data.frame(
    source_file = relative_file,
    source_md5 = source_md5,
    source_bytes = file.info(source_file)$size,
    rows = nrow(dataset), columns = ncol(dataset),
    dataset_label = if (is.null(attr(dataset, "label"))) "" else attr(dataset, "label"),
    converted_at_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
    haven_version = as.character(utils::packageVersion("haven")),
    readr_version = as.character(utils::packageVersion("readr")),
    stringsAsFactors = FALSE
  )

  dir.create(dirname(csv_file), recursive = TRUE, showWarnings = FALSE)
  dir.create(dirname(metadata_stem), recursive = TRUE, showWarnings = FALSE)

  # Write file_info last: its presence marks a complete export.
  # Remove an old completion marker before deliberately replacing an export.
  if (file.exists(info_file)) unlink(info_file)
  readr::write_csv(csv_dataset, csv_file, na = "")
  readr::write_csv(variable_metadata, variable_file, na = "")
  readr::write_csv(value_labels, value_file, na = "")
  readr::write_csv(tagged_missing, missing_file, na = "")
  readr::write_csv(file_info, info_file, na = "")

  data.frame(
    source_file = relative_file, status = "converted",
    rows = nrow(dataset), columns = ncol(dataset), message = "",
    stringsAsFactors = FALSE
  )
}

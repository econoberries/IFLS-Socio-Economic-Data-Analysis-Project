# Step 1 — Verify IFLS5 BLSM receipt, program codes and 2013 dates.
# Run from the RStudio project root: source("02_scripts/10_blsm_2013/01_treatment_audit.R")
# Only aggregate frequencies are exported. Raw IFLS files are never modified.
source("config.R", local = TRUE)
if (!requireNamespace("haven", quietly = TRUE)) stop("Install 'haven' first.")

find_dta <- function(wave, stem) {
  root <- file.path(raw_dta_folder, wave)
  if (!dir.exists(root)) stop("Missing source folder: ", root)
  paths <- list.files(root, pattern = "\\.dta$", ignore.case = TRUE,
                      full.names = TRUE, recursive = TRUE)
  paths <- paths[tolower(tools::file_path_sans_ext(basename(paths))) == stem]
  if (length(paths) != 1L) stop("Expected one ", stem, " in ", wave,
                                "; found ", length(paths))
  paths
}
audit_dir <- file.path(outputs_folder, "tables", "blsm_2013")
dir.create(audit_dir, recursive = TRUE, showWarnings = FALSE)
save_audit <- function(x, name) {
  utils::write.csv(x, file.path(audit_dir, name), row.names = FALSE, na = "")
}
raw_value <- function(x) as.character(haven::zap_labels(x))
decoded <- function(x) if (inherits(x, "haven_labelled")) {
  as.character(haven::as_factor(x))
} else as.character(x)
tabulate_value <- function(x, name) {
  d <- data.frame(code = raw_value(x), label = decoded(x))
  d[is.na(d)] <- "(missing)"
  tab <- as.data.frame(table(d$code, d$label), stringsAsFactors = FALSE)
  names(tab) <- c("code", "label", "n")
  tab <- subset(tab, n > 0L)
  save_audit(tab, paste0("01_", name, "_codes.csv"))
  print(tab, row.names = FALSE)
}
ksr <- haven::read_dta(find_dta("ifls5", "b1_ksr1"))
needed <- c("hhid14", "ksr3type", "ksr17", "ksr18m", "ksr18y", "ksr22m", "ksr22y")
if (!all(needed %in% names(ksr))) stop("Missing expected columns: ",
                                       paste(setdiff(needed,names(ksr)), collapse=", "))
meta <- data.frame(variable=names(ksr),
                   label=vapply(ksr, function(x) {
                     z<-attr(x, "label"); if (is.null(z)) "" else as.character(z)
                   }, character(1)))
save_audit(meta, "00_ksr1_variable_labels.csv")
tabulate_value(ksr$ksr3type, "program")
tabulate_value(ksr$ksr17, "receipt")

# Questionnaire: KSR3TYPE column C = BLSM. Some releases may use labelled
# numeric codes: if so, require confirmation from saved code table.
program_code <- toupper(trimws(raw_value(ksr$ksr3type)))
program_label <- toupper(trimws(decoded(ksr$ksr3type)))
candidate <- (!is.na(program_code) & program_code == "C") |
             (!is.na(program_label) & grepl("BLSM|BANTUAN LANGSUNG SEMENTARA", program_label))
if (!any(candidate)) stop("Cannot identify BLSM records unambiguously. ",
  "Review 01_program_codes.csv and edit the candidate selection after verifying the codebook.")

blsm <- ksr[candidate, , drop=FALSE]
hhid <- raw_value(blsm$hhid14)
if (anyDuplicated(hhid)) stop("Duplicate household x BLSM program rows: inspect source!")
receipt <- raw_value(blsm$ksr17)
year <- suppressWarnings(as.integer(raw_value(blsm$ksr18y)))
last_year <- suppressWarnings(as.integer(raw_value(blsm$ksr22y)))
year[is.na(year) | year < 2000L | year > 2015L] <- NA_integer_
last_year[is.na(last_year) | last_year < 2000L | last_year > 2015L] <- NA_integer_
class <- rep("unknown_or_other",length(receipt))
class[!is.na(receipt) & receipt=="3"] <- "reported_no"
class[!is.na(receipt) & receipt=="1"] <- "yes_first_year_unknown"
class[!is.na(receipt) & receipt=="1" & !is.na(year) & year==2013L] <- "yes_first_2013"
class[!is.na(receipt) & receipt=="1" & !is.na(year) & year<2013L] <- "yes_first_before_2013"
class[!is.na(receipt) & receipt=="1" & !is.na(year) & year>2013L] <- "yes_first_after_2013"
class[!is.na(receipt) & receipt=="6"] <- "no_program_code"
out <- as.data.frame(table(classification=class), stringsAsFactors=FALSE)
names(out)[2] <- "n"
save_audit(out, "02_blsm_timing_classification.csv")
print(out, row.names=FALSE)
year_summary <- as.data.frame(table(
  first_year=ifelse(is.na(year),"(unknown)",as.character(year)),
  last_year=ifelse(is.na(last_year),"(unknown)",as.character(last_year)),
  receipt=ifelse(is.na(receipt),"(missing)",receipt)), stringsAsFactors=FALSE)
names(year_summary)[4] <- "n"
save_audit(subset(year_summary, n>0), "03_blsm_first_last_year.csv")
cat("Rows classified as first received in 2013:",
    sum(class == "yes_first_2013"), "\n")
cat("Contradictory dates:",
    sum(!is.na(year) & !is.na(last_year) & last_year < year), "\n")
cat("The categories are only diagnostics: do not fit an ATT model yet.\n")

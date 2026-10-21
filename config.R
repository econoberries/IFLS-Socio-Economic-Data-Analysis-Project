# IFLS project configuration
# Open IFLS_Project.Rproj first. Run scripts from the project root.

project_folder <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)

if (!file.exists(file.path(project_folder, "IFLS_Project.Rproj"))) {
  stop("Open IFLS_Project.Rproj and run the script from the project root.")
}

# All data are stored locally inside the project and excluded from Git.
documentation_folder <- file.path(project_folder, "00_documentation")
data_folder <- file.path(project_folder, "01_data")
raw_dta_folder <- file.path(data_folder, "01_raw_dta")
raw_csv_folder <- file.path(data_folder, "02_raw_csv")
metadata_folder <- file.path(data_folder, "03_metadata")
intermediate_folder <- file.path(data_folder, "04_intermediate")
analysis_folder <- file.path(data_folder, "05_analysis")
outputs_folder <- file.path(project_folder, "05_outputs")
logs_folder <- file.path(outputs_folder, "logs")

# Optional survey extensions have separate folders; they are not extra panel waves.
survey_folders <- c(
  "ifls1", "ifls2", "ifls3", "ifls4", "ifls5",
  "ifls2plus", "ifls_east"
)

# FALSE protects existing CSVs. Set TRUE only to deliberately recreate exports.
overwrite_csv <- FALSE

# STEP 0: create the local project folders. Safe to run again.
# This script does not move, change, or delete existing files.

source("config.R", local = TRUE)

# 1. General folders
folders_to_create <- c(
  documentation_folder,
  file.path(documentation_folder, "general"),
  file.path(documentation_folder, "literature"),
  raw_dta_folder,
  raw_csv_folder,
  metadata_folder,
  intermediate_folder,
  analysis_folder,
  file.path(project_folder, "03_notebooks"),
  file.path(project_folder, "04_notes"),
  file.path(outputs_folder, "tables"),
  file.path(outputs_folder, "figures"),
  logs_folder,
  file.path(project_folder, "06_paper")
)

for (folder in folders_to_create) {
  dir.create(folder, recursive = TRUE, showWarnings = FALSE)
}

# 2. Separate each survey and each type of data / documentation
for (survey in survey_folders) {
  for (component in c("household", "community")) {
    dir.create(
      file.path(raw_dta_folder, survey, component),
      recursive = TRUE, showWarnings = FALSE
    )
    dir.create(
      file.path(raw_csv_folder, survey, component),
      recursive = TRUE, showWarnings = FALSE
    )
    dir.create(
      file.path(metadata_folder, survey, component),
      recursive = TRUE, showWarnings = FALSE
    )
  }

  for (document_type in c("questionnaires", "codebooks", "user_guides")) {
    dir.create(
      file.path(documentation_folder, survey, document_type),
      recursive = TRUE, showWarnings = FALSE
    )
  }
}

message("Project folders are ready at: ", project_folder)
message("Put original .dta files inside: ", raw_dta_folder)

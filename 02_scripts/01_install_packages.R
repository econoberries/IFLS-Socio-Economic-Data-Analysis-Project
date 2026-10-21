# STEP 1: install missing packages. Run once, or when setting up a new computer.

packages_needed <- c("haven", "readr", "rmarkdown", "knitr")

for (package in packages_needed) {
  if (!requireNamespace(package, quietly = TRUE)) {
    install.packages(package, repos = "https://cloud.r-project.org")
  }
}

message("Required packages are available.")

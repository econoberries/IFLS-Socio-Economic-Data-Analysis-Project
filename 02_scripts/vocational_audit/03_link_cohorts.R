# 03 — Conservative linkage and age-band feasibility counts.
# Requires verified unique one-person-per-wave rosters. Does not silently deduplicate.
source("02_scripts/vocational_audit/00_audit_setup.R")

# Confirm exact variable names in 02_roster_dictionary_*.csv before editing:
age4_var <- "ar09"  # candidate; verify in IFLS4
age5_var <- "ar09"  # candidate; verify in IFLS5

r4 <- read_raw_csv(roster4_file)
r5 <- read_raw_csv(roster5_file)
for (z in list(c("IFLS4", link_id, age4_var), c("IFLS5", link_id, age5_var))) {
  dat <- if (z[1] == "IFLS4") r4 else r5
  if (!all(z[2:3] %in% names(dat))) stop(z[1], ": required fields missing: ",
                                         paste(setdiff(z[2:3], names(dat)), collapse = ", "))
}
clean_id <- function(z) { z <- trimws(z); z[!is.na(z) & z == ""] <- NA_character_; z }
r4[[link_id]] <- clean_id(r4[[link_id]])
r5[[link_id]] <- clean_id(r5[[link_id]])
for (pair in list(list(r4, "IFLS4"), list(r5, "IFLS5"))) {
  ids <- pair[[1]][[link_id]]
  if (anyDuplicated(ids[!is.na(ids)]) > 0) {
    stop(pair[[2]], " contains duplicate valid IDs. Resolve household-membership/roster records first; do not deduplicate arbitrarily.")
  }
}
parse_age <- function(z) {
  a <- suppressWarnings(as.numeric(z))
  a[is.na(a) | a < 0 | a > 110] <- NA_real_ # includes special codes like 900
  a
}
base <- data.frame(pidlink_key = r4[[link_id]], age4 = parse_age(r4[[age4_var]]))
follow <- data.frame(pidlink_key = r5[[link_id]], age5 = parse_age(r5[[age5_var]]))
base <- base[!is.na(base$pidlink_key), , drop = FALSE]
follow <- follow[!is.na(follow$pidlink_key), , drop = FALSE]
base$observed5 <- base$pidlink_key %in% follow$pidlink_key
linked <- merge(base, follow, by = "pidlink_key", all.x = TRUE, sort = FALSE)
linked$observed5 <- !is.na(match(linked$pidlink_key, follow$pidlink_key))
linked$age_band <- cut(linked$age4, breaks = c(-Inf, 9, 11, 12, 13, 14, 15, 17, 20, Inf),
                       labels = c("<=9", "10-11", "12", "13", "14", "15", "16-17", "18-20", "21+"))
linked$age_gap <- linked$age5 - linked$age4
bands <- levels(linked$age_band)
counts <- do.call(rbind, lapply(bands, function(b) {
  z <- linked[!is.na(linked$age_band) & linked$age_band == b, , drop = FALSE]
  data.frame(age_band_ifls4 = b, n_baseline = nrow(z),
             n_observed_ifls5 = sum(z$observed5),
             n_age_observed_both = sum(z$observed5 & !is.na(z$age5)),
             followup_rate = if (nrow(z)) round(mean(z$observed5), 3) else NA_real_)
}))
save_audit(counts, "03_cohort_counts.csv")
save_audit(linked, "03_linked_age_audit.csv")
print(counts, row.names = FALSE)
cat("Inspect implausible age gaps and verify IFLS5 membership before interpreting attrition.\n")

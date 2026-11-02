# Step 2 — IFLS4/5 panel-linkage audit (no individual IDs exported).
# source("02_scripts/10_blsm_2013/02_panel_audit.R") from project root.
source("config.R", local=TRUE)
if (!requireNamespace("haven", quietly=TRUE)) stop("Install 'haven'.")
outdir <- file.path(outputs_folder,"tables","blsm_2013")
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
save <- function(x,file) utils::write.csv(x,file.path(outdir,file),
                                          row.names=FALSE,na="")
find_file <- function(wave,stems) {
  folder<-file.path(raw_dta_folder,wave)
  if (!dir.exists(folder)) stop("Missing folder: ",folder)
  p<-list.files(folder,pattern="\\.dta$",ignore.case=TRUE,
                recursive=TRUE,full.names=TRUE)
  p<-p[tolower(tools::file_path_sans_ext(basename(p))) %in% stems]
  if (length(p)!=1L) stop("Expected one of ",paste(stems,collapse=","),
                         " in ",wave,"; found ",length(p))
  p
}
read_source <- function(wave,stem) haven::read_dta(find_file(wave,stem))
id <- function(x) {
  z<-trimws(as.character(haven::zap_labels(x)))
  z[is.na(z)|z==""]<-NA_character_
  z
}
# Official IFLS guide: use PIDLINK for people, HTRACK14 for household
# history. Do not equate individual records with households or assume
# all split-off households form 1:1 matches.
ptrack<-haven::read_dta(find_file("ifls5",c("ptrack14","ptrack")))
necessary<-c("pidlink","hhid07","hhid14")
if (!all(necessary %in% names(ptrack)))
  stop("Tracking file missing ",paste(setdiff(necessary,names(ptrack)),collapse=", "))
pid<-id(ptrack$pidlink)
if (anyDuplicated(pid[!is.na(pid)])) stop("PTRACK PIDLINK not unique.")
h07<-id(ptrack$hhid07); h14<-id(ptrack$hhid14)
linked <- !is.na(h07) & !is.na(h14)
counts <- data.frame(
  indicator=c("Tracking records","Unique PIDLINK",
              "PIDLINK with HHID07","PIDLINK with HHID14",
              "PIDLINK with both HHIDs",
              "Distinct 2007 HHIDs among linked people",
              "Distinct 2014 HHIDs among linked people"),
  n=c(nrow(ptrack),length(unique(pid[!is.na(pid)])),
      sum(!is.na(h07)),sum(!is.na(h14)),sum(linked),
      length(unique(h07[linked])),length(unique(h14[linked]))))
save(counts,"04_ptrack_linkage_counts.csv")
print(counts,row.names=FALSE)

# A 2007 household can have tracked members in multiple 2014 households.
pairs <- unique(data.frame(hhid07=h07[linked],hhid14=h14[linked]))
per_base <- table(pairs$hhid07)
split_summary <- data.frame(
  n_followup_households=as.integer(names(table(per_base))),
  n_baseline_households=as.integer(table(per_base)),
  row.names=NULL)
save(split_summary,"05_splitoff_audit.csv")
print(split_summary,row.names=FALSE)

# Prefer household-tracking records to an unverified HHID07=HHID14 join.
ht<-haven::read_dta(find_file("ifls5",c("htrack14","htrack")))
if (!all(c("hhid07","hhid14") %in% names(ht))) {
  message("HTRACK columns available: ",paste(names(ht),collapse=", "))
  stop("Inspect HTRACK before constructing household-panel keys.")
}
ht07<-id(ht$hhid07); ht14<-id(ht$hhid14)
tracked<-data.frame(
  indicator=c("HTRACK records","HTRACK nonmissing 2007 HHID",
              "HTRACK nonmissing 2014 HHID",
              "HTRACK both IDs",
              "Duplicate pairs among complete IDs"),
  n=c(nrow(ht),sum(!is.na(ht07)),sum(!is.na(ht14)),
      sum(!is.na(ht07)&!is.na(ht14)),
      sum(duplicated(data.frame(hh07=ht07,hh14=ht14)) &
          !is.na(ht07)&!is.na(ht14))))
save(tracked,"06_htrack_linkage_counts.csv")
print(tracked,row.names=FALSE)

for (nm in intersect(c("result07","result14","member07","member14"),
                     names(ht))) {
  x<-as.character(haven::zap_labels(ht[[nm]]))
  x[is.na(x)]<-"(missing)"
  val<-as.data.frame(table(value=x),stringsAsFactors=FALSE)
  names(val)[2]<-"n";val$variable<-nm
  save(val,paste0("07_htrack_",nm,".csv"))
}
for (nm in intersect(c("member07","member14"),names(ptrack))) {
  x<-as.character(haven::zap_labels(ptrack[[nm]]))
  x[is.na(x)]<-"(missing)"
  val<-as.data.frame(table(value=x),stringsAsFactors=FALSE)
  names(val)[2]<-"n";val$variable<-nm
  save(val,paste0("08_ptrack_",nm,".csv"))
}
message("STEP 2 is descriptive only. Confirm MEMBER/RESULT codes, ",
        "split-off handling and the intended observation unit before merging.")

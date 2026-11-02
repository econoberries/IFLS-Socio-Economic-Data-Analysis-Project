# Step 3 — Inventory the components of household welfare in IFLS4 / IFLS5.
# source("02_scripts/10_blsm_2013/03_welfare_inventory.R")
# No guessed expenditure total is computed here.
source("config.R",local=TRUE)
if (!requireNamespace("haven",quietly=TRUE)) stop("Install 'haven'.")
outdir<-file.path(outputs_folder,"tables","blsm_2013")
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
save<-function(x,n) utils::write.csv(x,file.path(outdir,n),row.names=FALSE,na="")
files<-c("b1_ks0","b1_ks1","b1_ks2","b1_ks3","b1_ks4","b2_kr","bk_ar1")
find_file<-function(wave,stem) {
  root<-file.path(raw_dta_folder,wave)
  p<-list.files(root,pattern="\\.dta$",recursive=TRUE,
                full.names=TRUE,ignore.case=TRUE)
  matches<-p[tolower(tools::file_path_sans_ext(basename(p)))==stem]
  if (length(matches)!=1L) return(NA_character_)
  matches
}
inventory<-list();metadata<-list();i<-0L;j<-0L
for (wave in c("ifls4","ifls5")) for (stem in files) {
  path<-find_file(wave,stem)
  if (is.na(path)) {
    i<-i+1L
    inventory[[i]]<-data.frame(wave=wave,file=stem,exists=FALSE,
                               rows=NA_integer_,columns=NA_integer_)
    next
  }
  d<-haven::read_dta(path)
  i<-i+1L
  inventory[[i]]<-data.frame(wave=wave,file=stem,exists=TRUE,
                            rows=nrow(d),columns=ncol(d))
  j<-j+1L
  metadata[[j]]<-data.frame(
    wave=wave,file=stem,variable=names(d),
    description=vapply(d,function(x) {
      lab<-attr(x,"label");if (is.null(lab)) "" else as.character(lab)
    },character(1)),
    missing_n=vapply(d,function(x)sum(is.na(x)),integer(1)),
    n=nrow(d),stringsAsFactors=FALSE)
}
inventory<-do.call(rbind,inventory)
save(inventory,"09_welfare_file_inventory.csv")
print(inventory,row.names=FALSE)
if (length(metadata)) {
  vars<-do.call(rbind,metadata)
  save(vars,"10_welfare_variable_dictionary.csv")
  message("Read 10_welfare_variable_dictionary.csv to confirm:",
          "\n  KS1: weekly food; KS2: monthly nonfood;",
          "\n  KS3: yearly nonfood; KS0: additional items;",
          "\n  B2_KR: housing; BK_AR1: household composition.")
}
cat("\nDo not sum raw KS files yet. First harmonize reference periods, ",
    "deal with special/missing responses, own-produced consumption, ",
    "transfers, household size, and spatial/time deflators.\n",sep="")
cat("Proposed primary outcome: real monthly household consumption per capita.\n")
cat("Sensitivity: real per-adult-equivalent consumption; food consumption share.\n")
cat("A proper aggregate must avoid counting cash transfers as consumption.\n")

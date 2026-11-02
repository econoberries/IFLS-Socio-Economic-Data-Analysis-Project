# Step 4 — Identify interview month/year variables before coding exposure.
# This is a metadata audit: no interview calendar is guessed from file names.
# source("02_scripts/10_blsm_2013/04_interview_calendar_audit.R")
source("config.R", local=TRUE)
if (!requireNamespace("haven",quietly=TRUE)) stop("Install 'haven'.")
outdir<-file.path(outputs_folder,"tables","blsm_2013")
dir.create(outdir,recursive=TRUE,showWarnings=FALSE)
find_file<-function(wave,stem) {
  root<-file.path(raw_dta_folder,wave)
  paths<-list.files(root,pattern="\\.dta$",recursive=TRUE,
                    full.names=TRUE,ignore.case=TRUE)
  hits<-paths[tolower(tools::file_path_sans_ext(basename(paths)))==stem]
  if(length(hits)!=1L) return(NA_character_)
  hits
}
all<-list()
for(wave in c("ifls4","ifls5")) for(stem in c("b1_time","bk_time","b1_cov","bk_cov")) {
  p<-find_file(wave,stem)
  if(is.na(p)) next
  d<-haven::read_dta(p)
  labels<-vapply(d,function(x){a<-attr(x,"label");
                        if(is.null(a)) "" else as.character(a)},character(1))
  take<-grepl("date|month|year|interview|tanggal|bulan|tahun",labels,
              ignore.case=TRUE) |
        grepl("date|month|year|^time|^b1_time",names(d),ignore.case=TRUE)
  if(!any(take)) next
  all[[length(all)+1L]]<-data.frame(
    wave=wave,file=stem,variable=names(d)[take],
    label=labels[take],
    missing_n=vapply(d[take],function(x)sum(is.na(x)),integer(1)),
    n=nrow(d),stringsAsFactors=FALSE
  )
}
if(!length(all)) stop("No interview timing candidate columns found. ",
                       "Inspect B1_TIME / BK_TIME and cover files manually.")
results<-do.call(rbind,all)
utils::write.csv(results,file.path(outdir,"11_interview_date_variable_candidates.csv"),
                 row.names=FALSE,na="")
print(results,row.names=FALSE)
cat("\nNEXT: verify exact question codes and units (day/month/year) from ",
    "labels and guide. Then compare each BLSM payment date to the actual ",
    "IFLS5 interview date. Do NOT assume 2014 payments all predate interview.\n",sep="")

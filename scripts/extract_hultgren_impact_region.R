#!/usr/bin/env Rscript

# Extract one impact-region polygon point frame from the authors' public FST.
# The output is an ignored intermediate; source identity is checked downstream.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) {
  stop("usage: extract_hultgren_impact_region.R SOURCE_FST REGION_ID OUTPUT_CSV")
}
source_path <- args[[1]]
region_id <- args[[2]]
output_path <- args[[3]]
if (!requireNamespace("fst", quietly = TRUE)) {
  stop("R package 'fst' is required")
}
if (!file.exists(source_path)) {
  stop("source FST does not exist")
}
if (file.exists(output_path)) {
  stop("fresh output path required")
}
meta <- fst::metadata_fst(source_path)
expected_columns <- c("long", "lat", "order", "hole", "piece", "id", "group", "area_sqkm")
if (meta$nrOfRows != 714615L || !identical(meta$columnNames, expected_columns)) {
  stop("source FST metadata differs from reviewed contract")
}
points <- fst::read_fst(source_path, columns = expected_columns)
points <- points[points$id == region_id, expected_columns]
if (nrow(points) < 4L || length(unique(points$group)) < 1L) {
  stop("requested region has no valid polygon-ring support")
}
points <- points[order(points$order), ]
dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
write.csv(points, output_path, row.names = FALSE, quote = TRUE)
cat(sprintf("extracted %d rows for %s\n", nrow(points), region_id))

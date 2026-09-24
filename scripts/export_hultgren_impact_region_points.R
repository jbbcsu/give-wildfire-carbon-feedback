#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
extra_library <- Sys.getenv("HULTGREN_FST_LIB", unset = "")
if (nzchar(extra_library)) {
  .libPaths(c(extra_library, .libPaths()))
}
if (length(args) != 2) {
  stop("usage: export_hultgren_impact_region_points.R SOURCE_FST OUTPUT_CSV_GZ")
}

source_path <- args[[1]]
output_path <- args[[2]]
if (!file.exists(source_path) || file.exists(output_path)) {
  stop("source must exist and output must be fresh")
}
if (!requireNamespace("fst", quietly = TRUE)) {
  stop("the fst package is required")
}

points <- fst::read_fst(source_path, as.data.table = FALSE)
required <- c("long", "lat", "order", "hole", "piece", "id", "group", "area_sqkm")
if (!identical(names(points), required)) {
  stop("impact-region point schema changed")
}
if (nrow(points) != 714615L || length(unique(points$id)) != 24376L ||
    length(unique(points$group)) != 27005L || sum(points$hole) != 30L) {
  stop("impact-region point counts changed")
}
if (any(!is.finite(points$long)) || any(!is.finite(points$lat)) ||
    any(!is.finite(points$area_sqkm))) {
  stop("impact-region points contain nonfinite coordinates or areas")
}
if (any(diff(points$order) <= 0)) {
  stop("global point order is not strictly increasing")
}

connection <- gzfile(output_path, open = "wt", compression = 9)
write.csv(points, connection, row.names = FALSE, quote = TRUE)
close(connection)
cat(sprintf("exported %d points, %d regions, %d rings\n",
            nrow(points), length(unique(points$id)), length(unique(points$group))))

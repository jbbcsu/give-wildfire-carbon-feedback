args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) stop("usage: inspect_fredi_transport_runtime.R SYS_DATA")
env <- new.env()
load(args[[1]], envir = env)
state <- env$rDataList$stateData$data
scaled <- subset(state$data_scaledImpacts, sector %in% c("Roads", "Rail"))
info <- unique(subset(state$df_sectorsInfo, sector %in% c("Roads", "Rail"),
                      select = c(sector, variant, impactType, sectorprimary,
                                 includeaggregate, byState, modelType)))
scalars <- subset(state$df_mainScalars,
                  scalarName %in% c("road_miles", "rail_miles",
                                    "road_miles_and_pop_Reactive",
                                    "rail_growth_factor"))
scalar_support <- aggregate(year ~ scalarName, scalars,
                            function(x) c(min = min(x), max = max(x)))
result <- list(
  transport_scaled_rows = nrow(scaled),
  states = length(unique(scaled$postal)),
  models = sort(unique(scaled$model)),
  variants = sort(unique(scaled$variant)),
  sectors = sort(unique(scaled$sector)),
  impact_types = sort(unique(as.character(scaled$impactType))),
  primary_rows = info,
  scalar_support = scalar_support
)
cat(jsonlite::toJSON(result, auto_unbox = TRUE, dataframe = "rows", digits = 16))

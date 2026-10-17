args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) stop("usage: run_water_quality_annual_pair.R SYS_DATA GIVE_PAIR OUTPUT")

env <- new.env()
load(args[[1]], envir = env)
runtime <- env$rDataList$stateData$data
scaled <- subset(runtime$data_scaledImpacts, sector == "WaterQuality")
scalars <- runtime$df_mainScalars
functions <- runtime$list_impactFunctions
pair <- read.csv(args[[2]], stringsAsFactors = FALSE)

pair <- subset(pair, year >= 2025 & year <= 2092 &
  base_conus_anomaly_c >= 0 & pulse_conus_anomaly_c >= 0 &
  base_conus_anomaly_c <= 3 & pulse_conus_anomaly_c <= 3)
if (nrow(pair) != 68 || min(pair$year) != 2025 || max(pair$year) != 2092) {
  stop("matched pair does not have frozen 2025-2092 common support")
}

models <- c("CCSM4", "CanESM2", "GISS-E2-R", "HadGEM2-ES", "MIROC5")
out <- vector("list", length(models) * nrow(pair))
k <- 0
population <- subset(scalars, scalarName == "reg_pop" & byState == 1 & year >= 2025 & year <= 2092,
                     select = c(postal, year, value))
if (nrow(population) != 49 * 68) stop("incomplete official state population support")

for (model_i in models) {
  response_rows <- scaled[scaled$model == model_i, ]
  if (min(response_rows$modelUnitValue) != 1 || max(response_rows$modelUnitValue) < 3) {
    stop(paste("insufficient common response support", model_i))
  }
  states <- sort(unique(response_rows$postal))
  if (length(states) != 49) stop(paste("response does not cover 49 state/DC units", model_i))
  base_total <- rep(0, nrow(pair))
  pulse_total <- rep(0, nrow(pair))
  for (postal_i in states) {
    ids <- unique(response_rows$scenario_id[response_rows$postal == postal_i])
    if (length(ids) != 1 || is.null(functions[[ids[[1]]]])) {
      stop(paste("missing official response function", model_i, postal_i))
    }
    tabulated_two <- response_rows$scaledImpact[
      response_rows$postal == postal_i & response_rows$modelUnitValue == 2
    ]
    if (length(tabulated_two) != 1 ||
        abs(functions[[ids[[1]]]](2) - tabulated_two[[1]]) > 1e-10) {
      stop(paste("serialized response fails tabulated 2C check", model_i, postal_i))
    }
    state_pop <- population$value[population$postal == postal_i]
    if (length(state_pop) != nrow(pair)) stop(paste("incomplete population", postal_i))
    base_total <- base_total + functions[[ids[[1]]]](pair$base_conus_anomaly_c) * state_pop
    pulse_total <- pulse_total + functions[[ids[[1]]]](pair$pulse_conus_anomaly_c) * state_pop
  }
  for (i in seq_len(nrow(pair))) {
    k <- k + 1
    out[[k]] <- data.frame(
      scope = "CONUS_48_plus_DC",
      endpoint = "freshwater_recreation_WTP",
      year = pair$year[[i]],
      gcm = model_i,
      base_conus_anomaly_c = pair$base_conus_anomaly_c[[i]],
      pulse_conus_anomaly_c = pair$pulse_conus_anomaly_c[[i]],
      base_damage_2015usd = base_total[[i]],
      pulse_damage_2015usd = pulse_total[[i]],
      marginal_damage_2015usd = pulse_total[[i]] - base_total[[i]],
      ramsey_discount_factor = pair$ramsey_discount_factor[[i]],
      stringsAsFactors = FALSE
    )
  }
}

result <- do.call(rbind, out)
if (nrow(result) != 340 || any(!is.finite(as.matrix(result[, 5:10])))) stop("invalid annual output")
dir.create(dirname(args[[3]]), recursive = TRUE, showWarnings = FALSE)
options(digits = 17)
write.csv(result, args[[3]], row.names = FALSE, quote = TRUE)
cat(sprintf("PASS rows=%d years=%d-%d gcms=%d\n", nrow(result), min(result$year), max(result$year), length(models)))

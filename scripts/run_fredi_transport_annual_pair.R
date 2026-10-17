args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3) stop("usage: run_fredi_transport_annual_pair.R SYS_DATA GIVE_PAIR OUTPUT")

sysdata_path <- args[[1]]
pair_path <- args[[2]]
output_path <- args[[3]]

env <- new.env()
load(sysdata_path, envir = env)
runtime <- env$rDataList$stateData$data
scaled <- subset(runtime$data_scaledImpacts, sector %in% c("Roads", "Rail"))
scalars <- runtime$df_mainScalars
functions <- runtime$list_impactFunctions
pair <- read.csv(pair_path, stringsAsFactors = FALSE)

pair <- subset(pair, year >= 2025 &
  base_conus_anomaly_c >= 0 & pulse_conus_anomaly_c >= 0 &
  base_conus_anomaly_c <= 3 & pulse_conus_anomaly_c <= 3)
if (nrow(pair) != 68 || min(pair$year) != 2025 || max(pair$year) != 2092) {
  stop("matched pair does not have frozen 2025-2092 common support")
}

sectors <- c("Roads", "Rail")
variants <- c("NoAdapt", "Proactive", "Reactive")
models <- c("CCSM4", "CanESM2", "GFDL-CM3", "GISS-E2-R", "HadGEM2-ES", "MIROC5")
out <- vector("list", length(sectors) * length(variants) * length(models) * nrow(pair))
k <- 0

for (sector_i in sectors) {
  miles_name <- if (sector_i == "Roads") "road_miles" else "rail_miles"
  miles <- subset(scalars, scalarName == miles_name & year >= 2025 & year <= 2092,
                  select = c(postal, year, value))
  if (nrow(miles) != 49 * 68) stop(paste("incomplete", miles_name, "support"))
  for (variant_i in variants) {
    adj_name <- if (sector_i == "Roads") paste0("road_miles_and_pop_", variant_i) else "rail_growth_factor"
    adj <- subset(scalars, scalarName == adj_name & year >= 2025 & year <= 2092,
                  select = c(postal, year, value))
    for (model_i in models) {
      response_rows <- scaled[scaled$sector == sector_i & scaled$variant == variant_i & scaled$model == model_i, ]
      states <- sort(unique(response_rows$postal))
      if (length(states) != 49) stop("response does not cover 49 state/DC units")
      base_total <- rep(0, nrow(pair))
      pulse_total <- rep(0, nrow(pair))
      for (postal in states) {
        ids <- unique(response_rows$scenario_id[response_rows$postal == postal])
        if (length(ids) != 1 || is.null(functions[[ids[[1]]]])) {
          stop(paste("missing official response function", sector_i, variant_i, model_i, postal, paste(ids, collapse = ",")))
        }
        response_fun <- functions[[ids[[1]]]]
        state_miles <- miles$value[miles$postal == postal]
        if (length(state_miles) != nrow(pair)) stop("incomplete physical scalar")
        if (sector_i == "Roads") {
          state_adj <- adj$value[adj$postal == postal]
          if (length(state_adj) != nrow(pair)) stop("incomplete road adjustment")
        } else {
          state_adj <- adj$value
          if (length(state_adj) != nrow(pair)) stop("incomplete rail adjustment")
        }
        scalar <- state_miles * state_adj
        base_total <- base_total + response_fun(pair$base_conus_anomaly_c) * scalar
        pulse_total <- pulse_total + response_fun(pair$pulse_conus_anomaly_c) * scalar
      }
      for (i in seq_len(nrow(pair))) {
        k <- k + 1
        out[[k]] <- data.frame(
          scope = "CONUS_48_plus_DC",
          year = pair$year[[i]],
          gcm = model_i,
          variant = variant_i,
          released_aggregate = sector_i,
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
  }
}

result <- do.call(rbind, out)
if (nrow(result) != 2448 || any(!is.finite(as.matrix(result[, 6:11])))) stop("invalid annual output")
dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
options(digits = 17)
write.csv(result, output_path, row.names = FALSE, quote = TRUE)
cat(sprintf("PASS rows=%d years=%d-%d\n", nrow(result), min(result$year), max(result$year)))

#!/usr/bin/env Rscript

# PNG/PDF figure builder for the wildfire-carbon GIVE extension.
# This script deliberately uses ordinary R/ggplot2/jsonlite so the outputs can
# be opened without SVG support and without changing the Julia project env.

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(grid)
  library(gridExtra)
  library(jsonlite)
  library(readr)
  library(scales)
  library(tidyr)
  library(viridisLite)
})

args <- commandArgs(trailingOnly = TRUE)
repo <- if (length(args) >= 1) args[[1]] else getwd()
mcs_dir <- file.path(repo, "output", "wildfire_temperature_feedback_mcs_100_paired")
sector_dir <- file.path(repo, "output", "wildfire_sectoral_diagnostics_100")
regional_dir <- file.path(repo, "output", "wildfire_regional_damage_diagnostics")
scale_dir <- file.path(repo, "output", "wildfire_temperature_feedback_refyear_check")
geojson_path <- file.path(repo, "wildfire_extension", "data", "natural_earth", "ne_110m_admin_0_countries.geojson")
out_dir <- file.path(repo, "wildfire_extension", "manuscript", "figures", "png_pdf")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

scenario_levels <- c(
  "baseline",
  "feedback-residual-medium",
  "feedback-residual-high",
  "feedback-resfire-half-gross",
  "feedback-resfire-gross"
)

scenario_labels <- c(
  baseline = "Baseline",
  `feedback-residual-medium` = "Residual medium",
  `feedback-residual-high` = "Residual high",
  `feedback-resfire-half-gross` = "RESFire half-gross stress",
  `feedback-resfire-gross` = "RESFire gross stress"
)

scenario_colors <- c(
  baseline = "#2B6CB0",
  `feedback-residual-medium` = "#00A878",
  `feedback-residual-high` = "#E4572E",
  `feedback-resfire-half-gross` = "#7B2CBF",
  `feedback-resfire-gross` = "#F4A261"
)

theme_give <- function(base_size = 11) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 5, margin = margin(b = 4)),
      plot.subtitle = element_text(color = "grey30", margin = margin(b = 8)),
      panel.grid.minor = element_blank(),
      legend.title = element_text(face = "bold"),
      strip.text = element_text(face = "bold", hjust = 0),
      strip.background = element_rect(fill = "grey94", color = NA),
      plot.caption = element_text(color = "grey35", hjust = 0)
    )
}

draw_plot <- function(x) {
  if (inherits(x, "ggplot")) print(x) else grid.draw(x)
}

save_png_pdf <- function(plot, stem, width = 10, height = 6, dpi = 220) {
  pdf_path <- file.path(out_dir, paste0(stem, ".pdf"))
  png_path <- file.path(out_dir, paste0(stem, ".png"))
  pdf(pdf_path, width = width, height = height, useDingbats = FALSE)
  draw_plot(plot)
  dev.off()
  # Use R's default macOS PNG device. Cairo is not guaranteed on a clean
  # replication machine because it can depend on external X11 libraries.
  png(png_path, width = width, height = height, units = "in", res = dpi, bg = "white")
  draw_plot(plot)
  dev.off()
  invisible(c(pdf = pdf_path, png = png_path))
}

make_conceptual_audit_schematic <- function() {
  box <- function(label, x, y, w, h, fill = "white", border = "#2E4057", fontsize = 11) {
    grobTree(
      roundrectGrob(x = x, y = y, width = w, height = h, r = unit(0.035, "npc"),
                    gp = gpar(fill = fill, col = border, lwd = 1.1)),
      textGrob(label, x = x, y = y, gp = gpar(fontsize = fontsize, col = "#1F2933", fontface = "bold"))
    )
  }
  arr <- function(x0, y0, x1, y1, col = "#475569", lwd = 1.2) {
    segmentsGrob(x0 = x0, y0 = y0, x1 = x1, y1 = y1,
                 arrow = arrow(length = unit(0.018, "npc"), type = "closed"),
                 gp = gpar(col = col, lwd = lwd))
  }
  note <- function(label, x, y, fontsize = 9.5, col = "#46525E") {
    textGrob(label, x = x, y = y, gp = gpar(fontsize = fontsize, col = col), just = "center")
  }

  g <- grobTree(
    rectGrob(gp = gpar(fill = "white", col = NA)),
    textGrob("Exogenous baseline pathway and added wildfire-carbon feedback",
             x = 0.04, y = 0.95, just = "left", gp = gpar(fontsize = 17, fontface = "bold", col = "#111827")),
    textGrob("GIVE baseline", x = 0.18, y = 0.86, gp = gpar(fontsize = 12.5, fontface = "bold", col = "#1D4E89")),
    textGrob("This extension", x = 0.71, y = 0.86, gp = gpar(fontsize = 12.5, fontface = "bold", col = "#B45309")),
    box("RFF-SP aggregate\nCO2 emissions", 0.14, 0.70, 0.20, 0.12, fill = "#E8F1FA", border = "#1D4E89"),
    box("FAIR carbon\ncycle", 0.38, 0.70, 0.17, 0.12, fill = "#EEF6FF", border = "#1D4E89"),
    box("Forcing and\ntemperature", 0.58, 0.70, 0.18, 0.12, fill = "#F4F7FB", border = "#1D4E89"),
    box("Damages and\nSCC", 0.80, 0.70, 0.16, 0.12, fill = "#F8FAFC", border = "#1D4E89"),
    arr(0.24, 0.70, 0.30, 0.70),
    arr(0.465, 0.70, 0.49, 0.70),
    arr(0.67, 0.70, 0.72, 0.70),
    box("Marginal CO2\npulse", 0.37, 0.50, 0.16, 0.10, fill = "#FFFFFF", border = "#64748B", fontsize = 10.5),
    arr(0.37, 0.55, 0.37, 0.64, col = "#64748B"),
    box("Warming-driven\nwildfire CO2", 0.58, 0.36, 0.20, 0.11, fill = "#FFF7ED", border = "#B45309"),
    box("Residual net,\nnot embedded share", 0.80, 0.36, 0.18, 0.11, fill = "#FFFBEB", border = "#B45309", fontsize = 10.5),
    arr(0.58, 0.64, 0.58, 0.42, col = "#B45309"),
    arr(0.68, 0.36, 0.71, 0.36, col = "#B45309"),
    arr(0.80, 0.42, 0.45, 0.64, col = "#B45309"),
    note("Baseline pathways are exogenous:\nwarming does not internally create new emissions.", 0.25, 0.23, fontsize = 8.8),
    note("The added feedback lets the marginal pulse\nalter fire CO2 through temperature.", 0.76, 0.23, fontsize = 8.8),
    note("Gross fire additions are stress tests; central cases adjust for persistence and double counting.", 0.50, 0.11, fontsize = 10.5, col = "#78350F")
  )
  save_png_pdf(g, "figure_conceptual_audit_schematic", width = 10.8, height = 6.2)
}

make_mechanism_decomposition <- function() {
  physics_path <- file.path(sector_dir, "marginal_pulse_physics_check.csv")
  sector_path <- file.path(sector_dir, "sectoral_scc_summary.csv")
  if (!file.exists(physics_path) || !file.exists(sector_path)) return(invisible(NULL))

  physics <- read_csv(physics_path, show_col_types = FALSE) %>%
    filter(year %in% c(2050, 2100, 2300)) %>%
    select(scenario, year, pulse_delta_co2_ppm, pulse_delta_rf_co2, pulse_delta_T) %>%
    pivot_longer(cols = starts_with("pulse_delta"), names_to = "metric", values_to = "value") %>%
    pivot_wider(names_from = scenario, values_from = value) %>%
    mutate(
      percent_change = 100 * (wildfire - baseline) / abs(baseline),
      metric = recode(metric,
        pulse_delta_co2_ppm = "Pulse concentration",
        pulse_delta_rf_co2 = "Pulse CO2 forcing",
        pulse_delta_T = "Pulse temperature"
      )
    )

  sector <- read_csv(sector_path, show_col_types = FALSE) %>%
    filter(dr_label == "2.0%", scenario == "wildfire-source-uncertainty", sector != "total") %>%
    mutate(
      sector = recode(sector,
        cromar_mortality = "Mortality",
        agriculture = "Agriculture",
        energy = "Energy",
        slr = "Sea level rise",
        .default = sector
      )
    )

  p_physics <- ggplot(physics, aes(factor(year), percent_change, fill = metric)) +
    geom_hline(yintercept = 0, color = "grey45", linewidth = 0.35) +
    geom_col(position = position_dodge(width = 0.72), width = 0.64) +
    scale_fill_manual(values = c(
      "Pulse concentration" = "#2B6CB0",
      "Pulse CO2 forcing" = "#D95F02",
      "Pulse temperature" = "#5B8C5A"
    )) +
    labs(
      title = "Physical response of the marginal pulse",
      subtitle = "Wildfire pathway minus baseline, deterministic source-informed diagnostic.",
      x = NULL,
      y = "Change in pulse response (%)",
      fill = NULL
    ) +
    theme_give(10) +
    theme(legend.position = "bottom")

  p_sector <- ggplot(sector, aes(reorder(sector, delta_mean_scc), delta_mean_scc, fill = sector)) +
    geom_hline(yintercept = 0, color = "grey45", linewidth = 0.35) +
    geom_col(width = 0.62) +
    coord_flip() +
    scale_fill_manual(values = c(
      "Mortality" = "#8C3D78",
      "Agriculture" = "#4F7F39",
      "Energy" = "#C9862B",
      "Sea level rise" = "#3764AD"
    ), guide = "none") +
    labs(
      title = "Sectoral SCC response",
      subtitle = "Mean change in paired source-informed 100-draw diagnostic, 2% case.",
      x = NULL,
      y = "Change in SCC (2020 USD per tCO2)"
    ) +
    theme_give(10)

  combined <- arrangeGrob(
    p_physics, p_sector, ncol = 2, widths = c(1.05, 0.95),
    bottom = textGrob(
      "The higher background stock slightly changes the marginal pulse physics; sectoral effects then depend on local damage curvature and discounting.",
      gp = gpar(fontsize = 8.8, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "figure_mechanism_decomposition", width = 11.2, height = 5.8)
}

extract_ring <- function(ring, feature_id, polygon_id, ring_id, props) {
  coords <- do.call(rbind, lapply(ring, function(pt) c(as.numeric(pt[[1]]), as.numeric(pt[[2]]))))
  data.frame(
    lon = coords[, 1],
    lat = coords[, 2],
    order = seq_len(nrow(coords)),
    group = paste(feature_id, polygon_id, ring_id, sep = "_"),
    iso3 = props$ISO_A3 %||% props$ADM0_A3,
    adm0_a3 = props$ADM0_A3 %||% NA_character_,
    name = props$NAME %||% NA_character_,
    continent = props$CONTINENT %||% NA_character_,
    stringsAsFactors = FALSE
  )
}

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || is.na(x)) y else x

read_world_polygons <- function(path) {
  gj <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  rows <- list()
  k <- 1L
  for (feature_id in seq_along(gj$features)) {
    feature <- gj$features[[feature_id]]
    props <- feature$properties
    geom <- feature$geometry
    if (is.null(geom) || props$NAME == "Antarctica") next
    if (geom$type == "Polygon") {
      polygons <- list(geom$coordinates)
    } else if (geom$type == "MultiPolygon") {
      polygons <- geom$coordinates
    } else {
      next
    }
    for (polygon_id in seq_along(polygons)) {
      rings <- polygons[[polygon_id]]
      for (ring_id in seq_along(rings)) {
        # Draw exterior rings. Interior holes are small at this scale and can
        # confuse simple polygon rendering without an sf dependency.
        if (ring_id > 1) next
        rows[[k]] <- extract_ring(rings[[ring_id]], feature_id, polygon_id, ring_id, props)
        k <- k + 1L
      }
    }
  }
  bind_rows(rows) %>%
    mutate(
      iso3 = if_else(is.na(iso3) | iso3 == "-99", adm0_a3, iso3),
      iso3 = recode(iso3, "SDS" = "SSD", "KOS" = "XKX", .default = iso3)
    ) %>%
    arrange(group, order)
}

world_poly <- read_world_polygons(geojson_path)

make_scc_distribution <- function() {
  distribution_labels <- c(
    baseline = "Baseline",
    `feedback-residual-medium` = "Residual med.",
    `feedback-residual-high` = "Residual high",
    `feedback-resfire-half-gross` = "RESFire half",
    `feedback-resfire-gross` = "RESFire gross"
  )
  samples <- read_csv(file.path(mcs_dir, "all_scc_samples.csv"), show_col_types = FALSE) %>%
    filter(dr_label == "2.0%") %>%
    mutate(
      scenario = factor(scenario, levels = scenario_levels, labels = unname(distribution_labels[scenario_levels])),
      scenario_key = as.character(factor(as.character(scenario), levels = unname(scenario_labels[scenario_levels])))
    )

  cap <- 600
  clipped_counts <- samples %>%
    group_by(scenario) %>%
    summarise(
      n = n(),
      n_clipped = sum(scc_2020usd_per_tco2 > cap),
      mean_scc = mean(scc_2020usd_per_tco2),
      median_scc = median(scc_2020usd_per_tco2),
      .groups = "drop"
    )

  density_data <- samples %>% filter(scc_2020usd_per_tco2 <= cap)
  clipped_labels <- clipped_counts %>%
    mutate(label = paste0(n_clipped, "/", n, " above $", cap), x = cap * 0.985)

  p <- ggplot(density_data, aes(x = scc_2020usd_per_tco2, fill = scenario, color = scenario)) +
    geom_density(alpha = 0.28, linewidth = 0.75, adjust = 0.9, na.rm = TRUE) +
    geom_vline(data = clipped_counts, aes(xintercept = mean_scc, color = scenario), linewidth = 0.75) +
    geom_point(data = clipped_counts, aes(x = median_scc, y = 0, color = scenario), size = 2.2, inherit.aes = FALSE) +
    geom_text(data = clipped_labels, aes(x = x, y = Inf, label = label), inherit.aes = FALSE,
              hjust = 1, vjust = 1.7, size = 3.0, color = "grey25") +
    facet_grid(rows = vars(scenario), scales = "free_y") +
    scale_x_continuous(limits = c(0, cap), breaks = seq(0, cap, by = 100), labels = dollar_format(prefix = "$")) +
    scale_fill_manual(values = unname(scenario_colors[scenario_levels]), guide = "none") +
    scale_color_manual(values = unname(scenario_colors[scenario_levels]), guide = "none") +
    labs(
      title = "SCC distribution, central 2% discount-rate case",
      subtitle = paste0("Right tail truncated at $", cap, "/tCO2; labels report hidden tail counts. Vertical lines are means; points are medians."),
      x = "SCC, 2020 USD per tCO2",
      y = "Density",
      caption = "Paired 100-run validation sample. Means and medians are computed on full samples, not only the visible range."
    ) +
    theme_give(11) +
    theme(panel.grid.major.y = element_blank())

  write_csv(clipped_counts, file.path(out_dir, "scc_distribution_truncation_counts_2pct.csv"))
  save_png_pdf(p, "figure_scc_distribution_truncated_2pct", width = 10.8, height = 7.1)
  return(p)
}

make_paired_delta <- function() {
  samples <- read_csv(file.path(mcs_dir, "all_scc_samples.csv"), show_col_types = FALSE) %>%
    filter(dr_label == "2.0%")
  baseline <- samples %>%
    filter(scenario == "baseline") %>%
    transmute(trial, baseline_scc = scc_2020usd_per_tco2)
  delta <- samples %>%
    filter(scenario != "baseline") %>%
    left_join(baseline, by = "trial") %>%
    mutate(
      delta_scc = scc_2020usd_per_tco2 - baseline_scc,
      scenario = factor(scenario, levels = scenario_levels[-1], labels = unname(scenario_labels[scenario_levels[-1]]))
    )

  delta_cap <- 500
  delta_visible <- delta %>% filter(delta_scc <= delta_cap)
  delta_clipped <- delta %>%
    group_by(scenario) %>%
    summarise(n = n(), n_clipped = sum(delta_scc > delta_cap), .groups = "drop") %>%
    filter(n_clipped > 0) %>%
    mutate(label = paste0(n_clipped, "/", n, " above $", delta_cap), x = delta_cap * 0.98)

  p <- ggplot(delta_visible, aes(x = delta_scc, y = scenario, color = scenario, fill = scenario)) +
    geom_vline(xintercept = 0, color = "grey35") +
    geom_boxplot(width = 0.46, alpha = 0.24, outlier.shape = NA, linewidth = 0.7) +
    geom_jitter(height = 0.12, width = 0, alpha = 0.35, size = 1.2) +
    stat_summary(fun = mean, geom = "point", shape = 23, size = 3.2, color = "white", stroke = 0.5) +
    geom_text(data = delta_clipped, aes(x = x, y = scenario, label = label), inherit.aes = FALSE,
              hjust = 1, size = 3.0, color = "grey25") +
    scale_x_continuous(limits = c(min(-5, min(delta_visible$delta_scc, na.rm = TRUE)), delta_cap),
                       labels = dollar_format(prefix = "$")) +
    scale_fill_manual(values = unname(scenario_colors[scenario_levels[-1]]), guide = "none") +
    scale_color_manual(values = unname(scenario_colors[scenario_levels[-1]]), guide = "none") +
    labs(
      title = "Paired SCC increase relative to baseline",
      subtitle = paste0("Each point subtracts the matched baseline draw from the wildfire-feedback draw; x-axis truncated at $", delta_cap, "/tCO2."),
      x = "SCC change, 2020 USD per tCO2",
      y = NULL,
      caption = "Paired draws hold RFF-SP, FAIR, and discounting samples fixed within trial."
    ) +
    theme_give(11)

  write_csv(delta, file.path(out_dir, "paired_scc_delta_samples_2pct.csv"))
  save_png_pdf(p, "figure_paired_scc_delta_2pct", width = 10.2, height = 5.2)
  return(p)
}

paired_delta_data <- function() {
  samples <- read_csv(file.path(mcs_dir, "all_scc_samples.csv"), show_col_types = FALSE) %>%
    filter(dr_label == "2.0%")
  baseline <- samples %>%
    filter(scenario == "baseline") %>%
    transmute(trial, baseline_scc = scc_2020usd_per_tco2)
  draws <- read_csv(file.path(mcs_dir, "all_feedback_parameter_draws.csv"), show_col_types = FALSE) %>%
    filter(scenario != "baseline") %>%
    mutate(
      effective_feedback_intensity = sensitivity_per_c * net_persistence_fraction * not_embedded_fraction,
      scenario_label = recode(scenario, !!!scenario_labels)
    )
  samples %>%
    filter(scenario != "baseline") %>%
    left_join(baseline, by = "trial") %>%
    left_join(draws, by = c("trial", "scenario")) %>%
    mutate(
      delta_scc = scc_2020usd_per_tco2 - baseline_scc,
      pct_delta = 100 * delta_scc / baseline_scc,
      scenario_label = recode(scenario, !!!scenario_labels),
      scenario_label = factor(scenario_label, levels = unname(scenario_labels[scenario_levels[-1]]))
    )
}

make_delta_interval_figure <- function() {
  delta <- paired_delta_data()
  interval_summary <- delta %>%
    group_by(scenario, scenario_label) %>%
    summarise(
      n = n(),
      mean_delta = mean(delta_scc),
      median_delta = median(delta_scc),
      sd_delta = sd(delta_scc),
      p025_delta = quantile(delta_scc, 0.025),
      p05_delta = quantile(delta_scc, 0.05),
      p25_delta = quantile(delta_scc, 0.25),
      p75_delta = quantile(delta_scc, 0.75),
      p95_delta = quantile(delta_scc, 0.95),
      p975_delta = quantile(delta_scc, 0.975),
      mean_pct_delta = mean(pct_delta),
      median_pct_delta = median(pct_delta),
      p05_pct_delta = quantile(pct_delta, 0.05),
      p95_pct_delta = quantile(pct_delta, 0.95),
      prob_delta_gt_0 = mean(delta_scc > 0),
      prob_delta_gt_1 = mean(delta_scc > 1),
      prob_delta_gt_10 = mean(delta_scc > 10),
      prob_delta_gt_50 = mean(delta_scc > 50),
      .groups = "drop"
    ) %>%
    mutate(
      scenario = factor(scenario, levels = scenario_levels[-1]),
      scenario_label = factor(scenario_label, levels = unname(scenario_labels[scenario_levels[-1]]))
    ) %>%
    arrange(scenario)

  md_path <- file.path(out_dir, "paired_scc_delta_interval_summary_2pct.md")
  write_csv(interval_summary, file.path(out_dir, "paired_scc_delta_interval_summary_2pct.csv"))
  md_rows <- interval_summary %>%
    transmute(
      Scenario = as.character(scenario_label),
      `Mean delta` = sprintf("%.2f", mean_delta),
      `Median delta` = sprintf("%.2f", median_delta),
      `5-95% interval` = sprintf("%.2f to %.2f", p05_delta, p95_delta),
      `2.5-97.5% interval` = sprintf("%.2f to %.2f", p025_delta, p975_delta),
      `Pr(delta > 0)` = sprintf("%.0f%%", 100 * prob_delta_gt_0),
      `Pr(delta > $10)` = sprintf("%.0f%%", 100 * prob_delta_gt_10)
    )
  writeLines(
    c(
      "| Scenario | Mean delta | Median delta | 5-95% interval | 2.5-97.5% interval | Pr(delta > 0) | Pr(delta > $10) |",
      "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
      apply(md_rows, 1, function(row) paste0("| ", paste(row, collapse = " | "), " |"))
    ),
    md_path
  )

  plot_data <- interval_summary %>%
    mutate(scenario_label = factor(scenario_label, levels = rev(levels(delta$scenario_label))))
  label_data <- plot_data %>%
    mutate(
      label_x = pmin(p975_delta, 500) + 9,
      label = paste0("Pr>0: ", sprintf("%.0f%%", 100 * prob_delta_gt_0),
                     "\nPr>$10: ", sprintf("%.0f%%", 100 * prob_delta_gt_10))
    )

  p <- ggplot(plot_data, aes(y = scenario_label)) +
    geom_vline(xintercept = 0, color = "grey35", linewidth = 0.4) +
    geom_segment(aes(x = p025_delta, xend = p975_delta, yend = scenario_label, color = scenario),
                 linewidth = 2.8, alpha = 0.22) +
    geom_segment(aes(x = p05_delta, xend = p95_delta, yend = scenario_label, color = scenario),
                 linewidth = 5.0, alpha = 0.35) +
    geom_segment(aes(x = p25_delta, xend = p75_delta, yend = scenario_label, color = scenario),
                 linewidth = 8.0, alpha = 0.50) +
    geom_point(aes(x = median_delta, color = scenario), size = 3.4) +
    geom_point(aes(x = mean_delta, fill = scenario), shape = 23, color = "white", stroke = 0.45, size = 3.2) +
    geom_text(data = label_data, aes(x = label_x, y = scenario_label, label = label), inherit.aes = FALSE,
              hjust = 0, size = 3.1, color = "grey25", lineheight = 0.9) +
    scale_x_continuous(
      limits = c(min(-8, min(plot_data$p025_delta, na.rm = TRUE)), 560),
      labels = dollar_format(prefix = "$")
    ) +
    scale_color_manual(values = scenario_colors, guide = "none") +
    scale_fill_manual(values = scenario_colors, guide = "none") +
    labs(
      title = "Uncertainty in the SCC change, not only the SCC level",
      subtitle = "Thick, medium and thin bars show 25-75%, 5-95% and 2.5-97.5% paired-delta intervals. Dots are medians; diamonds are means.",
      x = "Paired SCC change relative to baseline, 2020 USD per tCO2",
      y = NULL,
      caption = "Paired 100-draw validation sample, 2% Ramsey case. Percentiles use draw-level SCC_scenario minus SCC_baseline."
    ) +
    theme_give(11)

  save_png_pdf(p, "figure_paired_delta_intervals_2pct", width = 11.0, height = 5.9)
  return(p)
}

make_parameter_uncertainty_figure <- function() {
  draws <- read_csv(file.path(mcs_dir, "all_feedback_parameter_draws.csv"), show_col_types = FALSE) %>%
    filter(scenario != "baseline") %>%
    mutate(
      scenario_label = recode(scenario, !!!scenario_labels),
      scenario_label = factor(scenario_label, levels = unname(scenario_labels[scenario_levels[-1]])),
      effective_feedback_intensity = sensitivity_per_c * net_persistence_fraction * not_embedded_fraction
    )

  param_summary <- draws %>%
    group_by(scenario, scenario_label) %>%
    summarise(
      n = n(),
      beta_mean = mean(sensitivity_per_c),
      beta_p05 = quantile(sensitivity_per_c, 0.05),
      beta_p50 = median(sensitivity_per_c),
      beta_p95 = quantile(sensitivity_per_c, 0.95),
      phi_net_mean = mean(net_persistence_fraction),
      phi_net_p05 = quantile(net_persistence_fraction, 0.05),
      phi_net_p50 = median(net_persistence_fraction),
      phi_net_p95 = quantile(net_persistence_fraction, 0.95),
      phi_missing_mean = mean(not_embedded_fraction),
      phi_missing_p05 = quantile(not_embedded_fraction, 0.05),
      phi_missing_p50 = median(not_embedded_fraction),
      phi_missing_p95 = quantile(not_embedded_fraction, 0.95),
      effective_intensity_mean = mean(effective_feedback_intensity),
      effective_intensity_p05 = quantile(effective_feedback_intensity, 0.05),
      effective_intensity_p50 = median(effective_feedback_intensity),
      effective_intensity_p95 = quantile(effective_feedback_intensity, 0.95),
      .groups = "drop"
    )
  write_csv(param_summary, file.path(out_dir, "wildfire_parameter_draw_summary.csv"))

  long <- draws %>%
    select(scenario, scenario_label, sensitivity_per_c, net_persistence_fraction, not_embedded_fraction, effective_feedback_intensity) %>%
    pivot_longer(
      c(sensitivity_per_c, net_persistence_fraction, not_embedded_fraction, effective_feedback_intensity),
      names_to = "parameter",
      values_to = "value"
    ) %>%
    mutate(
      parameter = recode(
        parameter,
        sensitivity_per_c = "beta: gross response per C",
        net_persistence_fraction = "phi_net: persistent share",
        not_embedded_fraction = "phi_missing: missing share",
        effective_feedback_intensity = "effective beta x phi_net x phi_missing"
      ),
      parameter = factor(
        parameter,
        levels = c(
          "beta: gross response per C",
          "phi_net: persistent share",
          "phi_missing: missing share",
          "effective beta x phi_net x phi_missing"
        )
      )
    )

  p <- ggplot(long, aes(value, scenario_label, fill = scenario, color = scenario)) +
    geom_boxplot(alpha = 0.28, outlier.shape = NA, width = 0.48, linewidth = 0.55) +
    geom_jitter(height = 0.13, width = 0, alpha = 0.33, size = 0.9) +
    facet_wrap(~parameter, scales = "free_x", ncol = 2) +
    scale_fill_manual(values = scenario_colors, guide = "none") +
    scale_color_manual(values = scenario_colors, guide = "none") +
    labs(
      title = "Sampled wildfire-feedback and accounting parameters",
      subtitle = "The residual cases sample physical response, net persistence and missing-share terms; gross stress cases set persistence and missing share to one.",
      x = "Draw value",
      y = NULL,
      caption = "These are exploratory bounded distributions for the 100-draw validation run. phi_missing is an accounting parameter, not a physical parameter."
    ) +
    theme_give(10)

  save_png_pdf(p, "figure_wildfire_parameter_uncertainty_2pct", width = 11.0, height = 7.4)
  return(p)
}

make_uncertainty_source_diagnostic <- function() {
  delta <- paired_delta_data() %>%
    mutate(
      feedback_intensity = sensitivity_per_c * net_persistence_fraction * not_embedded_fraction
    )

  safe_r2 <- function(formula, data) {
    fit <- tryCatch(lm(formula, data = data), error = function(e) NULL)
    if (is.null(fit)) return(NA_real_)
    summary(fit)$r.squared
  }
  safe_cor <- function(x, y) {
    if (sd(x, na.rm = TRUE) == 0 || sd(y, na.rm = TRUE) == 0) return(NA_real_)
    suppressWarnings(cor(x, y, method = "spearman", use = "complete.obs"))
  }

  diagnostic <- delta %>%
    group_by(scenario, scenario_label) %>%
    group_modify(~{
      d <- .x
      tibble(
        n = nrow(d),
        sd_baseline_scc = sd(d$baseline_scc),
        sd_delta_scc = sd(d$delta_scc),
        iqr_delta_scc = IQR(d$delta_scc),
        r2_baseline_state_proxy = safe_r2(delta_scc ~ baseline_scc, d),
        r2_feedback_intensity = safe_r2(delta_scc ~ feedback_intensity, d),
        r2_joint_proxy_model = safe_r2(delta_scc ~ baseline_scc + feedback_intensity, d),
        spearman_baseline_state = safe_cor(d$delta_scc, d$baseline_scc),
        spearman_feedback_intensity = safe_cor(d$delta_scc, d$feedback_intensity),
        spearman_beta = safe_cor(d$delta_scc, d$sensitivity_per_c),
        spearman_phi_net = safe_cor(d$delta_scc, d$net_persistence_fraction),
        spearman_phi_missing = safe_cor(d$delta_scc, d$not_embedded_fraction)
      )
    }) %>%
    ungroup()
  write_csv(diagnostic, file.path(out_dir, "uncertainty_source_diagnostics_2pct.csv"))

  r2_plot <- diagnostic %>%
    select(scenario, scenario_label, r2_baseline_state_proxy, r2_feedback_intensity, r2_joint_proxy_model) %>%
    pivot_longer(starts_with("r2_"), names_to = "diagnostic", values_to = "r2") %>%
    mutate(
      diagnostic = recode(
        diagnostic,
        r2_baseline_state_proxy = "Baseline SCC draw only",
        r2_feedback_intensity = "Fire intensity only",
        r2_joint_proxy_model = "Both proxies"
      ),
      diagnostic = factor(diagnostic, levels = c("Baseline SCC draw only", "Fire intensity only", "Both proxies")),
      scenario_label = factor(scenario_label, levels = rev(unname(scenario_labels[scenario_levels[-1]])))
    )

  sd_plot <- diagnostic %>%
    select(scenario, scenario_label, sd_baseline_scc, sd_delta_scc) %>%
    pivot_longer(c(sd_baseline_scc, sd_delta_scc), names_to = "metric", values_to = "sd") %>%
    mutate(
      metric = recode(
        metric,
        sd_baseline_scc = "Baseline SCC spread",
        sd_delta_scc = "Paired-delta spread"
      ),
      scenario_label = factor(scenario_label, levels = rev(unname(scenario_labels[scenario_levels[-1]])))
    )

  p_r2 <- ggplot(r2_plot, aes(r2, scenario_label, fill = diagnostic)) +
    geom_col(position = position_dodge(width = 0.72), width = 0.62) +
    scale_x_continuous(labels = label_percent(accuracy = 1), limits = c(0, 1)) +
    scale_fill_manual(values = c(
      "Baseline SCC draw only" = "#5B6C8C",
      "Fire intensity only" = "#D95F02",
      "Both proxies" = "#2B6CB0"
    )) +
    labs(
      title = "Descriptive drivers of paired-delta variation",
      subtitle = "R2 from simple proxy regressions; diagnostic only, not a formal Sobol decomposition.",
      x = "Share of delta variance explained",
      y = NULL,
      fill = NULL
    ) +
    theme_give(10) +
    theme(legend.position = "bottom")

  p_sd <- ggplot(sd_plot, aes(sd, scenario_label, fill = metric)) +
    geom_col(position = position_dodge(width = 0.72), width = 0.62) +
    scale_x_continuous(labels = dollar_format(prefix = "$")) +
    scale_fill_manual(values = c("Baseline SCC spread" = "#94A3B8", "Paired-delta spread" = "#E4572E")) +
    labs(
      title = "Baseline uncertainty versus feedback-effect uncertainty",
      subtitle = "The baseline SCC distribution is much wider than residual feedback deltas in the 100-draw validation sample.",
      x = "Standard deviation, 2020 USD per tCO2",
      y = NULL,
      fill = NULL
    ) +
    theme_give(10) +
    theme(legend.position = "bottom")

  combined <- arrangeGrob(
    p_sd, p_r2, ncol = 1, heights = c(0.95, 1.05),
    bottom = textGrob(
      "Uncertainty separation is limited by the 100-draw design: GIVE uncertainty and wildfire-parameter uncertainty are paired rather than factorially crossed.",
      gp = gpar(fontsize = 8.8, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "figure_uncertainty_source_diagnostics_2pct", width = 11.0, height = 10.2)
  return(combined)
}

make_scc_distribution_and_delta <- function(distribution_plot, delta_plot) {
  combined <- arrangeGrob(
    distribution_plot,
    delta_plot,
    ncol = 1,
    heights = c(1.25, 0.92),
    bottom = textGrob(
      "SCC densities are visually truncated at $600/tCO2; all means, medians and paired deltas use the full untruncated 100-draw validation samples.",
      gp = gpar(fontsize = 8.8, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "figure_scc_distribution_and_delta_2pct", width = 11.0, height = 12.4)
}

source_country_proxy <- function() {
  tribble(
    ~iso3, ~source_region, ~gross_source_index, ~residual_added_stock_index, ~double_counting_risk,
    "CAN", "Boreal Canada", 1.00, 0.95, "medium",
    "RUS", "Siberia and Far East Russia", 1.00, 0.95, "medium",
    "USA", "Alaska / western United States", 0.55, 0.45, "medium",
    "BRA", "Amazon and Cerrado", 0.45, 0.20, "high",
    "BOL", "Amazon and Cerrado", 0.45, 0.20, "high",
    "PER", "Amazon and Cerrado", 0.35, 0.16, "high",
    "COL", "Amazon and Cerrado", 0.30, 0.14, "high",
    "VEN", "Amazon and Cerrado", 0.30, 0.14, "high",
    "PRY", "Amazon and Cerrado", 0.30, 0.14, "high",
    "ARG", "South American fire/grassland margin", 0.22, 0.10, "high",
    "COD", "Congo basin and southern Africa", 0.35, 0.15, "high",
    "COG", "Congo basin and southern Africa", 0.35, 0.15, "high",
    "CAF", "Congo basin and southern Africa", 0.30, 0.13, "high",
    "CMR", "Congo basin and southern Africa", 0.28, 0.12, "high",
    "GAB", "Congo basin and southern Africa", 0.26, 0.11, "high",
    "AGO", "Congo basin and southern Africa", 0.34, 0.15, "high",
    "ZMB", "Congo basin and southern Africa", 0.32, 0.14, "high",
    "MOZ", "Congo basin and southern Africa", 0.28, 0.12, "high",
    "TZA", "Congo basin and southern Africa", 0.26, 0.11, "high",
    "ZAF", "Congo basin and southern Africa", 0.22, 0.10, "high",
    "IDN", "Indonesia and peat Southeast Asia", 0.50, 0.20, "high",
    "MYS", "Indonesia and peat Southeast Asia", 0.35, 0.14, "high",
    "PNG", "Indonesia and peat Southeast Asia", 0.30, 0.12, "high",
    "AUS", "Australia", 0.40, 0.20, "medium",
    "ESP", "Mediterranean Europe", 0.25, 0.15, "high",
    "PRT", "Mediterranean Europe", 0.25, 0.15, "high",
    "FRA", "Mediterranean Europe", 0.18, 0.10, "high",
    "ITA", "Mediterranean Europe", 0.22, 0.13, "high",
    "GRC", "Mediterranean Europe", 0.24, 0.14, "high",
    "TUR", "Mediterranean Europe", 0.22, 0.12, "high"
  )
}

make_source_maps <- function() {
  proxy <- source_country_proxy()
  write_csv(proxy, file.path(out_dir, "fire_source_country_proxy.csv"))

  map_data <- world_poly %>%
    left_join(proxy, by = "iso3") %>%
    arrange(group, order)

  label_points <- tribble(
    ~label, ~lon, ~lat,
    "Canada", -105, 58,
    "Russia", 95, 61,
    "Amazon/Cerrado", -58, -11,
    "Congo + southern Africa", 24, -13,
    "Indonesia/peat", 113, -4,
    "Australia", 135, -26
  )

  panel_map <- function(fill_col, title, subtitle) {
    ggplot(map_data, aes(lon, lat, group = group)) +
      geom_polygon(aes(fill = .data[[fill_col]]), color = "white", linewidth = 0.08) +
      geom_text(data = label_points, aes(lon, lat, label = label), inherit.aes = FALSE,
                size = 3.0, fontface = "bold", color = "grey15") +
      coord_quickmap(xlim = c(-180, 180), ylim = c(-58, 84), expand = FALSE) +
      scale_fill_gradientn(
        colors = c("#F2EFE9", "#F7C59F", "#D95F02", "#8C2D04"),
        values = rescale(c(0, 0.2, 0.55, 1.0)),
        limits = c(0, 1),
        na.value = "grey90",
        name = "Proxy index"
      ) +
      labs(title = title, subtitle = subtitle, x = NULL, y = NULL) +
      theme_void(base_size = 10) +
      theme(
        plot.title = element_text(face = "bold", size = 13),
        plot.subtitle = element_text(color = "grey30", size = 9),
        legend.position = "bottom"
      )
  }

  p1 <- panel_map(
    "gross_source_index",
    "Gross climate-sensitive fire-carbon source proxy",
    "Index = qualitative 0-1 relative source weight for gross climate-sensitive fire CO2 pressure."
  )
  p2 <- panel_map(
    "residual_added_stock_index",
    "Residual not-embedded stock-addition proxy",
    "Index = gross proxy downweighted for regrowth, AFOLU/inventory overlap and double-counting risk."
  )

  combined <- arrangeGrob(
    p1, p2, ncol = 1,
    top = textGrob(
      "Additional wildfire CO2 source proxies over actual country boundaries",
      gp = gpar(fontsize = 16, fontface = "bold"),
      x = 0.01, hjust = 0
    ),
    bottom = textGrob(
      "Proxy definition: hand-coded, literature-motivated 0-1 country index for where climate-sensitive fire-carbon additions plausibly originate.\nIt is not an emissions inventory, not a model output, and not a damage map.",
      gp = gpar(fontsize = 9, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "figure_fire_source_country_proxy_map", width = 11.2, height = 9.8)
}

make_fire_scale_figure <- function() {
  det_path <- file.path(scale_dir, "fire_scale_check_deterministic.csv")
  src_path <- file.path(sector_dir, "fire_scale_check_source_informed_mean.csv")
  if (!file.exists(det_path) || !file.exists(src_path)) {
    warning("Scale-check CSVs missing; skipping scale figure.")
    return(invisible(NULL))
  }

  det <- read_csv(det_path, show_col_types = FALSE) %>%
    transmute(
      scenario = recode(scenario, !!!scenario_labels),
      year,
      annual_share_pct = annual_fire_share_of_baseline_co2_emissions_pct,
      atmospheric_stock_pct = atmospheric_co2_c_stock_increase_pct
    )
  src <- read_csv(src_path, show_col_types = FALSE) %>%
    transmute(
      scenario = "Source-informed mean path",
      year,
      annual_share_pct = annual_fire_share_of_baseline_co2_emissions_pct,
      atmospheric_stock_pct = atmospheric_co2_c_stock_increase_pct
    )
  scale_data <- bind_rows(det, src) %>%
    filter(year >= 2030) %>%
    pivot_longer(
      c(annual_share_pct, atmospheric_stock_pct),
      names_to = "metric",
      values_to = "value_pct"
    ) %>%
    mutate(
      metric = recode(
        metric,
        annual_share_pct = "Added fire CO2 flow as share of baseline CO2 emissions",
        atmospheric_stock_pct = "Added atmospheric CO2-C stock as share of baseline stock"
      ),
      scenario = factor(
        scenario,
        levels = c(
          "Residual medium",
          "Residual high",
          "Source-informed mean path",
          "RESFire half-gross stress",
          "RESFire gross stress"
        )
      )
    )

  p <- ggplot(scale_data, aes(year, value_pct, color = scenario)) +
    geom_line(linewidth = 0.75) +
    geom_point(size = 2.0) +
    facet_wrap(~metric, ncol = 1, scales = "free_y") +
    scale_color_manual(values = c(
      "Residual medium" = "#00A878",
      "Residual high" = "#E4572E",
      "Source-informed mean path" = "#2B6CB0",
      "RESFire half-gross stress" = "#7B2CBF",
      "RESFire gross stress" = "#F4A261"
    ), na.value = "grey50") +
    scale_y_continuous(labels = label_percent(scale = 1)) +
    labs(
      title = "Scale of the added wildfire CO2 pathway",
      subtitle = "Annual flow shares can look large while atmospheric-stock shares remain much smaller.",
      x = NULL,
      y = "Percent",
      color = NULL,
      caption = "Flow denominator is GIVE/RFF-SP aggregate CO2 emissions, not fossil-only emissions. Stock denominator uses baseline atmospheric CO2-C from FAIR."
    ) +
    theme_give(11) +
    theme(legend.position = "bottom")

  save_png_pdf(p, "figure_fire_scale_shares", width = 10.8, height = 7.0)
}

make_incremental_damage_maps <- function() {
  path <- file.path(regional_dir, "regional_damage_delta_by_country.csv")
  if (!file.exists(path)) {
    warning("Regional damage diagnostics missing; skipping incremental damage maps.")
    return(invisible(NULL))
  }

  damage <- read_csv(path, show_col_types = FALSE) %>%
    mutate(
      pv_damage_billion = cumulative_discounted_damage_delta_billion_2020usd,
      pv_damage_per_person = cumulative_discounted_damage_delta_2020usd_per_2020_person,
      core_scc_delta = incremental_scc_core_delta_2020usd_per_tco2
    )

  map_data <- world_poly %>%
    left_join(damage, by = "iso3") %>%
    arrange(group, order)

  nonnegative_map <- function(fill_col, title, subtitle, legend_title, labels_fun, breaks = waiver()) {
    ggplot(map_data, aes(lon, lat, group = group)) +
      geom_polygon(aes(fill = pmax(.data[[fill_col]], 0)), color = "white", linewidth = 0.06) +
      coord_quickmap(xlim = c(-180, 180), ylim = c(-58, 84), expand = FALSE) +
      scale_fill_gradientn(
        colors = c("#F3F0EA", "#F7C59F", "#D95F02", "#8C2D04"),
        trans = "sqrt",
        breaks = breaks,
        na.value = "grey88",
        labels = labels_fun,
        name = legend_title
      ) +
      guides(fill = guide_colorbar(barwidth = unit(2.7, "in"), barheight = unit(0.18, "in"))) +
      labs(title = title, subtitle = subtitle, x = NULL, y = NULL) +
      theme_void(base_size = 10) +
      theme(
        plot.title = element_text(face = "bold", size = 12.5),
        plot.subtitle = element_text(color = "grey30", size = 8.8),
        legend.position = "bottom"
      )
  }

  p_abs <- nonnegative_map(
    "pv_damage_billion",
    "Present value of added core damages",
    "Billion 2020 USD, discounted with the 2% Ramsey specification.",
    "Billion $",
    label_number(accuracy = 1),
    breaks = c(0, 500, 1000, 2000)
  )
  p_pc <- nonnegative_map(
    "pv_damage_per_person",
    "Present value per 2020 resident",
    "2020 USD per person; same damages divided by 2020 population.",
    "$/person",
    dollar_format(prefix = "$", accuracy = 1),
    breaks = c(0, 10000, 20000, 30000)
  )

  combined <- arrangeGrob(
    p_abs, p_pc, ncol = 1,
    top = textGrob(
      "Where the added wildfire CO2 pathway increases modeled climate damages",
      gp = gpar(fontsize = 16, fontface = "bold"),
      x = 0.01, hjust = 0
    ),
    bottom = textGrob(
      "Diagnostic country allocation for the deterministic source-informed mean pathway. Includes GIVE core temperature mortality, energy and agriculture only;\nexcludes CIAM sea-level damages, smoke mortality and non-CO2 fire forcers. Agriculture is allocated from FUND regions to countries by GDP share.",
      gp = gpar(fontsize = 8.5, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )

  save_png_pdf(combined, "figure_incremental_damage_country_map", width = 11.2, height = 9.5)

  scc_map <- ggplot(map_data, aes(lon, lat, group = group)) +
    geom_polygon(aes(fill = core_scc_delta), color = "white", linewidth = 0.06) +
    coord_quickmap(xlim = c(-180, 180), ylim = c(-58, 84), expand = FALSE) +
    scale_fill_gradient2(
      low = "#2B6CB0",
      mid = "#F5F2EC",
      high = "#B23A48",
      midpoint = 0,
      breaks = c(-0.10, -0.05, 0.00, 0.05),
      na.value = "grey88",
      labels = label_number(accuracy = 0.001),
      name = "$/tCO2"
    ) +
    guides(fill = guide_colorbar(barwidth = unit(3.2, "in"), barheight = unit(0.18, "in"))) +
    labs(
      title = "Country contribution to the core-sector SCC change",
      subtitle = "Wildfire-path marginal damages minus baseline marginal damages; positive values raise the core SCC.",
      x = NULL,
      y = NULL,
      caption = "Core sectors only: mortality, energy and agriculture. Sea-level rise and smoke mortality are not allocated here."
    ) +
    theme_void(base_size = 10) +
    theme(
      plot.title = element_text(face = "bold", size = 15),
      plot.subtitle = element_text(color = "grey30"),
      plot.caption = element_text(color = "grey35", hjust = 0),
      legend.position = "bottom"
    )
  save_png_pdf(scc_map, "figure_incremental_core_scc_country_map", width = 11.2, height = 5.8)
}

make_incremental_damage_top_countries <- function() {
  path <- file.path(regional_dir, "top20_total_incremental_damage_countries.csv")
  if (!file.exists(path)) {
    warning("Top-country diagnostics missing; skipping top-country figure.")
    return(invisible(NULL))
  }

  top <- read_csv(path, show_col_types = FALSE) %>%
    slice_max(cumulative_discounted_damage_delta_billion_2020usd, n = 12) %>%
    mutate(country = factor(country, levels = rev(country))) %>%
    select(
      country,
      mortality = cumulative_discounted_mortality_delta_billion_2020usd,
      energy = cumulative_discounted_energy_delta_billion_2020usd,
      agriculture = cumulative_discounted_agriculture_delta_billion_2020usd,
      total = cumulative_discounted_damage_delta_billion_2020usd
    ) %>%
    pivot_longer(c(mortality, energy, agriculture), names_to = "sector", values_to = "pv_billion") %>%
    mutate(
      sector = recode(
        sector,
        mortality = "Temperature mortality",
        energy = "Energy",
        agriculture = "Agriculture"
      )
    )

  p <- ggplot(top, aes(x = pv_billion, y = country, fill = sector)) +
    geom_vline(xintercept = 0, color = "grey45", linewidth = 0.35) +
    geom_col(width = 0.72) +
    scale_fill_manual(values = c(
      "Temperature mortality" = "#8C3D78",
      "Energy" = "#C9862B",
      "Agriculture" = "#4F7F39"
    )) +
    scale_x_continuous(labels = label_number(suffix = "B")) +
    labs(
      title = "Largest modeled damage increases from the added wildfire CO2 path",
      subtitle = "Present-value core damages through 2300, by GIVE sector. Negative segments are benefits or reduced damages in that module.",
      x = "Billion 2020 USD, discounted with 2% Ramsey specification",
      y = NULL,
      fill = NULL,
      caption = "Source-informed mean wildfire CO2 pathway. Core damages only; agriculture is allocated from FUND regions by country GDP share."
    ) +
    theme_give(11) +
    theme(legend.position = "bottom")

  save_png_pdf(p, "figure_incremental_damage_top_countries", width = 10.8, height = 6.3)
}

make_give_region_maps <- function() {
  read_mapping <- function(path) read_csv(path, show_col_types = FALSE, locale = locale(encoding = "UTF-8"))
  gcam <- read_mapping(file.path(repo, "packages", "MimiGIVE", "data", "Mapping_countries_to_gcam_energy_regions.csv")) %>%
    rename(iso3 = ISO3, region = gcamregion) %>%
    mutate(system = "Energy damages: GCAM regions")
  fund <- read_mapping(file.path(repo, "packages", "MimiGIVE", "data", "Mapping_countries_to_fund_regions.csv")) %>%
    rename(iso3 = ISO3, region = fundregion) %>%
    mutate(system = "Agriculture damages: FUND regions")
  cromar <- read_mapping(file.path(repo, "packages", "MimiGIVE", "data", "Mapping_countries_to_cromar_mortality_regions.csv")) %>%
    rename(iso3 = ISO3, region = cromar_region) %>%
    mutate(system = "Mortality damages: Cromar regions")

  make_panel <- function(mapping, title) {
    dat <- world_poly %>%
      left_join(mapping %>% select(iso3, region), by = "iso3") %>%
      arrange(group, order)
    regions <- sort(unique(na.omit(dat$region)))
    pal <- setNames(viridis(length(regions), option = "turbo", begin = 0.05, end = 0.95), regions)
    ggplot(dat, aes(lon, lat, group = group)) +
      geom_polygon(aes(fill = region), color = "white", linewidth = 0.06) +
      coord_quickmap(xlim = c(-180, 180), ylim = c(-58, 84), expand = FALSE) +
      scale_fill_manual(values = pal, na.value = "grey88", name = NULL) +
      guides(fill = guide_legend(ncol = 2, override.aes = list(linewidth = 0))) +
      labs(title = title, x = NULL, y = NULL) +
      theme_void(base_size = 9) +
      theme(
        plot.title = element_text(face = "bold", size = 12),
        legend.text = element_text(size = 6.8),
        legend.position = "bottom",
        legend.key.size = unit(0.16, "in")
      )
  }

  p_energy <- make_panel(gcam, "GCAM energy regions")
  p_ag <- make_panel(fund, "FUND agriculture regions")
  p_mort <- make_panel(cromar, "Cromar mortality regions")
  combined <- arrangeGrob(
    p_energy, p_ag, p_mort, ncol = 1,
    top = textGrob(
      "Country-to-region systems used by GIVE damage modules",
      gp = gpar(fontsize = 16, fontface = "bold"),
      x = 0.01, hjust = 0
    ),
    bottom = textGrob(
      "GIVE's SCC object is global/sectoral here. Sector modules use different regional mappings; CIAM sea-level damages operate at coastal country/segment level.",
      gp = gpar(fontsize = 9, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "appendix_give_damage_region_maps", width = 11.2, height = 13.0)
}

make_sector_damage_figure <- function() {
  summary_path <- file.path(sector_dir, "sectoral_marginal_damage_summary_2pct.csv")
  diff_path <- file.path(sector_dir, "sectoral_marginal_damage_difference_2pct.csv")
  if (!file.exists(summary_path) || !file.exists(diff_path)) {
    warning("Sector diagnostics missing; skipping sector figure.")
    return(invisible(NULL))
  }
  md <- read_csv(summary_path, show_col_types = FALSE) %>%
    filter(sector != "total") %>%
    mutate(
      sector = recode(
        sector,
        cromar_mortality = "Mortality",
        agriculture = "Agriculture",
        energy = "Energy",
        slr = "Sea level rise",
        .default = sector
      ),
      scenario = recode(
        scenario,
        baseline = "Baseline",
        `wildfire-source-uncertainty` = "Added wildfire CO2"
      )
    )
  diff <- read_csv(diff_path, show_col_types = FALSE) %>%
    filter(sector != "total") %>%
    mutate(
      sector = recode(
        sector,
        cromar_mortality = "Mortality",
        agriculture = "Agriculture",
        energy = "Energy",
        slr = "Sea level rise",
        .default = sector
      )
    )

  sector_order <- c("Mortality", "Agriculture", "Energy", "Sea level rise")
  md$sector <- factor(md$sector, levels = sector_order)
  diff$sector <- factor(diff$sector, levels = sector_order)

  p_abs <- ggplot(md, aes(year, mean_md_2020usd_per_tco2, color = scenario)) +
    geom_line(linewidth = 0.55) +
    facet_wrap(~sector, scales = "free_y", ncol = 2) +
    scale_color_manual(values = c("Baseline" = "#2B6CB0", "Added wildfire CO2" = "#D95F02")) +
    labs(
      title = "Projected marginal damages by sector",
      subtitle = "Baseline versus added wildfire CO2 component; mean annual marginal damages, undiscounted.",
      x = NULL,
      y = "Mean marginal damages\n(2020 USD per tCO2 per year)",
      color = NULL
    ) +
    theme_give(10) +
    theme(legend.position = "bottom")

  p_delta <- ggplot(diff, aes(year, delta_mean_md_2020usd_per_tco2, color = sector)) +
    geom_hline(yintercept = 0, color = "grey40", linewidth = 0.35) +
    geom_line(linewidth = 0.7) +
    facet_wrap(~sector, scales = "free_y", ncol = 2) +
    scale_color_manual(values = c(
      "Mortality" = "#8C3D78",
      "Agriculture" = "#4F7F39",
      "Energy" = "#C9862B",
      "Sea level rise" = "#3764AD"
    ), guide = "none") +
    labs(
      title = "Wildfire CO2 effect on sectoral marginal damages",
      subtitle = "Wildfire minus baseline. This is the saved source-informed sector diagnostic, not a geographic damage allocation.",
      x = "Year",
      y = "Change in mean marginal damages\n(2020 USD per tCO2 per year)"
    ) +
    theme_give(10)

  combined <- arrangeGrob(
    p_abs, p_delta, ncol = 1, heights = c(1.05, 1.0),
    bottom = textGrob(
      "Source: output/wildfire_sectoral_diagnostics_100 with save_md=true and compute_sectoral_values=true.",
      gp = gpar(fontsize = 8.5, col = "grey35"),
      x = 0.01, hjust = 0
    )
  )
  save_png_pdf(combined, "figure_sectoral_marginal_damages_baseline_vs_wildfire", width = 11.0, height = 12.2)
}

make_conceptual_audit_schematic()
scc_distribution_plot <- make_scc_distribution()
paired_delta_plot <- make_paired_delta()
make_scc_distribution_and_delta(scc_distribution_plot, paired_delta_plot)
make_delta_interval_figure()
make_parameter_uncertainty_figure()
make_uncertainty_source_diagnostic()
make_source_maps()
make_fire_scale_figure()
make_incremental_damage_maps()
make_incremental_damage_top_countries()
make_give_region_maps()
make_sector_damage_figure()
make_mechanism_decomposition()

cat("Wrote PNG/PDF figures to: ", out_dir, "\n", sep = "")

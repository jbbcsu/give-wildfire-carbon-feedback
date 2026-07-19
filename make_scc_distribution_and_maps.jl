#!/usr/bin/env julia

# Create publication-oriented SCC distribution figures and transparent spatial
# proxy maps for the wildfire-carbon feedback experiment.
#
# The maps are intentionally not labeled as GIVE regional damage output. The
# implemented wildfire feedback is a global CO2 addition to FAIR, so the maps
# show source-side fire-carbon pressure and a mechanism schematic.

using CSVFiles
using DataFrames
using Statistics

const DEFAULT_MCS_DIR =
    joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback_mcs_100_paired")
const DEFAULT_OUTPUT_DIR = joinpath(@__DIR__, "manuscript", "figures", "creative")

const SCENARIO_ORDER = [
    "baseline",
    "feedback-residual-medium",
    "feedback-residual-high",
    "feedback-resfire-half-gross",
    "feedback-resfire-gross",
]

const SCENARIO_LABELS = Dict(
    "baseline" => "Baseline",
    "feedback-residual-medium" => "Residual medium",
    "feedback-residual-high" => "Residual high",
    "feedback-resfire-half-gross" => "RESFire half-gross stress",
    "feedback-resfire-gross" => "RESFire gross stress",
)

const SCENARIO_COLORS = Dict(
    "baseline" => "#2B6CB0",
    "feedback-residual-medium" => "#00A878",
    "feedback-residual-high" => "#E4572E",
    "feedback-resfire-half-gross" => "#7B2CBF",
    "feedback-resfire-gross" => "#F4A261",
)

const MAP_SOURCE = "#D95F02"
const MAP_RESIDUAL = "#1B9E77"
const MAP_HIGH_RISK = "#B2182B"

function escape_xml(x)
    s = string(x)
    s = replace(s, "&" => "&amp;")
    s = replace(s, "<" => "&lt;")
    s = replace(s, ">" => "&gt;")
    s = replace(s, "\"" => "&quot;")
    return replace(s, "'" => "&apos;")
end

function as_float(x)
    if ismissing(x)
        return missing
    elseif x isa Real
        return Float64(x)
    else
        s = strip(string(x))
        lowercase(s) == "na" && return missing
        return parse(Float64, replace(s, "," => ""))
    end
end

function dr_to_float(x)
    if x isa Real
        return Float64(x)
    end
    s = strip(string(x))
    if endswith(s, "%")
        return parse(Float64, replace(s, "%" => "")) / 100.0
    end
    return parse(Float64, s)
end

function filter_discount_rate(df::DataFrame, target::Float64)
    keep = [isapprox(dr_to_float(row.dr_label), target; atol = 1e-10) for row in eachrow(df)]
    out = df[keep, :]
    out[!, :scc_2020usd_per_tco2] = as_float.(out[!, :scc_2020usd_per_tco2])
    return out[.!ismissing.(out.scc_2020usd_per_tco2), :]
end

function scenario_rank(scenario::AbstractString)
    idx = findfirst(==(scenario), SCENARIO_ORDER)
    return isnothing(idx) ? length(SCENARIO_ORDER) + 1 : idx
end

function sorted_scenarios(df::DataFrame)
    return sort(collect(unique(string.(df.scenario))), by = scenario_rank)
end

function scenario_label(scenario::AbstractString)
    return get(SCENARIO_LABELS, scenario, scenario)
end

function scenario_color(scenario::AbstractString)
    return get(SCENARIO_COLORS, scenario, "#666666")
end

function quant(v, p)
    return quantile(collect(skipmissing(v)), p)
end

function polyline(points)
    return join(["$(round(x, digits = 2)),$(round(y, digits = 2))" for (x, y) in points], " ")
end

function polygon(points)
    return polyline(points)
end

function nice_upper(x; step = 50.0)
    return step * ceil(x / step)
end

function histogram_density(values::Vector{Float64}, xmin::Float64, xmax::Float64, bins::Int)
    edges = collect(range(xmin, xmax; length = bins + 1))
    centers = [(edges[i] + edges[i + 1]) / 2 for i in 1:bins]
    counts = zeros(Float64, bins)
    width = edges[2] - edges[1]
    for value in values
        if xmin <= value <= xmax
            idx = clamp(floor(Int, (value - xmin) / width) + 1, 1, bins)
            counts[idx] += 1
        end
    end
    density = counts ./ max(length(values) * width, eps())

    # Small triangular smooth so ridges read as densities without depending on
    # plotting packages outside the archived GIVE environment.
    smoothed = copy(density)
    for i in eachindex(density)
        left = i > 1 ? density[i - 1] : density[i]
        right = i < length(density) ? density[i + 1] : density[i]
        smoothed[i] = 0.25 * left + 0.5 * density[i] + 0.25 * right
    end
    return centers, smoothed
end

function write_ridgeline_svg(samples::DataFrame, output_path::String; dr_label = "2.0%")
    scenarios = sorted_scenarios(samples)
    all_values = Float64.(samples.scc_2020usd_per_tco2)
    xmax = nice_upper(maximum(all_values) * 1.03; step = 100.0)
    xmin = 0.0
    width, height = 1120, 720
    left, right, top, bottom = 130, 42, 86, 84
    plot_w = width - left - right
    plot_h = height - top - bottom
    lane_gap = plot_h / max(length(scenarios), 1)
    ridge_height = 0.62 * lane_gap
    bins = 70

    xscale(x) = left + (x - xmin) / (xmax - xmin) * plot_w

    max_density = 0.0
    density_cache = Dict{String, Tuple{Vector{Float64}, Vector{Float64}}}()
    for scenario in scenarios
        vals = Float64.(samples[samples.scenario .== scenario, :scc_2020usd_per_tco2])
        centers, density = histogram_density(vals, xmin, xmax, bins)
        density_cache[scenario] = (centers, density)
        max_density = max(max_density, maximum(density))
    end
    max_density = max(max_density, eps())

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">SCC distribution under wildfire-carbon feedback scenarios</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">Paired 100-run Monte Carlo validation sample; central $(escape_xml(dr_label)) discount-rate case. Lines show mean and median.</text>""")

        for tick in 0:100:Int(xmax)
            x = xscale(tick)
            println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + plot_h)" stroke="#E8E8E8" stroke-width="1"/>""")
            println(io, """<text x="$x" y="$(height - bottom + 28)" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">$tick</text>""")
        end
        println(io, """<line x1="$left" y1="$(height - bottom)" x2="$(left + plot_w)" y2="$(height - bottom)" stroke="#222" stroke-width="1"/>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 22)" text-anchor="middle" font-family="Arial" font-size="13" fill="#222">2020 USD per tCO2</text>""")

        for (i, scenario) in enumerate(scenarios)
            base_y = top + i * lane_gap - 0.18 * lane_gap
            vals = Float64.(samples[samples.scenario .== scenario, :scc_2020usd_per_tco2])
            centers, density = density_cache[scenario]
            color = scenario_color(scenario)
            top_points = [(xscale(centers[j]), base_y - density[j] / max_density * ridge_height) for j in eachindex(centers)]
            bottom_points = [(xscale(centers[j]), base_y) for j in reverse(eachindex(centers))]
            pts = vcat(top_points, bottom_points)
            println(io, """<line x1="$left" y1="$base_y" x2="$(left + plot_w)" y2="$base_y" stroke="#CFCFCF" stroke-width="1"/>""")
            println(io, """<polygon points="$(polygon(pts))" fill="$color" fill-opacity="0.28" stroke="$color" stroke-width="2"/>""")
            m = mean(vals)
            med = median(vals)
            p05 = quant(vals, 0.05)
            p95 = quant(vals, 0.95)
            println(io, """<line x1="$(xscale(p05))" y1="$(base_y + 5)" x2="$(xscale(p95))" y2="$(base_y + 5)" stroke="$color" stroke-width="5" stroke-linecap="round" opacity="0.42"/>""")
            println(io, """<line x1="$(xscale(m))" y1="$(base_y - ridge_height - 8)" x2="$(xscale(m))" y2="$(base_y + 10)" stroke="$color" stroke-width="2.2"/>""")
            println(io, """<circle cx="$(xscale(med))" cy="$(base_y - ridge_height - 2)" r="5.2" fill="#FFFFFF" stroke="$color" stroke-width="2"/>""")
            println(io, """<text x="$(left - 12)" y="$(base_y + 4)" text-anchor="end" font-family="Arial" font-size="13" font-weight="700" fill="#222">$(escape_xml(scenario_label(scenario)))</text>""")
            println(io, """<text x="$(xscale(m) + 5)" y="$(base_y - ridge_height - 12)" font-family="Arial" font-size="10.5" fill="$color">mean $(round(m, digits = 1))</text>""")
            println(io, """<text x="$(xscale(med) + 7)" y="$(base_y - ridge_height + 3)" font-family="Arial" font-size="10.5" fill="#333">median $(round(med, digits = 1))</text>""")
        end

        legend_x, legend_y = left, 76
        println(io, """<line x1="$legend_x" y1="$legend_y" x2="$(legend_x + 28)" y2="$legend_y" stroke="#444" stroke-width="2"/>""")
        println(io, """<text x="$(legend_x + 36)" y="$(legend_y + 4)" font-family="Arial" font-size="11" fill="#444">mean</text>""")
        println(io, """<circle cx="$(legend_x + 96)" cy="$legend_y" r="5" fill="#FFFFFF" stroke="#444" stroke-width="2"/>""")
        println(io, """<text x="$(legend_x + 108)" y="$(legend_y + 4)" font-family="Arial" font-size="11" fill="#444">median</text>""")
        println(io, "</svg>")
    end
end

function paired_delta_frame(samples::DataFrame)
    base_rows = samples[samples.scenario .== "baseline", :]
    baseline = Dict(Int(row.trial) => Float64(row.scc_2020usd_per_tco2) for row in eachrow(base_rows))
    out = DataFrame(
        scenario = String[],
        trial = Int[],
        baseline_scc = Float64[],
        scenario_scc = Float64[],
        delta_scc = Float64[],
        percent_delta_scc = Float64[],
    )
    for row in eachrow(samples)
        scenario = string(row.scenario)
        scenario == "baseline" && continue
        trial = Int(row.trial)
        haskey(baseline, trial) || continue
        b = baseline[trial]
        s = Float64(row.scc_2020usd_per_tco2)
        push!(out, (scenario, trial, b, s, s - b, 100.0 * (s - b) / b))
    end
    return out
end

function write_delta_svg(delta::DataFrame, output_path::String)
    scenarios = filter(!=("baseline"), SCENARIO_ORDER)
    xmin = min(0.0, quant(delta.delta_scc, 0.01))
    xmax = nice_upper(quant(delta.delta_scc, 0.99) * 1.15; step = 25.0)
    width, height = 1120, 650
    left, right, top, bottom = 215, 54, 82, 82
    plot_w = width - left - right
    plot_h = height - top - bottom
    lane_gap = plot_h / length(scenarios)
    xscale(x) = left + (x - xmin) / (xmax - xmin) * plot_w

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">Paired SCC increase relative to baseline</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">Each dot is one matched GIVE draw at the 2% discount rate; bars show 5th-95th percentiles.</text>""")
        for tick in 0:25:Int(xmax)
            x = xscale(tick)
            println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + plot_h)" stroke="#EAEAEA" stroke-width="1"/>""")
            println(io, """<text x="$x" y="$(height - bottom + 26)" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">$tick</text>""")
        end
        xzero = xscale(0.0)
        println(io, """<line x1="$xzero" y1="$top" x2="$xzero" y2="$(top + plot_h)" stroke="#222" stroke-width="1.3"/>""")
        println(io, """<line x1="$left" y1="$(height - bottom)" x2="$(left + plot_w)" y2="$(height - bottom)" stroke="#222" stroke-width="1"/>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 22)" text-anchor="middle" font-family="Arial" font-size="13" fill="#222">SCC change, 2020 USD per tCO2</text>""")

        for (i, scenario) in enumerate(scenarios)
            vals = sort(Float64.(delta[delta.scenario .== scenario, :delta_scc]))
            isempty(vals) && continue
            y = top + (i - 0.48) * lane_gap
            color = scenario_color(scenario)
            p05, p25, p50, p75, p95 = quant(vals, 0.05), quant(vals, 0.25), quant(vals, 0.50), quant(vals, 0.75), quant(vals, 0.95)
            m = mean(vals)
            println(io, """<text x="$(left - 14)" y="$(y + 5)" text-anchor="end" font-family="Arial" font-size="13" font-weight="700" fill="#222">$(escape_xml(scenario_label(scenario)))</text>""")
            println(io, """<line x1="$(xscale(p05))" y1="$y" x2="$(xscale(p95))" y2="$y" stroke="$color" stroke-width="8" stroke-linecap="round" opacity="0.34"/>""")
            println(io, """<rect x="$(xscale(p25))" y="$(y - 13)" width="$(max(xscale(p75) - xscale(p25), 2.0))" height="26" fill="$color" fill-opacity="0.28" stroke="$color" stroke-width="1.6"/>""")
            println(io, """<line x1="$(xscale(p50))" y1="$(y - 17)" x2="$(xscale(p50))" y2="$(y + 17)" stroke="$color" stroke-width="2.2"/>""")
            println(io, """<path d="M $(xscale(m)) $(y - 8) L $(xscale(m) + 8) $y L $(xscale(m)) $(y + 8) L $(xscale(m) - 8) $y Z" fill="$color" stroke="#FFFFFF" stroke-width="1"/>""")

            # Deterministic jitter from rank keeps the plot reproducible.
            for (j, value) in enumerate(vals)
                jitter = 18.0 * sin(0.83 * j)
                println(io, """<circle cx="$(xscale(value))" cy="$(y + jitter)" r="2.6" fill="$color" fill-opacity="0.34"/>""")
            end
            println(io, """<text x="$(xscale(m) + 12)" y="$(y - 19)" font-family="Arial" font-size="11" fill="$color">mean +$(round(m, digits = 1))</text>""")
        end
        println(io, "</svg>")
    end
end

function write_exceedance_svg(samples::DataFrame, output_path::String)
    scenarios = sorted_scenarios(samples)
    all_values = Float64.(samples.scc_2020usd_per_tco2)
    xmax = nice_upper(maximum(all_values) * 1.02; step = 100.0)
    thresholds = collect(range(0.0, xmax; length = 121))
    width, height = 1060, 640
    left, right, top, bottom = 82, 210, 82, 74
    plot_w = width - left - right
    plot_h = height - top - bottom
    xscale(x) = left + x / xmax * plot_w
    yscale(p) = top + (1.0 - p) * plot_h

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">Tail probability of high SCC outcomes</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">Exceedance curves: probability that the SCC is greater than the x-axis value.</text>""")
        for tick in 0:100:Int(xmax)
            x = xscale(tick)
            println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + plot_h)" stroke="#EAEAEA" stroke-width="1"/>""")
            println(io, """<text x="$x" y="$(top + plot_h + 22)" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">$tick</text>""")
        end
        for pct in 0.0:0.2:1.0
            y = yscale(pct)
            println(io, """<line x1="$left" y1="$y" x2="$(left + plot_w)" y2="$y" stroke="#EAEAEA" stroke-width="1"/>""")
            println(io, """<text x="$(left - 10)" y="$(y + 4)" text-anchor="end" font-family="Arial" font-size="11" fill="#555">$(Int(round(100 * pct)))%</text>""")
        end
        println(io, """<line x1="$left" y1="$(top + plot_h)" x2="$(left + plot_w)" y2="$(top + plot_h)" stroke="#222"/>""")
        println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + plot_h)" stroke="#222"/>""")
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 20)" text-anchor="middle" font-family="Arial" font-size="13" fill="#222">SCC threshold, 2020 USD per tCO2</text>""")
        println(io, """<text transform="translate(24,$(top + plot_h / 2)) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="13" fill="#222">Probability SCC exceeds threshold</text>""")

        for scenario in scenarios
            vals = Float64.(samples[samples.scenario .== scenario, :scc_2020usd_per_tco2])
            probs = [count(>(threshold), vals) / length(vals) for threshold in thresholds]
            pts = [(xscale(thresholds[i]), yscale(probs[i])) for i in eachindex(thresholds)]
            color = scenario_color(scenario)
            println(io, """<polyline points="$(polyline(pts))" fill="none" stroke="$color" stroke-width="2.6"/>""")
        end

        lx, ly = left + plot_w + 24, top + 18
        for (i, scenario) in enumerate(scenarios)
            y = ly + 25 * (i - 1)
            color = scenario_color(scenario)
            println(io, """<line x1="$lx" y1="$y" x2="$(lx + 24)" y2="$y" stroke="$color" stroke-width="3"/>""")
            println(io, """<text x="$(lx + 32)" y="$(y + 4)" font-family="Arial" font-size="12" fill="#222">$(escape_xml(scenario_label(scenario)))</text>""")
        end
        println(io, "</svg>")
    end
end

function write_probability_tiles(samples::DataFrame, output_path::String)
    thresholds = [185.0, 250.0, 500.0, 750.0]
    scenarios = sorted_scenarios(samples)
    width, height = 960, 470
    left, top = 260, 104
    cell_w, cell_h = 150, 54

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="44" y="36" font-family="Arial" font-size="23" font-weight="700">Probability mass above policy-relevant SCC thresholds</text>""")
        println(io, """<text x="44" y="60" font-family="Arial" font-size="13" fill="#555">Cells show P(SCC above threshold) in the 2% paired 100-run validation sample.</text>""")
        for (j, threshold) in enumerate(thresholds)
            x = left + (j - 1) * cell_w + cell_w / 2
            println(io, """<text x="$x" y="$(top - 18)" text-anchor="middle" font-family="Arial" font-size="12" font-weight="700" fill="#333">&gt; $threshold</text>""")
        end
        for (i, scenario) in enumerate(scenarios)
            y = top + (i - 1) * cell_h
            println(io, """<text x="$(left - 16)" y="$(y + 33)" text-anchor="end" font-family="Arial" font-size="12.5" font-weight="700" fill="#222">$(escape_xml(scenario_label(scenario)))</text>""")
            vals = Float64.(samples[samples.scenario .== scenario, :scc_2020usd_per_tco2])
            color = scenario_color(scenario)
            for (j, threshold) in enumerate(thresholds)
                p = count(>(threshold), vals) / length(vals)
                x = left + (j - 1) * cell_w
                opacity = 0.12 + 0.78 * p
                println(io, """<rect x="$x" y="$y" width="$(cell_w - 8)" height="$(cell_h - 8)" fill="$color" fill-opacity="$opacity" stroke="#FFFFFF" stroke-width="2"/>""")
                println(io, """<text x="$(x + (cell_w - 8) / 2)" y="$(y + 31)" text-anchor="middle" font-family="Arial" font-size="15" font-weight="700" fill="#111">$(round(100 * p, digits = 0))%</text>""")
            end
        end
        println(io, """<text x="$left" y="$(height - 34)" font-family="Arial" font-size="11" fill="#555">Threshold 185 is included as a rough visual anchor near recent U.S. central SCC discussions, not as a model parameter.</text>""")
        println(io, "</svg>")
    end
end

function spatial_proxy_regions()
    return DataFrame(
        region = [
            "Boreal Canada",
            "Alaska and NW Canada",
            "Siberia and Far East Russia",
            "Western United States",
            "Mediterranean Europe",
            "Amazon and Cerrado",
            "Congo basin and southern Africa",
            "Indonesia and peat SE Asia",
            "Australia",
        ],
        center_lon = [-104.0, -151.0, 104.0, -116.0, 16.0, -58.0, 24.0, 116.0, 135.0],
        center_lat = [58.0, 63.0, 62.0, 41.0, 41.0, -9.0, -12.0, -3.0, -25.0],
        radius_lon = [43.0, 20.0, 58.0, 18.0, 22.0, 30.0, 34.0, 24.0, 31.0],
        radius_lat = [12.0, 8.0, 12.0, 10.0, 8.0, 18.0, 22.0, 10.0, 15.0],
        gross_fire_source_index = [1.00, 0.55, 1.00, 0.35, 0.25, 0.45, 0.35, 0.50, 0.40],
        residual_added_stock_index = [0.95, 0.45, 0.95, 0.25, 0.15, 0.20, 0.15, 0.20, 0.20],
        double_counting_risk = [
            "medium",
            "medium",
            "medium",
            "high",
            "high",
            "high",
            "high",
            "high",
            "medium",
        ],
        note = [
            "Boreal forest carbon source emphasized by recent extreme Canadian fire evidence.",
            "Boreal/permafrost transition and high-latitude fire expansion proxy.",
            "Boreal Russia proxy for climate-sensitive large carbon stores.",
            "Well-observed fire risk, but inventories and land-use accounting make residual carbon attribution harder.",
            "High damages and fire risk relevance, but smaller global carbon-stock contribution proxy.",
            "Large fire and land-use interactions; high double-counting risk with AFOLU emissions.",
            "Savanna/forest burning with high gross emissions but high gross/net ambiguity.",
            "Peat carbon risk, but high overlap with land-use and peat-drainage accounting.",
            "Major fire-prone region; residual net carbon stock effect is uncertain.",
        ],
        source_anchor = [
            "Byrne et al. 2024 Canadian wildfire carbon emissions; Chen et al. 2026 RESFire high-latitude/forest-fire feedback framing.",
            "Chen et al. 2026 RESFire forest-fire feedback framing; boreal carbon-stock interpretation.",
            "Chen et al. 2026 RESFire forest-fire feedback framing; boreal carbon-stock interpretation.",
            "Chen et al. 2026 RESFire forest-fire feedback framing; high double-counting caution from aggregate AFOLU/inventory overlap.",
            "Chen et al. 2026 RESFire forest-fire feedback framing; smaller source-side carbon-stock proxy.",
            "Chen et al. 2026 identifies South Tropical America as a high forest-fire/reactive-carbon region; high AFOLU overlap caution.",
            "Jones et al. 2019 gross fire carbon and gross/net ambiguity; high regrowth and pyrogenic-carbon caveat.",
            "Chen et al. 2026 identifies South and Southeast Asia; peat and land-use overlap caution.",
            "Jones et al. 2019 gross fire carbon and gross/net ambiguity; regional residual effect uncertain.",
        ],
        source_url = [
            "https://www.nature.com/articles/s41586-024-07878-z; https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-026-01926-1",
            "https://www.nature.com/articles/s41561-019-0403-x",
            "https://www.nature.com/articles/s41561-026-01926-1; https://www.nature.com/articles/s41561-019-0403-x",
            "https://www.nature.com/articles/s41561-019-0403-x",
        ],
    )
end

function map_project(lon, lat, left, top, map_w, map_h)
    x = left + (lon + 180.0) / 360.0 * map_w
    y = top + (90.0 - lat) / 180.0 * map_h
    return x, y
end

function world_poly(points, left, top, map_w, map_h)
    return polygon([map_project(lon, lat, left, top, map_w, map_h) for (lon, lat) in points])
end

function draw_world_base(io, left, top, map_w, map_h)
    println(io, """<rect x="$left" y="$top" width="$map_w" height="$map_h" rx="8" fill="#EAF3F8" stroke="#9AB5C5" stroke-width="1"/>""")
    for lon in -180:60:180
        x, _ = map_project(lon, 0.0, left, top, map_w, map_h)
        println(io, """<line x1="$x" y1="$top" x2="$x" y2="$(top + map_h)" stroke="#C9DDE8" stroke-width="0.8"/>""")
    end
    for lat in -60:30:60
        _, y = map_project(0.0, lat, left, top, map_w, map_h)
        println(io, """<line x1="$left" y1="$y" x2="$(left + map_w)" y2="$y" stroke="#C9DDE8" stroke-width="0.8"/>""")
    end

    land = "#EEF1EA"
    stroke = "#AAB8A5"
    polys = [
        [(-168, 72), (-142, 62), (-132, 49), (-124, 35), (-112, 25), (-96, 19), (-82, 25), (-65, 45), (-54, 58), (-72, 72)],
        [(-82, 13), (-70, 10), (-56, -5), (-49, -20), (-60, -44), (-73, -55), (-78, -20)],
        [(-18, 72), (20, 70), (56, 58), (105, 66), (170, 62), (176, 42), (138, 31), (104, 21), (80, 8), (53, 26), (30, 38), (5, 35), (-9, 52)],
        [(-18, 35), (7, 36), (33, 31), (49, 12), (43, -25), (20, -35), (1, -28), (-15, -4)],
        [(112, -10), (153, -16), (154, -38), (137, -44), (116, -34)],
        [(-52, 74), (-33, 70), (-22, 62), (-35, 58), (-51, 62)],
        [(43, -13), (50, -18), (48, -25), (44, -24)],
    ]
    for p in polys
        println(io, """<polygon points="$(world_poly(p, left, top, map_w, map_h))" fill="$land" stroke="$stroke" stroke-width="1"/>""")
    end
end

function risk_dash(risk::AbstractString)
    lowercase(risk) == "high" ? " stroke-dasharray=\"5 4\"" : ""
end

function write_fire_source_map(regions::DataFrame, output_path::String)
    width, height = 1180, 690
    left, top, map_w, map_h = 55, 98, 1010, 505
    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">Likely source regions for additional climate-driven fire CO2</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">Spatial proxy only: ellipses encode relative gross fire-carbon pressure, not GIVE regional output.</text>""")
        draw_world_base(io, left, top, map_w, map_h)
        for row in eachrow(regions)
            x, y = map_project(row.center_lon, row.center_lat, left, top, map_w, map_h)
            rx = row.radius_lon / 360.0 * map_w
            ry = row.radius_lat / 180.0 * map_h
            opacity = 0.12 + 0.56 * row.gross_fire_source_index
            stroke_width = 1.6 + 2.0 * row.gross_fire_source_index
            dash = risk_dash(string(row.double_counting_risk))
            println(io, """<ellipse cx="$x" cy="$y" rx="$rx" ry="$ry" fill="$MAP_SOURCE" fill-opacity="$opacity" stroke="$MAP_SOURCE" stroke-width="$stroke_width"$dash><title>$(escape_xml(row.region)): gross source index $(row.gross_fire_source_index); double-counting risk $(row.double_counting_risk)</title></ellipse>""")
        end
        for row in eachrow(regions)
            row.gross_fire_source_index < 0.45 && continue
            x, y = map_project(row.center_lon, row.center_lat, left, top, map_w, map_h)
            println(io, """<text x="$(x + 6)" y="$(y - 7)" font-family="Arial" font-size="11" font-weight="700" fill="#333">$(escape_xml(row.region))</text>""")
        end
        legend_x, legend_y = left + map_w + 24, top + 26
        println(io, """<text x="$legend_x" y="$legend_y" font-family="Arial" font-size="12" font-weight="700" fill="#222">Encoding</text>""")
        println(io, """<circle cx="$(legend_x + 14)" cy="$(legend_y + 34)" r="9" fill="$MAP_SOURCE" fill-opacity="0.25" stroke="$MAP_SOURCE"/>""")
        println(io, """<circle cx="$(legend_x + 14)" cy="$(legend_y + 74)" r="18" fill="$MAP_SOURCE" fill-opacity="0.65" stroke="$MAP_SOURCE" stroke-width="3"/>""")
        println(io, """<text x="$(legend_x + 38)" y="$(legend_y + 38)" font-family="Arial" font-size="11" fill="#333">lower proxy</text>""")
        println(io, """<text x="$(legend_x + 38)" y="$(legend_y + 78)" font-family="Arial" font-size="11" fill="#333">higher proxy</text>""")
        println(io, """<line x1="$legend_x" y1="$(legend_y + 114)" x2="$(legend_x + 52)" y2="$(legend_y + 114)" stroke="$MAP_SOURCE" stroke-width="3" stroke-dasharray="5 4"/>""")
        println(io, """<text x="$legend_x" y="$(legend_y + 138)" font-family="Arial" font-size="11" fill="#333">dashed outline = higher double-counting risk</text>""")
        println(io, """<text x="$left" y="$(height - 44)" font-family="Arial" font-size="11" fill="#555">The largest source proxies are boreal Canada and Russia, consistent with the first-pass RESFire stress framing and the 2023 Canadian fire evidence.</text>""")
        println(io, "</svg>")
    end
end

function write_residual_source_map(regions::DataFrame, output_path::String)
    width, height = 1180, 690
    left, top, map_w, map_h = 55, 98, 1010, 505
    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">More defensible residual fire-carbon addition proxy</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">This map downweights regions where gross fire CO2 is most likely already counted in AFOLU, inventories, or short-run regrowth.</text>""")
        draw_world_base(io, left, top, map_w, map_h)
        for row in eachrow(regions)
            x, y = map_project(row.center_lon, row.center_lat, left, top, map_w, map_h)
            rx = max(row.radius_lon / 360.0 * map_w * (0.55 + row.residual_added_stock_index), 7.0)
            ry = max(row.radius_lat / 180.0 * map_h * (0.55 + row.residual_added_stock_index), 5.0)
            opacity = 0.10 + 0.62 * row.residual_added_stock_index
            dash = risk_dash(string(row.double_counting_risk))
            println(io, """<ellipse cx="$x" cy="$y" rx="$rx" ry="$ry" fill="$MAP_RESIDUAL" fill-opacity="$opacity" stroke="$MAP_RESIDUAL" stroke-width="2"$dash><title>$(escape_xml(row.region)): residual index $(row.residual_added_stock_index); double-counting risk $(row.double_counting_risk)</title></ellipse>""")
        end
        for row in eachrow(regions)
            row.residual_added_stock_index < 0.40 && continue
            x, y = map_project(row.center_lon, row.center_lat, left, top, map_w, map_h)
            println(io, """<text x="$(x + 6)" y="$(y - 7)" font-family="Arial" font-size="11" font-weight="700" fill="#333">$(escape_xml(row.region))</text>""")
        end
        legend_x, legend_y = left + map_w + 24, top + 28
        println(io, """<text x="$legend_x" y="$legend_y" font-family="Arial" font-size="12" font-weight="700" fill="#222">Interpretation</text>""")
        println(io, """<rect x="$legend_x" y="$(legend_y + 20)" width="78" height="20" fill="$MAP_RESIDUAL" fill-opacity="0.28" stroke="$MAP_RESIDUAL"/>""")
        println(io, """<text x="$legend_x" y="$(legend_y + 58)" font-family="Arial" font-size="11" fill="#333">smaller residual net-stock addition</text>""")
        println(io, """<rect x="$legend_x" y="$(legend_y + 84)" width="78" height="20" fill="$MAP_RESIDUAL" fill-opacity="0.74" stroke="$MAP_RESIDUAL"/>""")
        println(io, """<text x="$legend_x" y="$(legend_y + 122)" font-family="Arial" font-size="11" fill="#333">larger residual net-stock addition</text>""")
        println(io, """<line x1="$legend_x" y1="$(legend_y + 152)" x2="$(legend_x + 54)" y2="$(legend_y + 152)" stroke="$MAP_RESIDUAL" stroke-width="3" stroke-dasharray="5 4"/>""")
        println(io, """<text x="$legend_x" y="$(legend_y + 176)" font-family="Arial" font-size="11" fill="#333">dashed = higher double-counting risk</text>""")
        println(io, """<text x="$left" y="$(height - 44)" font-family="Arial" font-size="11" fill="#555">This residual proxy is the map version of the conservative scenario logic: net, not-embedded, climate-caused carbon stock additions.</text>""")
        println(io, "</svg>")
    end
end

function write_mechanism_map(regions::DataFrame, output_path::String)
    width, height = 1180, 690
    left, top, map_w, map_h = 55, 98, 1010, 505
    center_x, center_y = map_project(15.0, 12.0, left, top, map_w, map_h)
    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L8,3 z" fill="#555"/></marker></defs>""")
        println(io, """<rect width="100%" height="100%" fill="#FFFFFF"/>""")
        println(io, """<text x="$left" y="34" font-family="Arial" font-size="23" font-weight="700">How local fire-carbon sources enter a global SCC calculation</text>""")
        println(io, """<text x="$left" y="58" font-family="Arial" font-size="13" fill="#555">The implemented pathway affects global concentration, forcing, temperature, and discounted marginal damages. It does not allocate country-level wildfire damages.</text>""")
        draw_world_base(io, left, top, map_w, map_h)
        println(io, """<circle cx="$center_x" cy="$center_y" r="58" fill="#FFFFFF" stroke="#333" stroke-width="1.5"/>""")
        println(io, """<text x="$center_x" y="$(center_y - 10)" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="#222">Global</text>""")
        println(io, """<text x="$center_x" y="$(center_y + 8)" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">CO2 stock</text>""")
        println(io, """<text x="$center_x" y="$(center_y + 25)" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">and forcing</text>""")
        for row in eachrow(regions)
            row.residual_added_stock_index < 0.40 && continue
            x, y = map_project(row.center_lon, row.center_lat, left, top, map_w, map_h)
            println(io, """<line x1="$x" y1="$y" x2="$center_x" y2="$center_y" stroke="#555" stroke-width="$(1.2 + 2.5 * row.residual_added_stock_index)" stroke-opacity="0.58" marker-end="url(#arrow)"/>""")
            println(io, """<circle cx="$x" cy="$y" r="$(6 + 9 * row.residual_added_stock_index)" fill="$MAP_RESIDUAL" fill-opacity="0.65" stroke="#FFFFFF" stroke-width="1.2"><title>$(escape_xml(row.region)) source proxy</title></circle>""")
        end
        receiver_regions = DataFrame(
            label = ["South Asia heat/agriculture", "East Asia energy/agriculture", "Sub-Saharan Africa agriculture", "Coastal SLR exposure", "High-income mortality/energy"],
            lon = [78.0, 112.0, 22.0, -74.0, -5.0],
            lat = [22.0, 32.0, 2.0, 38.0, 50.0],
            weight = [0.95, 0.82, 0.88, 0.75, 0.62],
        )
        for row in eachrow(receiver_regions)
            x, y = map_project(row.lon, row.lat, left, top, map_w, map_h)
            println(io, """<circle cx="$x" cy="$y" r="$(12 + 12 * row.weight)" fill="#3366CC" fill-opacity="0.10" stroke="#3366CC" stroke-width="2"><title>$(escape_xml(row.label)): qualitative receptor proxy, not model-output geography</title></circle>""")
        end
        legend_x, legend_y = left + map_w + 24, top + 22
        println(io, """<text x="$legend_x" y="$legend_y" font-family="Arial" font-size="12" font-weight="700" fill="#222">Read as schematic</text>""")
        println(io, """<circle cx="$(legend_x + 14)" cy="$(legend_y + 34)" r="10" fill="$MAP_RESIDUAL" fill-opacity="0.65" stroke="#FFFFFF"/>""")
        println(io, """<text x="$(legend_x + 34)" y="$(legend_y + 38)" font-family="Arial" font-size="11" fill="#333">source-side added CO2 proxy</text>""")
        println(io, """<circle cx="$(legend_x + 14)" cy="$(legend_y + 72)" r="16" fill="#3366CC" fill-opacity="0.10" stroke="#3366CC" stroke-width="2"/>""")
        println(io, """<text x="$(legend_x + 34)" y="$(legend_y + 76)" font-family="Arial" font-size="11" fill="#333">qualitative damage receptor proxy</text>""")
        println(io, """<line x1="$legend_x" y1="$(legend_y + 110)" x2="$(legend_x + 46)" y2="$(legend_y + 110)" stroke="#555" stroke-width="3" marker-end="url(#arrow)"/>""")
        println(io, """<text x="$legend_x" y="$(legend_y + 136)" font-family="Arial" font-size="11" fill="#333">global CO2 channel, not smoke transport</text>""")
        println(io, """<text x="$left" y="$(height - 44)" font-family="Arial" font-size="11" fill="#555">Blue receptor rings are illustrative only; a real regional damage map would require extracting or extending GIVE's regional damage outputs.</text>""")
        println(io, "</svg>")
    end
end

function write_figure_notes(output_dir::String)
    path = joinpath(output_dir, "figure_notes.md")
    open(path, "w") do io
        println(io, "# Figure Notes")
        println(io)
        println(io, "These figures use `/output/wildfire_temperature_feedback_mcs_100_paired/all_scc_samples.csv` and focus on the 2.0% discount-rate case.")
        println(io)
        println(io, "## SCC distribution figures")
        println(io)
        println(io, "- `figure_scc_ridgeline_2pct.svg` shows full SCC distributions for the paired 100-run validation sample. Vertical lines mark means; open circles mark medians; horizontal bars mark the 5th-95th percentile span.")
        println(io, "- `figure_paired_scc_delta_2pct.svg` subtracts each paired baseline draw from the corresponding wildfire-feedback draw. This is the cleanest visual for the incremental SCC effect because common RFF-SP, FAIR, and discounting draws are held fixed within each trial.")
        println(io, "- `figure_scc_exceedance_2pct.svg` shows tail probabilities. This makes the stress scenarios' upper-tail effects easier to see than a single mean.")
        println(io, "- `figure_scc_threshold_tiles_2pct.svg` summarizes the same tail information at four thresholds.")
        println(io)
        println(io, "## Spatial proxy maps")
        println(io)
        println(io, "The maps are not GIVE-native regional damage outputs. The current wildfire extension adds global CO2 to FAIR. That higher global CO2 stock then affects global forcing, temperature, and damages. The model run does not allocate the incremental SCC geographically.")
        println(io)
        println(io, "- `figure_fire_source_proxy_map.svg` encodes a hand-auditable proxy for where additional climate-driven fire CO2 is most likely to originate. Boreal Canada and Siberia/Russia are weighted highest because this first-pass experiment is motivated by high-latitude carbon-stock and extreme-fire evidence.")
        println(io, "- `figure_residual_source_proxy_map.svg` downweights gross fire regions where AFOLU/inventory overlap, regrowth, or gross-vs-net ambiguity creates high double-counting risk.")
        println(io, "- `figure_global_fire_mechanism_map.svg` is a mechanism schematic: local source proxies feed a global atmospheric CO2 stock. Blue receptor rings are qualitative reminders that climate damages are distributed globally; they should not be cited as regional estimates.")
        println(io)
        println(io, "The spatial proxy weights are saved in `spatial_proxy_regions.csv` so they can be replaced by gridded RESFire, GFED, FireMIP, or CMIP/land-model outputs in the next iteration.")
        println(io)
        println(io, "## Source anchors")
        println(io)
        println(io, "- Byrne et al. 2024, `Nature`, estimates the 2023 Canadian fires at 647 TgC and links the event to hot-dry conditions that climate projections suggest may become typical by the 2050s under SSP2-4.5: https://www.nature.com/articles/s41586-024-07878-z")
        println(io, "- Chen et al. 2026, `Nature Geoscience`, uses CESM-RESFire and reports projected fire-emissions feedback quantities, including a 19% burned-area increase, 106% reactive-carbon increase, and a fire-CO2 burden-change calculation for 2000s-2050s: https://www.nature.com/articles/s41561-026-01926-1")
        println(io, "- Jones et al. 2019, `Nature Geoscience`, is included as a gross-vs-net caution because it emphasizes global fire carbon emissions, pyrogenic carbon, and carbon-accounting ambiguity: https://www.nature.com/articles/s41561-019-0403-x")
    end
    return path
end

function write_delta_table(delta::DataFrame, output_path::String)
    rows = DataFrame(
        scenario = String[],
        mean_delta_scc = Float64[],
        median_delta_scc = Float64[],
        p05_delta_scc = Float64[],
        p95_delta_scc = Float64[],
        mean_percent_delta_scc = Float64[],
    )
    for scenario in filter(!=("baseline"), SCENARIO_ORDER)
        vals = Float64.(delta[delta.scenario .== scenario, :delta_scc])
        pcts = Float64.(delta[delta.scenario .== scenario, :percent_delta_scc])
        isempty(vals) && continue
        push!(rows, (
            scenario_label(scenario),
            mean(vals),
            median(vals),
            quant(vals, 0.05),
            quant(vals, 0.95),
            mean(pcts),
        ))
    end
    rows |> save(output_path)
end

function main(; mcs_dir::String = DEFAULT_MCS_DIR, output_dir::String = DEFAULT_OUTPUT_DIR)
    samples_path = joinpath(mcs_dir, "all_scc_samples.csv")
    isfile(samples_path) || error("Missing SCC samples: $samples_path")

    mkpath(output_dir)
    samples = filter_discount_rate(DataFrame(load(samples_path)), 0.02)
    samples[!, :scenario] = string.(samples.scenario)
    samples[!, :trial] = Int.(samples.trial)

    delta = paired_delta_frame(samples)
    write_ridgeline_svg(samples, joinpath(output_dir, "figure_scc_ridgeline_2pct.svg"))
    write_delta_svg(delta, joinpath(output_dir, "figure_paired_scc_delta_2pct.svg"))
    write_exceedance_svg(samples, joinpath(output_dir, "figure_scc_exceedance_2pct.svg"))
    write_probability_tiles(samples, joinpath(output_dir, "figure_scc_threshold_tiles_2pct.svg"))
    write_delta_table(delta, joinpath(output_dir, "paired_scc_delta_summary_2pct.csv"))

    regions = spatial_proxy_regions()
    regions |> save(joinpath(output_dir, "spatial_proxy_regions.csv"))
    write_fire_source_map(regions, joinpath(output_dir, "figure_fire_source_proxy_map.svg"))
    write_residual_source_map(regions, joinpath(output_dir, "figure_residual_source_proxy_map.svg"))
    write_mechanism_map(regions, joinpath(output_dir, "figure_global_fire_mechanism_map.svg"))
    notes = write_figure_notes(output_dir)

    println("Wrote SCC figures, maps, proxy CSV, and notes to $output_dir")
    println("Notes: $notes")
end

if abspath(PROGRAM_FILE) == @__FILE__
    mcs_dir = length(ARGS) >= 1 ? ARGS[1] : DEFAULT_MCS_DIR
    output_dir = length(ARGS) >= 2 ? ARGS[2] : DEFAULT_OUTPUT_DIR
    main(mcs_dir = mcs_dir, output_dir = output_dir)
end

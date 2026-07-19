#!/usr/bin/env julia

# Build simple SVG figures from deterministic and Monte Carlo wildfire-feedback
# outputs. The script avoids extra plotting dependencies so it works in the
# archived GIVE Julia environment.

using CSVFiles
using DataFrames
using Statistics

const DEFAULT_DETERMINISTIC_DIR =
    joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback_refyear_check")
const DEFAULT_MCS_DIR =
    joinpath(@__DIR__, "..", "output", "wildfire_temperature_feedback_mcs_100")

const COLORS = Dict(
    "baseline" => "#345995",
    "feedback-residual-medium" => "#03CEA4",
    "feedback-residual-high" => "#FB4D3D",
    "feedback-resfire-half-gross" => "#7A5195",
    "feedback-resfire-gross" => "#F5A623",
)

function _as_float(x)
    if ismissing(x)
        return missing
    elseif x isa AbstractString
        lowercase(x) == "na" && return missing
        return parse(Float64, x)
    else
        return Float64(x)
    end
end

function _polyline(points)
    return join(["$(round(x, digits=2)),$(round(y, digits=2))" for (x, y) in points], " ")
end

function write_path_svg(df::DataFrame, output_path::String; ycol::Symbol, title::String, ylabel::String, year_min::Int = 2020, year_max::Int = 2300)
    data = df[(df.year .>= year_min) .& (df.year .<= year_max), :]
    data[!, ycol] = _as_float.(data[!, ycol])
    data = data[.!ismissing.(data[!, ycol]), :]

    width, height = 980, 560
    left, right, top, bottom = 82, 32, 42, 72
    plot_w = width - left - right
    plot_h = height - top - bottom

    ymin = minimum(skipmissing(data[!, ycol]))
    ymax = maximum(skipmissing(data[!, ycol]))
    if ymax == ymin
        ymax += 1.0
    end
    pad = 0.08 * (ymax - ymin)
    ymin -= pad
    ymax += pad

    xscale(year) = left + (year - year_min) / (year_max - year_min) * plot_w
    yscale(value) = top + plot_h - (value - ymin) / (ymax - ymin) * plot_h

    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, """<svg xmlns="http://www.w3.org/2000/svg" width="$width" height="$height" viewBox="0 0 $width $height">""")
        println(io, """<rect width="100%" height="100%" fill="white"/>""")
        println(io, """<text x="$left" y="26" font-family="Arial" font-size="18" font-weight="700">$title</text>""")
        println(io, """<line x1="$left" y1="$(top + plot_h)" x2="$(left + plot_w)" y2="$(top + plot_h)" stroke="#222"/>""")
        println(io, """<line x1="$left" y1="$top" x2="$left" y2="$(top + plot_h)" stroke="#222"/>""")
        for year in [2020, 2050, 2100, 2200, 2300]
            x = xscale(year)
            println(io, """<line x1="$x" y1="$(top + plot_h)" x2="$x" y2="$(top + plot_h + 5)" stroke="#222"/>""")
            println(io, """<text x="$x" y="$(top + plot_h + 22)" text-anchor="middle" font-family="Arial" font-size="11">$year</text>""")
        end
        for frac in 0.0:0.25:1.0
            val = ymin + frac * (ymax - ymin)
            y = yscale(val)
            println(io, """<line x1="$(left - 5)" y1="$y" x2="$left" y2="$y" stroke="#222"/>""")
            println(io, """<text x="$(left - 10)" y="$(y + 4)" text-anchor="end" font-family="Arial" font-size="11">$(round(val, digits=2))</text>""")
            if frac > 0.0
                println(io, """<line x1="$left" y1="$y" x2="$(left + plot_w)" y2="$y" stroke="#ddd"/>""")
            end
        end
        println(io, """<text x="$(left + plot_w / 2)" y="$(height - 22)" text-anchor="middle" font-family="Arial" font-size="13">Year</text>""")
        println(io, """<text transform="translate(23,$(top + plot_h / 2)) rotate(-90)" text-anchor="middle" font-family="Arial" font-size="13">$ylabel</text>""")

        scenarios = unique(data.scenario)
        for scenario in scenarios
            rows = sort(data[data.scenario .== scenario, :], :year)
            pts = [(xscale(row.year), yscale(row[ycol])) for row in eachrow(rows)]
            color = get(COLORS, scenario, "#777")
            println(io, """<polyline points="$(_polyline(pts))" fill="none" stroke="$color" stroke-width="2.2"/>""")
        end

        legend_x = left + 10
        legend_y = height - 48
        for (i, scenario) in enumerate(scenarios)
            color = get(COLORS, scenario, "#777")
            x = legend_x + ((i - 1) % 3) * 290
            y = legend_y + div(i - 1, 3) * 20
            println(io, """<rect x="$x" y="$y" width="12" height="12" fill="$color"/>""")
            println(io, """<text x="$(x + 18)" y="$(y + 11)" font-family="Arial" font-size="11">$scenario</text>""")
        end
        println(io, "</svg>")
    end
end

function write_summary_table(summary::DataFrame, output_path::String; dr_label = "2.0%")
    dr_target =
        occursin("%", dr_label) ? parse(Float64, replace(dr_label, "%" => "")) / 100.0 :
        parse(Float64, dr_label)
    rows = summary[
        [
            label isa Real ? isapprox(Float64(label), dr_target; atol = 1e-10) : string(label) == dr_label
            for label in summary.dr_label
        ],
        :,
    ]
    mkpath(dirname(output_path))
    open(output_path, "w") do io
        println(io, "| Scenario | Mean SCC | Median SCC | 5th | 95th | Delta mean | Delta % |")
        println(io, "| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for row in eachrow(rows)
            println(
                io,
                "| $(row.scenario) | $(round(row.mean_scc, digits=2)) | $(round(row.median_scc, digits=2)) | $(round(row.p05_scc, digits=2)) | $(round(row.p95_scc, digits=2)) | $(round(row.delta_mean_scc, digits=2)) | $(round(row.pct_delta_mean_scc, digits=2))% |",
            )
        end
    end
end

function main(; deterministic_dir::String = DEFAULT_DETERMINISTIC_DIR, mcs_dir::String = DEFAULT_MCS_DIR)
    det_path = joinpath(deterministic_dir, "deterministic_climate_damage_paths.csv")
    isfile(det_path) || error("Missing deterministic paths: $det_path")
    det = DataFrame(load(det_path))

    figure_dir = joinpath(@__DIR__, "manuscript", "figures")
    write_path_svg(
        det,
        joinpath(figure_dir, "figure_added_fire_co2.svg");
        ycol = :feedback_fire_gtco2,
        title = "Added wildfire CO2 feedback emissions",
        ylabel = "GtCO2 per year",
    )
    write_path_svg(
        det,
        joinpath(figure_dir, "figure_co2_concentration.svg");
        ycol = :co2_ppm,
        title = "Atmospheric CO2 concentration paths",
        ylabel = "ppm CO2",
    )
    write_path_svg(
        det,
        joinpath(figure_dir, "figure_temperature_paths.svg");
        ycol = :temperature_c,
        title = "Global mean temperature paths",
        ylabel = "degrees C anomaly",
    )
    write_path_svg(
        det,
        joinpath(figure_dir, "figure_total_damage_paths.svg");
        ycol = :total_damage_2005usd_per_year,
        title = "Total annual climate damages",
        ylabel = "billion 2005 USD per year",
    )

    summary_path = joinpath(mcs_dir, "scc_summary.csv")
    if isfile(summary_path)
        summary = DataFrame(load(summary_path))
        write_summary_table(summary, joinpath(@__DIR__, "manuscript", "mcs_summary_table.md"))
    end

    println("Wrote figures to $figure_dir")
end

if abspath(PROGRAM_FILE) == @__FILE__
    deterministic_dir = length(ARGS) >= 1 ? ARGS[1] : DEFAULT_DETERMINISTIC_DIR
    mcs_dir = length(ARGS) >= 2 ? ARGS[2] : DEFAULT_MCS_DIR
    main(deterministic_dir = deterministic_dir, mcs_dir = mcs_dir)
end

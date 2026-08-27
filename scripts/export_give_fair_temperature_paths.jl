#!/usr/bin/env julia
using MimiGIVE
using Mimi

function main()
    length(ARGS) == 1 || error("usage: export_give_fair_temperature_paths.jl OUTPUT.csv")
    output_path = ARGS[1]
    pulse_year = 2020
    pulse_sizes = [0.0, 1e-4, 5e-5, 2.5e-5]
    years = collect(1750:2300)
    model = MimiGIVE.get_model()
    baseline_reference = nothing
    rows = Tuple{Int, Float64, Float64, Float64, Float64}[]

    for pulse_size in pulse_sizes
        marginal = MimiGIVE.get_marginal_model(
            model; year=pulse_year, gas=:CO2, pulse_size=pulse_size
        )
        run(marginal)
        baseline = Float64.(marginal.base[:temperature, :T])
        pulse = Float64.(marginal.modified[:temperature, :T])
        length(baseline) == length(years) || error("unexpected FAIR year count")
        if baseline_reference === nothing
            baseline_reference = baseline
        elseif baseline != baseline_reference
            error("FAIR baseline path changed across pulse-size runs")
        end
        for (year, base_value, pulse_value) in zip(years, baseline, pulse)
            push!(rows, (year, pulse_size, base_value, pulse_value, pulse_value - base_value))
        end
    end

    mkpath(dirname(abspath(output_path)))
    open(output_path, "w") do stream
        println(stream, "year,pulse_size_gtc,baseline_temperature_c,pulse_temperature_c,difference_k")
        for row in rows
            println(stream, join(row, ","))
        end
    end
    println("wrote $(length(rows)) matched FAIR temperature rows to $output_path")
end

main()

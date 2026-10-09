using Dates
using Mimi

const ROOT = normpath(joinpath(@__DIR__, ".."))
const SOURCE = joinpath(
    ROOT,
    "vendor",
    "moore_2026",
    "lrennels-paper-2026-give-labor-ag-5d034e7",
)

include(joinpath(SOURCE, "src", "main.jl"))

const PRICELEVEL_2005_TO_2020 = 113.648 / 87.504
const DISCOUNT_RATES = [
    (label = "2.0%", prtp = exp(0.001972641) - 1, eta = 1.244458999),
]

function isolated_sector_scc(sector::Symbol; labor_function::String = "ISO")
    sector in (:agriculture, :labor) || error("Unsupported sector: $sector")
    m = get_model(
        # SSP245 avoids the large RFF-SP data dependency in this code-path test.
        # The paper-replication run below this gate uses the authors' RFF setup.
        socioeconomics_source = :SSP,
        SSP_scenario = "SSP245",
        labor_damage_function = labor_function,
    )

    update_param!(m, :DamageAggregator, :include_cromar_mortality, false)
    update_param!(m, :DamageAggregator, :include_ag, sector == :agriculture)
    update_param!(m, :DamageAggregator, :include_labor, sector == :labor)
    update_param!(m, :DamageAggregator, :include_slr, false)
    update_param!(m, :DamageAggregator, :include_energy, false)
    update_param!(m, :DamageAggregator, :include_dice2016R2, false)
    update_param!(m, :DamageAggregator, :include_hs_damage, false)

    result = compute_scc(
        m;
        year = 2025,
        last_year = 2300,
        discount_rates = DISCOUNT_RATES,
        n = 0,
        gas = :CO2,
        CIAM_foresight = :perfect,
        CIAM_GDPcap = true,
        pulse_size = 1e-4,
    )
    return only(values(result)) * PRICELEVEL_2005_TO_2020
end

mkpath(joinpath(ROOT, "output", "smoke"))
output_path = joinpath(ROOT, "output", "smoke", "deterministic_sector_scc.csv")

rows = [
    (sector = "labor", specification = "ISO", scc_2020usd_per_tco2 = isolated_sector_scc(:labor; labor_function = "ISO")),
    (sector = "labor", specification = "Lancet", scc_2020usd_per_tco2 = isolated_sector_scc(:labor; labor_function = "Lancet")),
    (sector = "agriculture", specification = "central", scc_2020usd_per_tco2 = isolated_sector_scc(:agriculture; labor_function = "ISO")),
]

open(output_path, "w") do io
    println(io, "sector,specification,socioeconomics,scc_2020usd_per_tco2")
    for row in rows
        println(io, "$(row.sector),$(row.specification),SSP245,$(row.scc_2020usd_per_tco2)")
    end
end

println("wrote $output_path at $(now())")
for row in rows
    println(row)
end

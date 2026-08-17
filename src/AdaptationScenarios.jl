"""Adaptation scenario utilities for the isolated agriculture replacement."""
module AdaptationScenarios

export adaptation_multiplier, adaptation_cost_share

"""
    adaptation_multiplier(years, nregions; scenario=:fixed, ...)

Return a `time × region` multiplier for the positive estimated joint climate response.
`fixed` preserves the observed baseline response. `trend` and `upper` attenuate
the response linearly from `base_year`, subject to their separate caps. These
are scenario controls, not estimated adaptation parameters: calibrate or
replace their values before producing SCC estimates.
"""
function adaptation_multiplier(years::AbstractVector{<:Integer}, nregions::Integer;
        scenario::Symbol = :fixed,
        base_year::Integer = first(years),
        trend_reduction_per_year::Float64 = 0.003,
        trend_max_reduction::Float64 = 0.35,
        upper_reduction_per_year::Float64 = 0.007,
        upper_max_reduction::Float64 = 0.70)
    nregions > 0 || throw(ArgumentError("nregions must be positive"))
    scenario in (:fixed, :trend, :upper) || throw(ArgumentError("scenario must be :fixed, :trend, or :upper"))

    multiplier = ones(Float64, length(years), nregions)
    scenario == :fixed && return multiplier
    rate, cap = scenario == :trend ?
        (trend_reduction_per_year, trend_max_reduction) :
        (upper_reduction_per_year, upper_max_reduction)
    (rate >= 0 && 0 <= cap <= 1) || throw(ArgumentError("adaptation rates must be nonnegative and caps in [0, 1]"))

    for (t, year) in enumerate(years)
        reduction = min(cap, max(0, year - base_year) * rate)
        multiplier[t, :] .= 1 - reduction
    end
    return multiplier
end

"""Return zero adaptation-cost shares until a calibrated cost schedule is supplied."""
adaptation_cost_share(years::AbstractVector{<:Integer}, nregions::Integer) = zeros(Float64, length(years), nregions)

end # module

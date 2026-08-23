"""
Fail-closed audit for paired agriculture-component outputs.

This module checks the outputs of matched baseline and CO2-pulse runs after
`CropResponseAggregation` and `JointAgriculture` have executed. It does not
estimate a response, validate welfare calibration, discount damages, or
authorize an SCC calculation.
"""
module PairedAgricultureAudit

export PairedOutputAudit, audit_paired_agriculture_outputs

const REQUIRED_FIELDS = (
    :crop_raw_loss_fraction,
    :crop_adjusted_loss_fraction,
    :regional_loss_fraction,
    :agcost,
)

struct PairedOutputAudit
    passed::Bool
    n_years::Int
    n_predivergence_years::Int
    first_divergence_year::Int
    maximum_absolute_differences::NamedTuple
    errors::Vector{String}
end

function _maximum_absolute_difference(left, right)
    isempty(left) && return 0.0
    return maximum(abs.(left .- right))
end

function _matched_within_tolerance(left, right, absolute_tolerance, relative_tolerance)
    return all(isapprox.(left, right; atol=absolute_tolerance, rtol=relative_tolerance))
end

_is_finite_numeric_array(values) =
    all(value -> value isa Real && isfinite(value), values)

function _field(outputs, name::Symbol, scenario::String, errors::Vector{String})
    if !hasproperty(outputs, name)
        push!(errors, "$(scenario) outputs are missing required field $(name)")
        return nothing
    end
    value = getproperty(outputs, name)
    if !(value isa AbstractArray)
        push!(errors, "$(scenario).$(name) must be an array")
        return nothing
    end
    return value
end

"""
    audit_paired_agriculture_outputs(years, baseline, pulse;
                                     first_divergence_year,
                                     expect_identical=false,
                                     absolute_tolerance=1e-10,
                                     relative_tolerance=0.0,
                                     throw_on_error=true)

Require matched finite baseline/pulse output arrays, strictly increasing model
years with observations on both sides of `first_divergence_year`, and exact
pre-divergence conservation within the declared tolerance. Set
`expect_identical=true` for the required zero-pulse control, which must match
over the complete model horizon.

`baseline` and `pulse` may be any objects with the four fields in
`REQUIRED_FIELDS`; a named tuple is convenient for extracting Mimi component
outputs. Crop fields must have dimensions `(time, region, crop)`, while
regional loss and `agcost` must have dimensions `(time, region)`.
"""
function audit_paired_agriculture_outputs(
    years,
    baseline,
    pulse;
    first_divergence_year::Integer,
    expect_identical::Bool=false,
    absolute_tolerance::Real=1e-10,
    relative_tolerance::Real=0.0,
    throw_on_error::Bool=true,
)
    errors = String[]
    isfinite(absolute_tolerance) && absolute_tolerance >= 0 ||
        push!(errors, "absolute_tolerance must be finite and nonnegative")
    isfinite(relative_tolerance) && relative_tolerance >= 0 ||
        push!(errors, "relative_tolerance must be finite and nonnegative")

    year_values = collect(years)
    valid_years = !isempty(year_values) && all(value -> value isa Integer, year_values)
    if !valid_years
        push!(errors, "years must be a nonempty integer sequence")
    elseif !issorted(year_values) || length(unique(year_values)) != length(year_values)
        push!(errors, "years must be strictly increasing and unique")
    end

    predivergence = valid_years ?
        findall(year -> year < first_divergence_year, year_values) : Int[]
    postdivergence = valid_years ?
        findall(year -> year >= first_divergence_year, year_values) : Int[]
    isempty(predivergence) &&
        push!(errors, "at least one modeled year must precede first_divergence_year")
    isempty(postdivergence) &&
        push!(errors, "first_divergence_year must fall within the modeled horizon")

    baseline_fields = Dict{Symbol, Any}()
    pulse_fields = Dict{Symbol, Any}()
    for name in REQUIRED_FIELDS
        baseline_fields[name] = _field(baseline, name, "baseline", errors)
        pulse_fields[name] = _field(pulse, name, "pulse", errors)
    end

    expected_ranks = Dict(
        :crop_raw_loss_fraction => 3,
        :crop_adjusted_loss_fraction => 3,
        :regional_loss_fraction => 2,
        :agcost => 2,
    )
    for name in REQUIRED_FIELDS
        left = baseline_fields[name]
        right = pulse_fields[name]
        (left === nothing || right === nothing) && continue
        ndims(left) == expected_ranks[name] ||
            push!(errors, "$(name) must have $(expected_ranks[name]) dimensions")
        size(left) == size(right) ||
            push!(errors, "baseline/pulse $(name) shapes are not matched")
        size(left, 1) == length(year_values) ||
            push!(errors, "$(name) time dimension does not match years")
        _is_finite_numeric_array(left) ||
            push!(errors, "baseline.$(name) contains nonnumeric or nonfinite values")
        _is_finite_numeric_array(right) ||
            push!(errors, "pulse.$(name) contains nonnumeric or nonfinite values")
    end

    raw = baseline_fields[:crop_raw_loss_fraction]
    adjusted = baseline_fields[:crop_adjusted_loss_fraction]
    regional = baseline_fields[:regional_loss_fraction]
    agcost = baseline_fields[:agcost]
    if all(value -> value !== nothing, (raw, adjusted, regional, agcost))
        size(raw) == size(adjusted) ||
            push!(errors, "crop raw and adjusted loss arrays must have identical shapes")
        size(raw, 1) == size(regional, 1) && size(raw, 2) == size(regional, 2) ||
            push!(errors, "crop and regional loss dimensions are inconsistent")
        size(regional) == size(agcost) ||
            push!(errors, "regional loss and agcost dimensions are inconsistent")
    end

    differences = Dict{Symbol, Float64}(name => NaN for name in REQUIRED_FIELDS)
    for name in REQUIRED_FIELDS
        left = baseline_fields[name]
        right = pulse_fields[name]
        if left === nothing || right === nothing || size(left) != size(right) ||
           !_is_finite_numeric_array(left) || !_is_finite_numeric_array(right)
            continue
        end
        differences[name] = _maximum_absolute_difference(left, right)
        if !isempty(predivergence)
            indices = (predivergence, ntuple(_ -> Colon(), ndims(left) - 1)...)
            if !_matched_within_tolerance(
                left[indices...], right[indices...], absolute_tolerance, relative_tolerance)
                push!(errors, "$(name) differs before first_divergence_year")
            end
        end
        if expect_identical && !_matched_within_tolerance(
            left, right, absolute_tolerance, relative_tolerance)
            push!(errors, "zero-pulse control changes $(name)")
        end
    end

    maximum_differences = NamedTuple{REQUIRED_FIELDS}(
        Tuple(differences[name] for name in REQUIRED_FIELDS)
    )
    audit = PairedOutputAudit(
        isempty(errors),
        length(year_values),
        length(predivergence),
        Int(first_divergence_year),
        maximum_differences,
        errors,
    )
    throw_on_error && !audit.passed && error(join(errors, "; "))
    return audit
end

end

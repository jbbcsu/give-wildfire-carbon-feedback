"""Anchored-level annual agriculture replacement for a marginal-response benchmark."""
module AnchoredAnnualAgriculture

using Mimi
using ..AgricultureReplacementAudit

export AnchoredAnnualMoney, install_anchored_replacement, set_anchored_pulse_path!

const ROLE = "anchored_marginal_response_replacement_benchmark"

@defcomp AnchoredAnnualMoney begin
    fund_regions = Index()
    damage = Parameter(index=[time, fund_regions], unit="billion US\$2005/yr")
    agcost = Variable(index=[time, fund_regions], unit="billion US\$2005/yr")

    function run_timestep(p, v, d, t)
        for region in d.fund_regions
            isfinite(p.damage[t, region]) || error("nonfinite anchored agriculture damage")
            v.agcost[t, region] = p.damage[t, region]
        end
    end
end

component_names(model) = Set(nameof(component) for component in Mimi.compdefs(model))

function validate_path(model, years, regions, amounts, role, source_hash)
    role == ROLE || error("anchored replacement role differs")
    occursin(r"^[0-9a-f]{64}$", source_hash) || error("canonical source hash required")
    collect(years) == collect(Mimi.dim_keys(model, :time)) || error("time axis differs")
    collect(regions) == collect(Mimi.dim_keys(model, :fund_regions)) || error("region axis differs")
    amounts isa AbstractMatrix || error("time-by-region matrix required")
    size(amounts) == (length(years), length(regions)) || error("damage dimensions differ")
    all(isfinite, amounts) || error("finite damages required")
    return Float64.(amounts)
end

function install_anchored_replacement(original; years, regions, baseline_amounts,
        evidence_role, baseline_source_hash)
    names = component_names(original)
    :Agriculture in names || error("legacy Agriculture component absent")
    !(:AnchoredAnnualMoney in names) || error("anchored replacement already installed")
    baseline = validate_path(original, years, regions, baseline_amounts,
        evidence_role, baseline_source_hash)
    outgoing = Mimi.get_connections(original, :Agriculture, :outgoing)
    length(outgoing) == 1 || error("unexpected legacy agriculture consumers")
    connection = only(outgoing)
    connection.src_var_name == :agcost || error("legacy source variable differs")
    model = deepcopy(original)
    delete!(model, :Agriculture; deep=true)
    add_comp!(model, AnchoredAnnualMoney; first=2020, before=:DamageAggregator)
    update_param!(model, :AnchoredAnnualMoney, :damage, copy(baseline))
    connect_param!(model, :DamageAggregator => :damage_ag, :AnchoredAnnualMoney => :agcost)
    audit_agriculture_replacement(model;
        expected_source_component=:AnchoredAnnualMoney,
        expected_source_variable=:agcost)
    return model
end

function set_anchored_pulse_path!(model; years, regions, baseline_amounts,
        marginal_increment, evidence_role, baseline_source_hash, increment_source_hash)
    baseline = validate_path(model, years, regions, baseline_amounts,
        evidence_role, baseline_source_hash)
    increment = validate_path(model, years, regions, marginal_increment,
        evidence_role, increment_source_hash)
    updated = baseline .+ increment
    all(isfinite, updated) || error("anchored pulse path overflow")
    update_param!(model, :AnchoredAnnualMoney, :damage, updated)
    return nothing
end

end

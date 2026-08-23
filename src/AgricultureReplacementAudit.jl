"""
Fail-closed structural audit for the GIVE agriculture replacement.

This module inspects Mimi's parameter-connection graph. It does not compare
damage totals, estimate a response, or authorize an SCC calculation.
"""
module AgricultureReplacementAudit

using Mimi

export AgricultureGraphAudit, audit_agriculture_replacement

const AgricultureProducer = NamedTuple{(:component, :variable), Tuple{Symbol, Symbol}}

struct AgricultureGraphAudit
    passed::Bool
    damage_ag_producers::Vector{AgricultureProducer}
    forbidden_components_present::Vector{Symbol}
    errors::Vector{String}
end

function _component_names(model::Mimi.Model)
    return Set(nameof(component) for component in Mimi.compdefs(model))
end

function _producer(model::Mimi.Model, connection)
    component = nameof(Mimi.compdef(Mimi.modeldef(model), connection.src_comp_path))
    return (component=component, variable=connection.src_var_name)
end

"""
    audit_agriculture_replacement(model; throw_on_error=true, ...)

Require exactly one internal producer for `DamageAggregator.damage_ag`, require
that producer to be `JointAgriculture.agcost`, and reject a simultaneously
instantiated component named `Agriculture`. The exact component names are part
of the production wiring contract so the audit remains transparent and
machine-checkable.

The returned object contains only graph metadata. By itself, a passing result
does not clear response-skill, welfare, coverage, future-support, or paired-run
validation gates.
"""
function audit_agriculture_replacement(
    model::Mimi.Model;
    damage_aggregator_component::Symbol=:DamageAggregator,
    damage_ag_parameter::Symbol=:damage_ag,
    expected_source_component::Symbol=:JointAgriculture,
    expected_source_variable::Symbol=:agcost,
    forbidden_component_names::Vector{Symbol}=[:Agriculture],
    throw_on_error::Bool=true,
)
    errors = String[]
    names = _component_names(model)

    producers = AgricultureProducer[]
    if !(damage_aggregator_component in names)
        push!(errors, "required component $(damage_aggregator_component) is absent")
    else
        incoming = Mimi.get_connections(model, damage_aggregator_component, :incoming)
        agriculture_connections = filter(
            connection -> connection.dst_par_name == damage_ag_parameter,
            incoming,
        )
        producers = [_producer(model, connection) for connection in agriculture_connections]
    end

    if damage_aggregator_component in names
        if length(producers) != 1
            push!(errors,
                  "$(damage_aggregator_component).$(damage_ag_parameter) must have exactly one internal producer; found $(length(producers))")
        elseif producers[1] != (component=expected_source_component, variable=expected_source_variable)
            producer = producers[1]
            push!(errors,
                  "$(damage_aggregator_component).$(damage_ag_parameter) is supplied by $(producer.component).$(producer.variable), not $(expected_source_component).$(expected_source_variable)")
        end
    end

    forbidden_present = sort!(collect(intersect(names, Set(forbidden_component_names))))
    if !isempty(forbidden_present)
        push!(errors,
              "forbidden agriculture component(s) remain instantiated: $(join(string.(forbidden_present), ", "))")
    end

    audit = AgricultureGraphAudit(isempty(errors), producers, forbidden_present, errors)
    throw_on_error && !audit.passed && error(join(errors, "; "))
    return audit
end

end

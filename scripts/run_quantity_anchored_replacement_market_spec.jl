#!/usr/bin/env julia

using DataFrames, CSVFiles, Mimi, MimiGIVE, SHA

length(ARGS) == 6 || error("usage: script GIVE_ROOT INCREMENT.csv EXPECTED.csv ELASTICITY_ID MAPPING OUTPUT.csv")
give_root, increment_path, expected_path, elasticity_id, supply_mapping, output_path = ARGS
isfile(output_path) && error("fresh output required")
dirname(Base.active_project()) == abspath(give_root) || error("GIVE project mismatch")
project = normpath(joinpath(@__DIR__, ".."))
include(joinpath(project, "src", "AgricultureReplacementAudit.jl")); include(joinpath(project, "src", "AnchoredAnnualAgriculture.jl"))
using .AgricultureReplacementAudit, .AnchoredAnnualAgriculture

const PULSE=0.000025; const RFF_SAMPLE_ID=6546; const SOURCE_HASH=bytes2hex(sha256(read(increment_path)))
const RATES=[(label="1.5%",prtp=exp(9.149606e-05)-1,eta=1.016010),(label="2.0%",prtp=exp(0.001972641)-1,eta=1.244458999),(label="2.5%",prtp=exp(0.004618784)-1,eta=1.421158088),(label="3.0%",prtp=exp(0.007702711)-1,eta=1.567899391)]
input=DataFrame(load(increment_path)); expected=DataFrame(load(expected_path)); paths=unique(input[:,[:climate_model,:adaptation,:tail_rule]]); sort!(paths,[:climate_model,:adaptation,:tail_rule]); nrow(paths)==156 || error("path support differs")
original=MimiGIVE.get_model(socioeconomics_source=:RFF,RFFSPsample=RFF_SAMPLE_ID); Mimi.run(original); years=collect(Mimi.dim_keys(original,:time)); regions=collect(Mimi.dim_keys(original,:fund_regions)); active=findall(y->y>=2020,years)
baseline=zeros(length(years),length(regions)); baseline[active,:]=original[:Agriculture,:agcost][active,:]; baseline_hash=bytes2hex(sha256(reinterpret(UInt8,vec(baseline)))); original_ag=copy(original[:DamageAggregator,:agriculture_damage]); original_cpc=copy(original[:global_netconsumption,:net_cpc])
fresh=MimiGIVE.get_model(socioeconomics_source=:RFF,RFFSPsample=RFF_SAMPLE_ID); anchored=install_anchored_replacement(fresh;years=years,regions=regions,baseline_amounts=baseline,evidence_role=AnchoredAnnualAgriculture.ROLE,baseline_source_hash=baseline_hash); audit_agriculture_replacement(anchored;expected_source_component=:AnchoredAnnualMoney,expected_source_variable=:agcost); Mimi.run(anchored)
base_ag_error=maximum(abs.(anchored[:DamageAggregator,:agriculture_damage][active].-original_ag[active])); base_cpc_error=maximum(abs.(anchored[:global_netconsumption,:net_cpc][active].-original_cpc[active])); base_ag_error==0.0 || error("baseline agriculture differs"); base_cpc_error==0.0 || error("baseline CPC differs")
yi=Dict(y=>i for (i,y) in enumerate(years)); ri=Dict(String(r)=>i for (i,r) in enumerate(regions)); y0=findfirst(==(2020),years); last=findfirst(==(2300),years); cpc=anchored[:global_netconsumption,:net_cpc]
open(output_path,"w") do io
 println(io,"climate_model,adaptation,tail_rule,elasticity_id,yield_to_supply_mapping,discount_rate_label,paired_replacement_usd2005_per_tco2,expected_usd2005_per_tco2,expected_usd2020_per_tco2,absolute_error,numerical_error_bound_usd2005_per_tco2,baseline_agriculture_error_usd,baseline_cpc_error,regional_increment_error_billion_usd2005,aggregated_increment_error_usd")
 for (path_number,path) in enumerate(eachrow(paths))
  model=String(path.climate_model); adaptation=String(path.adaptation); tail=String(path.tail_rule); rows=filter(r->String(r.climate_model)==model&&String(r.adaptation)==adaptation&&String(r.tail_rule)==tail,input); nrow(rows)==281*16 || error("regional support differs")
  increment=zeros(size(baseline)); for row in eachrow(rows); increment[yi[Int(row.year)],ri[String(row.fund_region)]]=Float64(row.marginal_damage_difference_billion_usd2005); end; count(v->!iszero(v),increment)>0 || error("empty increment")
  mm=MimiGIVE.get_marginal_model(anchored;year=2020,gas=:CO2,pulse_size=PULSE); set_anchored_pulse_path!(mm.modified;years=years,regions=regions,baseline_amounts=baseline,marginal_increment=increment,evidence_role=AnchoredAnnualAgriculture.ROLE,baseline_source_hash=baseline_hash,increment_source_hash=SOURCE_HASH); audit_agriculture_replacement(mm.base;expected_source_component=:AnchoredAnnualMoney,expected_source_variable=:agcost); audit_agriculture_replacement(mm.modified;expected_source_component=:AnchoredAnnualMoney,expected_source_variable=:agcost); Mimi.run(mm)
  observed=mm.modified[:AnchoredAnnualMoney,:agcost].-mm.base[:AnchoredAnnualMoney,:agcost]; region_error=maximum(abs.(observed[active,:].-increment[active,:])); region_error<=1e-12 || error("regional increment differs"); delta=mm.modified[:DamageAggregator,:agriculture_damage].-mm.base[:DamageAggregator,:agriculture_damage]; expected_delta=vec(sum(increment,dims=2)).*1e9; aggregate_error=maximum(abs.(delta[active].-expected_delta[active])); isfinite(aggregate_error)&&aggregate_error<=0.05 || error("aggregate differs")
  md=delta.*(12/44)./(1e9*PULSE); exp_rows=filter(r->String(r.climate_model)==model&&r.pulse_size_gtc==PULSE&&String(r.adaptation)==adaptation&&String(r.tail_rule)==tail&&String(r.elasticity_id)==elasticity_id&&String(r.yield_to_supply_mapping)==supply_mapping,expected); nrow(exp_rows)==4 || error("expected support differs")
  for rate in RATES
   factors=[(cpc[y0]/cpc[i])^rate.eta/(1+rate.prtp)^(years[i]-2020) for i in y0:last]; paired=sum(factors.*md[y0:last]); match=findfirst(x->isapprox(Float64(x),rate.prtp;rtol=0.0,atol=1e-15),exp_rows.prtp); isnothing(match)&&error("discount schedule absent"); exp2005=Float64(exp_rows[match,:partial_scc_diagnostic_usd2005_per_tco2]); exp2020=Float64(exp_rows[match,:partial_scc_diagnostic_usd2020_per_tco2]); err=abs(paired-exp2005); bound=aggregate_error*sum(abs,factors)*(12/44)/(1e9*PULSE); err<=bound+1e-15 || error("paired diagnostic differs"); println(io,join((model,adaptation,tail,elasticity_id,supply_mapping,rate.label,paired,exp2005,exp2020,err,bound,base_ag_error,base_cpc_error,region_error,aggregate_error),","))
  end
  path_number%20==0&&(println("completed_path=$(path_number)/156");flush(stdout)); mm=nothing; GC.gc()
 end
end
println("status=pass"); println("elasticity_id=$(elasticity_id)"); println("supply_mapping=$(supply_mapping)"); println("output_sha256=$(bytes2hex(sha256(read(output_path))))")

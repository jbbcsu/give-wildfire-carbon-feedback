# Biodiversity GIVE replication-access audit

Status: public-source follow-up completed September 19, 2026. No numerical
calibration or SCC result is authorized.

## Publicly specified model

The current RFF working paper provides the model architecture needed to test a
coefficient-free implementation:

- remaining biodiversity evolves as a function of a fixed non-climate loss
  term and squared annual global temperature change;
- the authors retain `theta = 0.001` for non-climate loss;
- their updated bootstrap estimate of the temperature coefficient `phi` has a
  reported mean of 2.77 and a 5th--95th percentile range of 2.33--3.25;
- the preferred valuation imposes unit income elasticity and uses the analytic
  logarithmic-limit willingness-to-pay expression;
- willingness to pay is calculated at country level using population, income,
  and one of 16 FUND-region preference coefficients; and
- the partial SCC is calculated from paired baseline and 0.1 Mt CO2 pulse
  runs through 2300, with one result per Monte Carlo draw.

Primary source: [Wingenroth et al., *Accounting for Biodiversity Loss Raises
the Social Cost of CO2*](https://www.rff.org/documents/4714/WP_24-23.pdf),
especially pp. 5--7. The paper reports a preferred biodiversity-nonuse partial
SC-CO2 of about USD 8/tCO2 (USD 3--16, 5th--95th percentile) and an original
Brooks--Newbold comparison of about USD 6/tCO2 (USD 2--13). These values are
external publication benchmarks, not results reproduced by this repository.

## Inputs still not publicly resolved

The working paper does not include the numerical table of 16 recalculated
regional `beta` coefficients, the underlying regional income/WTP calibration
table used to derive them at unit income elasticity, the 20,000-draw `phi`
sample, or the joint 10,000-run parameter bundle used for the reported SCC.
It also does not state a public code or data-availability link.

A focused September 19 search of RFF, GitHub, and Zenodo for the paper title,
authors, and replication terminology did not identify an author-controlled
replication package. This is a scoped search result, not proof that no package
exists or that inputs cannot be obtained from the authors.

## Consequence for implementation

The existing Python and Julia kernels remain correctly coefficient-free. The
paper's printed central `phi` must not be installed as a calibrated default:
doing so would discard empirical uncertainty and still leave regional
valuation unresolved. Likewise, back-solving a single global valuation
coefficient from the reported USD 8/tCO2 would confound preferences, climate,
socioeconomics, discounting, and model nonlinearities.

The next defensible source step is an author request for:

1. the 16 preferred regional `beta` values and their source income/WTP units;
2. the bootstrapped `phi` draw vector or sufficient grouped Urban inputs to
   reconstruct it;
3. the country-to-FUND-region mapping/version used in the paper;
4. the joint Monte Carlo pairing rule; and
5. a code/data license or public replication location.

Until those inputs are obtained and independently reconciled, this project can
validate only the algebra, paired baseline/pulse accounting, mappings supplied
explicitly by a caller, and limiting identities. It cannot reproduce the
published distribution, choose empirical parameters, add biodiversity damages
to GIVE, or report an SCC.

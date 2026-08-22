module BiodiversityNonuse

export next_biodiversity, no_climate_biodiversity, climate_deficit,
       per_capita_wtp, country_damage

function next_biodiversity(stock, temperature_change; theta, phi)
    stock >= 0 || throw(DomainError(stock, "biodiversity stock must be nonnegative"))
    theta >= 0 || throw(DomainError(theta, "theta must be nonnegative"))
    phi >= 0 || throw(DomainError(phi, "phi must be nonnegative"))
    loss_rate = theta + phi * temperature_change^2
    0 <= loss_rate < 1 || throw(DomainError(loss_rate, "annual loss rate must be in [0, 1)"))
    stock * (1 - loss_rate)
end

function no_climate_biodiversity(initial_stock, years; theta)
    initial_stock >= 0 || throw(DomainError(initial_stock))
    years >= 0 || throw(DomainError(years))
    0 <= theta < 1 || throw(DomainError(theta))
    initial_stock * (1 - theta)^years
end

function climate_deficit(no_climate_stock, climate_stock)
    no_climate_stock >= 0 || throw(DomainError(no_climate_stock))
    climate_stock >= 0 || throw(DomainError(climate_stock))
    max(no_climate_stock - climate_stock, zero(promote_type(typeof(no_climate_stock), typeof(climate_stock))))
end

function per_capita_wtp(income, remaining_stock, deficit; beta)
    income >= 0 || throw(DomainError(income))
    remaining_stock > 0 || throw(DomainError(remaining_stock))
    deficit >= 0 || throw(DomainError(deficit))
    beta >= 0 || throw(DomainError(beta))
    income * (1 - (1 + deficit / remaining_stock)^(-beta))
end

function country_damage(population, income, remaining_stock, deficit; beta)
    population >= 0 || throw(DomainError(population))
    population * per_capita_wtp(income, remaining_stock, deficit; beta=beta)
end

end

"""Executable reference equations for the biodiversity nonuse module."""


def next_biodiversity(stock: float, temperature_change: float, *, theta: float, phi: float) -> float:
    if stock < 0 or theta < 0 or phi < 0:
        raise ValueError("stock and loss parameters must be nonnegative")
    loss_rate = theta + phi * temperature_change**2
    if not 0 <= loss_rate < 1:
        raise ValueError("annual loss rate must be in [0, 1)")
    return stock * (1 - loss_rate)


def no_climate_biodiversity(initial_stock: float, years: int, *, theta: float) -> float:
    if initial_stock < 0 or years < 0 or not 0 <= theta < 1:
        raise ValueError("invalid stock, years, or theta")
    return initial_stock * (1 - theta) ** years


def climate_deficit(no_climate_stock: float, climate_stock: float) -> float:
    if no_climate_stock < 0 or climate_stock < 0:
        raise ValueError("stocks must be nonnegative")
    return max(no_climate_stock - climate_stock, 0.0)


def per_capita_wtp(income: float, remaining_stock: float, deficit: float, *, beta: float) -> float:
    if income < 0 or remaining_stock <= 0 or deficit < 0 or beta < 0:
        raise ValueError("invalid valuation input")
    return income * (1 - (1 + deficit / remaining_stock) ** (-beta))


def country_damage(population: float, income: float, remaining_stock: float, deficit: float, *, beta: float) -> float:
    if population < 0:
        raise ValueError("population must be nonnegative")
    return population * per_capita_wtp(income, remaining_stock, deficit, beta=beta)

"""Small calendar arithmetic tests for raw-CMIP6 annual GMST reduction."""
import math

from build_pangeo_annual_gmst import annualize


def rejects(rows):
    try:
        annualize(rows, 2001, 2001)
    except ValueError:
        return
    raise AssertionError("invalid annual source accepted")


def main():
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    rows = [dict(year=2001, month=m, seconds=d * 86400,
                 gmst_month_k=280.0 + m) for m, d in enumerate(days, 1)]
    got, = annualize(rows, 2001, 2001)
    expect = math.fsum((280 + m) * d for m, d in enumerate(days, 1)) / 365
    assert math.isclose(got["gmst_value_k"], expect, rel_tol=0, abs_tol=1e-12)
    assert got["seconds"] == 365 * 86400
    rejects(rows[:-1])
    bad = [dict(r) for r in rows]; bad[-1]["month"] = 11
    rejects(bad)
    bad = [dict(r) for r in rows]; bad[-1]["seconds"] = 25 * 86400
    rejects(bad)
    print("raw-CMIP6 GMST calendar arithmetic checks pass")


if __name__ == "__main__":
    main()

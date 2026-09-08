"""Explicit source-bound daily date contracts, without loading climate arrays."""
from datetime import date


def date_contract(start=2041, end=2050):
    if type(start) is not int or type(end) is not int or not 1900 <= start <= end <= 2100:
        raise ValueError('invalid registered climate years')
    first, last = date(start, 1, 1), date(end, 12, 31)
    return first.isoformat(), last.isoformat(), (last-first).days+1


def registered_years(config):
    start = config.get('expected_start_year', 2041)
    end = config.get('expected_end_year', 2050)
    _, _, days = date_contract(start, end)
    if not config['file_name'].endswith(f'_{start}_{end}.nc'):
        raise ValueError('registered dates disagree with source file name')
    if config['expected_gregorian_daily_count'] != days:
        raise ValueError('registered daily count disagrees with Gregorian dates')
    return start, end

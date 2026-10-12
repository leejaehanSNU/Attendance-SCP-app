from datetime import date, timedelta


UNAUTHORIZED_OUT = '\ubb34\ub2e8 \ud1f4\uadfc'
UNAUTHORIZED_ABSENT = '\ubb34\ub2e8 \uacb0\uadfc'
UNAUTHORIZED_LATE = '\ubb34\ub2e8 \uc9c0\uac01'

CLOCK_IN_TYPES = frozenset(('\ucd9c\uadfc', '\uc9c0\uac01'))
CLOCK_OUT_TYPES = frozenset(('\ud1f4\uadfc', '\uc870\ud1f4'))
AUTO_TYPES = frozenset((UNAUTHORIZED_OUT, UNAUTHORIZED_ABSENT, UNAUTHORIZED_LATE))
REAL_ATTENDANCE_TYPES = CLOCK_IN_TYPES | CLOCK_OUT_TYPES | frozenset(('\uacb0\uadfc',))

# Official Republic of Korea public holidays for the year covered by the
# current attendance sheet. Weekend dates are harmless but omitted here.
KOREAN_PUBLIC_HOLIDAYS = frozenset((
    date(2026, 1, 1),
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 3, 2),
    date(2026, 5, 5), date(2026, 5, 25),
    date(2026, 6, 3),
    date(2026, 8, 17),
    date(2026, 9, 24), date(2026, 9, 25),
    date(2026, 10, 5), date(2026, 10, 9),
    date(2026, 12, 25),
))


def is_workday(day):
    return day.weekday() < 5 and day not in KOREAN_PUBLIC_HOLIDAYS


def has_real_attendance(record_types):
    return bool(set(record_types).intersection(REAL_ATTENDANCE_TYPES))


def unauthorized_status_for(record_types):
    '''Return the one automatic status needed for a completed workday.'''
    types = set(record_types)
    if '\uacb0\uadfc' in types or types.intersection(AUTO_TYPES):
        return None

    has_clock_in = bool(types.intersection(CLOCK_IN_TYPES))
    has_clock_out = bool(types.intersection(CLOCK_OUT_TYPES))

    if not has_clock_in and not has_clock_out:
        return UNAUTHORIZED_ABSENT
    if has_clock_in and not has_clock_out:
        return UNAUTHORIZED_OUT
    if not has_clock_in and has_clock_out:
        return UNAUTHORIZED_LATE
    return None


def work_dates_to_close(now_kst):
    '''Return workdays safe to close without racing normal 18:00 check-outs.'''
    last_closed_date = now_kst.date() - timedelta(days=1)
    if is_workday(now_kst.date()) and (now_kst.hour, now_kst.minute) >= (23, 59):
        last_closed_date = now_kst.date()

    current = now_kst.date().replace(day=1)
    dates = []
    while current <= last_closed_date:
        if is_workday(current):
            dates.append(current)
        current += timedelta(days=1)
    return dates

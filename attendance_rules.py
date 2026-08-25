from datetime import timedelta


UNAUTHORIZED_OUT = '\ubb34\ub2e8 \ud1f4\uadfc'
UNAUTHORIZED_ABSENT = '\ubb34\ub2e8 \uacb0\uadfc'
UNAUTHORIZED_LATE = '\ubb34\ub2e8 \uc9c0\uac01'

CLOCK_IN_TYPES = frozenset(('\ucd9c\uadfc', '\uc9c0\uac01'))
CLOCK_OUT_TYPES = frozenset(('\ud1f4\uadfc', '\uc870\ud1f4'))
AUTO_TYPES = frozenset((UNAUTHORIZED_OUT, UNAUTHORIZED_ABSENT, UNAUTHORIZED_LATE))


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
    previous_workday = now_kst.date() - timedelta(days=1)
    while previous_workday.weekday() >= 5:
        previous_workday -= timedelta(days=1)

    dates = {previous_workday}
    if now_kst.weekday() < 5 and (now_kst.hour, now_kst.minute) >= (23, 59):
        dates.add(now_kst.date())
    return sorted(dates)

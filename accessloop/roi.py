"""Value of an agent run: measured agent time next to an estimate of the same work done by hand.

What is MEASURED comes from the run itself: how many fixes were kept (each one verified by a re-scan), how many were
handed to a person, and how long the agent took (real time, presentation pauses excluded).

What is ASSUMED is shown, labelled and editable, never hidden: minutes for a developer to find, fix and re-test one
issue by hand; minutes for a person to check one agent fix in the run report; minutes to type one answer the agent
asked for; the cost of an hour of developer time; how many pages a year. The defaults are deliberately modest
placeholders for an organisation to replace with its own figures.
"""
from __future__ import annotations

DEFAULTS = {
    'minutes_by_hand': 12.0,      # find the code, change it, re-test the page, for one issue
    'minutes_to_check': 0.5,      # read one verified agent fix in the run report
    'minutes_to_answer': 2.0,     # type one answer the agent asked for (alt text, a name)
    'cost_per_hour': 1200.0,      # fully loaded developer cost per hour
    'pages_per_year': 200,        # customer-facing pages repaired in a year
    'currency': '₹',
}

LABELS = {
    'minutes_by_hand': 'Minutes to find, fix and re-test one issue by hand',
    'minutes_to_check': 'Minutes to check one verified agent fix',
    'minutes_to_answer': 'Minutes to type one answer the agent asks for',
    'cost_per_hour': 'Developer cost per hour',
    'pages_per_year': 'Pages repaired per year',
}


def assumptions(overrides: dict | None = None) -> dict:
    out = dict(DEFAULTS)
    for k, v in (overrides or {}).items():
        if k in DEFAULTS and k != 'currency':
            try:
                out[k] = max(0.0, float(v))
            except (TypeError, ValueError):
                pass
        elif k == 'currency' and isinstance(v, str) and 0 < len(v) <= 4:
            out[k] = v
    out['pages_per_year'] = int(out['pages_per_year'])
    return out


def money(value: float, currency: str = '₹') -> str:
    """Indian grouping for rupees (1,23,456), Western grouping otherwise."""
    n = int(round(value))
    sign = '-' if n < 0 else ''
    n = abs(n)
    if currency == '₹':
        s = str(n)
        if len(s) > 3:
            head, tail = s[:-3], s[-3:]
            groups = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            if head:
                groups.insert(0, head)
            s = ','.join(groups) + ',' + tail
        return f'{sign}{currency}{s}'
    return f'{sign}{currency}{n:,}'


def _hm(minutes: float) -> str:
    if minutes < 1:
        return f'{round(minutes * 60)} s'
    if minutes < 60:
        return f'{minutes:.0f} min'
    return f'{minutes / 60:.1f} h'


def estimate(run: dict, overrides: dict | None = None) -> dict:
    """run: Run.to_dict() (or the session's agent_run). Returns measured figures, assumptions and the estimate."""
    a = assumptions(overrides)
    fixes = int(run.get('applied') or 0)
    asked = len(run.get('questions') or [])
    agent_minutes = float(run.get('seconds') or 0) / 60
    by_hand = (fixes + asked) * a['minutes_by_hand']
    with_tool = agent_minutes + fixes * a['minutes_to_check'] + asked * a['minutes_to_answer']
    saved = max(0.0, by_hand - with_tool)
    per_hour = a['cost_per_hour'] / 60
    year_saved = saved * a['pages_per_year']
    return {
        'measured': {'fixes_kept_and_verified': fixes, 'handed_to_a_person': asked, 'rolled_back': int(run.get('rolled_back') or 0),
                     'agent_seconds': round(float(run.get('seconds') or 0), 1),
                     'violations_before': run.get('before'), 'violations_after': run.get('after')},
        'assumptions': a,
        'estimate': {'minutes_by_hand': round(by_hand, 1), 'minutes_with_accessloop': round(with_tool, 1),
                     'minutes_saved': round(saved, 1), 'percent_saved': round(100 * saved / by_hand) if by_hand else 0,
                     'cost_by_hand': round(by_hand * per_hour), 'cost_with_accessloop': round(with_tool * per_hour),
                     'cost_saved': round(saved * per_hour),
                     'hours_saved_per_year': round(year_saved / 60), 'cost_saved_per_year': round(year_saved * per_hour)},
        'basis': ('Measured: fixes kept (each verified by an independent re-scan), items handed to a person, agent time. '
                  'Assumed (editable): the minutes and cost figures listed. The yearly figure assumes every page is like '
                  'this one. Not counted: avoided complaints, penalties or audit costs.'),
    }


def summary(value: dict) -> str:
    """One sentence for a slide, a console line or a report."""
    m, e, a = value['measured'], value['estimate'], value['assumptions']
    if not (m['fixes_kept_and_verified'] + m['handed_to_a_person']):
        return 'Nothing was fixed in this run, so there is no time saving to show.'
    return (f'{m["fixes_kept_and_verified"]} verified fixes in {m["agent_seconds"]} s of agent time: about '
            f'{_hm(e["minutes_by_hand"])} of work by hand becomes {_hm(e["minutes_with_accessloop"])} of a person\'s time '
            f'({e["percent_saved"]}% less, about {money(e["cost_saved"], a["currency"])} on this page at the assumed rates).')


def table_rows(value: dict) -> list[tuple[str, str, str]]:
    """(what, figure, kind) rows for reports: kind is 'measured', 'assumed' or 'estimate'."""
    m, a, e = value['measured'], value['assumptions'], value['estimate']
    c = a['currency']
    return [
        ('Fixes kept, each verified by a re-scan', str(m['fixes_kept_and_verified']), 'measured'),
        ('Fixes that needed a person\'s words', str(m['handed_to_a_person']), 'measured'),
        ('Agent time', f'{m["agent_seconds"]} s', 'measured'),
        (LABELS['minutes_by_hand'], f'{a["minutes_by_hand"]:g}', 'assumed'),
        (LABELS['minutes_to_check'], f'{a["minutes_to_check"]:g}', 'assumed'),
        (LABELS['minutes_to_answer'], f'{a["minutes_to_answer"]:g}', 'assumed'),
        (LABELS['cost_per_hour'], money(a['cost_per_hour'], c), 'assumed'),
        (LABELS['pages_per_year'], str(a['pages_per_year']), 'assumed'),
        ('Same work by hand', f'{_hm(e["minutes_by_hand"])} · {money(e["cost_by_hand"], c)}', 'estimate'),
        ('With AccessLoop (agent + a person)', f'{_hm(e["minutes_with_accessloop"])} · {money(e["cost_with_accessloop"], c)}', 'estimate'),
        ('Saved on this page', f'{_hm(e["minutes_saved"])} · {money(e["cost_saved"], c)} ({e["percent_saved"]}%)', 'estimate'),
        ('Saved per year at that page count', f'{e["hours_saved_per_year"]:,} h · {money(e["cost_saved_per_year"], c)}', 'estimate'),
    ]

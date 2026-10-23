"""Guards that make the issue catalogue complete and honest."""
import re
from accessloop import catalog
from accessloop.scanner import TAGS


def test_every_axe_rule_is_classified():
    ids = [r['ruleId'] for r in catalog.load_rules()['rules']]
    assert catalog.unclassified(ids) == [], 'new axe rule(s) need a handling class in accessloop/catalog.py'


def test_no_rule_in_two_classes():
    assert catalog.overlapping() == []


def test_no_stale_entries_for_rules_axe_no_longer_has():
    ids = {r['ruleId'] for r in catalog.load_rules()['rules']}
    known = set(catalog.LIVE) | set(catalog.AUTO) | set(catalog.ASSISTED) | catalog.GUIDED | set(catalog.EXCLUDED)
    assert known - ids == set()


def test_all_55_wcag_22_a_aa_criteria_present_and_unique():
    nums = [c[0] for c in catalog.CRITERIA]
    assert len(nums) == 55 and len(set(nums)) == 55
    assert sum(1 for c in catalog.CRITERIA if c[2] == 'A') == 31
    assert sum(1 for c in catalog.CRITERIA if c[2] == 'AA') == 24
    assert all(re.fullmatch(r'\d\.\d\.\d+', n) for n in nums)


def test_live_fixes_match_the_planner():
    from accessloop.fixers import FIXERS, MODES
    assert set(catalog.LIVE) == {r for r in FIXERS if not r.startswith('al-')}
    assert len(catalog.LIVE) >= 30
    assert set(MODES.values()) <= {'auto', 'input', 'mixed'}
    # A rule is either live or planned, never both.
    assert not (set(catalog.LIVE) & (set(catalog.AUTO) | set(catalog.ASSISTED) | catalog.GUIDED))


def test_summary_numbers_add_up():
    built = catalog.build()
    s = built['summary']
    assert sum(s['by_handling'].values()) == s['total_rules'] == len(built['rules'])
    assert s['scanned_today'] + s['not_scanned_today'] == s['total_rules']
    assert s['criteria_axe_testable'] + s['criteria_manual_only'] == 55


def test_scan_tags_match_what_was_measured():
    # data/axe_scanned_today.json was measured with these tags; if they change, re-run --refresh.
    assert tuple(TAGS) == ('wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa')


def test_excluded_rules_are_not_run_today():
    built = {r['rule_id']: r for r in catalog.build()['rules']}
    for rule in catalog.EXCLUDED:
        assert not built[rule]['scanned_today'], rule


def test_outputs_render():
    built = catalog.build()
    md = catalog.to_markdown(built)
    assert 'UNCLASSIFIED' not in md and '3.3.4' in md
    assert catalog.to_csv(built).count('\n') >= built['summary']['total_rules']

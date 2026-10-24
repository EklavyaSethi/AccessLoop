from accessloop import roi, agent_report

Q = {'rule': 'image-alt', 'selector': 'img', 'line': 3, 'question': 'Describe the image'}
RUN = {'applied': 7, 'questions': [Q, Q, Q], 'seconds': 3.9, 'rolled_back': 1, 'before': 40, 'after': 12}


def test_estimate_uses_measured_figures_and_labelled_assumptions():
    v = roi.estimate(RUN)
    assert v['measured']['fixes_kept_and_verified'] == 7 and v['measured']['handed_to_a_person'] == 3
    e = v['estimate']
    assert e['minutes_by_hand'] == 120.0                       # (7 + 3) x 12
    assert abs(e['minutes_with_accessloop'] - (3.9 / 60 + 3.5 + 6)) < 0.1
    assert 0 < e['percent_saved'] < 100
    assert e['cost_saved_per_year'] == round((120 - (3.9 / 60 + 9.5)) * 200 * 20)     # 200 pages, Rs 1,200/h = Rs 20/min
    kinds = {k for _, _, k in roi.table_rows(v)}
    assert kinds == {'measured', 'assumed', 'estimate'}
    assert 'Assumed' in v['basis']


def test_overrides_are_validated():
    a = roi.assumptions({'minutes_by_hand': '30', 'cost_per_hour': 'lots', 'pages_per_year': -5, 'evil': 1})
    assert a['minutes_by_hand'] == 30.0 and a['cost_per_hour'] == roi.DEFAULTS['cost_per_hour']
    assert a['pages_per_year'] == 0 and 'evil' not in a


def test_nothing_fixed_claims_no_saving():
    v = roi.estimate({'applied': 0, 'questions': [], 'seconds': 2})
    assert v['estimate']['minutes_saved'] == 0
    assert 'no time saving' in roi.summary(v)


def test_indian_money_format():
    assert roi.money(441740) == '₹4,41,740'
    assert roi.money(12345678) == '₹1,23,45,678'
    assert roi.money(1500, '$') == '$1,500'


def test_run_report_contains_value_section():
    state = {'agent': {**RUN, 'policy': {}, 'policy_text': 'p', 'held': [], 'console': [], 'reviews_before': 0,
                       'reviews_after': 0, 'decisions': 1, 'stopped': ''}, 'events': [], 'fix_log': [], 'audit': {}}
    doc = agent_report.build(state)
    assert doc['value']['measured']['fixes_kept_and_verified'] == 7
    html = agent_report.to_html(doc)
    assert 'Value of this run (estimate)' in html and 'assumption' in html and '₹' in html

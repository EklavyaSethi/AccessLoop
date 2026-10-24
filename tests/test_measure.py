from accessloop import measure


def test_markdown_reports_measured_figures():
    res = {'summary': {'pages': 2, 'ai_provider': 'off (rule-based)', 'violations_before': 10, 'violations_after_agent': 4,
                       'violations_after_drafts': 2, 'fixes_kept': 6, 'rolled_back': 0, 'questions': 3, 'drafts': 2,
                       'drafts_ai': 0, 'drafts_verified': 2, 'draft_pass_rate': 100, 'scan_plus_agent_seconds_median': 1.0,
                       'scan_plus_agent_seconds_total': 2.0, 'pages_per_minute': 60.0, 'agent_seconds_per_fix': 0.2,
                       'machine': 'test', 'refused_unsafe_pages': 1},
           'pages': [{'page': 'a.html', 'violations_before': 5, 'violations_after': 2, 'violations_final': 1, 'fixes_kept': 3,
                      'drafts_verified': 1, 'drafts': 1, 'total_s': 1.0}]}
    md = measure.to_markdown(res, 'Rule-based drafts (no AI)')
    assert '10 → 4 → 2' in md and '60.0 pages per minute' in md and '(+ 1)' in md
    assert 'still needs a person' in md

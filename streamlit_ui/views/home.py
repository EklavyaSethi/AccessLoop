from __future__ import annotations
import streamlit as st
from .. import ui


def render() -> None:
    s = ui.session()
    summary = s.catalog['summary']
    st.markdown(f"""
<div class="al-hero">
  <span class="al-eyebrow">Accessibility repair with a human in the loop</span>
  <h1>Fix accessibility issues. Prove every fix.</h1>
  <p>AccessLoop scans a web page, proposes small template-based repairs, applies only the ones you approve,
  re-scans to verify, and automatically undoes anything that makes the page worse.</p>
</div>""", unsafe_allow_html=True)
    a, b, c = st.columns([1, 1, 2])
    with a:
        ui.link('load', 'Start with a page', ':material/play_arrow:')
    with b:
        ui.link('how', 'How it works', ':material/help:')

    st.markdown(f"""
<div class="al-trust">
  <div class="al-stat"><div class="n">{summary['by_handling']['live']}</div><div class="l">issue types it can fix, each proven in a real browser</div></div>
  <div class="al-stat"><div class="n">{summary['scanned_today'] + summary['best_practice_optional']}</div><div class="l">rules checked on every scan</div></div>
  <div class="al-stat"><div class="n">{summary['criteria_total']}</div><div class="l">WCAG 2.2 A and AA criteria mapped</div></div>
  <div class="al-stat"><div class="n">100%</div><div class="l">of source changes need your approval</div></div>
</div>

<div class="al-section"><h2>How a repair works</h2><p>Four steps, each one visible and reversible.</p></div>
<div class="al-grid c4">
  <div class="al-card"><div class="al-ico">1</div><h3>Scan</h3><p>A real browser opens the page and the industry-standard axe-core engine lists every barrier it can detect, by severity.</p></div>
  <div class="al-card"><div class="al-ico">2</div><h3>Propose</h3><p>For safe, unambiguous problems, a fixed template prepares an exact before-and-after change. No free-form generated code.</p></div>
  <div class="al-card"><div class="al-ico">3</div><h3>Approve</h3><p>You review each diff and approve or reject it. Nothing is written without your decision, and your name is recorded.</p></div>
  <div class="al-card"><div class="al-ico">4</div><h3>Verify</h3><p>The page is scanned again. If the issue is not gone, or anything else got worse, the change is rolled back automatically.</p></div>
</div>

<div class="al-section"><h2>Built for regulated finance teams</h2><p>Banks, insurers and wealth platforms need accessible digital services and a trail an auditor can read.</p></div>
<div class="al-grid c3">
  <div class="al-card"><h3>Evidence for auditors</h3><p>A printable report lists every decision, who made it, the exact change, and file fingerprints (SHA-256) before and after.</p></div>
  <div class="al-card"><h3>Safe on sensitive forms</h3><p>KYC, payment and claim forms are never auto-rewritten. Changes are small, reviewed, re-tested and reversible.</p></div>
  <div class="al-card"><h3>Mapped to the standards</h3><p>Every rule is mapped to WCAG 2.2, supporting teams working towards SEBI digital-accessibility and EU Accessibility Act expectations. It is not a compliance certificate.</p></div>
</div>

<div class="al-section"><h2>What it does today, and what is next</h2></div>
<div class="al-grid c2">
  <div class="al-card"><h3>Available now</h3><p>Static HTML pages, whole sites (.zip) and server-side templates. Agent mode plus human-approved fixes for {summary['by_handling']['live']} rule types: missing alt text, link and button names, labels, page language and title, zoom blocking, low contrast, invalid ARIA, headings, landmarks, tables and more. Text only you can supply is always typed by you, never guessed. A WCAG checklist covers what no tool can test.</p></div>
  <div class="al-card"><h3>Roadmap</h3><p>React, Angular and Vue component sources; company single sign-on; AI-drafted wording that a person approves; the {summary['by_handling']['guided']} remaining structural rules as reviewer-decided fixes.</p></div>
</div>
""", unsafe_allow_html=True)
    ui.footer()

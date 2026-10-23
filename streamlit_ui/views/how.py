from __future__ import annotations
import streamlit as st
from .. import ui


def render() -> None:
    ui.page_header('How AccessLoop works', 'In plain language: an inspector, a contractor and you.', None, None)
    ui.h2('The six parts')
    st.markdown("""
<div class="al-grid c3">
  <div class="al-card"><div class="al-ico">🔍</div><h3>The inspector</h3><p>The scanner walks through the page in a real browser and writes down every barrier it can detect, with how serious each one is.</p></div>
  <div class="al-card"><div class="al-ico">📝</div><h3>The contractor</h3><p>The planner prepares an exact work order, but only for safe repairs such as page language, form labels and button names. It uses fixed templates, not free-form code.</p></div>
  <div class="al-card"><div class="al-ico">✅</div><h3>You, the site manager</h3><p>You see each change as a before-and-after comparison. Nothing is written until you press Approve.</p></div>
</div>
<div class="al-grid c3" style="margin-top:14px">
  <div class="al-card"><div class="al-ico">🔁</div><h3>The re-inspection</h3><p>Right after each approved change the page is scanned again. A fix counts only if the problem is gone and nothing else got worse.</p></div>
  <div class="al-card"><div class="al-ico">↩️</div><h3>The undo button</h3><p>If the problem is still there, or anything else got worse, the change is reverted automatically to exactly what it was before.</p></div>
  <div class="al-card"><div class="al-ico">📄</div><h3>The paperwork</h3><p>Every decision, the reviewer, the exact change and file fingerprints go into a report an auditor can read without trusting the tool.</p></div>
</div>""", unsafe_allow_html=True)
    ui.h2('What it deliberately does not do')
    st.write('- It does not change anything without your approval.')
    st.write('- It does not let AI write code. The optional AI step only comments on a proposal.')
    st.write('- It does not guess. If the page language is not set, you choose it. If a button is ambiguous, a human decides.')
    st.write('- It does not claim a page is "WCAG compliant". Automated checking finds only part of the real barriers.')
    st.write('- It works on static HTML today. JavaScript frameworks are on the roadmap.')
    st.write('- Your page code stays on this machine. The only exception is the optional AI review, which you trigger yourself.')
    ui.h2('Walk-through')
    st.write('1. **Load** a sample or your own HTML file.  2. **Scan** it.  3. **Review** each proposed fix and approve or reject it.  '
             '4. **Verify** the re-scan result.  5. **Report**: download the evidence report.')
    ui.h2('Why it suits banking and insurance')
    st.write('Regulators such as SEBI in India and the European Accessibility Act expect accessible digital services. Finance flows also need '
             'careful handling of error prevention and re-entry of data. Reviewed, logged, reversible changes with an evidence report fit how regulated teams already work.')
    ui.footer()

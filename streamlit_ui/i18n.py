"""Interface language for the Streamlit app: English (default) or Hindi.

Translations cover navigation, page titles and introductions, step names, workflow buttons and key labels. Text that
comes from the accessibility engine (rule names, WCAG titles, evidence) stays in English, as auditors expect.
Hindi text is marked lang="hi" so screen readers switch voice. Machine-written: have a native speaker review it.
"""
from __future__ import annotations
import streamlit as st

LANGS = {'en': 'English', 'hi': 'हिन्दी (Hindi)'}

HI: dict[str, str] = {
    # navigation
    'Home': 'होम', '1 · Load page': '1 · पेज लोड करें', '2 · Scan': '2 · स्कैन', '3 · Review fixes': '3 · सुधारों की समीक्षा',
    '4 · Verify results': '4 · परिणाम सत्यापित करें', 'Manual review queue': 'मैनुअल समीक्षा सूची',
    'WCAG manual checklist': 'WCAG मैनुअल जाँच सूची', 'Page preview': 'पेज पूर्वावलोकन', 'Site scan (many pages)': 'साइट स्कैन (कई पेज)',
    'Reports and downloads': 'रिपोर्ट और डाउनलोड', 'Audit trail': 'ऑडिट ट्रेल', 'Agent trace': 'एजेंट ट्रेस',
    '★ Agent mode': '★ एजेंट मोड', 'Let the agent repair this page': 'एजेंट को यह पेज ठीक करने दें',
    'Apply my answers': 'मेरे उत्तर लागू करें', 'Fixes kept': 'रखे गए सुधार', 'Waiting for you': 'आपकी प्रतीक्षा में',
    'Issue coverage': 'समस्याओं का कवरेज', 'How it works': 'यह कैसे काम करता है',
    'Workflow': 'कार्यप्रवाह', 'Workspace': 'कार्यक्षेत्र', 'Evidence': 'साक्ष्य', 'Reference': 'संदर्भ',
    # steps
    'Load': 'लोड', 'Scan': 'स्कैन', 'Review': 'समीक्षा', 'Verify': 'सत्यापन', 'Report': 'रिपोर्ट',
    # buttons and labels
    'Load sample page': 'नमूना पेज लोड करें', 'Load uploaded file': 'अपलोड की गई फ़ाइल लोड करें', 'Load pasted HTML': 'चिपकाया गया HTML लोड करें',
    'Run accessibility scan': 'सुलभता स्कैन चलाएँ', 'Approve and verify': 'स्वीकृत करें और सत्यापित करें',
    'Reject (no change)': 'अस्वीकार करें (कोई बदलाव नहीं)', 'Preview what a screen reader will hear': 'देखें कि स्क्रीन रीडर क्या बोलेगा',
    'Request AI review': 'AI समीक्षा माँगें', 'Render both versions': 'दोनों संस्करण दिखाएँ', 'Save result': 'परिणाम सहेजें',
    'Scan site': 'साइट स्कैन करें', 'Undo': 'वापस लें', 'Confirm and apply': 'पुष्टि करें और लागू करें', 'Sign in': 'साइन इन करें',
    'Sign out': 'साइन आउट', 'Sample pages': 'नमूना पेज', 'Upload a file': 'फ़ाइल अपलोड करें', 'Paste HTML': 'HTML चिपकाएँ',
    'Reviewer settings': 'समीक्षक सेटिंग', 'Choose the page': 'पेज चुनें', 'Scan results': 'स्कैन परिणाम',
    'Interface language': 'इंटरफ़ेस की भाषा',
    # metrics
    'Waiting for your decision': 'आपके निर्णय की प्रतीक्षा', 'Verified': 'सत्यापित', 'Rejected': 'अस्वीकृत', 'Rolled back': 'वापस लिया गया',
    'Violation nodes found': 'मिले उल्लंघन', 'Violation nodes now': 'अभी के उल्लंघन', 'Fixes ready for review': 'समीक्षा के लिए तैयार सुधार',
    'Manual review items': 'मैनुअल समीक्षा वाले मद', 'Needs a human check': 'मानवीय जाँच ज़रूरी', 'Rules that passed': 'पास हुए नियम',
    'Rules run per scan': 'हर स्कैन में चलने वाले नियम', 'Rules in the engine': 'इंजन के कुल नियम', 'Chosen page language': 'चुनी गई पेज भाषा',
    'Violation nodes at first scan': 'पहले स्कैन में उल्लंघन', 'Net improvement': 'कुल सुधार',
    'Runs locally. Page code never leaves this machine.': 'यह इसी कंप्यूटर पर चलता है। पेज का कोड बाहर नहीं जाता।',
}

PAGES_HI: dict[str, tuple[str, str]] = {
    'Load a page': ('पेज लोड करें', 'नमूना चुनें, HTML फ़ाइल अपलोड करें या मार्कअप चिपकाएँ। 2 MB तक की HTML फ़ाइलें स्वीकार हैं, और आपकी मूल फ़ाइल कभी नहीं बदली जाती।'),
    'Scan the page': ('पेज स्कैन करें', 'एक सुरक्षित ब्राउज़र आपका पेज खोलता है (कोई स्क्रिप्ट नहीं चलती, कोई इंटरनेट नहीं) और WCAG 2.0, 2.1 और 2.2 के A और AA नियमों से जाँच करता है।'),
    'Review repair proposals': ('सुधार प्रस्तावों की समीक्षा', 'आपकी स्वीकृति के बिना कुछ नहीं बदलता। हर सुधार तय टेम्पलेट से बनता है; फिर पेज दोबारा स्कैन होता है और कुछ भी बिगड़ने पर बदलाव अपने-आप वापस हो जाता है।'),
    'Verify results': ('परिणाम सत्यापित करें', 'हर स्वीकृत बदलाव के बाद AccessLoop दोबारा स्कैन करता है। सुधार तभी गिना जाता है जब समस्या हट जाए और कोई दूसरा नियम न बिगड़े।'),
    'Agent mode': ('एजेंट मोड', 'नियम एक बार तय करें और एजेंट को पेज ठीक करने दें। यह स्कैन करता है, केवल वही सुधार लागू करता है जिनकी आपकी नीति अनुमति देती है, हर बदलाव के बाद दोबारा स्कैन करता है, जो मदद न करे उसे वापस लेता है, और जिन शब्दों को केवल आप जानते हैं उनके लिए आपसे पूछता है।'),
    'Manual review queue': ('मैनुअल समीक्षा सूची', 'वे समस्याएँ जिन्हें AccessLoop अपने-आप नहीं बदलता: या तो अभी समर्थित नहीं, या बिना अनुमान लगाए ठीक करना संभव नहीं।'),
    'WCAG manual checklist': ('WCAG मैनुअल जाँच सूची', 'स्वचालित नियम WCAG का केवल एक हिस्सा जाँचते हैं। हर मानदंड को दिए गए चरणों से जाँचें; हर परिणाम ऑडिट लॉग और अनुरूपता रिपोर्ट में जाता है।'),
    'Page preview': ('पेज पूर्वावलोकन', 'मूल पेज और वर्तमान कॉपी साथ-साथ। पूर्वावलोकन में पेज की स्क्रिप्ट कभी नहीं चलती और इंटरनेट से कुछ नहीं आता।'),
    'Site scan': ('साइट स्कैन', 'कई पेज या साइट की .zip अपलोड करें। AccessLoop हर पेज जाँचता है, साझा टेम्पलेट से आई एक जैसी समस्याओं को समूह में दिखाता है, और चाहें तो हर पेज पर स्वचालित सुधार लगाता है।'),
    'Reports and downloads': ('रिपोर्ट और डाउनलोड', 'ऑडिटर, सहकर्मी या नियामक के लिए ज़रूरी हर चीज़, इसी सत्र से बनी हुई।'),
    'Audit trail': ('ऑडिट ट्रेल', 'हर कार्रवाई समय और फ़ाइल के फ़िंगरप्रिंट (SHA-256) के साथ दर्ज होती है, ताकि हर बदलाव की जाँच हो सके।'),
    'Agent trace': ('एजेंट ट्रेस', 'एजेंट ने इस पेज पर जो भी कदम उठाए, क्रम से, समय के साथ, और वे सुरक्षा जाँचें जिन्होंने कुछ रोका या वापस लिया।'),
    'Issue coverage': ('समस्याओं का कवरेज', 'हर axe नियम और WCAG 2.2 के सभी 55 A और AA मानदंडों का ईमानदार नक्शा: क्या ठीक होता है, क्या केवल बताया जाता है, और क्या कोई टूल नहीं जाँच सकता।'),
    'How AccessLoop works': ('AccessLoop कैसे काम करता है', 'सरल भाषा में: एक निरीक्षक, एक ठेकेदार, और आप।'),
}


def lang() -> str:
    return st.session_state.get('al_ui_lang', 'en')


def t(text: str) -> str:
    return HI.get(text, text) if lang() == 'hi' else text


def page(title: str, subtitle: str) -> tuple[str, str, str]:
    """(title, subtitle, html lang) for a page header."""
    if lang() == 'hi' and title in PAGES_HI:
        return (*PAGES_HI[title], 'hi')
    return title, subtitle, 'en'

"""Guided manual-test worksheet for every WCAG 2.2 A/AA criterion.

Automated rules cover part of WCAG; the rest needs a person. Each entry says how to test in plain steps and what
counts as a pass. Results are saved to the hash-chained audit log and feed the conformance report (exports.acr_html).
"""
from __future__ import annotations

RESULTS = [('pass', 'Pass'), ('fail', 'Fail'), ('partial', 'Partly'), ('na', 'Not applicable'), ('', 'Not tested yet')]

# criterion -> (how to test, pass when)
STEPS: dict[str, tuple[str, str]] = {
    '1.1.1': ('Look at every image, icon and chart. Read its alt text or name (the Review page shows what a screen reader announces).',
              'Each informative image says what it shows or does; decorative images are silent.'),
    '1.2.1': ('Find audio-only or video-only content (for example a voice message or silent animation).',
              'Audio has a transcript; silent video has a text or audio description.'),
    '1.2.2': ('Play each prerecorded video with sound.', 'Captions are available and match the speech and important sounds.'),
    '1.2.3': ('Watch each video with the screen turned away.', 'Important visual information is also in an audio description or a text alternative.'),
    '1.2.4': ('Find live audio or video (webinars, live streams).', 'Live captions are provided.'),
    '1.2.5': ('Watch each prerecorded video with your eyes closed.', 'An audio description covers important visual information.'),
    '1.3.1': ('Check headings, lists, tables and form groups are real HTML structures, not just bold text or spacing.',
              'Structure conveyed visually is also in the markup.'),
    '1.3.2': ('Turn CSS off (or read with a screen reader in browse mode) and read the page top to bottom.',
              'The reading order still makes sense, for example a form reads label, field, help, error.'),
    '1.3.3': ('Search for instructions that rely on shape, colour, position or sound ("click the green button", "see right").',
              'Instructions also name the control or give text.'),
    '1.3.4': ('Rotate a phone or narrow the window to portrait and landscape.', 'Content works in both orientations unless one is essential.'),
    '1.3.5': ('Check personal-data fields (name, email, phone, address, date of birth).', 'They carry a correct autocomplete value.'),
    '1.4.1': ('Find information shown by colour (required fields, errors, links in text, chart series).',
              'It is also shown by text, an icon, underline or pattern.'),
    '1.4.2': ('Load the page with sound on.', 'Nothing plays sound for more than 3 seconds without a pause or volume control.'),
    '1.4.3': ('Check text against its background, including on images and hover states.', 'Contrast is at least 4.5:1, or 3:1 for large text.'),
    '1.4.4': ('Zoom the browser to 200%.', 'All text and functions still work; nothing is cut off or overlaps.'),
    '1.4.5': ('Look for text that is part of an image (banners, scanned forms, buttons).', 'Real text is used, except logos or where essential.'),
    '1.4.10': ('Set the window to 320 CSS pixels wide (or zoom to 400%). AccessLoop\'s responsive check measures this.',
               'No horizontal scrolling for normal content; nothing lost or overlapping.'),
    '1.4.11': ('Check borders of inputs, focus rings, checkboxes and chart lines against their background.',
               'Each has at least 3:1 contrast.'),
    '1.4.12': ('Apply increased line height, paragraph, letter and word spacing. AccessLoop\'s text-spacing check does this.',
               'No text is cut off or overlaps.'),
    '1.4.13': ('Hover over and focus elements that show tooltips or pop-ups.',
               'The extra content can be dismissed (Esc), can be hovered itself, and stays until dismissed.'),
    '2.1.1': ('Unplug the mouse. Use Tab, Shift+Tab, Enter, Space and arrow keys to complete the main task.',
              'Every function works from the keyboard.'),
    '2.1.2': ('Tab through every control, including dialogs, date pickers and embedded widgets.', 'Focus never gets stuck.'),
    '2.1.4': ('Check for single-key shortcuts (letters, numbers) without Ctrl or Alt.', 'They can be turned off, remapped, or only work on focus.'),
    '2.2.1': ('Look for time limits, especially session time-outs on banking pages.',
              'Users are warned and can extend the time at least ten times, or the limit is essential or over 20 hours.'),
    '2.2.2': ('Find carousels, tickers and animations that run for more than 5 seconds.', 'They can be paused, stopped or hidden.'),
    '2.3.1': ('Look for flashing content (animations, video).', 'Nothing flashes more than three times per second.'),
    '2.4.1': ('Press Tab on page load.', 'A skip link or landmarks let users jump past repeated navigation.'),
    '2.4.2': ('Read the browser tab title.', 'It describes the page and its purpose, for example "Open a savings account | Bank".'),
    '2.4.3': ('Tab through the page.', 'Focus moves in an order that keeps meaning and operability.'),
    '2.4.4': ('Read each link with its sentence or list item.', 'Its purpose is clear (no bare "click here" without context).'),
    '2.4.5': ('Find this page another way: menu, search or site map.', 'There are at least two ways to reach it (unless it is a step in a process).'),
    '2.4.6': ('Read headings and form labels on their own.', 'They describe the topic or purpose.'),
    '2.4.7': ('Tab through every control. AccessLoop\'s focus check flags controls with no visible change.', 'Keyboard focus is always visible.'),
    '2.4.11': ('Tab through the page with sticky headers, cookie banners and chat widgets open.',
               'The focused element is never completely hidden.'),
    '2.5.1': ('Find gestures that need two fingers or a path (pinch, swipe, draw).', 'A single tap or click alternative exists.'),
    '2.5.2': ('Press a button, move off it, then release.', 'Actions run on release, and can be cancelled by moving away.'),
    '2.5.3': ('Compare each control\'s visible text with what a screen reader announces.', 'The announced name contains the visible text.'),
    '2.5.4': ('Look for actions triggered by shaking or tilting.', 'A button alternative exists and motion can be turned off.'),
    '2.5.7': ('Find drag-and-drop or sliders.', 'A single-pointer alternative (buttons, input) exists.'),
    '2.5.8': ('Check small icons and links. AccessLoop flags targets under 24 × 24 pixels.', 'Targets are at least 24 × 24 pixels or well spaced.'),
    '3.1.1': ('Check the page language attribute.', 'It matches the main language of the page.'),
    '3.1.2': ('Find passages in another language (a Hindi disclaimer on an English page).', 'They are marked with their own lang attribute.'),
    '3.2.1': ('Tab onto each control.', 'Focusing alone never submits a form, opens a window or changes the page.'),
    '3.2.2': ('Change each select, checkbox and field.', 'Nothing unexpected happens until the user submits, or they were warned.'),
    '3.2.3': ('Compare navigation across several pages.', 'Repeated menus appear in the same order.'),
    '3.2.4': ('Compare icons and buttons with the same function across pages.', 'They are named and labelled the same way.'),
    '3.2.6': ('Find help (contact, chat, FAQ) on several pages.', 'It is in the same place each time.'),
    '3.3.1': ('Submit forms with mistakes.', 'Errors are described in text and the field is identified.'),
    '3.3.2': ('Check each field has a visible label or instructions (format, required).', 'Users know what to enter before submitting.'),
    '3.3.3': ('Submit wrong formats (IFSC, PAN, date).', 'The error message suggests how to fix it.'),
    '3.3.4': ('Go through a payment, transfer or legal submission.',
              'The user can review, correct and confirm before it is final, or reverse it afterwards.'),
    '3.3.7': ('Complete a multi-step process.', 'Information already given is not asked for again (or can be selected).'),
    '3.3.8': ('Log in or verify identity.', 'No memory or puzzle test is required unless an alternative exists (password managers and paste work).'),
    '4.1.2': ('Use a screen reader on custom widgets (tabs, accordions, toggles).', 'Each announces its name, role and state, and updates when it changes.'),
    '4.1.3': ('Trigger status messages (saved, error, loading, results found).', 'A screen reader announces them without moving focus.'),
}


def worksheet(catalog: dict, saved: dict | None = None) -> list[dict]:
    """Every criterion with its steps, pass condition, automation status and any saved result."""
    saved = saved or {}
    rows = []
    for c in catalog['criteria']:
        how, ok = STEPS.get(c['criterion'], ('Check this criterion manually.', 'It is met.'))
        rows.append({**{k: c[k] for k in ('criterion', 'name', 'level', 'principle', 'axe_testable', 'axe_rules', 'bfsi')},
                     'how': how, 'pass_when': ok, **(saved.get(c['criterion']) or {})})
    return rows

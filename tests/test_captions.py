"""Captions a person writes in AccessLoop become a real WebVTT file, linked from the video and shipped with the page."""
import io
import zipfile
from pathlib import Path

import pytest
from accessloop import scanner
from accessloop.fixers import FixInputError
from accessloop.fixers_extra import captions_vtt

ROOT = Path(__file__).resolve().parent.parent
needs_axe = pytest.mark.skipif(not scanner.AXE_PATH.is_file(), reason='axe-core not installed (npm install)')


def test_simple_lines_become_timed_cues():
    vtt, n = captions_vtt('0:00 Open your UPI app\n0:04 Tap "Send money"\n0:09-0:15 Enter the amount and your UPI PIN')
    assert n == 3 and vtt.startswith('WEBVTT\n')
    assert '00:00:00.000 --> 00:00:04.000\nOpen your UPI app' in vtt
    assert '00:00:09.000 --> 00:00:15.000\nEnter the amount' in vtt


def test_pasted_srt_and_vtt_are_accepted():
    srt = '1\n00:00:01,500 --> 00:00:03,000\nHello\n\n2\n00:00:03,000 --> 00:00:05,250\nWelcome to UPI\n'
    vtt, n = captions_vtt(srt)
    assert n == 2 and '00:00:01.500 --> 00:00:03.000' in vtt and '00:00:05.250' in vtt
    assert captions_vtt('WEBVTT\n\n00:00.000 --> 00:02.000\nHi\n')[1] == 1


@pytest.mark.parametrize('bad', ['', 'just words with no time', '0:05 later\n0:01 earlier', '0:00 <b>bold</b>',
                                 '0:04-0:02 backwards', '0:00'])
def test_bad_captions_are_refused_with_a_reason(bad):
    with pytest.raises(FixInputError):
        captions_vtt(bad)


@needs_axe
def test_write_captions_end_to_end():
    from accessloop.web.server import Session
    s = Session(ROOT)
    s.load(None, '', 'examples/samples/09_netbanking_structure_gallery.html')
    s.scan('en', best_practice=True)
    p = next(p for p in s.state()['proposals'] if p['rule'] == 'video-caption')
    assert [f['name'] for f in p['fields']] == ['how', 'cues', 'src'] and 'how-to-upi.en.vtt' in p['diff'][-1]['text']
    s.approve(p['id'], 'en', 'Yanis Singla', {'how': 'write', 'cues': '0:00 Open your UPI app\n0:04 Tap Send money', 'src': ''})
    st = s.state()
    assert st['outcome']['status'] == 'verified'
    files = s.new_files()
    assert list(files) == ['how-to-upi.en.vtt'] and 'Tap Send money' in files['how-to-upi.en.vtt']
    assert 'src="how-to-upi.en.vtt"' in s.file('working')
    patch, _, _ = s.export('patch')
    assert 'new file mode 100644' in patch and '+WEBVTT' in patch
    z = zipfile.ZipFile(io.BytesIO(s.bundle()))
    assert sorted(z.namelist()) == sorted([st['source_name'], 'how-to-upi.en.vtt'])
    verified = next(e for e in st['events'] if e['event'] == 'verified' and e.get('rule') == 'video-caption')
    assert verified['files'][0]['path'] == 'how-to-upi.en.vtt' and len(verified['files'][0]['sha256']) == 64

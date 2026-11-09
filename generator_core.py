import unicodedata
import re

SAFE_REPLACEMENTS = {
    'ेणी': 'श्रेणी',
    'ारा': 'द्वारा',
    'प्रिया': 'प्रक्रिया',
    'प्रि या': 'प्रक्रिया',
    'संेषण': 'संश्लेषण',
    'वाोत्सजन': 'वाष्पोत्सर्जन',
    'कीटभी': 'कीटभक्षी',
    'परमेय': 'परिमेय',
    'अपरमेय': 'अपरिमेय',
    'संाओं': 'संख्याओं',
    'संा': 'संख्या',
    'पूणाक': 'पूर्णांक',
    'ाकृितक': 'प्राकृतिक',
    'महाा': 'महात्मा',
    'साग्रह': 'सत्याग्रह',
    'ापना': 'स्थापना',
    'िवश्विवालय': 'विश्वविद्यालय',
    'ंदगुप्त': 'स्कंदगुप्त',
    'ितीय': 'द्वितीय',
    'िद ी': 'दिल्ली',
    'टो ो': 'टोक्यो',
    'ब कॉक': 'बैंकॉक',
    'िप ा': 'पिल्ला',
    'िब ी': 'बिल्ली',
    'पित्तयों': 'पत्तियों',
    'पति्तयों': 'पत्तियों',
    'ंथि': 'ग्रंथि',
    'ाक': 'दाब',
    'ात कर': 'ज्ञात करें',
    'ात': 'ज्ञात',
    'छांिटए': 'छाँटिए',
    'अं ेजी': 'अंग्रेजी',
    'िवषम': 'विषम',
    'िबहार': 'बिहार',
    'िव ान': 'विज्ञान',
    'िवज्ञान': 'विज्ञान',
    'िवभाग': 'विभाग',
    'प्रितलोम': 'प्रतिलोम',
    'गुणनफल': 'गुणनफल',
    'िवस्तृत': 'विस्तृत',
    'िनम्निलखत': 'निम्नलिखित',
    'िनम्निल खत': 'निम्नलिखित',
    'कसि': 'किस',
    'वधिि': 'विधि',
    'कसिी': 'किसी',
    'नही ं': 'नहीं',
    'हैंैंोती': 'होती',
    'हैंैंै': 'है',
    'हैंैं': '',
    'अंतमि': 'अंतिम',
    'पि्रज़्म': 'प्रिज्म',
    'कतिने': 'कितने',
    'वभिक्त': 'विभक्त',
    'ांति': 'क्रांति',
    'ेत्रफला': 'क्षेत्रफल क्या',
    'सी ंग': 'सींग',
    'गडे': 'गैंडे',
    'प्रसदि्ध': 'प्रसिद्ध',
    'राीय': 'राष्ट्रीय',
    'उान': 'उद्यान',
    'त ': 'स्थित ',
}

def clean_text(text):
    if not text:
        return ""

    # Safe NFC normalization
    text = unicodedata.normalize('NFC', text)

    # Word-level fixes
    for bad, good in SAFE_REPLACEMENTS.items():
        text = text.replace(bad, good)

    # Specific phrase fixes
    text = re.sub(r'\s+ा\s+', ' क्या ', text)
    text = re.sub(r'\s+म\s+', ' में ', text)
    text = re.sub(r'\s+ह\s+', ' हैं ', text)

    # Remove any $ or \x00
    text = text.replace('$', '').replace('\x00', '').replace('\u200b', '')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_q(question, options, correct_idx, explanation=""):
    q_clean = clean_text(question)
    opts_clean = [clean_text(o) for o in options]
    
    assert len(opts_clean) == 4, f"Options must be 4: {opts_clean}"
    assert 0 <= correct_idx <= 3, f"Invalid correct_idx: {correct_idx}"
    assert "$" not in q_clean, f"$ found in question: {q_clean}"
    for o in opts_clean:
        assert "$" not in o, f"$ found in option: {o}"
    
    if not explanation:
        explanation = f"सही उत्तर विकल्प ({chr(65 + correct_idx)}) है।"
    else:
        explanation = clean_text(explanation)
        
    return {
        "question": q_clean,
        "options": opts_clean,
        "correct_option_id": correct_idx,
        "explanation": explanation
    }

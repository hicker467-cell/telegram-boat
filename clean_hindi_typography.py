import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "questions_db.json"

CHHOTI_I = '\u093F'

WORD_REPLACEMENTS = [
    # Missing shra / reph
    (r'\bेणी\b', 'श्रेणी'),
    (r'\bसूय\b', 'सूर्य'),
    (r'\bपूव\b', 'पूर्व'),
    (r'\bपूण\b', 'पूर्ण'),
    (r'\bदपण\b', 'दर्पण'),
    (r'\bप्रितिबंब\b', 'प्रतिबिंब'),
    (r'\bव्य\b', 'व्यक्ति'),
    (r'\bवणमाला\b', 'वर्णमाला'),
    (r'\bचतुभुज\b', 'चतुर्भुज'),
    (r'\bित्रभुज\b', 'त्रिभुज'),
    (r'\bसंेषण\b', 'संश्लेषण'),
    (r'\bवाोत्सजन\b', 'वाष्पोत्सर्जन'),
    (r'\bकीटभी\b', 'कीटभक्षी'),
    (r'\bपरमेय\b', 'परिमेय'),
    (r'\bअपरमेय\b', 'अपरिमेय'),
    (r'\bसंाओं\b', 'संख्याओं'),
    (r'\bसंा\b', 'संख्या'),
    (r'\bपूणाक\b', 'पूर्णांक'),
    (r'\bाकृितक\b', 'प्राकृतिक'),
    (r'\bमहाा\b', 'महात्मा'),
    (r'\bसाग्रह\b', 'सत्याग्रह'),
    (r'\bप्रिया\b', 'प्रक्रिया'),
    (r'\bापना\b', 'स्थापना'),
    (r'\bिवश्विवालय\b', 'विश्वविद्यालय'),
    (r'\bंदगुप्त\b', 'स्कंदगुप्त'),
    (r'\bितीय\b', 'द्वितीय'),
    (r'\bिद ी\b', 'दिल्ली'),
    (r'\bटो ो\b', 'टोक्यो'),
    (r'\bब कॉक\b', 'बैंकॉक'),
    (r'\bिप ा\b', 'पिल्ला'),
    (r'\bिब ी\b', 'बिल्ली'),
    (r'\bगुबारे\b', 'गुब्बारे'),
    (r'\bा\b', 'क्या'),
    (r'\bम\b', 'में'),
    (r'\bह\b', 'हैं'),
    (r'ह ें', 'हैं'),
]

def fix_hindi_text(text):
    if not text:
        return ""
    
    # 1. Invert misplaced chhoti-i matra: \u093F followed by consonant
    # e.g., िकसी -> किसी, यिद -> यदि, िलखा -> लिखा, िफर -> फिर
    text = re.sub(CHHOTI_I + r'([\u0915-\u0939])', r'\g<1>' + CHHOTI_I, text)
    
    # 2. Word-level cleanups
    for pattern, repl in WORD_REPLACEMENTS:
        text = re.sub(pattern, repl, text)

    # 3. Fix isolated matras or standalone characters
    text = re.sub(r'(^|\s)ा(\s|\?|$)', r'\1क्या\2', text)
    text = re.sub(r'(^|\s)म(\s)', r'\1में\2', text)
    text = re.sub(r'(^|\s)ह(\s)', r'\1हैं\2', text)
    
    # 4. Remove any $ or \x00
    text = text.replace('$', '').replace('\x00', '').replace('\u200b', '')

    # 5. Clean extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def main():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    count = 0
    # Process full_mocks
    for mock_k, mock_v in db.get("full_mocks", {}).items():
        for set_k, set_v in mock_v.get("sets", {}).items():
            for q in set_v.get("questions", []):
                q["question"] = fix_hindi_text(q["question"])
                q["options"] = [fix_hindi_text(opt) for opt in q["options"]]
                if "explanation" in q:
                    q["explanation"] = fix_hindi_text(q["explanation"])
                count += 1

    # Process subjects
    for subj_k, subj_v in db.get("subjects", {}).items():
        for set_k, set_v in subj_v.get("sets", {}).items():
            for q in set_v.get("questions", []):
                q["question"] = fix_hindi_text(q["question"])
                q["options"] = [fix_hindi_text(opt) for opt in q["options"]]
                if "explanation" in q:
                    q["explanation"] = fix_hindi_text(q["explanation"])

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"Cleaned {count} questions in full_mocks and all subject sets!")

    # Now verify remaining issues
    issues = []
    for mock_k, mock_v in db.get("full_mocks", {}).items():
        for set_k, set_v in mock_v.get("sets", {}).items():
            for i, q in enumerate(set_v.get("questions", [])):
                if re.search(r'[\u0900-\u097F]\s+[\u093E-\u094F\u0902\u0903]', q['question']):
                    issues.append(f"{mock_k}.{set_k}.Q{i+1}: {q['question']}")
                for opt in q['options']:
                    if re.search(r'[\u0900-\u097F]\s+[\u093E-\u094F\u0902\u0903]', opt):
                        issues.append(f"{mock_k}.{set_k}.Q{i+1} opt: {opt}")

    print(f"Remaining formatting issues after cleaning: {len(issues)}")
    if issues:
        for iss in issues[:5]:
            print("  -", iss)

if __name__ == "__main__":
    main()

import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "extracted_raw.json"
OUTPUT_FILE = BASE_DIR / "questions_db.json"

fixes = [
    ('महाा', 'महात्मा'),
    ('साग्रह', 'सत्याग्रह'),
    ('प्रिया', 'प्रक्रिया'),
    ('ारा', 'द्वारा'),
    ('संेषण', 'संश्लेषण'),
    ('वाोत्सजन', 'वाष्पोत्सर्जन'),
    ('कीटभी', 'कीटभक्षी'),
    ('िवश्विवालय', 'विश्वविद्यालय'),
    ('ापना', 'स्थापना'),
    ('ितीय', 'द्वितीय'),
    ('ंदगुप्त', 'स्कंदगुप्त'),
    ('ेणी', 'श्रेणी'),
    ('परमेय', 'परिमेय'),
    ('अपरमेय', 'अपरिमेय'),
    ('संाओं', 'संख्याओं'),
    ('संा', 'संख्या'),
    ('ाकृितक', 'प्राकृतिक'),
    ('पूणाक', 'पूर्णांक'),
    ('तक श', 'तर्कशक्ति'),
    ('वण माला', 'वर्णमाला'),
    ('सादृश्यता पूण कर', 'सादृश्यता पूर्ण करें'),
    ('िवषम', 'विषम'),
    ('छांिटए', 'छाँटिए'),
    ('अं ेजी', 'अंग्रेजी'),
    ('िबहार', 'बिहार'),
    ('िव ान', 'विज्ञान'),
    ('िवभाग', 'विभाग'),
    ('प्रितलोम', 'प्रतिलोम'),
    ('गुणनफल', 'गुणनफल'),
    ('िवस्तृत', 'विस्तृत'),
    ('ित्रभुज', 'त्रिभुज'),
    ('चतुभु ज', 'चतुर्भुज'),
    ('िनम्निलखत', 'निम्नलिखित'),
    ('िकस', 'किस'),
    ('िकसे', 'किसे'),
    ('िद ी', 'दिल्ली'),
    ('टो ो', 'टोक्यो'),
    ('ब कॉक', 'बैंकॉक'),
    ('िप ा', 'पिल्ला'),
    ('िब ी', 'बिल्ली'),
]

def clean_text(t):
    if not t:
        return ""
    t = t.replace('\x00', '').replace('\u200b', '')
    for old, new in fixes:
        t = t.replace(old, new)
    t = re.sub(r'(^|\s)ा(\s|\?|$)', r'\1क्या\2', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def load_and_clean_raw():
    if not RAW_FILE.exists():
        return {}
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    cleaned = {}
    for subj, q_list in data.items():
        cleaned[subj] = []
        for q in q_list:
            cq = {
                "question": clean_text(q["question"]),
                "options": [clean_text(o) for o in q["options"]],
                "correct_option_id": q["correct_option_id"],
                "subject": subj,
                "explanation": f"सही उत्तर विकल्प ({chr(65 + q['correct_option_id'])}) है।"
            }
            cleaned[subj].append(cq)
    return cleaned

# Extra MAT Questions to complete 50
EXTRA_MAT = [
    {
        "question": "यदि CLOCK को KCOLC लिखा जाता है, तो WATCH को क्या लिखा जाएगा?",
        "options": ["HCTAW", "HCTWA", "HTCAW", "HACTW"],
        "correct_option_id": 0,
        "explanation": "शब्द के अक्षरों को विपरीत (Reverse) क्रम में लिखा गया है। WATCH ➔ HCTAW।"
    },
    {
        "question": "श्रेणी में अगला पद क्या होगा? 10, 19, 28, 37, ?",
        "options": ["45", "46", "47", "48"],
        "correct_option_id": 1,
        "explanation": "प्रत्येक पद में 9 जोड़ा जा रहा है: 37 + 9 = 46।"
    },
    {
        "question": "सादृश्यता पूर्ण करें : डॉक्टर : अस्पताल :: शिक्षक : ?",
        "options": ["अदालत", "विद्यालय (स्कूल)", "दुकान", "कार्यालय"],
        "correct_option_id": 1,
        "explanation": "डॉक्टर का कार्यस्थल अस्पताल है, उसी प्रकार शिक्षक का कार्यस्थल विद्यालय है।"
    },
    {
        "question": "विषम पद छाँटिए :",
        "options": ["जनवरी", "मार्च", "अप्रैल", "मई"],
        "correct_option_id": 2,
        "explanation": "अप्रैल में 30 दिन होते हैं, जबकि जनवरी, मार्च और मई में 31 दिन होते हैं।"
    },
    {
        "question": "एक व्यक्ति उत्तर दिशा की ओर 5 किमी चलता है, फिर दाएँ मुड़कर 3 किमी चलता है। अब वह किस दिशा में जा रहा है?",
        "options": ["उत्तर", "पूर्व", "दक्षिण", "पश्चिम"],
        "correct_option_id": 1,
        "explanation": "उत्तर की ओर जाते हुए दाएँ मुड़ने पर दिशा 'पूर्व' (East) होगी।"
    },
    {
        "question": "A, B का भाई है और C, A की माँ है। तो C का B से क्या संबंध है?",
        "options": ["बहन", "चाची", "माँ", "दादी"],
        "correct_option_id": 2,
        "explanation": "क्योंकि A और B भाई हैं और C, A की माँ है, इसलिए C, B की भी माँ होगी।"
    },
    {
        "question": "श्रेणी में लुप्त पद ज्ञात करें: 2, 5, 10, 17, 26, ?",
        "options": ["35", "36", "37", "38"],
        "correct_option_id": 2,
        "explanation": "पैटर्न: +3, +5, +7, +9, +11। अतः 26 + 11 = 37 (या n² + 1)।"
    },
    {
        "question": "यदि '+' का अर्थ '×', '×' का अर्थ '-', और '-' का अर्थ '+' हो, तो 5 + 4 × 6 = ?",
        "options": ["14", "26", "20", "12"],
        "correct_option_id": 0,
        "explanation": "चिन्ह बदलने पर: 5 × 4 - 6 = 20 - 6 = 14।"
    },
    {
        "question": "अंग्रेजी वर्णमाला में बाएँ से 15वाँ अक्षर कौन सा है?",
        "options": ["M", "N", "O", "P"],
        "correct_option_id": 2,
        "explanation": "EJOTY फॉर्मूले से 15वाँ अक्षर 'O' होता है।"
    },
    {
        "question": "एक पंक्ति में राहुल का स्थान दोनों छोरों से 11वाँ है। पंक्ति में कुल कितने छात्र हैं?",
        "options": ["20", "21", "22", "19"],
        "correct_option_id": 1,
        "explanation": "कुल छात्र = (बायाँ + दायाँ) - 1 = (11 + 11) - 1 = 21।"
    },
    {
        "question": "सादृश्यता पूर्ण करें : पुस्तक : लेखक :: मूर्ति : ?",
        "options": ["चित्रकार", "मूर्तिकार", "कवि", "गायक"],
        "correct_option_id": 1,
        "explanation": "पुस्तक लेखक बनाता है, मूर्ति मूर्तिकार बनाता है।"
    },
    {
        "question": "विषम पद छाँटिए :",
        "options": ["आँख", "कान", "नाक", "यकृत (Liver)"],
        "correct_option_id": 3,
        "explanation": "यकृत आंतरिक अंग है, जबकि आँख, कान और नाक बाहरी ज्ञानेन्द्रियाँ हैं।"
    },
    {
        "question": "यदि किसी कूटभाषा में RED = 27 हो, तो BLUE = ? (R=18, E=5, D=4 ➔ 18+5+4=27)",
        "options": ["38", "40", "42", "44"],
        "correct_option_id": 1,
        "explanation": "B=2, L=12, U=21, E=5 ➔ 2 + 12 + 21 + 5 = 40।"
    },
    {
        "question": "श्रेणी में अगला पद क्या होगा? 100, 90, 81, 73, ?",
        "options": ["66", "64", "65", "67"],
        "correct_option_id": 0,
        "explanation": "पैटर्न: -10, -9, -8, -7। अतः 73 - 7 = 66।"
    },
    {
        "question": "एक घड़ी में जब 3:00 बजते हैं, तो दोनों सुइयों के बीच कितने अंश का कोण बनता है?",
        "options": ["60°", "90°", "120°", "180°"],
        "correct_option_id": 1,
        "explanation": "3:00 बजे घंटे की सुई 3 पर और मिनट की सुई 12 पर होती है, जो 90° का समकोण बनाती है।"
    },
    {
        "question": "सादृश्यता पूर्ण करें : वृत्त : परिधि :: वर्ग : ?",
        "options": ["क्षेत्रफल", "परिमाप", "विकर्ण", "भुजा"],
        "correct_option_id": 1,
        "explanation": "वृत्त की बाहरी सीमा परिधि कहलाती है और वर्ग की बाहरी सीमा परिमाप कहलाती है।"
    },
    {
        "question": "यदि बीते हुए कल से पहले का दिन रविवार था, तो आने वाले कल के बाद का दिन क्या होगा?",
        "options": ["गुरुवार", "शुक्रवार", "शनिवार", "बुधवार"],
        "correct_option_id": 0,
        "explanation": "परसों रविवार था तो आज मंगलवार है। कल बुधवार और कल के बाद गुरुवार होगा।"
    },
    {
        "question": "श्रेणी पूर्ण करें : 1, 8, 27, 64, 125, ?",
        "options": ["216", "225", "343", "196"],
        "correct_option_id": 0,
        "explanation": "यह घनों (Cubes) की श्रृंखला है: 1³, 2³, 3³, 4³, 5³, 6³ = 216।"
    },
    {
        "question": "विषम संख्या युग्म छाँटिए :",
        "options": ["2 : 4", "3 : 9", "4 : 16", "5 : 20"],
        "correct_option_id": 3,
        "explanation": "बाकी सभी संख्याओं के वर्ग (Squares) हैं, जबकि 5² = 25 होता है न कि 20।"
    },
    {
        "question": "एक पासे (Dice) में 1 के विपरीत फलक पर क्या होगा, यदि मानक पासा हो?",
        "options": ["2", "4", "5", "6"],
        "correct_option_id": 3,
        "explanation": "मानक पासे में विपरीत फलकों का योग 7 होता है: 7 - 1 = 6।"
    },
    {
        "question": "सादृश्यता पूर्ण करें : थर्मामीटर : तापमान :: बैरोमीटर : ?",
        "options": ["वायुदाब", "आर्द्रता", "गति", "भूकंप"],
        "correct_option_id": 0,
        "explanation": "थर्मामीटर से तापमान नापा जाता है, बैरोमीटर से वायुमंडलीय दाब नापा जाता है।"
    }
]

# Extra Mathematics Questions to complete 50
EXTRA_MATH = [
    {
        "question": "संख्या 144 का वर्गमूल (Square Root) क्या होगा?",
        "options": ["11", "12", "13", "14"],
        "correct_option_id": 1,
        "explanation": "12 × 12 = 144, अतः √144 = 12।"
    },
    {
        "question": "यदि 3x - 5 = 16 हो, तो x का मान क्या होगा?",
        "options": ["5", "6", "7", "8"],
        "correct_option_id": 2,
        "explanation": "3x = 16 + 5 = 21 ➔ x = 21 / 3 = 7।"
    },
    {
        "question": "किसी त्रिभुज के तीनों अन्तः कोणों का योग कितना होता है?",
        "options": ["90°", "180°", "270°", "360°"],
        "correct_option_id": 1,
        "explanation": "त्रिभुज के तीनों कोणों का योग हमेशा 180° होता है।"
    },
    {
        "question": "25 का 20% कितना होगा?",
        "options": ["4", "5", "6", "8"],
        "correct_option_id": 1,
        "explanation": "25 × (20 / 100) = 25 / 5 = 5।"
    },
    {
        "question": "एक समचतुर्भुज (Rhombus) के विकर्ण एक-दूसरे को किस कोण पर काटते हैं?",
        "options": ["45°", "60°", "90°", "180°"],
        "correct_option_id": 2,
        "explanation": "समचतुर्भुज के विकर्ण परस्पर लंबवत (90° पर) समद्विभाजित करते हैं।"
    },
    {
        "question": "संख्या 8 का घन (Cube) क्या होगा?",
        "options": ["64", "256", "512", "1024"],
        "correct_option_id": 2,
        "explanation": "8 × 8 × 8 = 512।"
    },
    {
        "question": "(a + b)² का सही विस्तार सूत्र क्या है?",
        "options": ["a² + b²", "a² + 2ab + b²", "a² - 2ab + b²", "a² - b²"],
        "correct_option_id": 1,
        "explanation": "(a + b)² = a² + 2ab + b² सर्वसमिका है।"
    },
    {
        "question": "एक वृत्त का व्यास (Diameter) 14 सेमी है। उसकी परिधि (Circumference) क्या होगी? (π = 22/7)",
        "options": ["22 सेमी", "44 सेमी", "88 सेमी", "154 सेमी"],
        "correct_option_id": 1,
        "explanation": "परिधि = π × d = (22/7) × 14 = 44 सेमी।"
    },
    {
        "question": "यदि किसी वस्तु का क्रय मूल्य ₹500 और विक्रय मूल्य ₹600 है, तो लाभ प्रतिशत क्या होगा?",
        "options": ["10%", "15%", "20%", "25%"],
        "correct_option_id": 2,
        "explanation": "लाभ = 600 - 500 = ₹100। लाभ% = (100 / 500) × 100 = 20%।"
    },
    {
        "question": "2³ × 2⁴ का मान घातांक के रूप में क्या होगा?",
        "options": ["2⁷", "2¹²", "4⁷", "4¹²"],
        "correct_option_id": 0,
        "explanation": "आधार समान होने पर गुणा में घातें जुड़ जाती हैं: aᵐ × aⁿ = aᵐ⁺ⁿ ➔ 2³⁺⁴ = 2⁷।"
    },
    {
        "question": "चतुर्भुज के चारों अन्तः कोणों का योग कितना होता है?",
        "options": ["180°", "270°", "360°", "540°"],
        "correct_option_id": 2,
        "explanation": "किसी भी चतुर्भुज के चारों कोणों का योग 360° होता है।"
    },
    {
        "question": "₹1000 का 10% वार्षिक दर से 2 वर्ष का साधारण ब्याज (Simple Interest) क्या होगा?",
        "options": ["₹100", "₹150", "₹200", "₹250"],
        "correct_option_id": 2,
        "explanation": "SI = (P × R × T) / 100 = (1000 × 10 × 2) / 100 = ₹200।"
    },
    {
        "question": "संख्या 0.25 को भिन्न (Fraction) के सरलतम रूप में कैसे लिखा जाएगा?",
        "options": ["1/2", "1/4", "1/5", "2/5"],
        "correct_option_id": 1,
        "explanation": "0.25 = 25 / 100 = 1 / 4।"
    },
    {
        "question": "एक पासे को फेंकने पर सम संख्या (Even Number) आने की प्रायिकता (Probability) क्या है?",
        "options": ["1/6", "1/3", "1/2", "2/3"],
        "correct_option_id": 2,
        "explanation": "कुल परिणाम = {1, 2, 3, 4, 5, 6} = 6। सम संख्याएँ = {2, 4, 6} = 3। प्रायिकता = 3/6 = 1/2।"
    },
    {
        "question": "एक आयत की लंबाई 10 सेमी और चौड़ाई 6 सेमी है। इसका क्षेत्रफल (Area) क्या होगा?",
        "options": ["32 वर्ग सेमी", "60 वर्ग सेमी", "16 वर्ग सेमी", "120 वर्ग सेमी"],
        "correct_option_id": 1,
        "explanation": "आयत का क्षेत्रफल = लंबाई × चौड़ाई = 10 × 6 = 60 वर्ग सेमी।"
    },
    {
        "question": "(-1) की घात विषम संख्या (Odd Power) होने पर मान क्या होगा? जैसे (-1)⁹⁹",
        "options": ["1", "-1", "0", "99"],
        "correct_option_id": 1,
        "explanation": "ऋणात्मक 1 की घात विषम होने पर परिणाम हमेशा -1 होता है।"
    },
    {
        "question": "एक वर्ग का परिमाप 40 सेमी है। इसकी एक भुजा की माप क्या होगी?",
        "options": ["8 सेमी", "10 सेमी", "12 सेमी", "20 सेमी"],
        "correct_option_id": 1,
        "explanation": "वर्ग का परिमाप = 4 × भुजा ➔ भुजा = 40 / 4 = 10 सेमी।"
    },
    {
        "question": "यदि 5 मजदूर किसी काम को 12 दिन में करते हैं, तो 10 मजदूर उसी काम को कितने दिन में करेंगे?",
        "options": ["6 दिन", "10 दिन", "15 दिन", "24 दिन"],
        "correct_option_id": 0,
        "explanation": "व्युत्क्रमानुपात (Inverse Proportion): M1 × D1 = M2 × D2 ➔ 5 × 12 = 10 × D2 ➔ D2 = 60 / 10 = 6 दिन।"
    },
    {
        "question": "5⁰ + 7⁰ का मान क्या होगा?",
        "options": ["0", "1", "2", "12"],
        "correct_option_id": 2,
        "explanation": "किसी भी संख्या की घात 0 होने पर उसका मान 1 होता है (a⁰ = 1)। 1 + 1 = 2।"
    },
    {
        "question": "व्यंजक x² - y² के सही गुणनखंड (Factors) क्या हैं?",
        "options": ["(x - y)(x - y)", "(x + y)(x + y)", "(x + y)(x - y)", "x² - 2xy + y²"],
        "correct_option_id": 2,
        "explanation": "सर्वसमिका: a² - b² = (a + b)(a - b)।"
    },
    {
        "question": "एक घन (Cube) के कुल कितने फलक (Faces) होते हैं?",
        "options": ["4", "6", "8", "12"],
        "correct_option_id": 1,
        "explanation": "घन में कुल 6 फलक (Faces), 8 शीर्ष (Vertices), और 12 किनारे (Edges) होते हैं।"
    },
    {
        "question": "संख्या 0 का गुणात्मक प्रतिलोम (Multiplicative Inverse / Reciprocal) क्या होगा?",
        "options": ["0", "1", "-1", "अपरिभाषित (अस्तित्व नहीं है)"],
        "correct_option_id": 3,
        "explanation": "शून्य का कोई गुणात्मक प्रतिलोम नहीं होता क्योंकि 1/0 अपरिभाषित है।"
    },
    {
        "question": "एक समबाहु त्रिभुज (Equilateral Triangle) का प्रत्येक कोण कितने अंश का होता है?",
        "options": ["45°", "60°", "90°", "120°"],
        "correct_option_id": 1,
        "explanation": "समबाहु त्रिभुज की तीनों भुजाएं और तीनों कोण बराबर होते हैं: 180° / 3 = 60°।"
    },
    {
        "question": "प्रथम 5 विषम प्राकृत संख्याओं का औसत (Mean) क्या होगा?",
        "options": ["3", "4", "5", "6"],
        "correct_option_id": 2,
        "explanation": "संख्याएँ: 1, 3, 5, 7, 9। योग = 25। औसत = 25 / 5 = 5 (प्रथम n विषम संख्याओं का औसत n होता है)।"
    },
    {
        "question": "एक बेलन (Cylinder) का आयतन (Volume) ज्ञात करने का सूत्र क्या है?",
        "options": ["πr²h", "2πrh", "πrl", "4/3 πr³"],
        "correct_option_id": 0,
        "explanation": "बेलन का आयतन = πr²h होता है।"
    },
    {
        "question": "1 से 100 तक कुल कितनी अभाज्य संख्याएँ (Prime Numbers) होती हैं?",
        "options": ["21", "25", "30", "35"],
        "correct_option_id": 1,
        "explanation": "1 से 100 के बीच कुल 25 अभाज्य संख्याएँ होती हैं।"
    },
    {
        "question": "(-4) × (-5) × (-2) का मान क्या होगा?",
        "options": ["40", "-40", "20", "-20"],
        "correct_option_id": 1,
        "explanation": "(-4) × (-5) = +20; फिर +20 × (-2) = -40।"
    },
    {
        "question": "यदि किसी वृत्त की त्रिज्या (Radius) 7 सेमी है, तो उसका क्षेत्रफल क्या होगा? (π = 22/7)",
        "options": ["44 सेमी²", "154 सेमी²", "77 सेमी²", "308 सेमी²"],
        "correct_option_id": 1,
        "explanation": "क्षेत्रफल = πr² = (22/7) × 7 × 7 = 154 सेमी²।"
    },
    {
        "question": "किसी संख्या के 4 गुने में 10 जोड़ने पर 50 प्राप्त होता है। वह संख्या क्या है?",
        "options": ["8", "10", "12", "15"],
        "correct_option_id": 1,
        "explanation": "4x + 10 = 50 ➔ 4x = 40 ➔ x = 10।"
    },
    {
        "question": "संख्या 729 का घनमूल (Cube Root) क्या है?",
        "options": ["7", "8", "9", "11"],
        "correct_option_id": 2,
        "explanation": "9 × 9 × 9 = 729, अतः ∛729 = 9।"
    }
]

def main():
    cleaned = load_and_clean_raw()
    
    # 1. Science sets
    sci_list = cleaned.get("Science", [])
    science_set_1 = sci_list[:50]
    science_set_2 = sci_list[50:100] if len(sci_list) >= 100 else sci_list[50:]
    
    # 2. Social Science set
    sst_list = cleaned.get("Social_Science", [])
    sst_set_1 = sst_list[:50]
    
    # 3. MAT set
    mat_list = cleaned.get("Mental_Ability", [])
    for extra in EXTRA_MAT:
        extra["subject"] = "Mental_Ability"
        mat_list.append(extra)
    mat_set_1 = mat_list[:50]
    
    # 4. Mathematics set
    math_list = cleaned.get("Mathematics", [])
    for extra in EXTRA_MATH:
        extra["subject"] = "Mathematics"
        math_list.append(extra)
    math_set_1 = math_list[:50]
    
    database = {
        "subjects": {
            "Science": {
                "name": "विज्ञान (Science - SAT)",
                "timer_seconds": 30,
                "sets": {
                    "set_1": {
                        "name": "Set 01 - भौतिक, रसायन व जीव विज्ञान (50 प्रश्न)",
                        "questions": science_set_1
                    },
                    "set_2": {
                        "name": "Set 02 - पर्यावरण, पादप व सूक्ष्मजीव (50 प्रश्न)",
                        "questions": science_set_2
                    }
                }
            },
            "Social_Science": {
                "name": "सामाजिक विज्ञान (SST - SAT)",
                "timer_seconds": 30,
                "sets": {
                    "set_1": {
                        "name": "Set 01 - इतिहास, भूगोल व नागरिक शास्त्र (50 प्रश्न)",
                        "questions": sst_set_1
                    }
                }
            },
            "Mental_Ability": {
                "name": "मानसिक योग्यता (MAT Reasoning)",
                "timer_seconds": 60,
                "sets": {
                    "set_1": {
                        "name": "Set 01 - श्रृंखला, सादृश्यता, कोडिंग व तर्कशक्ति (50 प्रश्न)",
                        "questions": mat_set_1
                    }
                }
            },
            "Mathematics": {
                "name": "गणित (Mathematics - SAT)",
                "timer_seconds": 60,
                "sets": {
                    "set_1": {
                        "name": "Set 01 - अंकगणित, बीजगणित व ज्यामिति (50 प्रश्न)",
                        "questions": math_set_1
                    }
                }
            }
        }
    }
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(database, f, ensure_ascii=False, indent=2)
        
    print("Database built successfully!")
    for subj_key, subj_val in database["subjects"].items():
        print(f"Subject: {subj_val['name']} | Timer: {subj_val['timer_seconds']}s")
        for set_key, set_val in subj_val["sets"].items():
            print(f"  - {set_val['name']}: {len(set_val['questions'])} questions")

if __name__ == "__main__":
    main()

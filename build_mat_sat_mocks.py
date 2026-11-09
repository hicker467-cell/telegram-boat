import json
import random
from pathlib import Path
from generator_core import clean_text

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "questions_db.json"

def main():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    subjects = existing.get("subjects", {})
    sci_sets = subjects.get("Science", {}).get("sets", {})
    sst_sets = subjects.get("Social_Science", {}).get("sets", {})
    mat_sets = subjects.get("Mental_Ability", {}).get("sets", {})
    math_sets = subjects.get("Mathematics", {}).get("sets", {})

    # Gather full question pools
    all_sci = []
    for s in sci_sets.values(): all_sci.extend(s["questions"])
    all_sst = []
    for s in sst_sets.values(): all_sst.extend(s["questions"])
    all_mat = []
    for s in mat_sets.values(): all_mat.extend(s["questions"])
    all_math = []
    for s in math_sets.values(): all_math.extend(s["questions"])

    print(f"Pool sizes: Science={len(all_sci)}, SST={len(all_sst)}, MAT={len(all_mat)}, Math={len(all_math)}")

    # 1. Build 3 MAT Mock Sets (90 questions each = 270)
    mat_mock_1 = all_mat[0:90]
    mat_mock_2 = all_mat[90:180]
    mat_mock_3 = all_mat[180:270]

    # 2. Build 3 SAT Mock Sets (90 questions each = 35 Science + 35 SST + 20 Math)
    sat_mock_1 = all_sci[0:35] + all_sst[0:35] + all_math[0:20]
    sat_mock_2 = all_sci[35:70] + all_sst[35:70] + all_math[20:40]
    sat_mock_3 = all_sci[70:105] + all_sst[70:105] + all_math[40:60]

    assert len(mat_mock_1) == 90
    assert len(mat_mock_2) == 90
    assert len(mat_mock_3) == 90
    assert len(sat_mock_1) == 90
    assert len(sat_mock_2) == 90
    assert len(sat_mock_3) == 90

    # New database structure with top-level MAT Mock, SAT Mock and Subject-wise
    new_db = {
        "full_mocks": {
            "MAT": {
                "name": "🧠 MAT मॉक टेस्ट (मानसिक योग्यता परीक्षा)",
                "timer_seconds": 90,
                "sets": {
                    "mat_1": {
                        "name": "MAT मॉक सेट 01 (90 प्रश्न)",
                        "questions": mat_mock_1
                    },
                    "mat_2": {
                        "name": "MAT मॉक सेट 02 (90 प्रश्न)",
                        "questions": mat_mock_2
                    },
                    "mat_3": {
                        "name": "MAT मॉक सेट 03 (90 प्रश्न)",
                        "questions": mat_mock_3
                    }
                }
            },
            "SAT": {
                "name": "📚 SAT मॉक टेस्ट (शैक्षिक योग्यता परीक्षा)",
                "timer_seconds": 90,
                "sets": {
                    "sat_1": {
                        "name": "SAT मॉक सेट 01 (90 प्रश्न: 35 वि. + 35 सा.वि. + 20 गणित)",
                        "questions": sat_mock_1
                    },
                    "sat_2": {
                        "name": "SAT मॉक सेट 02 (90 प्रश्न: 35 वि. + 35 सा.वि. + 20 गणित)",
                        "questions": sat_mock_2
                    },
                    "sat_3": {
                        "name": "SAT मॉक सेट 03 (90 प्रश्न: 35 वि. + 35 सा.वि. + 20 गणित)",
                        "questions": sat_mock_3
                    }
                }
            }
        },
        "subjects": subjects  # Keep subject practice intact too!
    }

    # Verify no $ symbol
    dumped = json.dumps(new_db, ensure_ascii=False)
    assert "$" not in dumped, "FATAL: $ found in JSON!"

    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(dumped)

    print("SUCCESS: 3 MAT Sets (90Q each) & 3 SAT Sets (90Q each) created with 90s timer and ZERO '$' symbols!")

if __name__ == "__main__":
    main()

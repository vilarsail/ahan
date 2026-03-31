import re
import os
import json
from collections import defaultdict

def classify_char(ch):
    code = ord(ch)

    if 0xE000 <= code <= 0xF8FF:
        return "PUA(私有区-疑似CBETA缺字)"
    elif 0x20000 <= code <= 0x2A6DF:
        return "Unicode扩展区B"
    elif 0x2A700 <= code <= 0x2B73F:
        return "Unicode扩展区C"
    elif 0x2B740 <= code <= 0x2B81F:
        return "Unicode扩展区D"
    elif 0x2B820 <= code <= 0x2CEAF:
        return "Unicode扩展区E"
    elif 0x2CEB0 <= code <= 0x2EBEF:
        return "Unicode扩展区F"
    elif 0x30000 <= code <= 0x3134F:
        return "Unicode扩展区G"
    elif code >= 0x20000:
        return "Unicode扩展区(其他)"
    elif ch == "\uFFFD":
        return "乱码替换符"
    elif code < 32 and ch not in ['\n', '\t', '\r']:
        return "控制字符"
    elif '\u2FF0' <= ch <= '\u2FFF':
        return "组合字结构符"
    else:
        return None

def analyze_directory(directory_path, context_window=10):
    # key: "char (U+XXXX)"
    stats = {}

    for filename in sorted(os.listdir(directory_path), key=lambda x: int(x.split('.')[0]) if x.endswith('.txt') and x.split('.')[0].isdigit() else x):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(directory_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        for i, ch in enumerate(text):
            category = classify_char(ch)
            if category:
                hex_code = f"U+{ord(ch):04X}"
                key = f"{ch} ({hex_code})"

                if key not in stats:
                    stats[key] = {
                        "char": ch,
                        "hex": hex_code,
                        "type": category,
                        "count": 0,
                        "occurrences": []
                    }

                stats[key]["count"] += 1

                # Limit examples to 5 per character overall to keep JSON manageable
                if len(stats[key]["occurrences"]) < 5:
                    start = max(0, i - context_window)
                    end = min(len(text), i + context_window)
                    snippet = text[start:end].replace("\n", "\\n").replace("\r", "\\r")
                    stats[key]["occurrences"].append({
                        "file": filename,
                        "context": snippet
                    })

    return stats

if __name__ == "__main__":
    split_dir = 'chang/split/'
    output_json = 'chang/encode-check.json'

    print(f"Analyzing files in {split_dir}...")
    results = analyze_directory(split_dir)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Analysis complete. Results saved to {output_json}")
    print(f"Found {len(results)} unique problematic characters.")

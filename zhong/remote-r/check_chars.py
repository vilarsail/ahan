import json
import os
import re

dir_path = "/Users/zhangwei/work/ahan/zhong/remote-r"
file_list = [f for f in os.listdir(dir_path) if f.endswith('.json')]

# allowed chars in translation text: 
# Chinese chars, common full-width and half-width punctuations, spaces, numbers
# \u4e00-\u9fa5 : Chinese characters
# \u3000-\u303f : CJK Symbols and Punctuation
# \uff00-\uffef : Halfwidth and Fullwidth Forms
# \u2000-\u206f : General Punctuation (like quotes “ ”)
# a-zA-Z : English letters (we will flag them to check if they are expected)
# 0-9 : numbers
# We'll use a regex to find anything that is NOT a common Chinese character, punctuation, or number.

# Let's find English letters, strange Unicode blocks, etc.
# Actually, let's just find everything that isn't Chinese characters, standard punctuation, or numbers.
allowed_pattern = re.compile(r'[\u4e00-\u9fa5\u3000-\u303f\uff00-\uffef\u2000-\u206f\w\s，。！？；：“”‘’（）【】《》、·\.,!\?;:\-\'\(\)\[\]<>]+')

# We want to collect any character that isn't standard Chinese or punctuation
# Instead of regex exclusion, we can check for characters that are out of bounds.
def is_allowed_char(c):
    code = ord(c)
    if 0x4E00 <= code <= 0x9FFF: return True # CJK Unified Ideographs
    if 0x3400 <= code <= 0x4DBF: return True # CJK Extension A
    if 0x20000 <= code <= 0x2A6DF: return True # CJK Extension B
    if 0x3000 <= code <= 0x303F: return True # CJK Symbols and Punctuation
    if 0xFF00 <= code <= 0xFFEF: return True # Halfwidth and Fullwidth Forms
    if 0x2000 <= code <= 0x206F: return True # General Punctuation
    if c in '0123456789': return True
    if c in ' \t\n\r\v\f': return True
    if c in ',.!?;:-\'()[]<>"/\\_{}+=*&^%$#@~`|': return True # basic ascii punctuation
    return False

english_letters = []
special_chars = set()

for file_name in file_list:
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            for key, val in data.items():
                if isinstance(val, str):
                    # Check for english letters
                    eng_matches = re.findall(r'[a-zA-Z]+', val)
                    if eng_matches:
                        english_letters.append((file_name, key, val, eng_matches))
                    
                    # Check for strange characters
                    for c in val:
                        if not is_allowed_char(c) and not ('a' <= c <= 'z' or 'A' <= c <= 'Z'):
                            special_chars.add(c)
        except Exception as e:
            print(f"Error parsing {file_name}: {e}")

print("=== English Words Found ===")
for item in english_letters:
    print(f"{item[0]} [{item[1]}]: {item[3]} -> {item[2][:50]}...")
print("\n=== Total English matches: {} ===".format(len(english_letters)))

print("\n=== Special/Other Characters Found ===")
for c in special_chars:
    print(f"Char: {c} (U+{ord(c):04X})")


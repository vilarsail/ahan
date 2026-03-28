import os
import re

def check_translations():
    split_dir = 'chang/split/'
    placeholder = "*（此处填写翻译）*"

    # Check all files
    for filename in sorted(os.listdir(split_dir)):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(split_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_para = 0
        translated_range_end = 0
        if filename == "1.md":
            translated_range_end = 80 # Based on our current progress

        for i, line in enumerate(lines):
            match = re.match(r'^(\d+)\.', line)
            if match:
                current_para = int(match.group(1))

            if placeholder in line:
                if current_para <= translated_range_end:
                    print(f"!!! 错误: {filename} 第 {current_para} 段发现占位符 (行 {i + 1})")

if __name__ == "__main__":
    check_translations()

import os
import re

def check_translations():
    split_dir = 'chang/split/'
    placeholder = "*（此处填写翻译）*"

    # We claim 1.md is fully translated (133 paragraphs)
    translated_files = {
        "1.md": 133
    }

    found_errors = False

    for filename, limit in translated_files.items():
        filepath = os.path.join(split_dir, filename)
        if not os.path.exists(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_para = 0
        for i, line in enumerate(lines):
            match = re.match(r'^(\d+)\.', line)
            if match:
                current_para = int(match.group(1))

            if placeholder in line:
                if current_para <= limit:
                    print(f"!!! 错误: {filename} 第 {current_para} 段发现占位符 (行 {i + 1})")
                    found_errors = True

    if not found_errors:
        print("验证通过：所有声明已翻译的段落均已完成。")

if __name__ == "__main__":
    check_translations()

import os
import json

def apply_replacements():
    check_json_path = 'zhong/encode-check.json'
    split_dir = 'zhong/split/'
    log_path = 'zhong/replace-log.txt'

    if not os.path.exists(check_json_path):
        print(f"Error: {check_json_path} not found.")
        return

    with open(check_json_path, 'r', encoding='utf-8') as f:
        check_data = json.load(f)

    # Extract valid replacements: old_char -> new_char
    replacements = {}
    for key, item in check_data.items():
        old_char = item['char']
        new_char = item['replacement']
        if new_char and new_char.strip():
            replacements[old_char] = new_char

    if not replacements:
        print("No replacements found in the JSON file.")
        return

    print(f"Found {len(replacements)} characters to replace.")
    log_entries = []

    # Process each .txt and .md file in the split directory
    files = sorted([f for f in os.listdir(split_dir) if f.endswith('.txt') or f.endswith('.md')])
    
    for filename in files:
        filepath = os.path.join(split_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for old_char, new_char in replacements.items():
            if old_char in content:
                count = content.count(old_char)
                content = content.replace(old_char, new_char)
                log_entries.append(f"File {filename}: Replaced '{old_char}' with '{new_char}' {count} times.")

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(log_entries))

    print(f"Replacements applied to {len(files)} files. Log saved to {log_path}")

if __name__ == "__main__":
    apply_replacements()

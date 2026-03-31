import os
import json

def apply_replacements():
    proposal_path = 'chang/replace/proposal.json'
    split_dir = 'chang/split/'
    log_path = 'chang/replace/log.txt'

    with open(proposal_path, 'r', encoding='utf-8') as f:
        replacements = json.load(f)

    log_entries = []

    # Process each file in the split directory
    for filename in sorted(os.listdir(split_dir)):
        if not filename.endswith('.txt'):
            continue

        filepath = os.path.join(split_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        for old_char_entry, new_char in replacements.items():
            # The key in JSON is "char (U+XXXX)"
            old_char = old_char_entry.split(' ')[0]
            if old_char in content:
                count = content.count(old_char)
                content = content.replace(old_char, new_char)
                log_entries.append(f"File {filename}: Replaced '{old_char}' ({old_char_entry}) with '{new_char}' {count} times.")

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(log_entries))

    print(f"Replacements applied. Log saved to {log_path}")

if __name__ == "__main__":
    apply_replacements()

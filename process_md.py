import os
import re

def process_files(directory, start, end):
    # Regex to match numbered lists at the beginning of a line (e.g., "1. ", "100. ")
    # Using re.match to ensure it only matches at the beginning of the string
    pattern = re.compile(r'^\d+\.\s+')

    for i in range(start, end + 1):
        filename = f"{i}.md"
        filepath = os.path.join(directory, filename)

        if not os.path.exists(filepath):
            print(f"File {filepath} does not exist, skipping.")
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                # If it's a translation line starting with "*", we skip replacing.
                # But actually, the translation lines usually start with "*" or just text.
                # Our pattern `^\d+\.\s+` won't match lines starting with "*".
                # It will only match lines starting with numbers followed by a dot and space.

                # Check if it matches the numbered list pattern
                if pattern.match(line):
                    # Remove the numbered list pattern by substituting it with empty string
                    new_line = pattern.sub('', line)
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            print(f"Processed {filepath}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    split_dir = "chang/split/"
    process_files(split_dir, 1, 22)

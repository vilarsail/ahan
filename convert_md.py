import os

def convert_to_md():
    split_dir = 'chang/split/'

    # Process each .txt file in the split directory
    for filename in sorted(os.listdir(split_dir)):
        if not filename.endswith('.txt'):
            continue

        txt_path = os.path.join(split_dir, filename)
        md_path = os.path.join(split_dir, filename.replace('.txt', '.md'))

        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            continue

        # Transform the first line into an H1 header
        # Find the first non-empty line
        first_content_line_idx = -1
        for i, line in enumerate(lines):
            if line.strip():
                first_content_line_idx = i
                break

        if first_content_line_idx != -1:
            # Add # to the beginning of the first non-empty line
            lines[first_content_line_idx] = "# " + lines[first_content_line_idx].strip() + "\n"

        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    print(f"Converted .txt files to .md in {split_dir}")

if __name__ == "__main__":
    convert_to_md()

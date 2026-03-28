import os

def reformat_md_for_translation():
    split_dir = 'chang/split/'

    for filename in sorted(os.listdir(split_dir)):
        if not filename.endswith('.md'):
            continue

        md_path = os.path.join(split_dir, filename)

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        if not lines:
            continue

        new_lines = []
        # Find the H1 header (usually the first non-empty line)
        h1_found = False
        paragraph_count = 0

        # Split by double newline to get paragraphs
        # However, to be more robust, we'll iterate through lines and group them

        current_paragraph = []

        for line in lines:
            stripped_line = line.strip()

            if stripped_line.startswith('# '):
                # Header line
                new_lines.append(line)
                h1_found = True
                continue

            if not stripped_line:
                # Empty line - indicates end of a paragraph
                if current_paragraph:
                    paragraph_count += 1
                    para_text = "\n".join(current_paragraph)
                    new_lines.append(f"{paragraph_count}. {para_text}")
                    new_lines.append("") # Empty line between para and translation
                    new_lines.append("*（此处填写翻译）*")
                    new_lines.append("") # Empty line before next para
                    current_paragraph = []
                continue

            # Non-empty line, not a header
            # Remove leading full-width and half-width spaces
            # The user said remove leading full-width spaces
            clean_line = line.lstrip(' 　\t')
            current_paragraph.append(clean_line)

        # Add the last paragraph if exists
        if current_paragraph:
            paragraph_count += 1
            para_text = "\n".join(current_paragraph)
            new_lines.append(f"{paragraph_count}. {para_text}")
            new_lines.append("")
            new_lines.append("*（此处填写翻译）*")

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines))

    print(f"Reformatted all .md files in {split_dir} for translation.")

if __name__ == "__main__":
    reformat_md_for_translation()

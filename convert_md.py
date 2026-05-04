import os

def convert_to_md():
    split_dir = 'zhong/split/'

    if not os.path.exists(split_dir):
        print(f"Error: Directory {split_dir} does not exist.")
        return

    # Process each .txt file in the split directory
    files = sorted([f for f in os.listdir(split_dir) if f.endswith('.txt')], 
                   key=lambda x: int(x.split('.')[0]) if x.split('.')[0].isdigit() else x)

    for filename in files:
        txt_path = os.path.join(split_dir, filename)
        md_path = os.path.join(split_dir, filename.replace('.txt', '.md'))

        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            continue

        # Transform the first non-empty line into an H1 header
        new_lines = []
        header_done = False
        
        for line in lines:
            stripped = line.strip()
            if stripped and not header_done:
                # Add # to the beginning of the first non-empty line
                new_lines.append("# " + stripped + "\n")
                header_done = True
            else:
                new_lines.append(line)

        with open(md_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

    print(f"Converted {len(files)} .txt files to .md in {split_dir}")

if __name__ == "__main__":
    convert_to_md()

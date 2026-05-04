import os
import re

md_dir = '/Users/zhangwei/work/ahan/zhong/split'

def process_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Repeatedly add blank lines between lines that are not separated by one.
    # This ensures that even blocks of multiple lines get separated.
    new_content = content
    prev_content = ""
    while new_content != prev_content:
        prev_content = new_content
        # Match a non-newline character, a single newline, and another non-newline character.
        new_content = re.sub(r'([^\n])\n([^\n])', r'\1\n\n\2', new_content)
    
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

files = [f for f in os.listdir(md_dir) if f.endswith('.md')]
files.sort()

count = 0
for f in files:
    if process_file(os.path.join(md_dir, f)):
        count += 1
        print(f"Added blank lines to {f}")

print(f"Done! Processed {count} files.")

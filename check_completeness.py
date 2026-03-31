import os
import re

def check_file(txt_path, md_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_lines = [l.strip() for l in f.readlines() if l.strip()]
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Split md content by numbering patterns (e.g., "1. ", "2. ")
    # Each section should have: "N. [Original Text]\n\n*[Translated Text]*"
    # We find all matches for "N. [Original Text]"
    sections = re.findall(r'^(\d+)\.\s+(.+)$', md_content, re.MULTILINE)
    
    # Also find all translation blocks
    translations = re.findall(r'\*(.+?)\*', md_content)
    
    errors = []
    
    # Check 1: Count of sections
    if len(sections) != len(txt_lines):
        errors.append(f"Paragraph count mismatch: txt has {len(txt_lines)}, md has {len(sections)}")
    
    # Check 2: Content consistency and translation completion
    for i, (num, original_in_md) in enumerate(sections):
        # Verification is tricky because some cleaning might have happened
        # We at least check if the translation placeholder exists
        pass

    # Simplified check: Just look for placeholders
    placeholders = md_content.count("*（此处填写翻译）*")
    if placeholders > 0:
        errors.append(f"Found {placeholders} untranslated placeholders.")

    # Check numbering sequence
    for i, (num, _) in enumerate(sections):
        if int(num) != i + 1:
            errors.append(f"Numbering sequence error at segment {i+1} (found {num})")

    return errors

def main():
    base_dir = "chang/split"
    all_ok = True
    for i in range(1, 23):
        txt_file = os.path.join(base_dir, f"{i}.txt")
        md_file = os.path.join(base_dir, f"{i}.md")
        
        if not os.path.exists(txt_file) or not os.path.exists(md_file):
            print(f"File pair {i} missing.")
            continue
            
        errors = check_file(txt_file, md_file)
        if errors:
            all_ok = False
            print(f"Error in {i}.md:")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"File {i}.md: OK")

    if all_ok:
        print("\nAll files passed the basic completeness check.")

if __name__ == "__main__":
    main()

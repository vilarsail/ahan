import os
import re

def clean_text(text):
    # Remove whitespace and common variations to facilitate matching
    return re.sub(r'\s+', '', text)

def check_alignment(i):
    txt_path = f"chang/split/{i}.txt"
    md_path = f"chang/split/{i}.md"
    
    if not os.path.exists(txt_path) or not os.path.exists(md_path):
        return [f"Files missing for index {i}"]

    with open(txt_path, 'r', encoding='utf-8') as f:
        txt_content = clean_text(f.read())
    
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Pattern to find: N. [Original Text]\n\n*[Translated Text]*
    # We use a non-greedy match for the original text
    # Note: The md file structure is:
    # N. Original
    # 
    # *Translation*
    
    # Split the md into blocks starting with digit + dot
    blocks = re.split(r'\n(?=\d+\.)', md_content)
    # The first block might be a title, skip it if it doesn't start with 1.
    if blocks and not re.match(r'^\d+\.', blocks[0]):
        blocks = blocks[1:]

    errors = []
    placeholder = "（此处填写翻译）"
    
    for idx, block in enumerate(blocks):
        # Extract original and translation from block
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if len(lines) < 2:
            continue
            
        # Match "N. Original"
        header_match = re.match(r'^\d+\.\s*(.+)$', lines[0])
        if not header_match:
            continue
            
        original = header_match.group(1)
        cleaned_original = clean_text(original)
        
        # Check if original exists in txt
        if cleaned_original not in txt_content:
            # Try a slightly more relaxed match if it fails
            errors.append(f"Segment {idx+1}: Original text not found in .txt source.")
        
        # Check translation (usually in italics between stars)
        # We look for anything between * * that is NOT the placeholder
        trans_text = ""
        trans_matches = re.findall(r'\*(.*?)\*', block, re.DOTALL)
        if not trans_matches:
            errors.append(f"Segment {idx+1}: No translation block found (missing * *)")
        else:
            merged_trans = "".join(trans_matches)
            if placeholder in merged_trans:
                errors.append(f"Segment {idx+1}: Translation placeholder still present.")
            elif len(merged_trans.strip()) < 2:
                errors.append(f"Segment {idx+1}: Translation appears empty.")

    return errors

def main():
    all_ok = True
    for i in range(1, 23):
        errors = check_alignment(i)
        if errors:
            all_ok = False
            print(f"File {i}.md Issues:")
            # Limit output per file
            for e in errors[:5]:
                print(f"  - {e}")
            if len(errors) > 5:
                print(f"  ... and {len(errors)-5} more issues.")
        else:
            print(f"File {i}.md: OK")
            
    if all_ok:
        print("\nAll translated files are aligned and contain translations.")

if __name__ == "__main__":
    main()

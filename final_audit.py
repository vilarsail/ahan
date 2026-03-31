import os
import re
import random

def get_blocks(content):
    # Match segments like: N. Original\n\n*Translation*
    return re.findall(r'(\d+\..+?\n\n\*.*?\*)', content, re.DOTALL)

def audit():
    for i in range(1, 23):
        path = f"chang/split/{i}.md"
        if not os.path.exists(path):
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        blocks = get_blocks(content)
        if not blocks:
            print(f"--- {i}.md: No valid segments found! ---")
            continue
            
        # Pick a random block from the middle to be representative
        sample = random.choice(blocks[len(blocks)//4 : len(blocks)*3//4])
        
        # Check for placeholder
        has_placeholder = "（此处填写翻译）" in sample
        
        print(f"--- File: {i}.md (Segments: {len(blocks)}) ---")
        if has_placeholder:
            print("  [!] WARNING: Contains untranslated placeholder in this sample.")
        
        # Clean up the sample for display
        lines = sample.strip().split('\n')
        orig = lines[0]
        trans = "\n".join(lines[1:]).strip()
        
        print(f"  Original: {orig[:100]}...")
        print(f"  Translation: {trans[:100]}...")
        print("-" * 30)

if __name__ == "__main__":
    audit()

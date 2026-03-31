import os
import re
import random

def clean(text):
    return re.sub(r'\s+', '', text)

def get_md_blocks(md_content):
    # Split by numbering pattern at start of line
    blocks = re.split(r'\n(?=\d+\.)', md_content)
    # Filter out title or non-numbered leading blocks
    return [b.strip() for b in blocks if re.match(r'^\d+\.', b.strip())]

def spot_check():
    results = []
    for i in range(1, 23):
        txt_path = f"chang/split/{i}.txt"
        md_path = f"chang/split/{i}.md"
        
        if not os.path.exists(txt_path) or not os.path.exists(md_path):
            continue
            
        with open(txt_path, 'r', encoding='utf-8') as f:
            txt_lines = [l.strip() for l in f.readlines() if l.strip()]
        
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
            
        md_blocks = get_md_blocks(md_content)
        placeholders = md_content.count("（此处填写翻译）")
        
        # Pick 3 random indices to check alignment
        num_checks = min(3, len(md_blocks), len(txt_lines))
        indices = sorted(random.sample(range(num_checks, min(len(md_blocks), len(txt_lines))), num_checks)) if min(len(md_blocks), len(txt_lines)) > num_checks else range(num_checks)
        
        file_report = {
            "file": f"{i}.md",
            "total_segments": len(md_blocks),
            "txt_lines": len(txt_lines),
            "placeholders": placeholders,
            "samples": []
        }
        
        for idx in indices:
            txt_orig = txt_lines[idx]
            
            # Extract original from md block (first line usually)
            block = md_blocks[idx]
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            md_orig = re.sub(r'^\d+\.\s*', '', lines[0]) if lines else "N/A"
            
            # Extract translation (between * *)
            trans = re.search(r'\*(.*?)\*', block, re.DOTALL)
            trans_text = trans.group(1).strip() if trans else "MISSING"
            
            file_report["samples"].append({
                "index": idx + 1,
                "match": clean(txt_orig)[:20] == clean(md_orig)[:20],
                "txt_orig": txt_orig[:50] + "...",
                "md_orig": md_orig[:50] + "...",
                "translation": trans_text[:50] + "..."
            })
        results.append(file_report)
    return results

if __name__ == "__main__":
    reports = spot_check()
    for r in reports:
        print(f"--- File: {r['file']} (Total: {r['total_segments']}, Placeholders: {r['placeholders']}) ---")
        if r['total_segments'] != r['txt_lines']:
            print(f"  [!] Count mismatch: TXT({r['txt_lines']}) vs MD({r['total_segments']})")
        for s in r['samples']:
            status = "[OK]" if s['match'] else "[MISMATCH]"
            print(f"  {status} Seg {s['index']}:")
            print(f"    Source: {s['txt_orig']}")
            print(f"    MD Orig: {s['md_orig']}")
            print(f"    Trans: {s['translation']}")
        print()

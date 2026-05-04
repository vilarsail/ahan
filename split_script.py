import os
import re

def split_text():
    input_path = 'zhong/origin/origin.txt'
    output_dir = 'zhong/split/'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # We are looking for "中阿含经卷第"
    # The requirement is:
    # 1. Start with "中阿含经卷第"
    # 2. End with "中阿含经卷第"
    # 3. Keep start line, discard end line
    # 4. Discard prologue

    vol_pattern = re.compile(r'中阿含经卷第([一二三四五六七八九十百]+)')

    current_vol_num = 0
    current_vol_content = []
    in_vol = False

    # Map Chinese numerals to integers for counting if needed,
    # but the prompt says 1.txt, 2.txt... based on the sequence.
    # Since there are 22 volumes, we can just increment a counter
    # every time we find a NEW start of a volume.

    # Actually, each volume has a start marker and an end marker which are identical.
    # We want to catch the first occurrence of "卷第i" as the start and the second as the end.

    vol_count = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        match = vol_pattern.search(line)
        if match:
            # Found a marker. Is it a start or an end?
            # If we are not currently in a volume, it's a start.
            if not in_vol:
                in_vol = True
                vol_count += 1
                current_vol_content = [line]
            else:
                # We are in a volume. This must be the end marker.
                # Save the current volume.
                with open(os.path.join(output_dir, f"{vol_count}.txt"), 'w', encoding='utf-8') as out_f:
                    out_f.writelines(current_vol_content)
                in_vol = False
                current_vol_content = []
        else:
            if in_vol:
                current_vol_content.append(line)
        i += 1

if __name__ == "__main__":
    split_text()

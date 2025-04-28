import os
import argparse
import re

FN_NAMES = [
    'run',
    'cleanup',
    '_remote_file_exists',
    '_configure_module',
    '_make_tmp_path',
    '_remove_tmp_path',
    '_transfer_file',
    '_transfer_data',
    '_fixup_perms2',
    '_remote_chmod',
    '_remote_chown',
    '_remote_chgrp',
    '_remote_set_user_facl',
    '_execute_remote_stat',
    '_remote_expand_user',
    '_execute_module',
    '_low_level_execute_command',
    '_get_diff_data',
]

def load_lines(path):
    with open(path, encoding='utf-8') as f:
        return list(f)

def save_lines(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))

def get_class_name(line):
    m = re.search('class ([0-9a-z_]+)\\(([0-9a-z_]+)\\)', line, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    m = re.search('class ([0-9a-z_]+)', line, re.IGNORECASE)
    if m:
        return m.group(1), None
    return None, None

def get_def_name(line):
    m = re.search('(\\s*)def ([0-9a-z_]+)', line, re.IGNORECASE)
    is_class_fn = len(m.group(1)) > 3
    name = m.group(2)
    return name, is_class_fn

def def_add_async(line):
    if 'async' not in line:
        line = re.sub('def ', lambda m: 'async def ', line)
    return line

def super_add_async(line):
    if 'async' not in line:
        p = line.index('super')
        line = line[:p] + 'await ' + line[p:]
    return line

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()

    for root, dirs, files in os.walk(args.path):
        for name in files:
            if os.path.splitext(name)[1] != '.py':
                continue
            path = os.path.join(root, name)
            lines = load_lines(path)
            changed = False
            
            class_name = None
            base_class_name = None
            for i, line in enumerate(lines):
                if 'class' in line:
                    class_name, base_class_name = get_class_name(line)
                #print(name, class_name, base_class_name, line)
                if 'def ' in line:
                    name, is_class_fn = get_def_name(line)
                    if not is_class_fn:
                        class_name, base_class_name = None, None
                    if base_class_name == 'ActionBase':
                        if name in FN_NAMES:
                            line = def_add_async(line)
                            lines[i] = line
                            changed = True
                if 'super(' in line and 'run(' in line:
                    if base_class_name == 'ActionBase':
                        line = super_add_async(line)
                        lines[i] = line
                        changed = True
               
                def repl(m):
                    nonlocal changed
                    changed = True
                    fn_name = m.group(1)
                    if fn_name in FN_NAMES:
                        return 'await ' + m.group(0)
                    return m.group(0)
                
                if base_class_name == 'ActionBase':
                    line = re.sub('self.([0-9a-z_]+)', repl, line, flags=re.IGNORECASE)
                    line = line.replace('await await ', 'await ')
                    lines[i] = line

            if changed:
                save_lines(path, lines)
                
if __name__ == "__main__":
    main()
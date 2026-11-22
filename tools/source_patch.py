"""Strict application of this project's text-only unified source deltas."""
from pathlib import PurePosixPath
import re

def sections(text):
    for block in re.split(r'(?m)(?=^--- )', text):
        if not block.strip(): continue
        lines = block.splitlines(keepends=True)
        if len(lines)<3 or not lines[0].startswith('--- ') or not lines[1].startswith('+++ '):
            raise ValueError('Invalid source patch header')
        old, new = lines[0][4:].strip(), lines[1][4:].strip()
        if not new.startswith('b/') or (old != '/dev/null' and old != 'a/'+new[2:]):
            raise ValueError('Unexpected source patch path')
        name = new[2:]
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe source patch path')
        yield name, old == '/dev/null', ''.join(lines[2:])

def apply_text(original, hunks):
    lines = original.splitlines(keepends=True)
    output, cursor = [], 0
    for hunk in re.split(r'(?m)(?=^@@ )', hunks):
        if not hunk: continue
        header, *body = hunk.splitlines(keepends=True)
        match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n', header)
        if not match: raise ValueError('Invalid source patch hunk')
        old_count = int(match[2] if match[2] is not None else 1)
        new_count = int(match[4] if match[4] is not None else 1)
        at = int(match[1])-1 if old_count else int(match[1])
        if at < cursor or at > len(lines): raise ValueError('Overlapping/out-of-range hunk')
        output.extend(lines[cursor:at]); cursor = at
        if len(output) != (int(match[3])-1 if new_count else int(match[3])):
            raise ValueError('Incorrect new hunk position')
        removed = added = 0
        for line in body:
            if not line or line[0] not in ' +-': raise ValueError('Unsupported source patch line')
            if line[0] in ' -':
                if cursor >= len(lines) or lines[cursor] != line[1:]:
                    raise ValueError('Source patch context mismatch')
                cursor += 1; removed += 1
            if line[0] in ' +': output.append(line[1:]); added += 1
        if (removed,added) != (old_count,new_count): raise ValueError('Incorrect hunk counts')
    output.extend(lines[cursor:])
    return ''.join(output)

def apply_directory(root, text):
    staged = []
    for name, created, hunks in sections(text):
        path = root / name
        if created and path.exists(): raise ValueError(f'New source already exists: {name}')
        original = '' if created else path.read_text(encoding='utf-8')
        staged.append((path, apply_text(original,hunks)))
    # Validate every hunk before writing any file.
    for path, result in staged:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result, encoding='utf-8', newline='\n')


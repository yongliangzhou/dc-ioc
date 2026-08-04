import pathlib, re

root = pathlib.Path('src')
# 匹配任意事件绑定 @xxx=" 后面在闭合引号前出现换行（容忍 CRLF）
pat = re.compile(r'@\w[\w-]*="[^"]*?[\r\n]')
# 同样检查 v-on:xxx="
pat2 = re.compile(r'v-on:[^"]*="[^"]*?[\r\n]')

n = 0
for f in sorted(root.rglob('*.vue')):
    try:
        txt = f.read_text(encoding='utf-8', errors='replace')
    except Exception as e:
        print('ERR', f, e)
        continue
    if pat.search(txt) or pat2.search(txt):
        print('HIT', f.as_posix())
        n += 1
print('TOTAL_HITS', n)

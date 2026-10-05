import os, subprocess, base64, json, urllib.request, urllib.error

root = r"D:\.cogseed\userWorkSpace\我的挑战有哪些\C4A_技能提交自动评审"
repo = "Yuzi1414/C4A-skill-evaluator"

# token from gh
token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()

def upload(rel_path, content_bytes):
    url = f"https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(rel_path, safe='/')}"
    b64 = base64.b64encode(content_bytes).decode()
    body = json.dumps({"message": f"add {rel_path}", "content": b64}).encode()
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    try:
        urllib.request.urlopen(req, timeout=30)
        return True
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} {e.read().decode()[:200]}"
    except Exception as e:
        return str(e)[:200]

import urllib.parse
results = []
for dirpath, dirnames, filenames in os.walk(root):
    if ".git" in dirpath:
        continue
    for fn in filenames:
        if fn == "_upload_repo.ps1":
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, root).replace("\\", "/")
        with open(full, "rb") as fh:
            data = fh.read()
        r = upload(rel, data)
        results.append((rel, r))

ok = sum(1 for _, r in results if r is True)
fail = [(rel, r) for rel, r in results if r is not True]
print(f"TOTAL={len(results)} OK={ok} FAIL={len(fail)}")
for rel, r in fail:
    print(f"FAIL {rel}: {r}")

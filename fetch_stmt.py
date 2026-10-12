"""Скачивает выписку Т-Банка по base64-хвосту ссылки из письма: fetch_stmt.py <b64> <out_dir>"""
import base64, os, shutil, subprocess, sys, zipfile

b64, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
url = base64.b64decode(b64).decode()
curl = shutil.which("curl.exe") or shutil.which("curl")
zp = os.path.join(out, "statement.zip")
cmd = [curl, "-sS", "--max-time", "60", "-o", zp, "-w", "%{http_code}"]
if len(sys.argv) > 3:
    cmd += ["--cacert", sys.argv[3]]
p = subprocess.run(cmd + [url], capture_output=True, text=True)
print("HTTP", p.stdout, p.stderr.strip())
with zipfile.ZipFile(zp) as z:
    z.extractall(out)
    print("\n".join(z.namelist()))

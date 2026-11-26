"""Start a tool detached, with no console window and below-normal priority; write its PID to state/<name>.pid.
python -I tools/launch.py <name> <script.py> [args...]"""
import os, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, "state"), exist_ok=True)
name, script, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
flags = 0x08000000 | 0x00004000 | 0x00000008 | 0x00000200  # NO_WINDOW | BELOW_NORMAL | DETACHED | NEW_PROCESS_GROUP
out = open(os.path.join(ROOT, "state", name + ".out"), "ab")
p = subprocess.Popen([sys.executable, "-I", os.path.join(ROOT, "tools", script)] + rest, cwd=ROOT,
                     stdin=subprocess.DEVNULL, stdout=out, stderr=out, creationflags=flags, close_fds=True)
open(os.path.join(ROOT, "state", name + ".pid"), "w").write(str(p.pid))
print(name, p.pid)

from flask import Flask, render_template, jsonify, request, send_file
import subprocess
import os
import shutil
import json
import tarfile
import tempfile
from datetime import datetime

app = Flask(__name__)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "Command timed out"
    except Exception as e:
        return "", str(e)

@app.route('/')
def index():
    return render_template('index.html')

# ─── STORAGE OVERVIEW ───────────────────────────────────────────────
@app.route('/api/storage/overview')
def storage_overview():
    termux_base = "/data/data/com.termux/files"
    
    total_out, _ = run_cmd(f"du -sb {termux_base} 2>/dev/null | awk '{{print $1}}'")
    home_out, _  = run_cmd(f"du -sb {termux_base}/home 2>/dev/null | awk '{{print $1}}'")
    usr_out, _   = run_cmd(f"du -sb {termux_base}/usr  2>/dev/null | awk '{{print $1}}'")
    
    df_out, _ = run_cmd("df -h /data | tail -1")
    df_parts  = df_out.split()
    
    return jsonify({
        "total_termux": int(total_out or 0),
        "home":         int(home_out  or 0),
        "usr":          int(usr_out   or 0),
        "disk_total":   df_parts[1] if len(df_parts) > 1 else "N/A",
        "disk_used":    df_parts[2] if len(df_parts) > 2 else "N/A",
        "disk_avail":   df_parts[3] if len(df_parts) > 3 else "N/A",
        "disk_percent": df_parts[4] if len(df_parts) > 4 else "N/A",
    })

@app.route('/api/storage/home_breakdown')
def home_breakdown():
    out, _ = run_cmd("du -sb ~//* 2>/dev/null | sort -rn | head -30")
    items = []
    for line in out.splitlines():
        parts = line.split('\t', 1)
        if len(parts) == 2:
            size = int(parts[0])
            path = parts[1]
            name = os.path.basename(path)
            items.append({"name": name, "path": path, "size": size})
    return jsonify(items)

# ─── PACKAGES ───────────────────────────────────────────────────────
@app.route('/api/packages/large')
def large_packages():
    out, _ = run_cmd("dpkg-query -Wf '${Installed-Size}\t${Package}\n' | sort -rn | head -50")
    items = []
    for line in out.splitlines():
        parts = line.split('\t', 1)
        if len(parts) == 2:
            size_kb = int(parts[0])
            if size_kb > 1024:  # only > 1MB
                items.append({"name": parts[1], "size": size_kb * 1024})
    return jsonify(items)

@app.route('/api/packages/delete', methods=['POST'])
def delete_package():
    data = request.json
    pkg  = data.get('package', '').strip()
    if not pkg or any(c in pkg for c in [';', '&', '|', '`', '$', '(', ')']):
        return jsonify({"success": False, "message": "Invalid package name"})
    out, err = run_cmd(f"pkg uninstall -y {pkg} 2>&1")
    success  = "removing" in (out + err).lower() or err == ""
    return jsonify({"success": True, "message": out or err})

# ─── PIP PACKAGES ───────────────────────────────────────────────────
@app.route('/api/pip/list')
def pip_list():
    out, _ = run_cmd("pip list --format=columns 2>/dev/null | tail -n +3")
    items  = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            items.append({"name": parts[0], "version": parts[1]})
    # get sizes
    sizes_out, _ = run_cmd(
        "du -sb /data/data/com.termux/files/usr/lib/python3*/site-packages/*/ 2>/dev/null | sort -rn"
    )
    size_map = {}
    for line in sizes_out.splitlines():
        p = line.split('\t', 1)
        if len(p) == 2:
            name = os.path.basename(p[1].rstrip('/'))
            size_map[name.lower()] = int(p[0])
    for item in items:
        item['size'] = size_map.get(item['name'].lower(), 0)
    items.sort(key=lambda x: x['size'], reverse=True)
    return jsonify(items)

@app.route('/api/pip/uninstall', methods=['POST'])
def pip_uninstall():
    data = request.json
    pkg  = data.get('package', '').strip()
    if not pkg or any(c in pkg for c in [';', '&', '|', '`', '$']):
        return jsonify({"success": False, "message": "Invalid package name"})
    out, err = run_cmd(f"pip uninstall -y {pkg} 2>&1")
    return jsonify({"success": True, "message": out or err})

@app.route('/api/pip/cache_purge', methods=['POST'])
def pip_cache_purge():
    out, err = run_cmd("pip cache purge 2>&1")
    return jsonify({"success": True, "message": out or err})

# ─── CLEANUP ────────────────────────────────────────────────────────
@app.route('/api/cleanup/apt', methods=['POST'])
def cleanup_apt():
    out, err = run_cmd("apt clean 2>&1 && apt autoremove -y 2>&1")
    return jsonify({"success": True, "message": out or err})

@app.route('/api/cleanup/pycache', methods=['POST'])
def cleanup_pycache():
    out1, _ = run_cmd('find ~ -name "__pycache__" -exec rm -rf {} + 2>/dev/null; echo "done"')
    out2, _ = run_cmd('find ~ -name "*.pyc" -delete 2>/dev/null; echo "done"')
    return jsonify({"success": True, "message": "Python cache cleared!"})

@app.route('/api/cleanup/delete_path', methods=['POST'])
def delete_path():
    data = request.json
    path = data.get('path', '').strip()
    home = os.path.expanduser("~")
    # Safety: only allow deletion inside home
    if not os.path.abspath(path).startswith(os.path.abspath(home)):
        return jsonify({"success": False, "message": "Only home folder paths allowed!"})
    if not os.path.exists(path):
        return jsonify({"success": False, "message": "Path not found"})
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return jsonify({"success": True, "message": f"Deleted: {path}"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ─── BACKUP ─────────────────────────────────────────────────────────
@app.route('/api/backup/full', methods=['POST'])
def backup_full():
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"/sdcard/termux-full-backup-{ts}.tar.gz"
    out, err = run_cmd(
        f"tar -czf {out_path} -C /data/data/com.termux/files ./home ./usr 2>&1"
    )
    if os.path.exists(out_path):
        restore_txt = _generate_restore_txt(out_path, "full")
        restore_path = f"/sdcard/termux-restore-guide-{ts}.txt"
        with open(restore_path, 'w') as f:
            f.write(restore_txt)
        return jsonify({"success": True, "message": f"Backup saved!\n{out_path}\nRestore guide: {restore_path}"})
    return jsonify({"success": False, "message": err or out})

@app.route('/api/backup/scripts', methods=['POST'])
def backup_scripts():
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = f"/sdcard/termux-scripts-backup-{ts}.tar.gz"
    home     = os.path.expanduser("~")
    
    # Collect script/config files only
    includes = []
    for item in os.listdir(home):
        full = os.path.join(home, item)
        if os.path.isfile(full):
            includes.append(item)
        elif os.path.isdir(full) and item in ['bin', '.config', '.ssh', 'scripts']:
            includes.append(item)
    
    if not includes:
        return jsonify({"success": False, "message": "No scripts/configs found in home"})
    
    include_str = ' '.join([f'"./{i}"' for i in includes])
    out, err    = run_cmd(f"tar -czf {out_path} -C {home} {include_str} 2>&1")
    
    if os.path.exists(out_path):
        restore_txt  = _generate_restore_txt(out_path, "scripts")
        restore_path = f"/sdcard/termux-scripts-restore-guide-{ts}.txt"
        with open(restore_path, 'w') as f:
            f.write(restore_txt)
        return jsonify({"success": True, "message": f"Scripts backup saved!\n{out_path}\nRestore guide: {restore_path}"})
    return jsonify({"success": False, "message": err or out})

def _generate_restore_txt(backup_path, backup_type):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if backup_type == "full":
        restore_cmd = f"tar -xzf {backup_path} -C /data/data/com.termux/files --recursive-unlink --preserve-permissions"
        desc        = "Full Environment (home + usr)"
    else:
        restore_cmd = f"tar -xzf {backup_path} -C ~ --recursive-unlink --preserve-permissions"
        desc        = "Scripts & Configs (home folder)"

    return f"""================================================================
        TERMUX BACKUP - RESTORE GUIDE
================================================================
  Backup Type : {desc}
  Backup File : {backup_path}
  Created At  : {ts}
----------------------------------------------------------------

================================================================
STEP 1 — Termux Install Karo (Fresh install pe)
================================================================

  F-Droid se Termux download karo:
  https://f-droid.org/en/packages/com.termux/

  Termux open karo aur run karo:
     pkg update && pkg upgrade -y

================================================================
STEP 2 — Storage Permission Do
================================================================

     termux-setup-storage

  Popup aaye toh "Allow" karo.

================================================================
STEP 3 — Backup File Check Karo
================================================================

     ls {backup_path}

  File dikh rahi hai? Toh aage badho.

================================================================
STEP 4 — RESTORE COMMAND
================================================================

  ⚠️  Ye command purana data replace kar dega!

     {restore_cmd}

  2-5 minute lag sakte hain. Beech mein band mat karna!

================================================================
STEP 5 — Termux Restart Karo
================================================================

  Termux force close karo aur dobara open karo.
  Ya run karo:  exit

================================================================
STEP 6 — Verify Karo
================================================================

     ls ~/
     pkg list-installed | head -20
     python --version

================================================================
⚠️  COMMON ERRORS & FIXES
================================================================

  ERROR: Permission denied
  FIX:   chmod -R 700 /data/data/com.termux/files/home

  ERROR: No space left
  FIX:   Phone mein storage free karo pehle

  ERROR: Cannot open backup file
  FIX:   ls /sdcard/*.tar.gz  — file path check karo

  ERROR: Packages kaam nahi kar rahe
  FIX:   pkg update && pkg upgrade -y

================================================================
        Backup safe rakho, scripts safe rahegi! 🔥
================================================================
"""

if __name__ == '__main__':
    import threading, subprocess, time
    def open_browser():
        time.sleep(1.5)
        subprocess.Popen(['termux-open-url', 'http://localhost:5000'])
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)

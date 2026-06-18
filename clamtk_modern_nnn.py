import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import queue
import json
import shutil
import os
from pathlib import Path
from datetime import datetime

# =========================
# CONFIG
# =========================

APP_NAME = "ClamTK Pro V2"

BASE_DIR = Path.home() / ".clamtk_pro"
QUARANTINE_DIR = BASE_DIR / "quarantine"
HISTORY_FILE = BASE_DIR / "history.json"

BASE_DIR.mkdir(exist_ok=True)
QUARANTINE_DIR.mkdir(exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================
# HELPERS
# =========================

def cmd_exists(cmd):
    return shutil.which(cmd) is not None


def load_history():
    if HISTORY_FILE.exists():
        return json.load(open(HISTORY_FILE))
    return []


def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================
# APP
# =========================

class ClamTKPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1400x850")

        self.queue = queue.Queue()
        self.scanning = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar()
        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=1, sticky="nsew")

        self.dashboard()

        self.after(100, self.update_ui)

    # =========================
    # SIDEBAR
    # =========================

    def sidebar(self):

        side = ctk.CTkFrame(self, width=240)
        side.grid(row=0, column=0, sticky="ns")

        ctk.CTkLabel(side, text="🛡 ClamTK Pro", font=("Arial", 24, "bold")).pack(pady=20)

        buttons = [
            ("Dashboard", self.dashboard),
            ("Quick Scan", self.quick),
            ("Full Scan", self.full),
            ("Custom Scan", self.custom),
            ("Quarantine", self.quarantine),
            ("History", self.history),
            ("Update", self.update_db),
        ]

        for t, c in buttons:
            ctk.CTkButton(side, text=t, command=c).pack(fill="x", padx=10, pady=5)

        self.daemon = ctk.CTkLabel(side, text="")
        self.daemon.pack(side="bottom", pady=10)

        self.check_daemon()

    # =========================
    # UI CORE
    # =========================

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def log(self, msg):
        self.queue.put(("log", msg))

    def update_ui(self):

        try:
            while True:
                item = self.queue.get_nowait()

                if item[0] == "log" and hasattr(self, "box"):
                    self.box.insert("end", item[1] + "\n")
                    self.box.see("end")

                if item[0] == "status" and hasattr(self, "status"):
                    self.status.configure(text=item[1])

                if item[0] == "progress" and hasattr(self, "bar"):
                    self.bar.set(item[1])

        except:
            pass

        self.after(100, self.update_ui)

    # =========================
    # DASHBOARD
    # =========================

    def dashboard(self):

        self.clear()

        ctk.CTkLabel(self.main, text="Security Dashboard", font=("Arial", 30, "bold")).pack(pady=20)

        self.status = ctk.CTkLabel(self.main, text="Ready")
        self.status.pack()

        self.bar = ctk.CTkProgressBar(self.main)
        self.bar.set(0)
        self.bar.pack(fill="x", padx=20, pady=10)

        self.box = ctk.CTkTextbox(self.main)
        self.box.pack(fill="both", expand=True, padx=20, pady=20)

    # =========================
    # SCAN ENGINE
    # =========================

    def scan(self, target, mode):

        if self.scanning:
            self.log("Scan already running")
            return

        self.scanning = True

        if not cmd_exists("clamdscan"):
            self.log("clamdscan not found")
            self.scanning = False
            return

        self.log(f"Start {mode}: {target}")

        infected = 0

        cmd = ["clamdscan", "--infected", "--no-summary", target]

        try:

            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

            for i, line in enumerate(p.stdout):

                self.log(line.strip())

                # fake progress (ClamAV does not give progress)
                self.queue.put(("progress", min(i / 200, 1)))

                if "FOUND" in line:
                    infected += 1

                    # AUTO QUARANTINE
                    try:
                        file = line.split(":")[0]
                        if os.path.exists(file):
                            shutil.move(file, QUARANTINE_DIR / os.path.basename(file))
                    except:
                        pass

            p.wait()

            self.log("SCAN DONE")
            self.queue.put(("status", f"Done ({infected} threats)"))

            history = load_history()
            history.insert(0, {
                "time": str(datetime.now()),
                "mode": mode,
                "target": target,
                "infected": infected
            })
            save_history(history)

        finally:
            self.scanning = False
            self.queue.put(("progress", 0))

    # =========================
    # SCAN MODES
    # =========================

    def quick(self):
        self.dashboard()
        threading.Thread(target=self.scan, args=(str(Path.home()), "Quick"), daemon=True).start()

    def full(self):
        if not messagebox.askyesno("Warning", "Full scan may slow system"):
            return

        self.dashboard()
        threading.Thread(target=self.scan, args=("/", "Full"), daemon=True).start()

    def custom(self):
        f = filedialog.askdirectory()
        if not f:
            return

        self.dashboard()
        threading.Thread(target=self.scan, args=(f, "Custom"), daemon=True).start()

    # =========================
    # QUARANTINE
    # =========================

    def quarantine(self):

        self.clear()

        ctk.CTkLabel(self.main, text="Quarantine", font=("Arial", 28)).pack(pady=20)

        frame = ctk.CTkScrollableFrame(self.main)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        files = list(QUARANTINE_DIR.glob("*"))

        for f in files:

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=f.name).pack(side="left", padx=10)

            def restore(file=f):
                shutil.move(file, Path.home() / file.name)
                self.quarantine()

            ctk.CTkButton(row, text="Restore", command=restore).pack(side="right")
            ctk.CTkButton(row, text="Delete", command=f.unlink).pack(side="right")

    # =========================
    # HISTORY
    # =========================

    def history(self):

        self.clear()

        box = ctk.CTkTextbox(self.main)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        for h in load_history():
            box.insert("end", f"{h}\n")

    # =========================
    # UPDATE DB
    # =========================

    def update_db(self):

        def run():
            self.queue.put(("status", "Updating..."))
            subprocess.run(["systemctl", "restart", "clamav-freshclam"])
            self.queue.put(("status", "Updated"))

        threading.Thread(target=run, daemon=True).start()

    # =========================
    # DAEMON
    # =========================

    def check_daemon(self):

        out = subprocess.getoutput("systemctl is-active clamav-daemon")

        if "active" in out:
            self.daemon.configure(text="🟢 daemon active")
        else:
            self.daemon.configure(text="🔴 daemon stopped")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = ClamTKPro()
    app.mainloop()

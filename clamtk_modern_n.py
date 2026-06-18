import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import queue
import json
import shutil
from pathlib import Path
from datetime import datetime

# =========================
# CONFIG
# =========================

APP_NAME = "ClamTK Pro"

CONFIG_DIR = Path.home() / ".clamtk_pro"
CONFIG_DIR.mkdir(exist_ok=True)

HISTORY_FILE = CONFIG_DIR / "history.json"
QUARANTINE_DIR = CONFIG_DIR / "quarantine"
QUARANTINE_DIR.mkdir(exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================
# HELPERS
# =========================

def command_exists(cmd):
    return shutil.which(cmd) is not None


def load_history():
    if HISTORY_FILE.exists():
        try:
            return json.load(open(HISTORY_FILE))
        except:
            return []
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

        self.scan_queue = queue.Queue()
        self.scanning = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.show_dashboard()

        self.after(100, self.process_queue)

    # =========================
    # SIDEBAR
    # =========================

    def create_sidebar(self):

        sidebar = ctk.CTkFrame(self, width=240)
        sidebar.grid(row=0, column=0, sticky="ns")

        ctk.CTkLabel(
            sidebar,
            text="🛡 ClamTK Pro",
            font=("Arial", 24, "bold")
        ).pack(pady=20)

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("Quick Scan", self.quick_scan),
            ("Full Scan", self.full_scan),
            ("Custom Scan", self.custom_scan),
            ("Quarantine", self.show_quarantine),
            ("History", self.show_history),
            ("Update DB", self.update_definitions),
        ]

        for t, c in buttons:
            ctk.CTkButton(sidebar, text=t, command=c).pack(fill="x", padx=10, pady=5)

        self.status_daemon = ctk.CTkLabel(sidebar, text="")
        self.status_daemon.pack(side="bottom", pady=20)

        self.check_daemon()

    # =========================
    # UI CORE
    # =========================

    def clear(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    def log(self, msg):
        self.scan_queue.put(("log", msg))

    def process_queue(self):

        try:
            while True:
                item = self.scan_queue.get_nowait()

                if item[0] == "log":
                    if hasattr(self, "logbox") and self.logbox.winfo_exists():
                        self.logbox.insert("end", item[1] + "\n")
                        self.logbox.see("end")

                elif item[0] == "status":
                    if hasattr(self, "status") and self.status.winfo_exists():
                        self.status.configure(text=item[1])

        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(100, self.process_queue)

    # =========================
    # DASHBOARD
    # =========================

    def show_dashboard(self):

        self.clear()

        ctk.CTkLabel(
            self.main_frame,
            text="Security Dashboard",
            font=("Arial", 28, "bold")
        ).pack(pady=20)

        self.status = ctk.CTkLabel(self.main_frame, text="Ready")
        self.status.pack()

        self.logbox = ctk.CTkTextbox(self.main_frame, height=500)
        self.logbox.pack(fill="both", expand=True, padx=20, pady=20)

    # =========================
    # SCAN ENGINE
    # =========================

    def run_scan(self, target, scan_type):

        if self.scanning:
            self.log("Scan already running")
            return

        self.scanning = True

        if not command_exists("clamdscan"):
            self.log("clamdscan not found")
            self.scanning = False
            return

        self.log(f"Starting {scan_type} scan: {target}")

        infected = 0

        cmd = [
            "clamdscan",
            "--fdpass",
            "--infected",
            "--no-summary",
            target
        ]

        try:

            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in p.stdout:

                line = line.strip()
                self.log(line)

                if "FOUND" in line:
                    infected += 1

            p.wait()

            self.log("=" * 50)
            self.log(f"Scan finished - infected: {infected}")
            self.log("=" * 50)

            self.scan_queue.put(("status", f"Done ({infected} threats)"))

            history = load_history()
            history.insert(0, {
                "time": str(datetime.now()),
                "type": scan_type,
                "target": target,
                "infected": infected
            })
            save_history(history)

        finally:
            self.scanning = False

    # =========================
    # SCAN TYPES
    # =========================

    def quick_scan(self):
        self.show_dashboard()
        threading.Thread(
            target=self.run_scan,
            args=(str(Path.home()), "Quick"),
            daemon=True
        ).start()

    def full_scan(self):
        if not messagebox.askyesno("Warning", "Full scan may take long time"):
            return

        self.show_dashboard()

        threading.Thread(
            target=self.run_scan,
            args=("/", "Full"),
            daemon=True
        ).start()

    def custom_scan(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.show_dashboard()

        threading.Thread(
            target=self.run_scan,
            args=(folder, "Custom"),
            daemon=True
        ).start()

    # =========================
    # QUARANTINE
    # =========================

    def show_quarantine(self):

        self.clear()

        ctk.CTkLabel(self.main_frame, text="Quarantine", font=("Arial", 26)).pack(pady=20)

        frame = ctk.CTkScrollableFrame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        files = list(QUARANTINE_DIR.glob("*"))

        if not files:
            ctk.CTkLabel(frame, text="Empty").pack()
            return

        for f in files:

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=f.name).pack(side="left", padx=10)

            ctk.CTkButton(
                row,
                text="Delete",
                command=lambda x=f: x.unlink()
            ).pack(side="right")

    # =========================
    # HISTORY
    # =========================

    def show_history(self):

        self.clear()

        ctk.CTkLabel(self.main_frame, text="History", font=("Arial", 26)).pack(pady=20)

        box = ctk.CTkTextbox(self.main_frame)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        history = load_history()

        for h in history:
            box.insert("end", f"{h}\n")

    # =========================
    # UPDATE
    # =========================

    def update_definitions(self):

        def worker():

            self.scan_queue.put(("status", "Updating DB..."))

            subprocess.Popen(
                ["systemctl", "restart", "clamav-freshclam"]
            )

            self.scan_queue.put(("status", "Updated"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================
    # DAEMON CHECK
    # =========================

    def check_daemon(self):

        try:
            out = subprocess.getoutput("systemctl is-active clamav-daemon")

            if "active" in out:
                self.status_daemon.configure(text="🟢 daemon active")
            else:
                self.status_daemon.configure(text="🔴 daemon stopped")

        except:
            self.status_daemon.configure(text="unknown")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = ClamTKPro()
    app.mainloop()

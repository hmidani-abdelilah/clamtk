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
# CONFIG (FIXED & CONSISTENT)
# =========================

APP_NAME = "ClamTK Pro Stable"

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
# MAIN APP
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

        self.create_sidebar()

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        self.dashboard()

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
            ("Dashboard", self.dashboard),
            ("Quick Scan", self.quick_scan),
            ("Full Scan", self.full_scan),
            ("Custom Scan", self.custom_scan),
            ("Quarantine", self.show_quarantine),
            ("History", self.show_history),
            ("Update DB", self.update_db),
        ]

        for text, cmd in buttons:
            ctk.CTkButton(sidebar, text=text, command=cmd).pack(fill="x", padx=10, pady=5)

        self.daemon_status = ctk.CTkLabel(sidebar, text="")
        self.daemon_status.pack(side="bottom", pady=15)

        self.check_daemon()

    # =========================
    # UI CORE
    # =========================

    def clear(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    def log(self, msg):
        self.queue.put(("log", msg))

    def process_queue(self):

        try:
            while True:
                item = self.queue.get_nowait()

                if item[0] == "log":
                    if hasattr(self, "logbox") and self.logbox.winfo_exists():
                        self.logbox.insert("end", item[1] + "\n")
                        self.logbox.see("end")

                elif item[0] == "status":
                    if hasattr(self, "status") and self.status.winfo_exists():
                        self.status.configure(text=item[1])

        except queue.Empty:
            pass

        self.after(100, self.process_queue)

    # =========================
    # DASHBOARD
    # =========================

    def dashboard(self):

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
    # SCAN ENGINE (FIXED)
    # =========================

    def run_scan(self, target, mode):

        if self.scanning:
            self.log("Scan already running...")
            return

        if not command_exists("clamdscan"):
            self.log("clamdscan not found")
            return

        self.scanning = True

        self.log(f"Starting {mode} scan: {target}")

        infected = 0

        cmd = [
            "clamdscan",
            "--infected",
            "--no-summary",
            target
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in process.stdout:

                line = line.strip()
                self.log(line)

                if "FOUND" in line:
                    infected += 1

                    # AUTO QUARANTINE (SAFE)
                    try:
                        file_path = line.split(":")[0]
                        src = Path(file_path)

                        if src.exists():
                            dst = QUARANTINE_DIR / src.name
                            shutil.move(str(src), str(dst))

                    except:
                        pass

            process.wait()

            self.log("=" * 50)
            self.log(f"Scan completed")
            self.log(f"Infected files: {infected}")
            self.log("=" * 50)

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

    # =========================
    # SCAN MODES
    # =========================

    def quick_scan(self):
        self.dashboard()
        threading.Thread(target=self.run_scan, args=(str(Path.home()), "Quick"), daemon=True).start()

    def full_scan(self):
        if not messagebox.askyesno("Warning", "Full scan may take long time. Continue?"):
            return

        self.dashboard()
        threading.Thread(target=self.run_scan, args=("/", "Full"), daemon=True).start()

    def custom_scan(self):
        folder = filedialog.askdirectory()
        if folder:
            self.dashboard()
            threading.Thread(target=self.run_scan, args=(folder, "Custom"), daemon=True).start()

    # =========================
    # QUARANTINE (FIXED)
    # =========================

    def show_quarantine(self):

        self.clear()

        ctk.CTkLabel(self.main_frame, text="Quarantine", font=("Arial", 26)).pack(pady=20)

        frame = ctk.CTkScrollableFrame(self.main_frame)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        files = list(QUARANTINE_DIR.glob("*"))

        if not files:
            ctk.CTkLabel(frame, text="No files in quarantine").pack()
            return

        for f in files:

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=f.name).pack(side="left", padx=10)

            ctk.CTkButton(
                row,
                text="Restore",
                command=lambda x=f: self.restore_file(x)
            ).pack(side="right", padx=5)

            ctk.CTkButton(
                row,
                text="Delete",
                command=lambda x=f: x.unlink()
            ).pack(side="right")

    def restore_file(self, file):

        try:
            shutil.move(str(file), str(Path.home() / file.name))
            self.show_quarantine()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================
    # HISTORY
    # =========================

    def show_history(self):

        self.clear()

        box = ctk.CTkTextbox(self.main_frame)
        box.pack(fill="both", expand=True, padx=20, pady=20)

        for h in load_history():
            box.insert("end", f"{h}\n")

    # =========================
    # UPDATE DB (FIXED)
    # =========================

    def update_db(self):

        def worker():
            self.queue.put(("status", "Updating virus database..."))

            subprocess.run(
                ["systemctl", "restart", "clamav-freshclam"]
            )

            self.queue.put(("status", "Database updated"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================
    # DAEMON CHECK
    # =========================

    def check_daemon(self):

        try:
            out = subprocess.getoutput("systemctl is-active clamav-daemon")

            if "active" in out:
                self.daemon_status.configure(text="🟢 clamd active")
            else:
                self.daemon_status.configure(text="🔴 clamd stopped")

        except:
            self.daemon_status.configure(text="unknown")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = ClamTKPro()
    app.mainloop()

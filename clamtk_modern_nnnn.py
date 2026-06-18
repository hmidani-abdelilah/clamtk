import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import queue
import shutil
import os
import json
from pathlib import Path
from datetime import datetime
import pystray
from PIL import Image, ImageDraw
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# =========================
# CONFIG
# =========================

APP = "ClamTK Pro V3"

BASE = Path.home() / ".clamtk_pro"
QUAR = BASE / "quarantine"
LOGS = BASE / "logs"
HIST = BASE / "history.json"

BASE.mkdir(exist_ok=True)
QUAR.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# =========================
# HELPERS
# =========================

def load_history():
    if HIST.exists():
        return json.load(open(HIST))
    return []

def save_history(d):
    with open(HIST, "w") as f:
        json.dump(d, f, indent=4)


# =========================
# REAL TIME MONITOR
# =========================

class Watcher(FileSystemEventHandler):

    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        if not event.is_directory:
            self.app.notify(f"File changed: {event.src_path}")


# =========================
# APP
# =========================

class ClamTKPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP)
        self.geometry("1400x850")

        self.q = queue.Queue()
        self.running = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar()
        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=1, sticky="nsew")

        self.dashboard()

        self.after(100, self.loop)

        self.start_tray()
        self.start_monitor()

    # =========================
    # SYSTEM TRAY
    # =========================

    def tray_icon(self):

        img = Image.new("RGB", (64, 64), "green")
        d = ImageDraw.Draw(img)
        d.rectangle([16, 16, 48, 48], fill="white")

        return img

    def start_tray(self):

        icon = pystray.Icon(
            "clamtk",
            self.tray_icon(),
            "ClamTK Pro",
            menu=pystray.Menu(
                pystray.MenuItem("Open", self.show_window),
                pystray.MenuItem("Exit", self.exit_app)
            )
        )

        threading.Thread(target=icon.run, daemon=True).start()

    def show_window(self, icon=None, item=None):
        self.deiconify()

    def exit_app(self, icon=None, item=None):
        self.destroy()

    # =========================
    # NOTIFICATIONS
    # =========================

    def notify(self, msg):
        print("[NOTIFY]", msg)

    # =========================
    # MONITOR
    # =========================

    def start_monitor(self):

        event_handler = Watcher(self)
        observer = Observer()
        observer.schedule(event_handler, str(Path.home()), recursive=True)
        observer.start()

    # =========================
    # UI
    # =========================

    def sidebar(self):

        s = ctk.CTkFrame(self, width=240)
        s.grid(row=0, column=0, sticky="ns")

        ctk.CTkLabel(s, text="🛡 ClamTK Pro", font=("Arial", 24)).pack(pady=20)

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
            ctk.CTkButton(s, text=t, command=c).pack(fill="x", padx=10, pady=5)

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    # =========================
    # QUEUE LOOP
    # =========================

    def loop(self):

        try:
            while True:
                i = self.q.get_nowait()

                if i[0] == "log":
                    self.box.insert("end", i[1] + "\n")

                if i[0] == "status":
                    self.status.configure(text=i[1])

        except:
            pass

        self.after(100, self.loop)

    # =========================
    # DASHBOARD
    # =========================

    def dashboard(self):

        self.clear()

        ctk.CTkLabel(self.main, text="Security Center", font=("Arial", 28)).pack(pady=20)

        self.status = ctk.CTkLabel(self.main, text="Ready")
        self.status.pack()

        self.box = ctk.CTkTextbox(self.main)
        self.box.pack(fill="both", expand=True, padx=20, pady=20)

    # =========================
    # SCAN ENGINE
    # =========================

    def scan(self, target, mode):

        if self.running:
            return

        self.running = True

        self.q.put(("status", f"Scanning {mode}"))

        cmd = ["clamdscan", "--infected", "--no-summary", target]

        infected = 0

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

        for line in p.stdout:

            self.q.put(("log", line.strip()))

            if "FOUND" in line:
                infected += 1

                try:
                    file = line.split(":")[0]
                    shutil.move(file, QUAR / os.path.basename(file))
                except:
                    pass

        p.wait()

        self.q.put(("status", f"Done ({infected})"))

        hist = load_history()
        hist.insert(0, {
            "time": str(datetime.now()),
            "mode": mode,
            "target": target,
            "infected": infected
        })
        save_history(hist)

        self.running = False

    # =========================
    # MODES
    # =========================

    def quick(self):
        self.dashboard()
        threading.Thread(target=self.scan, args=(str(Path.home()), "Quick"), daemon=True).start()

    def full(self):
        self.dashboard()
        threading.Thread(target=self.scan, args=("/", "Full"), daemon=True).start()

    def custom(self):
        f = filedialog.askdirectory()
        if f:
            self.dashboard()
            threading.Thread(target=self.scan, args=(f, "Custom"), daemon=True).start()

    # =========================
    # QUARANTINE
    # =========================

    def quarantine(self):

        self.clear()

        frame = ctk.CTkScrollableFrame(self.main)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        for f in QUARANTINE_DIR.glob("*"):

            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=5)

            ctk.CTkLabel(row, text=f.name).pack(side="left")

            ctk.CTkButton(row, text="Restore",
                          command=lambda x=f: shutil.move(x, Path.home() / x.name)).pack(side="right")

    # =========================
    # HISTORY
    # =========================

    def history(self):

        self.clear()

        box = ctk.CTkTextbox(self.main)
        box.pack(fill="both", expand=True)

        for h in load_history():
            box.insert("end", f"{h}\n")

    # =========================
    # UPDATE
    # =========================

    def update_db(self):

        subprocess.Popen(["systemctl", "restart", "clamav-freshclam"])


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app = ClamTKPro()
    app.mainloop()

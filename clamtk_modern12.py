import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import queue
import os
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
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)


# =========================
# MAIN APP
# =========================

class ClamTKPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1400x850")
        self.minsize(1200, 700)

        self.scan_queue = queue.Queue()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.show_dashboard()

        self.after(
            100,
            self.process_queue
        )

    # =====================
    # SIDEBAR
    # =====================

    def create_sidebar(self):

        sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0
        )

        sidebar.grid(
            row=0,
            column=0,
            sticky="ns"
        )

        ctk.CTkLabel(
            sidebar,
            text="🛡 ClamTK Pro",
            font=("Segoe UI", 28, "bold")
        ).pack(
            pady=(25, 25)
        )

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("Quick Scan", self.quick_scan),
            ("Full Scan", self.full_scan),
            ("Custom Scan", self.custom_scan),
            ("Quarantine", self.show_quarantine),
            ("History", self.show_history),
            ("Updates", self.update_definitions),
            ("Settings", self.show_settings)
        ]

        for text, cmd in buttons:
            ctk.CTkButton(
                sidebar,
                text=text,
                command=cmd,
                height=45
            ).pack(
                fill="x",
                padx=15,
                pady=5
            )

        self.daemon_label = ctk.CTkLabel(
            sidebar,
            text="Checking daemon..."
        )

        self.daemon_label.pack(
            side="bottom",
            pady=15
        )

        self.check_daemon_status()

    # =====================
    # VIEW HELPERS
    # =====================

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def add_log(self, text):
        self.scan_queue.put(("log", text))

    def process_queue(self):

        try:
            while True:

                item = self.scan_queue.get_nowait()

                if item[0] == "log":
                    if hasattr(self, "logbox"):
                        self.logbox.insert(
                            "end",
                            item[1] + "\n"
                        )
                        self.logbox.see("end")

                elif item[0] == "status":
                    if hasattr(self, "status_label"):
                        self.status_label.configure(
                            text=item[1]
                        )

        except queue.Empty:
            pass

        self.after(
            100,
            self.process_queue
        )

    # =====================
    # DASHBOARD
    # =====================

    def show_dashboard(self):

        self.clear_main()

        title = ctk.CTkLabel(
            self.main_frame,
            text="Security Dashboard",
            font=("Segoe UI", 32, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=20
        )

        cards = ctk.CTkFrame(self.main_frame)
        cards.pack(
            fill="x",
            padx=20
        )

        cards.grid_columnconfigure(
            (0, 1, 2),
            weight=1
        )

        stats = [
            ("Protection", "Active"),
            ("Threats", "0"),
            ("Definitions", "Ready")
        ]

        for idx, stat in enumerate(stats):

            card = ctk.CTkFrame(
                cards,
                height=120
            )

            card.grid(
                row=0,
                column=idx,
                sticky="nsew",
                padx=10,
                pady=10
            )

            ctk.CTkLabel(
                card,
                text=stat[0],
                font=("Segoe UI", 18)
            ).pack(
                pady=(20, 5)
            )

            ctk.CTkLabel(
                card,
                text=stat[1],
                font=("Segoe UI", 24, "bold")
            ).pack()

        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready"
        )

        self.status_label.pack(
            pady=10
        )

        self.logbox = ctk.CTkTextbox(
            self.main_frame,
            height=400
        )

        self.logbox.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

    # =====================
    # DAEMON STATUS
    # =====================

    def check_daemon_status(self):

        try:

            result = subprocess.run(
                [
                    "systemctl",
                    "is-active",
                    "clamav-daemon"
                ],
                capture_output=True,
                text=True
            )

            if result.stdout.strip() == "active":
                self.daemon_label.configure(
                    text="🟢 clamd active"
                )
            else:
                self.daemon_label.configure(
                    text="🔴 clamd stopped"
                )

        except:
            self.daemon_label.configure(
                text="Unknown status"
            )
    # =====================
    # HISTORY
    # =====================

    def add_history(self, scan_type, target, infected):

        history = load_history()

        history.insert(
            0,
            {
                "date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "scan_type": scan_type,
                "target": target,
                "infected": infected
            }
        )

        save_history(history)

    # =====================
    # SCAN THREAD
    # =====================

    def run_scan(
        self,
        target,
        scan_type="Custom"
    ):

        if not command_exists("clamdscan"):

            self.add_log(
                "ERROR: clamdscan not found."
            )

            return

        self.add_log(
            f"\nStarting {scan_type} scan"
        )

        self.add_log(
            f"Target: {target}\n"
        )

        infected_count = 0

        try:

            cmd = [
                "clamdscan",
                "--fdpass",
                "--multiscan",
                target
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:

                line = line.rstrip()

                self.add_log(line)

                if "FOUND" in line:
                    infected_count += 1

            process.wait()

            self.add_log("")
            self.add_log(
                "=" * 50
            )

            self.add_log(
                f"Scan completed"
            )

            self.add_log(
                f"Infected files: {infected_count}"
            )

            self.add_log(
                "=" * 50
            )

            self.scan_queue.put(
                (
                    "status",
                    f"Completed ({infected_count} threats)"
                )
            )

            self.add_history(
                scan_type,
                target,
                infected_count
            )

        except Exception as e:

            self.add_log(
                f"ERROR: {e}"
            )

            self.scan_queue.put(
                (
                    "status",
                    "Scan failed"
                )
            )

    # =====================
    # QUICK SCAN
    # =====================

    def quick_scan(self):

        self.show_dashboard()

        home = str(
            Path.home()
        )

        self.scan_queue.put(
            (
                "status",
                "Quick scan running..."
            )
        )

        threading.Thread(
            target=self.run_scan,
            args=(home, "Quick"),
            daemon=True
        ).start()

    # =====================
    # FULL SCAN
    # =====================

    def full_scan(self):

        answer = messagebox.askyesno(
            "Full Scan",
            (
                "A full system scan may take a long time.\n\n"
                "Continue?"
            )
        )

        if not answer:
            return

        self.show_dashboard()

        self.scan_queue.put(
            (
                "status",
                "Full scan running..."
            )
        )

        threading.Thread(
            target=self.run_scan,
            args=("/", "Full"),
            daemon=True
        ).start()

    # =====================
    # CUSTOM SCAN
    # =====================

    def custom_scan(self):

        folder = filedialog.askdirectory()

        if not folder:
            return

        self.show_dashboard()

        self.scan_queue.put(
            (
                "status",
                "Custom scan running..."
            )
        )

        threading.Thread(
            target=self.run_scan,
            args=(folder, "Custom"),
            daemon=True
        ).start()

    # =====================
    # FILE SCAN
    # =====================

    def scan_single_file(self):

        file_path = filedialog.askopenfilename()

        if not file_path:
            return

        self.show_dashboard()

        threading.Thread(
            target=self.run_scan,
            args=(file_path, "File"),
            daemon=True
        ).start()

    # =====================
    # UPDATE DEFINITIONS
    # =====================

    def update_definitions(self):

        def worker():

            self.scan_queue.put(("status", "Updating signatures..."))

            try:
                process = subprocess.Popen(
                    ["sudo", "systemctl", "restart", "clamav-freshclam"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                for line in process.stdout:
                    self.add_log(line.strip())

                process.wait()

                self.scan_queue.put(("status", "Definitions updated"))

            except Exception as e:
                self.add_log(f"Update error: {e}")
                self.scan_queue.put(("status", "Update failed"))

        threading.Thread(target=worker, daemon=True).start()

    # =====================
    # HISTORY PAGE
    # =====================

    def show_history(self):

        self.clear_main()

        ctk.CTkLabel(
            self.main_frame,
            text="Scan History",
            font=("Segoe UI", 30, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=20
        )

        textbox = ctk.CTkTextbox(
            self.main_frame
        )

        textbox.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        history = load_history()

        if not history:

            textbox.insert(
                "end",
                "No scan history available."
            )

            return

        for item in history:

            textbox.insert(
                "end",
                f"{item['date']}\n"
            )

            textbox.insert(
                "end",
                f"Type: {item['scan_type']}\n"
            )

            textbox.insert(
                "end",
                f"Target: {item['target']}\n"
            )

            textbox.insert(
                "end",
                f"Infected: {item['infected']}\n"
            )

            textbox.insert(
                "end",
                "-" * 60 + "\n"
            )

    # =====================
    # QUARANTINE
    # =====================

    def show_quarantine(self):

        self.clear_main()

        title = ctk.CTkLabel(
            self.main_frame,
            text="Quarantine",
            font=("Segoe UI", 30, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=20
        )

        files_frame = ctk.CTkScrollableFrame(
            self.main_frame
        )

        files_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        files = list(
            QUARANTINE_DIR.glob("*")
        )

        if not files:

            ctk.CTkLabel(
                files_frame,
                text="Quarantine is empty."
            ).pack(
                pady=20
            )

            return

        for file in files:

            row = ctk.CTkFrame(
                files_frame
            )

            row.pack(
                fill="x",
                pady=5
            )

            ctk.CTkLabel(
                row,
                text=file.name
            ).pack(
                side="left",
                padx=10
            )

            ctk.CTkButton(
                row,
                text="Delete",
                width=90,
                command=lambda f=file:
                    self.delete_quarantine(f)
            ).pack(
                side="right",
                padx=5
            )

    def delete_quarantine(self, file_path):

        try:

            file_path.unlink()

            messagebox.showinfo(
                "Deleted",
                f"{file_path.name} removed."
            )

            self.show_quarantine()

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================
    # SETTINGS
    # =====================

    def show_settings(self):

        self.clear_main()

        ctk.CTkLabel(
            self.main_frame,
            text="Settings",
            font=("Segoe UI", 30, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=20
        )

        ctk.CTkLabel(
            self.main_frame,
            text="Theme"
        ).pack(
            anchor="w",
            padx=20
        )

        theme_menu = ctk.CTkOptionMenu(
            self.main_frame,
            values=[
                "dark",
                "light",
                "system"
            ],
            command=self.change_theme
        )

        theme_menu.pack(
            anchor="w",
            padx=20,
            pady=10
        )

        ctk.CTkButton(
            self.main_frame,
            text="Check ClamAV Installation",
            command=self.check_clamav
        ).pack(
            anchor="w",
            padx=20,
            pady=20
        )

    def change_theme(self, mode):

        ctk.set_appearance_mode(
            mode
        )

    def check_clamav(self):

        cmds = [
            "clamdscan",
            "freshclam",
            "clamscan"
        ]

        result = []

        for cmd in cmds:

            if command_exists(cmd):
                result.append(
                    f"✓ {cmd}"
                )
            else:
                result.append(
                    f"✗ {cmd}"
                )

        messagebox.showinfo(
            "ClamAV Status",
            "\n".join(result)
        )

# =====================
# MAIN
# =====================

if __name__ == "__main__":

    app = ClamTKPro()

    app.mainloop()

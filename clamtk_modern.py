import customtkinter as ctk
import threading
import time
from tkinter import filedialog

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ClamTKPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("ClamTK Pro")
        self.geometry("1400x850")
        self.minsize(1200, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_area()

    # =========================
    # Sidebar
    # =========================

    def create_sidebar(self):

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        title = ctk.CTkLabel(
            self.sidebar,
            text="🛡 ClamTK Pro",
            font=("Segoe UI", 28, "bold")
        )
        title.pack(pady=(30, 30))

        buttons = [
            ("Dashboard", self.show_dashboard),
            ("Quick Scan", self.quick_scan),
            ("Full Scan", self.full_scan),
            ("Custom Scan", self.custom_scan),
            ("Quarantine", self.show_quarantine),
            ("Settings", self.show_settings)
        ]

        for text, cmd in buttons:
            ctk.CTkButton(
                self.sidebar,
                text=text,
                height=45,
                command=cmd
            ).pack(fill="x", padx=15, pady=6)

        ctk.CTkLabel(
            self.sidebar,
            text="Version 1.0",
            text_color="gray"
        ).pack(side="bottom", pady=20)

    # =========================
    # Main Area
    # =========================

    def create_main_area(self):

        self.main = ctk.CTkFrame(self)
        self.main.grid(row=0, column=1, sticky="nsew")

        self.show_dashboard()

    def clear_main(self):

        for widget in self.main.winfo_children():
            widget.destroy()

    # =========================
    # Dashboard
    # =========================

    def show_dashboard(self):

        self.clear_main()

        header = ctk.CTkLabel(
            self.main,
            text="Security Dashboard",
            font=("Segoe UI", 32, "bold")
        )
        header.pack(anchor="w", padx=25, pady=20)

        cards_frame = ctk.CTkFrame(self.main)
        cards_frame.pack(fill="x", padx=20)

        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        stats = [
            ("Protected", "✓ Active"),
            ("Threats", "0"),
            ("Definitions", "Updated")
        ]

        for i, (title, value) in enumerate(stats):
            card = ctk.CTkFrame(cards_frame, height=120)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")

            ctk.CTkLabel(
                card,
                text=title,
                font=("Segoe UI", 18)
            ).pack(pady=(20, 5))

            ctk.CTkLabel(
                card,
                text=value,
                font=("Segoe UI", 26, "bold")
            ).pack()

        self.progress = ctk.CTkProgressBar(self.main)
        self.progress.pack(fill="x", padx=30, pady=25)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            self.main,
            text="Ready"
        )
        self.status_label.pack()

        self.logbox = ctk.CTkTextbox(
            self.main,
            height=300
        )
        self.logbox.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

    # =========================
    # Scan Engine
    # =========================

    def run_scan(self, scan_type):

        self.show_dashboard()

        self.logbox.insert("end", f"\nStarting {scan_type} scan...\n")

        for i in range(101):

            self.progress.set(i / 100)

            self.status_label.configure(
                text=f"{scan_type} Scan: {i}%"
            )

            self.update_idletasks()
            time.sleep(0.05)

        self.logbox.insert(
            "end",
            f"\n{scan_type} scan completed.\n"
        )

        self.status_label.configure(
            text="Scan Completed"
        )

    def start_scan_thread(self, scan_type):

        threading.Thread(
            target=self.run_scan,
            args=(scan_type,),
            daemon=True
        ).start()

    def quick_scan(self):
        self.start_scan_thread("Quick")

    def full_scan(self):
        self.start_scan_thread("Full")

    def custom_scan(self):

        folder = filedialog.askdirectory()

        if folder:
            self.start_scan_thread(
                f"Custom ({folder})"
            )

    # =========================
    # Quarantine
    # =========================

    def show_quarantine(self):

        self.clear_main()

        ctk.CTkLabel(
            self.main,
            text="Quarantine",
            font=("Segoe UI", 30, "bold")
        ).pack(anchor="w", padx=25, pady=20)

        table = ctk.CTkTextbox(
            self.main
        )

        table.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        table.insert(
            "end",
            "No quarantined files.\n"
        )

    # =========================
    # Settings
    # =========================

    def show_settings(self):

        self.clear_main()

        ctk.CTkLabel(
            self.main,
            text="Settings",
            font=("Segoe UI", 30, "bold")
        ).pack(anchor="w", padx=25, pady=20)

        ctk.CTkLabel(
            self.main,
            text="Appearance Mode"
        ).pack(anchor="w", padx=25)

        mode = ctk.CTkOptionMenu(
            self.main,
            values=["Dark", "Light", "System"],
            command=self.change_theme
        )

        mode.pack(
            anchor="w",
            padx=25,
            pady=10
        )

    def change_theme(self, choice):

        ctk.set_appearance_mode(choice.lower())


if __name__ == "__main__":

    app = ClamTKPro()
    app.mainloop()



import customtkinter as ctk
from PIL import Image
import os

# Configuration globale du thème
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue") # Options: "blue", "green", "dark-blue"

class ClamTkModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuration de la fenêtre principale
        self.title("ClamTk - Interface Antivirus Moderne")
        self.geometry("680x520")
        self.resizable(False, False)

        # Grille principale (4 colonnes)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1, pad=10)
        self.grid_rowconfigure((0, 1, 2, 3, 4), weight=1, pad=10)

        # --- SECTION 1 : CONFIGURATION ---
        self.create_section_header("Configuration", row=0)
        self.create_action_button("🎛️", "Paramètres", "Configurer l'antivirus", self.on_settings, row=1, col=0)
        self.create_action_button("🛡️", "Liste blanche", "Exclure des fichiers", self.on_whitelist, row=1, col=1)
        self.create_action_button("📅", "Planificateur", "Automatiser les scans", self.on_scheduler, row=1, col=2)

        # --- SECTION 2 : HISTORIQUE ---
        self.create_section_header("Historique", row=2)
        self.create_action_button("📜", "Historique", "Voir les anciens scans", self.on_history, row=3, col=0)
        self.create_action_button("☣️", "Quarantaine", "Gérer les fichiers isolés", self.on_quarantine, row=3, col=1)

        # --- SECTION 3 : MISE À JOUR & ANALYSE ---
        self.create_section_header("Mises à jour et Analyses", row=4)
        self.create_action_button("🔄", "Mises à jour", "Télécharger les signatures", self.on_update, row=5, col=0)
        self.create_action_button("📁", "Analyser un dossier", "Scanner un répertoire", self.on_scan_directory, row=5, col=1)
        self.create_action_button("📄", "Analyser un fichier", "Scanner un fichier unique", self.on_scan_file, row=5, col=2)

        # --- BARRE D'ÉTAT (BOTTOM BAR) ---
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(20, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_bar, 
            text="Status : Prêt - Base de données à jour", 
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=20, pady=5)

    def create_section_header(self, title_text, row):
        """Crée un titre de section élégant."""
        header = ctk.CTkLabel(
            self, 
            text=title_text, 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("gray40", "gray70")
        )
        header.grid(row=row, column=0, columnspan=4, sticky="w", padx=20, pady=(15, 2))

    def create_action_button(self, icon_str, title, subtitle, command_func, row, col):
        """Crée un bloc cliquable contenant une icône, un titre et une description."""
        # Conteneur du bouton (Frame cliquable)
        button_frame = ctk.CTkButton(
            self,
            text="",
            width=150,
            height=80,
            fg_color=("gray85", "gray25"),
            hover_color=("gray75", "gray35"),
            command=command_func,
            corner_radius=8
        )
        button_frame.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")

        # Rendre les éléments internes insensibles aux clics pour que la Frame capture tout
        # Icône (Emoji ou texte pour l'exemple, remplaçable par CTkImage)
        icon_label = ctk.CTkLabel(button_frame, text=icon_str, font=ctk.CTkFont(size=24))
        icon_label.pack(pady=(8, 2))

        # Titre principal
        lbl_title = ctk.CTkLabel(button_frame, text=title, font=ctk.CTkFont(size=12, weight="bold"))
        lbl_title.pack()

        # Description courte
        lbl_sub = ctk.CTkLabel(button_frame, text=subtitle, font=ctk.CTkFont(size=9), text_color="gray")
        lbl_sub.pack(pady=(0, 5))

    # --- FONCTIONS REPRÉSENTANT LES ACTIONS ---
    def on_settings(self):
        self.update_status("Ouverture des paramètres...")
        # Logique pour modifier les options de scan (ex: scan de fichiers cachés)

    def on_whitelist(self):
        self.update_status("Gestion de la liste blanche...")

    def on_scheduler(self):
        self.update_status("Planification des tâches en cours...")

    def on_history(self):
        self.update_status("Lecture des fichiers de log...")

    def on_quarantine(self):
        self.update_status("Affichage de la quarantaine...")

    def on_update(self):
        self.update_status("Vérification des mises à jour ClamAV...")
        # Exemple d'appel système : subprocess.run(["freshclam"])

    def on_scan_directory(self):
        directory = ctk.filedialog.askdirectory()
        if directory:
            self.update_status(f"Analyse du dossier : {directory}")
            # Exemple d'appel système : subprocess.run(["clamscan", "-r", directory])

    def on_scan_file(self):
        file_path = ctk.filedialog.askopenfilename()
        if file_path:
            self.update_status(f"Analyse du fichier : {file_path}")

    def update_status(self, text):
        """Met à jour le texte de la barre d'état."""
        self.status_label.configure(text=f"Status : {text}")


if __name__ == "__main__":
    app = ClamTkModernApp()
    app.mainloop()

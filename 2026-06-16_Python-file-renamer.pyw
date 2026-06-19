import os
import sys
import re
import ctypes
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class FileRenamerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Datei-Konverter")
        self.root.geometry("1050x850")
        self.root.minsize(900, 700)

        # Variablen für die GUI
        desktop_path = str(Path.home() / "Desktop")
        self.source_dir = tk.StringVar()
        self.log_dir = tk.StringVar(value=desktop_path)
        self.include_subdirs = tk.BooleanVar(value=False)
        
        # Variablen für die Datums-Auswahl
        self.date_source = tk.StringVar(value="Erstellungsdatum")
        self.manual_date_val = tk.StringVar(value=datetime.now().strftime("%d.%m.%Y"))

        # Liste für die dynamischen Ausschluss-Ordner
        self.excluded_dirs = []

        # Standardformat
        self.naming_format = tk.StringVar(value="{jahr}-{monat}-{tag}_{name}")

        self.setup_ui()

    def setup_ui(self):
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)

        # --- OBERER BEREICH: EINSTELLUNGEN ---
        self.config_frame = tk.LabelFrame(self.main_container, text=" Einstellungen ", padx=10, pady=10)
        self.config_frame.pack(fill="x", padx=15, pady=10, side="top")

        # Quellordner
        lbl_source = tk.Frame(self.config_frame)
        lbl_source.grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(lbl_source, text="Quellordner").pack(side="left")
        tk.Label(lbl_source, text="*", fg="red").pack(side="left")
        tk.Label(lbl_source, text=":").pack(side="left")
        
        self.entry_source = tk.Entry(self.config_frame, textvariable=self.source_dir, width=60)
        self.entry_source.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.config_frame, text="Durchsuchen...", command=self.browse_source).grid(row=0, column=2, padx=5, pady=5)

        # Log-Ordner
        lbl_log = tk.Frame(self.config_frame)
        lbl_log.grid(row=1, column=0, sticky="w", pady=5)
        tk.Label(lbl_log, text="Log-Speicherort").pack(side="left")
        tk.Label(lbl_log, text="*", fg="red").pack(side="left")
        tk.Label(lbl_log, text=":").pack(side="left")
        
        self.entry_log = tk.Entry(self.config_frame, textvariable=self.log_dir, width=60)
        self.entry_log.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.config_frame, text="Durchsuchen...", command=self.browse_log).grid(row=1, column=2, padx=5, pady=5)

        # Unterordner Checkbox
        tk.Checkbutton(self.config_frame, text="Unterordner mit einbeziehen", variable=self.include_subdirs).grid(row=2, column=1, sticky="w", pady=5)

        # --- DATUMS-OPTIONEN ---
        date_frame = tk.Frame(self.config_frame)
        date_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=5)
        
        tk.Label(date_frame, text="Zu verwendendes Datum:").pack(side="left", padx=(0, 5))
        
        self.date_dropdown = ttk.Combobox(
            date_frame, textvariable=self.date_source, 
            values=["Erstellungsdatum", "Änderungsdatum", "Manuelles Datum"], 
            state="readonly", width=18
        )
        self.date_dropdown.pack(side="left", padx=5)
        self.date_dropdown.bind("<<ComboboxSelected>>", self.toggle_manual_date_entry)
        
        self.lbl_manual_hint = tk.Label(date_frame, text="Format (TT.MM.JJJJ):")
        self.entry_manual_date = tk.Entry(date_frame, textvariable=self.manual_date_val, width=12)
        
        self.toggle_manual_date_entry()

        # --- DYNAMISCHER AUSSCHLUSS-BEREICH ---
        self.exclude_frame = tk.Frame(self.config_frame)
        self.exclude_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=5)
        
        tk.Label(self.exclude_frame, text="Ordner ausschließen:").pack(side="left", padx=(0, 5))
        self.btn_add_exclude = tk.Button(self.exclude_frame, text="Ordner hinzufügen...", command=self.add_exclusion_dir, bg="#F0F0F0")
        self.btn_add_exclude.pack(side="left")

        # Container für die Liste der ausgeschlossenen Ordner
        self.list_exclude_frame = tk.Frame(self.config_frame)
        self.list_exclude_frame.grid(row=5, column=1, columnspan=2, sticky="w", padx=5)

        # --- MITTLERER BEREICH: FORMATIERUNG & ANLEITUNG ---
        format_frame = tk.LabelFrame(self.main_container, text=" Namensformat anpassen ", padx=10, pady=10)
        format_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(format_frame, text="Format-Muster:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(format_frame, textvariable=self.naming_format, width=60, font=("Courier", 10)).grid(row=0, column=1, padx=5, pady=5)
        
        # Start Button
        self.start_btn = tk.Button(format_frame, text="Konvertierung Starten", command=self.press_start_button, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.start_btn.grid(row=0, column=2, padx=5, pady=5)

        # Infobox / Anleitung
        info_text = (
            "Platzhalter: {name} = Originalname (Leerzeichen zu _) | {jahr} = YYYY | {monat} = MM | {tag} = DD\n"
            "Hinweis: Die Verarbeitung läuft im Hintergrund. Du siehst den Fortschritt live in der Tabelle."
        )
        info_label = tk.Label(format_frame, text=info_text, justify="left", fg="#555555", font=("Arial", 9))
        info_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=5)

        # --- FORTSCHRITTS-BEREICH (LADEBALKEN) ---
        self.progress_frame = tk.Frame(self.main_container, padx=15, pady=5)
        self.progress_frame.pack(fill="x")
        
        self.progress_label = tk.Label(self.progress_frame, text="Bereit.", font=("Arial", 9, "bold"), fg="#333333")
        self.progress_label.pack(anchor="w", pady=(0, 2))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x")

        # --- UNTERER BEREICH: PROTOKOLL / TABELLE ---
        log_frame = tk.LabelFrame(self.main_container, text=" Protokoll / Live-Vorschau (Doppelklick zum Öffnen im Explorer) ", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        # Tabelle (Treeview)
        columns = ("alt", "neu", "datum", "pfad", "status")
        self.tree = ttk.Treeview(log_frame, columns=columns, show="headings")
        
        self.tree.heading("alt", text="Alter Name")
        self.tree.heading("neu", text="Neuer Name")
        self.tree.heading("datum", text="Gewähltes Datum")
        self.tree.heading("pfad", text="Dateipfad")
        self.tree.heading("status", text="Status / Fehler")

        self.tree.column("alt", width=180, anchor="w")
        self.tree.column("neu", width=180, anchor="w")
        self.tree.column("datum", width=110, anchor="center")
        self.tree.column("pfad", width=250, anchor="w")
        self.tree.column("status", width=140, anchor="w")

        self.tree.bind("<Double-1>", self.open_in_explorer)

        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(log_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

    def toggle_manual_date_entry(self, event=None):
        if self.date_source.get() == "Manuelles Datum":
            self.lbl_manual_hint.pack(side="left", padx=(15, 5))
            self.entry_manual_date.pack(side="left")
        else:
            self.lbl_manual_hint.pack_forget()
            self.entry_manual_date.pack_forget()

    def browse_source(self):
        directory = filedialog.askdirectory()
        if directory:
            self.source_dir.set(directory)

    def browse_log(self):
        directory = filedialog.askdirectory()
        if directory:
            self.log_dir.set(directory)

    def add_exclusion_dir(self):
        directory = filedialog.askdirectory(title="Ordner vom Umbenennen ausschließen")
        if directory:
            norm_dir = str(Path(directory).resolve())
            if norm_dir not in self.excluded_dirs:
                self.excluded_dirs.append(norm_dir)
                self.update_exclusion_ui()
            else:
                messagebox.showinfo("Info", "Dieser Ordner ist bereits auf der Liste.")

    def remove_exclusion_dir(self, directory):
        if directory in self.excluded_dirs:
            self.excluded_dirs.remove(directory)
            self.update_exclusion_ui()

    def update_exclusion_ui(self):
        for widget in self.list_exclude_frame.winfo_children():
            widget.destroy()

        for d_path in self.excluded_dirs:
            row_frame = tk.Frame(self.list_exclude_frame, pady=2)
            row_frame.pack(fill="x", anchor="w")

            lbl = tk.Label(row_frame, text=f"• {d_path}", fg="#C62828", font=("Arial", 9, "italic"))
            lbl.pack(side="left", padx=5)

            btn_del = tk.Button(row_frame, text="❌", font=("Arial", 7), bg="#FFEBEE", fg="#C62828", 
                                bd=0, cursor="hand2", command=lambda d=d_path: self.remove_exclusion_dir(d))
            btn_del.pack(side="left", padx=5)

    def open_in_explorer(self, event):
        item = self.tree.selection()
        if not item:
            return
        
        values = self.tree.item(item[0])['values']
        if not values:
            return

        folder = values[3]
        new_name = values[1]
        
        if new_name == "-":
            new_name = values[0]

        full_file_path = Path(folder) / new_name

        if sys.platform == "win32":
            if full_file_path.exists():
                subprocess.run(['explorer', '/select,', str(full_file_path)])
            elif Path(folder).exists():
                subprocess.run(['explorer', str(folder)])
        else:
            if Path(folder).exists():
                os.system(f'open "{folder}"' if sys.platform == "darwin" else f'xdg-open "{folder}"')

    def validate_format(self, pattern):
        if not pattern.strip():
            return False, "Das Formatfeld darf nicht leer sein."
        if "{name}" not in pattern:
            return False, "Das Format muss zwingend den Platzhalter '{name}' enthalten!"
        
        extracted = re.findall(r'\{(.*?)\}', pattern)
        allowed = ["name", "jahr", "monat", "tag", "datum"]
        for item in extracted:
            if item not in allowed:
                return False, f"Unbekannter Platzhalter: '{{{item}}}'."
        return True, ""

    def is_hidden_or_system(self, file_path):
        blacklist = ["desktop.ini", "thumbs.db", "ntuser.dat", ".ds_store", "bootini", "virlock"]
        if file_path.name.lower() in blacklist or file_path.name.startswith("."):
            return True
            
        if sys.platform == "win32":
            try:
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
                if attrs != -1:
                    if (attrs & 2) or (attrs & 4):
                        return True
            except:
                pass
        return False

    def get_file_dates(self, file_path):
        stat = file_path.stat()
        m_time = datetime.fromtimestamp(stat.st_mtime)
        
        if sys.platform == "win32":
            c_time = datetime.fromtimestamp(stat.st_ctime)
        else:
            try:
                c_time = datetime.fromtimestamp(stat.st_birthtime)
            except AttributeError:
                c_time = m_time
        return c_time, m_time

    def get_unique_log_filename(self, base_dir, extension=".html"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today_str}_Datei_Konverter_Log{extension}"
        full_path = Path(base_dir) / filename
        
        if not full_path.exists():
            return full_path

        counter = 1
        while True:
            filename = f"{today_str}_Datei_Konverter_Log_V{counter}{extension}"
            full_path = Path(base_dir) / filename
            if not full_path.exists():
                return full_path
            counter += 1

    def build_new_name(self, pattern, original_name, c_date):
        suffix = Path(original_name).suffix
        text_stem = Path(original_name).stem

        replacements = {
            "jahr": c_date.strftime("%Y"),
            "monat": c_date.strftime("%m"),
            "tag": c_date.strftime("%d"),
            "datum": c_date.strftime("%Y%m%d")
        }

        regex_pattern = pattern
        for key, value in replacements.items():
            regex_pattern = regex_pattern.replace(f"{{{key}}}", re.escape(value))
        
        regex_pattern = regex_pattern.replace("{name}", "(.+)")
        match = re.match(f"^{regex_pattern}$", text_stem)
        
        if match:
            extracted_name = match.group(1)
            clean_stem_part = extracted_name.replace(" ", "_")
        else:
            clean_stem_part = text_stem.replace(" ", "_")

        final_replacements = replacements.copy()
        final_replacements["name"] = clean_stem_part

        new_stem = pattern
        for key, value in final_replacements.items():
            new_stem = new_stem.replace(f"{{{key}}}", value)
            
        return f"{new_stem}{suffix}"

    def update_progress_gui(self, percent, text):
        self.progress_bar["value"] = percent
        self.progress_label.config(text=text)

    def finalize_process(self, log_name):
        self.progress_bar["value"] = 100
        self.progress_label.config(text="Abgeschlossen!")
        self.start_btn.config(state="normal", bg="#4CAF50")
        messagebox.showinfo("Fertig!", f"Massenumbenennung abgeschlossen!\n\nLog gesichert unter:\n{log_name}")

    def initialize_html_log(self, path, src, pattern):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Datei Konverter Protokoll</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #FAFAFA; color: #333; }}
        h2 {{ color: #1B365D; margin-bottom: 5px; }}
        .meta-box {{ background: #FFF; padding: 15px; border-radius: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; line-height: 1.6; }}
        table {{ width: 100%; border-collapse: collapse; background: #FFF; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 4px; overflow: hidden; }}
        th {{ background-color: #1B365D; color: white; padding: 12px 10px; text-align: left; font-size: 14px; }}
        td {{ padding: 10px; border-bottom: 1px solid #E0E0E0; font-size: 13px; max-width: 300px; word-wrap: break-word; }}
        tr:nth-child(even) {{ background-color: #F8F9FA; }}
        .copy-path {{ color: #0288D1; font-weight: bold; cursor: pointer; text-decoration: underline; }}
        .copy-path:hover {{ color: #1B365D; }}
        #toast {{
            visibility: hidden; min-width: 250px; background-color: #333; color: #fff;
            text-align: center; border-radius: 4px; padding: 12px; position: fixed;
            z-index: 1; left: 50%; bottom: 30px; transform: translateX(-50%); font-size: 14px;
        }}
        #toast.show {{ visibility: visible; animation: fadein 0.5s, fadeout 0.5s 2.5s; }}
        @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
        @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}
        .status-success {{ color: #2E7D32; font-weight: bold; }}
        .status-already {{ color: #0288D1; font-weight: bold; }}
        .status-error {{ background-color: #FFEBEE; color: #C62828; font-weight: bold; }}
    </style>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(function() {{
                var x = document.getElementById("toast");
                x.className = "show";
                setTimeout(function(){{ x.className = x.className.replace("show", ""); }}, 3000);
            }});
        }}
    </script>
</head>
<body>
    <h2>=== DATEI KONVERTER PROTOKOLL (Live-Update) ===</h2>
    <div id="meta-section"></div>
    <table>
        <thead>
            <tr>
                <th>Alter Name</th>
                <th>Neuer Name</th>
                <th>Gewähltes Datum</th>
                <th>Dateipfad (Klicken zum Kopieren)</th>
                <th>Status / Fehlermeldung</th>
            </tr>
        </thead>
        <tbody id="log-rows">
        </tbody>
    </table>
    <div id="toast">Pfad in Zwischenablage kopiert!</div>
</body>
</html>
""")

    def append_to_html_log(self, path, new_row, src, pattern, success, error, all_rows):
        try:
            meta_html = f"""
    <div class="meta-box">
        <strong>Ausgeführt am:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}<br>
        <strong>Quellordner:</strong> {src}<br>
        <strong>Datum-Modus:</strong> {self.date_source.get()}<br>
        <strong>Ausgeschlossene Ordner:</strong> {', '.join(self.excluded_dirs) if self.excluded_dirs else 'Keine'}<br>
        <strong>Gewähltes Format:</strong> {pattern}<br>
        <strong>Status:</strong> Erfolgreich: {success} | Fehler: {error}
    </div>"""

            rows_html = ""
            for val in all_rows:
                is_error = "Fehler" in str(val[4])
                row_class = ' class="status-error"' if is_error else ''
                
                status_styled = str(val[4])
                if "Erfolgreich" in status_styled:
                    status_styled = f'<span class="status-success">{status_styled}</span>'
                elif "Bereits" in status_styled:
                    status_styled = f'<span class="status-already">{status_styled}</span>'
                
                raw_path = str(val[3])
                js_safe_path = raw_path.replace("\\", "\\\\")
                clickable_link = f'<span class="copy-path" onclick="copyToClipboard(\'{js_safe_path}\')">{raw_path}</span>'
                
                rows_html += f"""            <tr{row_class}>
                <td>{val[0]}</td>
                <td>{val[1]}</td>
                <td style='text-align:center;'>{val[2]}</td>
                <td>{clickable_link}</td>
                <td>{status_styled}</td>
            </tr>\n"""

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            start_body = content.split('<h2>=== DATEI KONVERTER PROTOKOLL (Live-Update) ===</h2>')[0]
            
            updated_content = start_body + f"""<h2>=== DATEI KONVERTER PROTOKOLL (Live-Update) ===</h2>
    {meta_html}
    <table>
        <thead>
            <tr>
                <th>Alter Name</th>
                <th>Neuer Name</th>
                <th>Gewähltes Datum</th>
                <th>Dateipfad (Klicken zum Kopieren)</th>
                <th>Status / Fehlermeldung</th>
            </tr>
        </thead>
        <tbody>
{rows_html}        </tbody>
    </table>
    <div id="toast">Pfad in Zwischenablage kopiert!</div>
</body>
</html>"""

            with open(path, "w", encoding="utf-8") as f:
                f.write(updated_content)
        except Exception:
            pass

    def press_start_button(self):
        src = self.source_dir.get().strip()
        log_d = self.log_dir.get().strip()
        pattern = self.naming_format.get()
        date_mode = self.date_source.get()
        manual_str = self.manual_date_val.get().strip()

        if not src or not log_d:
            messagebox.showerror("Pflichtfeld fehlt", "Bitte fülle Quellordner und Log-Speicherort aus.")
            return

        is_valid, error_msg = self.validate_format(pattern)
        if not is_valid:
            messagebox.showerror("Ungültiges Format", error_msg)
            return

        parsed_manual_date = None
        if date_mode == "Manuelles Datum":
            try:
                parsed_manual_date = datetime.strptime(manual_str, "%d.%m.%Y")
            except ValueError:
                messagebox.showerror("Ungültiges Datum", "Das manuelle Datum muss im Format TT.MM.JJJJ eingegeben werden (z.B. 24.12.2025)!")
                return

        src_path = Path(src)
        if not src_path.exists():
            messagebox.showerror("Fehler", "Der Quellordner existiert nicht!")
            return

        self.start_btn.config(state="disabled", bg="#9E9E9E")
        
        for item in self.tree.get_children():
            self.tree.delete(item)

        t = threading.Thread(
            target=self.start_renaming_worker, 
            args=(src_path, log_d, pattern, date_mode, parsed_manual_date), 
            daemon=True
        )
        t.start()

    def start_renaming_worker(self, src_path, log_d, pattern, date_mode, parsed_manual_date):
        if self.include_subdirs.get():
            all_files = [f for f in src_path.rglob("*") if f.is_file()]
        else:
            all_files = [f for f in src_path.iterdir() if f.is_file()]

        files = []
        for file in all_files:
            if "Datei_Konverter_Log" in file.name or self.is_hidden_or_system(file):
                continue
            
            file_resolved_path = str(file.resolve())
            should_skip = False
            for excluded_d in self.excluded_dirs:
                if file_resolved_path.startswith(excluded_d):
                    should_skip = True
                    break
            
            if not should_skip:
                files.append(file)

        total_files = len(files)
        if total_files == 0:
            self.root.after(0, lambda: self.progress_label.config(text="Keine passenden Dateien gefunden."))
            self.root.after(0, lambda: self.start_btn.config(state="normal", bg="#4CAF50"))
            return

        log_file_path = self.get_unique_log_filename(log_d, extension=".html")
        self.initialize_html_log(log_file_path, str(src_path), pattern)

        success_count = 0
        error_count = 0
        current_rows_data = []

        for idx, file in enumerate(files, start=1):
            percent = int((idx / total_files) * 100)
            status_text = f"Verarbeite Datei {idx} von {total_files} ({percent}%) - {file.name[:30]}..."
            self.root.after(0, lambda p=percent, t=status_text: self.update_progress_gui(p, t))

            folder_path = str(file.parent)
            try:
                c_date, m_date = self.get_file_dates(file)
                
                if date_mode == "Erstellungsdatum":
                    chosen_date = c_date
                elif date_mode == "Änderungsdatum":
                    chosen_date = m_date
                else:
                    chosen_date = parsed_manual_date

                date_display = chosen_date.strftime("%d.%m.%Y")
                new_name = self.build_new_name(pattern, file.name, chosen_date)
                new_file_path = file.parent / new_name

                if file.name == new_name:
                    status = "Bereits konvertiert"
                else:
                    if new_file_path.exists():
                        raise FileExistsError(f"Zieldatei '{new_name}' existiert bereits.")
                    file.rename(new_file_path)
                    status = "Erfolgreich"
                    success_count += 1

                row_values = (file.name, new_name, date_display, folder_path, status)

            except Exception as e:
                status = f"Fehler: {str(e)}"
                row_values = (file.name, "-", "-", folder_path, status)
                error_count += 1

            self.root.after(0, lambda v=row_values: self.tree.insert("", "end", values=v))
            current_rows_data.append(row_values)
            self.append_to_html_log(log_file_path, row_values, str(src_path), pattern, success_count, error_count, current_rows_data)

        self.root.after(0, lambda: self.finalize_process(log_file_path.name))


if __name__ == "__main__":
    root = tk.Tk()
    app = FileRenamerGUI(root)
    root.mainloop()
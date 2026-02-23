import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, subprocess, os, threading

CONFIG_FILE = "start_configs.json"

# ─── COULEURS & STYLE ───────────────────────────────────────────────
BG       = "#0f1117"
PANEL    = "#1a1d2e"
ACCENT   = "#4f8ef7"
ACCENT2  = "#7c3aed"
SUCCESS  = "#10b981"
DANGER   = "#ef4444"
TEXT     = "#e2e8f0"
SUBTEXT  = "#64748b"
BORDER   = "#2d3148"
HOVER    = "#252840"

APP_TYPES = ["Spring Boot", "ActiveMQ", "Elasticsearch", "Podman", "Timer"]

TYPE_FIELDS = {
    "Spring Boot":   [("Path du projet",  "path",       False),
                      ("Chemin du JAR",   "jar",        False),
                      ("Run Config",      "run_config", True )],
    "ActiveMQ":      [("Home path",       "home",       False)],
    "Elasticsearch": [("Home path",       "home",       False)],
    "Podman":        [("Nom du container","container",  False)],
    "Timer":         [("Secondes",        "seconds",    False)],
}

TYPE_ICON = {
    "Spring Boot":   "🌱",
    "ActiveMQ":      "📨",
    "Elasticsearch": "🔍",
    "Podman":        "📦",
    "Timer":         "⏱️",
}

# ─── DATA MANAGER ────────────────────────────────────────────────────
class Manager:
    def __init__(self):
        self.data = {"configs": []}
        self.load()

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"configs": []}

    @property
    def config_names(self):
        return [c["name"] for c in self.data["configs"]]

    def add_config(self, name):
        if name in self.config_names:
            return False
        self.data["configs"].append({"name": name, "apps": []})
        self.save()
        return True

    def delete_config(self, name):
        self.data["configs"] = [c for c in self.data["configs"] if c["name"] != name]
        self.save()

    def get_config(self, name):
        return next((c for c in self.data["configs"] if c["name"] == name), None)

    def add_app(self, config_name, app):
        cfg = self.get_config(config_name)
        if cfg is not None:
            cfg["apps"].append(app)
            self.save()

    def remove_app(self, config_name, idx):
        cfg = self.get_config(config_name)
        if cfg and 0 <= idx < len(cfg["apps"]):
            cfg["apps"].pop(idx)
            self.save()

    def move_app(self, config_name, from_idx, to_idx):
        cfg = self.get_config(config_name)
        if cfg and 0 <= from_idx < len(cfg["apps"]) and 0 <= to_idx <= len(cfg["apps"]):
            app = cfg["apps"].pop(from_idx)
            cfg["apps"].insert(to_idx, app)
            self.save()

# ─── STYLE HELPERS ───────────────────────────────────────────────────
def styled(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame",       background=BG)
    style.configure("Panel.TFrame", background=PANEL)
    style.configure("TLabel",       background=BG,    foreground=TEXT)
    style.configure("Sub.TLabel",   background=PANEL, foreground=SUBTEXT, font=("Segoe UI", 9))
    style.configure("Head.TLabel",  background=BG,    foreground=TEXT,
                    font=("Segoe UI", 13, "bold"))
    style.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                    foreground=TEXT, selectbackground=ACCENT, arrowcolor=TEXT)
    style.map("TCombobox", fieldbackground=[("readonly", PANEL)],
              foreground=[("readonly", TEXT)])

def btn(parent, text, cmd, color=ACCENT, fg="white", **kw):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=color, fg=fg, relief="flat", cursor="hand2",
                  font=("Segoe UI", 10), padx=12, pady=6,
                  activebackground=color, activeforeground=fg, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=_lighten(color)))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b

def entry(parent, width=28, **kw):
    e = tk.Entry(parent, bg=PANEL, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 10),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, width=width, **kw)
    return e

def _lighten(hex_color):
    r,g,b = int(hex_color[1:3],16), int(hex_color[3:5],16), int(hex_color[5:7],16)
    r,g,b = min(r+30,255), min(g+30,255), min(b+30,255)
    return f"#{r:02x}{g:02x}{b:02x}"

# ─── MAIN UI ─────────────────────────────────────────────────────────
class UI:
    def __init__(self, root):
        self.root = root
        self.mgr = Manager()
        root.title("🚀 App Launcher")
        root.configure(bg=BG)
        root.geometry("900x600")
        root.minsize(800, 500)
        styled(root)
        self._build()

    def _build(self):
        # LEFT PANEL – config list
        left = tk.Frame(self.root, bg=PANEL, width=240)
        left.pack(side="left", fill="y", padx=(10,0), pady=10)
        left.pack_propagate(False)

        tk.Label(left, text="CONFIGURATIONS", bg=PANEL, fg=SUBTEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(12,4))

        self.cfg_lb = tk.Listbox(left, bg=PANEL, fg=TEXT, selectbackground=ACCENT,
                                 selectforeground="white", relief="flat",
                                 font=("Segoe UI", 10), borderwidth=0,
                                 highlightthickness=0, activestyle="none")
        self.cfg_lb.pack(fill="both", expand=True, padx=8, pady=4)
        self.cfg_lb.bind("<<ListboxSelect>>", self._on_select_config)

        bbar = tk.Frame(left, bg=PANEL)
        bbar.pack(fill="x", padx=8, pady=8)
        btn(bbar, "+ Nouvelle", self._new_config_dlg, color=ACCENT2).pack(side="left", fill="x", expand=True, padx=(0,4))
        btn(bbar, "🗑", self._del_config, color=DANGER).pack(side="left")

        # RIGHT PANEL – config detail
        self.right = tk.Frame(self.root, bg=BG)
        self.right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self._show_empty()
        self._refresh_configs()

    # ── Config list management ────────────────────────────────────────
    def _refresh_configs(self):
        self.cfg_lb.delete(0, "end")
        for n in self.mgr.config_names:
            self.cfg_lb.insert("end", f"  {n}")

    def _on_select_config(self, *_):
        sel = self.cfg_lb.curselection()
        if sel:
            name = self.cfg_lb.get(sel[0]).strip()
            self._show_config(name)

    def _selected_name(self):
        sel = self.cfg_lb.curselection()
        if sel:
            return self.cfg_lb.get(sel[0]).strip()
        return None

    def _new_config_dlg(self):
        dlg = Dlg(self.root, "Nouvelle configuration", 340, 160)
        tk.Label(dlg.body, text="Nom :", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")
        e = entry(dlg.body, width=34)
        e.pack(pady=(4,10))
        e.focus()

        def ok():
            n = e.get().strip()
            if not n:
                return
            if not self.mgr.add_config(n):
                messagebox.showerror("Erreur", "Nom déjà utilisé.", parent=dlg)
                return
            self._refresh_configs()
            dlg.destroy()
            # select new
            for i, cn in enumerate(self.mgr.config_names):
                if cn == n:
                    self.cfg_lb.selection_set(i)
                    self._show_config(n)
                    break

        btn(dlg.body, "Créer", ok).pack()
        dlg.bind("<Return>", lambda e: ok())

    def _del_config(self):
        n = self._selected_name()
        if not n:
            return
        if messagebox.askyesno("Supprimer", f"Supprimer « {n} » ?"):
            self.mgr.delete_config(n)
            self._refresh_configs()
            self._show_empty()

    # ── Right panel ──────────────────────────────────────────────────
    def _clear_right(self):
        for w in self.right.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear_right()
        tk.Label(self.right, text="← Sélectionnez ou créez\nune configuration",
                 bg=BG, fg=SUBTEXT, font=("Segoe UI", 13)).pack(expand=True)

    def _show_config(self, name):
        cfg = self.mgr.get_config(name)
        if not cfg:
            return
        self._clear_right()

        # Header
        hdr = tk.Frame(self.right, bg=BG)
        hdr.pack(fill="x", pady=(0,8))
        tk.Label(hdr, text=name, bg=BG, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        btn(hdr, "▶  Lancer tout", lambda: self._launch(name),
            color=SUCCESS).pack(side="right")
        btn(hdr, "+ Ajouter app", lambda: self._add_app_dlg(name),
            color=ACCENT).pack(side="right", padx=(0,8))

        tk.Frame(self.right, bg=BORDER, height=1).pack(fill="x", pady=(0,10))

        # App list
        scroll = tk.Frame(self.right, bg=BG)
        scroll.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(scroll, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0,0), window=inner, anchor="nw")

        def on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", on_resize)

        def on_frame(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", on_frame)

        if not cfg["apps"]:
            tk.Label(inner, text="Aucune application. Cliquez sur « + Ajouter app ».",
                     bg=BG, fg=SUBTEXT, font=("Segoe UI", 10)).pack(pady=20)
        else:
            for i, app in enumerate(cfg["apps"]):
                self._app_card(inner, name, i, app)

    def _app_card(self, parent, config_name, idx, app):
        card = tk.Frame(parent, bg=PANEL, bd=1, relief="solid")
        card.pack(fill="x", pady=4, padx=2)

        # Drag handle
        handle = tk.Label(card, text="⋮⋮", bg=ACCENT, fg="white",
                         font=("Segoe UI", 10), width=3, cursor="hand2")
        handle.grid(row=0, rowspan=2, column=0, sticky="ns", padx=(4,8), pady=8)

        # Store drag data
        card.drag_data = {"config": config_name, "idx": idx, "card": card, "original_bg": PANEL}

        def on_press(e):
            card.drag_data["start_y"] = e.y_root
            card.drag_data["start_x"] = e.x_root
            card.config(bg="#2d3a5a", relief="solid", bd=2)
            card.lift()

        def on_motion(e):
            # Move card with mouse
            delta_y = e.y_root - card.drag_data["start_y"]
            current_y = card.winfo_y()
            new_y = current_y + delta_y
            card.drag_data["start_y"] = e.y_root
            
            # Translate Y position to window coordinates and move
            try:
                card.place(y=new_y, relx=0, relwidth=1)
                card.lift()
            except:
                pass

        def on_release(e):
            # Reset position with pack
            card.place_forget()
            card.config(bg=PANEL, relief="solid", bd=1)
            # Find target position based on final mouse Y
            y_pos = e.y_root
            target_idx = self._find_drop_index_global(parent, y_pos)
            if target_idx is not None and target_idx != idx:
                self.mgr.move_app(config_name, idx, target_idx)
                self._show_config(config_name)

        handle.bind("<Button-1>", on_press)
        handle.bind("<B1-Motion>", on_motion)
        handle.bind("<ButtonRelease-1>", on_release)

        icon = TYPE_ICON.get(app.get("type",""), "⚙️")
        tk.Label(card, text=f"{icon}  {app.get('name','?')}",
                 bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).grid(
                     row=0, column=1, sticky="w", padx=8, pady=(10,4))

        tk.Label(card, text=app.get("type",""), bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=8)

        # Fields preview
        col = 3
        for key, val in app.items():
            if key in ("name","type"):
                continue
            if val:
                f = tk.Frame(card, bg=PANEL)
                f.grid(row=1, column=col, sticky="w", padx=8, pady=(0,8))
                tk.Label(f, text=key.replace("_"," ").title()+":", bg=PANEL,
                         fg=SUBTEXT, font=("Segoe UI", 8)).pack(anchor="w")
                tk.Label(f, text=val, bg=PANEL, fg=TEXT,
                         font=("Segoe UI", 9)).pack(anchor="w")
                col += 1

        del_btn = btn(card, "✕", lambda i=idx: self._del_app(config_name, i),
                      color=PANEL, fg=DANGER)
        del_btn.grid(row=0, column=99, sticky="e", padx=8)
        card.columnconfigure(99, weight=1)

    def _find_drop_index(self, parent, y_pos):
        """Trouve l'index où déposer l'élément basé sur la position Y"""
        children = parent.winfo_children()
        for i, child in enumerate(children):
            if hasattr(child, 'winfo_y'):
                child_y = child.winfo_y()
                child_height = child.winfo_height()
                if y_pos < child_y + child_height / 2:
                    return i
        return len(children)

    def _find_drop_index_global(self, parent, global_y):
        """Trouve l'index où déposer basé sur les coordonnées globales"""
        children = parent.winfo_children()
        parent_y = parent.winfo_rooty()
        relative_y = global_y - parent_y
        
        for i, child in enumerate(children):
            if hasattr(child, 'winfo_y'):
                child_y = child.winfo_y()
                child_height = child.winfo_height()
                if relative_y < child_y + child_height / 2:
                    return i
        return len(children)

    def _del_app(self, config_name, idx):
        if messagebox.askyesno("Supprimer", "Retirer cette application ?"):
            self.mgr.remove_app(config_name, idx)
            self._show_config(config_name)

    # ── Add app dialog ───────────────────────────────────────────────
    def _add_app_dlg(self, config_name):
        dlg = Dlg(self.root, "Ajouter une application", 440, 420)

        tk.Label(dlg.body, text="Nom :", bg=PANEL, fg=TEXT).pack(anchor="w")
        name_e = entry(dlg.body, width=38)
        name_e.pack(pady=(2,10), fill="x")

        tk.Label(dlg.body, text="Type :", bg=PANEL, fg=TEXT).pack(anchor="w")
        type_var = tk.StringVar(value=APP_TYPES[0])
        type_cb = ttk.Combobox(dlg.body, values=APP_TYPES,
                               textvariable=type_var, state="readonly", width=36)
        type_cb.pack(pady=(2,12), fill="x")

        fields_frame = tk.Frame(dlg.body, bg=PANEL)
        fields_frame.pack(fill="both", expand=True)

        field_entries = {}

        def build_fields(*_):
            for w in fields_frame.winfo_children():
                w.destroy()
            field_entries.clear()
            atype = type_var.get()
            for label, key, optional in TYPE_FIELDS.get(atype, []):
                row = tk.Frame(fields_frame, bg=PANEL)
                row.pack(fill="x", pady=3)
                lbl_txt = label + (" (optionnel)" if optional else " *")
                tk.Label(row, text=lbl_txt, bg=PANEL, fg=TEXT if not optional else SUBTEXT,
                         font=("Segoe UI", 9)).pack(anchor="w")
                ent = entry(row, width=38)
                ent.pack(fill="x")

                # Browse button for path-like fields
                if "path" in key.lower() or "jar" in key.lower() or "home" in key.lower():
                    def browse(e=ent, lbl=label):
                        if "jar" in lbl.lower():
                            path = filedialog.askopenfilename(
                                parent=dlg, filetypes=[("JAR files","*.jar"),("All","*.*")])
                        else:
                            path = filedialog.askdirectory(parent=dlg)
                        if path:
                            e.delete(0,"end")
                            e.insert(0, path)
                    btn(row, "📁", browse, color=BORDER, fg=TEXT).pack(anchor="e", pady=2)

                field_entries[key] = ent

        type_cb.bind("<<ComboboxSelected>>", build_fields)
        build_fields()

        def add():
            atype = type_var.get()
            name  = name_e.get().strip()
            if not name:
                messagebox.showerror("Erreur", "Nom requis.", parent=dlg)
                return
            app = {"type": atype, "name": name}
            required_missing = False
            for label, key, optional in TYPE_FIELDS.get(atype, []):
                val = field_entries[key].get().strip()
                if not optional and not val:
                    required_missing = True
                app[key] = val
            if required_missing:
                if not messagebox.askyesno("Champs manquants",
                                           "Certains champs requis sont vides. Continuer ?",
                                           parent=dlg):
                    return
            self.mgr.add_app(config_name, app)
            self._show_config(config_name)
            dlg.destroy()

        btn(dlg.body, "Ajouter", add, color=ACCENT).pack(pady=(14,0), fill="x")

    # ── Launcher ─────────────────────────────────────────────────────
    def _launch(self, config_name):
        cfg = self.mgr.get_config(config_name)
        if not cfg or not cfg["apps"]:
            messagebox.showinfo("Info", "Aucune application à lancer.")
            return

        log_win = Dlg(self.root, f"Lancement – {config_name}", 600, 400)
        log = tk.Text(log_win.body, bg="#0a0d14", fg=TEXT, font=("Consolas",9),
                      relief="flat", state="disabled")
        log.pack(fill="both", expand=True)

        def write(msg):
            log.config(state="normal")
            log.insert("end", msg+"\n")
            log.see("end")
            log.config(state="disabled")

        def run():
            import time
            for app in cfg["apps"]:
                atype = app.get("type","")
                name  = app.get("name","?")
                write(f"▶ {name} [{atype}]…")
                try:
                    if atype == "Timer":
                        # Handle Timer type
                        seconds = int(app.get("seconds","0"))
                        write(f"  ⏱️ Attente de {seconds} seconde(s)...")
                        for i in range(seconds):
                            time.sleep(1)
                            remaining = seconds - i - 1
                            if remaining > 0:
                                write(f"  {remaining}s...")
                        write(f"  ✅ Délai écoulé - passage à l'app suivante")
                    else:
                        cmd = self._build_cmd(app)
                        if not cmd:
                            write(f"  ⚠ Type inconnu, ignoré.")
                            continue
                        write(f"  $ {cmd}")
                        # Launch in separate terminal window
                        full_cmd = f'start "App Launcher - {name}" cmd /k "{cmd}"'
                        subprocess.Popen(full_cmd, shell=True)
                        write(f"  ✅ Lancé dans un nouveau terminal")
                except Exception as ex:
                    write(f"  ❌ Erreur : {ex}")
            write("\n— Terminé —")

        threading.Thread(target=run, daemon=True).start()

    def _build_cmd(self, app):
        t = app.get("type","")
        if t == "Spring Boot":
            jar = app.get("jar","")
            rc  = app.get("run_config","").strip()
            return f'java -jar "{jar}" {rc}'.strip()
        elif t == "ActiveMQ":
            home = app.get("home","")
            return f'"{home}/bin/activemq" start'
        elif t == "Elasticsearch":
            home = app.get("home","")
            return f'"{home}/bin/elasticsearch"'
        elif t == "Podman":
            return f'podman start {app.get("container","")}'
        return None

# ─── DIALOG HELPER ───────────────────────────────────────────────────
class Dlg(tk.Toplevel):
    def __init__(self, parent, title, w, h):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=PANEL)
        self.resizable(False, False)
        # center
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width()  - w)//2
        y = parent.winfo_y() + (parent.winfo_height() - h)//2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.grab_set()
        self.body = tk.Frame(self, bg=PANEL, padx=16, pady=12)
        self.body.pack(fill="both", expand=True)

# ─── MAIN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    UI(root)
    root.mainloop()

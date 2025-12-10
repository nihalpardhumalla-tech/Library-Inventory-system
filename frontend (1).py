#!/usr/bin/env python3
"""
Production-ready single-file Online Library app.

Features:
- Optional mock Flask backend (background thread) prepopulated with 20 magazines.
- Tkinter frontend with crisp, high-resolution UI and clear fonts.
- Filter (All/Book/Magazine), search, add item (with Option A), delete (requires typing 'b' to confirm).
- Sequential serial numbers (1..N) that remain contiguous after add/delete.
- Headless smoke test (--no-gui) and mock backend (--mock).
"""

import os
import sys
import time
import uuid
import threading
import argparse
import atexit
from http import HTTPStatus

# Optional dependencies
try:
    from flask import Flask, jsonify, request
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

try:
    import requests
except Exception:
    requests = None

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageSequence

# ---------------- Configuration ----------------
DEFAULT_BACKEND_PORT = 5001
BACKEND_HOST = "127.0.0.1"
BACKEND_URL = os.environ.get("LIBRARY_BACKEND_URL", f"http://{BACKEND_HOST}:{DEFAULT_BACKEND_PORT}")

# ---------------- UI Theme & Fonts (sharp, subtle) ----------------
# Preferred font stack: Inter -> Segoe UI -> system sans
FONT_FAMILY = ("Inter", "Segoe UI", "Helvetica", "Arial")
FONT_TITLE = (FONT_FAMILY[0], 22, "bold")
FONT_NORMAL = (FONT_FAMILY[0], 11)
FONT_SMALL = (FONT_FAMILY[0], 10)
BG_MAIN = "#ffffff"        # white background
PANEL = "#f7f7f7"          # sidebar (light gray)
CARD = "#ffffff"           # card background (white)
TEXT = "#111111"           # dark text for contrast
SUBTEXT = "#555555"        # muted dark gray
ACCENT = "#f59e0b"         # amber/orange
BTN_OK = "#16a34a"
BTN_DANGER = "#ef4444"

# ---------------- Mock Backend Implementation ----------------
# The mock backend stores items in a list to preserve order and uses 1..N serials.
_mock_app = None
_mock_thread = None
_mock_shutdown = threading.Event()


def _create_mock_app():
    app = Flask("mock_library_backend")
    # store: list of dicts. Each dict has fields: id (int serial as string), name, author, publication_date, category, option_a (bool)
    store = []

    def _populate():
        # Empty database - no initial data
        pass

    _populate()

    @app.route("/media", methods=["GET"])
    def list_media():
        return jsonify(list(store)), HTTPStatus.OK

    @app.route("/media/category/<category>", methods=["GET"])
    def media_by_category(category):
        cat = category.strip().lower()
        filtered = [v for v in store if v.get("category", "").lower() == cat]
        return jsonify(filtered), HTTPStatus.OK

    @app.route("/media/search/<name>", methods=["GET"])
    def search_media(name):
        q = name.strip().lower()
        results = [v for v in store if q in (v.get("name", "").lower() + v.get("author", "").lower())]
        return jsonify(results), HTTPStatus.OK

    @app.route("/media/create", methods=["POST"])
    def create_media():
        data = request.get_json(force=True) or {}
        name = data.get("name", "").strip()
        author = data.get("author", "").strip() or "Unknown"
        pub = data.get("publication_date", "").strip() or ""
        category = data.get("category", "Book").strip() or "Book"
        option_a = bool(data.get("option_a", False))
        if not name:
            return jsonify({"error": "name is required"}), HTTPStatus.BAD_REQUEST
        # append new item
        store.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "author": author,
            "publication_date": pub,
            "category": category,
            "option_a": option_a
        })
        return jsonify(store[-1]), HTTPStatus.CREATED

    @app.route("/media/delete/<item_id>", methods=["DELETE"])
    def delete_media(item_id):
        nonlocal store
        found = False
        for i, v in enumerate(store):
            if str(v.get("id")) == str(item_id):
                found = True
                del store[i]
                break
        if not found:
            return jsonify({"error": "not found"}), HTTPStatus.NOT_FOUND
        return jsonify({"deleted": item_id}), HTTPStatus.OK

    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        _mock_shutdown.set()
        return jsonify({"status": "shutting down"}), HTTPStatus.OK

    app._store = store
    return app


def start_mock_backend(port=DEFAULT_BACKEND_PORT, host=BACKEND_HOST, wait=3.0):
    global _mock_app, _mock_thread, BACKEND_URL
    if not FLASK_AVAILABLE:
        raise RuntimeError("Flask not available. Install 'flask' to use --mock.")
    if _mock_app is not None:
        return
    _mock_app = _create_mock_app()

    def run():
        from werkzeug.serving import make_server
        srv = make_server(host, port, _mock_app)
        srv.timeout = 1
        srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
        srv_thread.start()
        try:
            while not _mock_shutdown.is_set():
                time.sleep(0.2)
        finally:
            try:
                srv.shutdown()
            except Exception:
                pass

    _mock_thread = threading.Thread(target=run, daemon=True)
    _mock_thread.start()

    url = f"http://{host}:{port}/media"
    deadline = time.time() + wait
    if requests is None:
        BACKEND_URL = f"http://{host}:{port}"
        return
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1)
            if r.ok:
                BACKEND_URL = f"http://{host}:{port}"
                return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Mock backend did not start in time")


def stop_mock_backend():
    global _mock_app
    if _mock_app is None:
        return
    try:
        try:
            requests.post(f"{BACKEND_URL}/shutdown", timeout=1)
        except Exception:
            pass
        _mock_shutdown.set()
    finally:
        _mock_app = None


atexit.register(stop_mock_backend)

# ---------------- Backend client helpers ----------------


def normalize_media_response(resp):
    """
    Normalize backend response (list or dict) into dict mapping id->item.
    """
    out = {}
    if not resp:
        return out
    if isinstance(resp, dict):
        # single object? wrap
        if "id" in resp:
            out[str(resp["id"])] = resp
            return out
        # else assume mapping already
        for k, v in resp.items():
            out[str(k)] = v
        return out
    if isinstance(resp, list):
        for item in resp:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or item.get("_id") or str(uuid.uuid4())
            out[str(item_id)] = item
        return out
    return out


class BackendClient:
    def __init__(self, base_url=None, timeout=4.0):
        self.base_url = (base_url or BACKEND_URL).rstrip("/")
        self.timeout = timeout

    def _url(self, path):
        return f"{self.base_url}/{path.lstrip('/')}"

    def _get(self, path):
        if requests is None:
            raise RuntimeError("requests required")
        try:
            r = requests.get(self._url(path), timeout=self.timeout)
            if r.ok:
                return r.json()
            return {}
        except requests.exceptions.RequestException:
            return None

    def _post(self, path, data):
        if requests is None:
            raise RuntimeError("requests required")
        try:
            r = requests.post(self._url(path), json=data, timeout=self.timeout)
            if r.ok or r.status_code == 201:
                return r.json()
            return {}
        except requests.exceptions.RequestException:
            return None

    def _delete(self, path):
        if requests is None:
            raise RuntimeError("requests required")
        try:
            r = requests.delete(self._url(path), timeout=self.timeout)
            if r.ok:
                return r.json()
            return {}
        except requests.exceptions.RequestException:
            return None

    def list_all(self):
        return normalize_media_response(self._get("/media") or [])

    def list_category(self, category):
        return normalize_media_response(self._get(f"/media/category/{category}") or [])

    def search(self, name):
        return normalize_media_response(self._get(f"/media/search/{requests.utils.requote_uri(name)}") or [])

    def create(self, name, author, date, category, option_a=False):
        payload = {
            "name": name,
            "author": author,
            "publication_date": date,
            "category": category,
            "option_a": bool(option_a)
        }
        return self._post("/media/create", payload)

    def delete(self, item_id):
        return self._delete(f"/media/delete/{item_id}")


# ---------------- GUI ----------------


class AnimatedGIFLabel(tk.Label):
    def __init__(self, master, path=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.sequence = []
        self.index = 0
        if not path:
            return
        try:
            if not os.path.exists(path):
                return
            im = Image.open(path)
            frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
            self.sequence = [ImageTk.PhotoImage(frame.resize((860, 140), Image.LANCZOS)) for frame in frames]
            if self.sequence:
                self.config(image=self.sequence[0], bg=BG_MAIN)
                self.after(120, self._animate)
        except Exception:
            self.sequence = []

    def _animate(self):
        if not self.sequence:
            return
        self.index = (self.index + 1) % len(self.sequence)
        self.config(image=self.sequence[self.index])
        self.after(120, self._animate)


class LibraryGUI:
    def __init__(self, root, client: BackendClient):
        self.root = root
        self.client = client
        self.root.title("LibraryDesk")
        self.root.geometry("1300x820")
        self.root.configure(bg=BG_MAIN)

        # apply a default font for widgets; some platforms will fallback
        try:
            root.option_add("*Font", "Inter 11")
        except Exception:
            pass

        # Header
        header = tk.Frame(root, bg=BG_MAIN)
        header.pack(fill="x", padx=12, pady=8)

        # Optional animated banner if you have library.gif in same folder
        banner = AnimatedGIFLabel(header, "library.gif", bg=BG_MAIN)
        if banner.sequence:
            banner.pack(pady=(0, 6))

        title_frame = tk.Frame(header, bg=BG_MAIN)
        title_frame.pack(fill="x", padx=6)
        tk.Label(title_frame, text="LibraryDesk", font=FONT_TITLE, bg=BG_MAIN, fg=TEXT).pack(anchor="w")
        tk.Label(title_frame, text="Bookstore & Media Manager", font=FONT_SMALL, bg=BG_MAIN, fg=SUBTEXT).pack(anchor="w")

        # Controls row
        controls = tk.Frame(root, bg=BG_MAIN)
        controls.pack(fill="x", padx=12, pady=8)

        tk.Label(controls, text="Filter:", bg=BG_MAIN, fg=SUBTEXT).grid(row=0, column=0, sticky="w")
        self.filter_var = tk.StringVar(value="All")
        self.filter_menu = ttk.Combobox(controls, textvariable=self.filter_var, values=["All", "Book", "Magazine"], state="readonly", width=12)
        self.filter_menu.grid(row=0, column=1, padx=(6, 12))
        self.filter_menu.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(controls, text="Search:", bg=BG_MAIN, fg=SUBTEXT).grid(row=0, column=2, sticky="w")
        self.search_var = tk.StringVar()
        se = tk.Entry(controls, textvariable=self.search_var, width=32)
        se.grid(row=0, column=3, padx=(6, 8))
        se.bind("<Return>", lambda e: self.on_search())

        search_btn = tk.Button(controls, text="Search", bg=ACCENT, fg="#000000", relief="flat", command=self.on_search)
        search_btn.grid(row=0, column=4, padx=(0, 8))

        refresh_btn = tk.Button(controls, text="Refresh", bg="#2b6cb0", fg="white", relief="flat", command=self.load_all)
        refresh_btn.grid(row=0, column=5, padx=(0, 8))

        # Main content
        content = tk.Frame(root, bg=BG_MAIN)
        content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Center: main table
        center_frame = tk.Frame(content, bg=BG_MAIN)
        center_frame.pack(side="left", fill="both", expand=True)

        # Top search bar area (already above), then table area
        table_card = tk.Frame(center_frame, bg=CARD)
        table_card.pack(fill="both", expand=True, padx=(0, 12), pady=(0, 6))

        # Using a simple Listbox of compact lines for high-res crisp text
        tk.Label(table_card, text="Catalog", bg=CARD, fg=TEXT, font=(FONT_FAMILY[0], 13, "bold")).pack(anchor="w", padx=10, pady=(8, 0))

        listbox_frame = tk.Frame(table_card, bg=CARD)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=8)

        # Scrollbar and listbox
        self.lb_scroll = tk.Scrollbar(listbox_frame)
        self.lb_scroll.pack(side="right", fill="y")
        self.listbox = tk.Listbox(listbox_frame, font=FONT_NORMAL, bg=CARD, fg=TEXT, selectbackground="#153e75",
                                  activestyle="none", yscrollcommand=self.lb_scroll.set, width=80, height=22)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.lb_scroll.config(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self.on_list_select)

        # Details & actions
        details_card = tk.Frame(center_frame, bg=CARD, height=120)
        details_card.pack(fill="x", padx=(0, 12))

        tk.Label(details_card, text="Details", bg=CARD, fg=TEXT, font=(FONT_FAMILY[0], 12, "bold")).pack(anchor="w", padx=8, pady=(8, 0))
        self.details_label = tk.Label(details_card, text="Select an item to view details", bg=CARD, fg=SUBTEXT, justify="left", anchor="w", font=FONT_NORMAL)
        self.details_label.pack(fill="x", padx=8, pady=(4, 8))

        action_row = tk.Frame(details_card, bg=CARD)
        action_row.pack(fill="x", padx=8, pady=(0, 8))
        self.delete_btn = tk.Button(action_row, text="DELETE", bg=BTN_DANGER, fg="white", relief="flat", command=self.open_delete_confirm)
        self.delete_btn.pack(side="left", padx=(0, 8))

        # Right: sidebar add form
        sidebar = tk.Frame(content, bg=PANEL, width=340)
        sidebar.pack(side="right", fill="y", pady=6, padx=(12, 0))

        tk.Label(sidebar, text="ADD NEW ITEM", bg=PANEL, fg=ACCENT, font=(FONT_FAMILY[0], 12, "bold")).pack(anchor="w", padx=18, pady=(14, 6))

        tk.Label(sidebar, text="Title", bg=PANEL, fg=TEXT).pack(anchor="w", padx=18)
        self.add_title = tk.Entry(sidebar, bg=CARD, fg=TEXT, insertbackground=TEXT, width=28)
        self.add_title.pack(padx=18, pady=(2, 8))

        tk.Label(sidebar, text="Creator", bg=PANEL, fg=TEXT).pack(anchor="w", padx=18)
        self.add_author = tk.Entry(sidebar, bg=CARD, fg=TEXT, insertbackground=TEXT, width=28)
        self.add_author.pack(padx=18, pady=(2, 8))

        tk.Label(sidebar, text="Category", bg=PANEL, fg=TEXT).pack(anchor="w", padx=18)
        self.add_category = ttk.Combobox(sidebar, values=["Book", "Magazine"], state="readonly", width=26)
        self.add_category.set("Book")
        self.add_category.pack(padx=18, pady=(2, 8))

        tk.Label(sidebar, text="Year", bg=PANEL, fg=TEXT).pack(anchor="w", padx=18)
        self.add_year = tk.Entry(sidebar, bg=CARD, fg=TEXT, insertbackground=TEXT, width=12)
        self.add_year.pack(padx=18, pady=(2, 8))

        add_btn = tk.Button(sidebar, text="ADD TO LIBRARY", bg=BTN_OK, fg="white", relief="flat", command=self.add_item_from_sidebar)
        add_btn.pack(padx=18, pady=(0, 12), fill="x")

        self.add_modal_btn = tk.Button(sidebar, text="+ Add (modal)", bg=ACCENT, fg="#000000", relief="flat", command=self.open_add_modal)
        self.add_modal_btn.pack(padx=18, fill="x", pady=(0, 12))

        self.status_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.status_var, bg=BG_MAIN, fg=SUBTEXT).pack(anchor="w", padx=12, pady=(0, 10))

        # Internal state
        self.media_data = {}    # id -> item
        self.visible_ids = []   # ordered visible ids for listbox indices
        self.selected_id = None

        # initial load
        self.load_all()

    # -------- Networking & data loading --------
    def set_status(self, txt):
        self.status_var.set(txt)

    def load_all(self):
        self.set_status("Loading...")
        data = self.client.list_all()
        if data is None:
            messagebox.showerror("Connection", f"Cannot reach backend at {self.client.base_url}")
            self.set_status("Offline")
            return
        # Keep media_data as the complete dataset (ordered by serial natural)
        # Sort by numeric id to preserve the expected serial order
        # data is dict mapping id->item; we want ordered by int(id)
        try:
            ordered_keys = sorted(data.keys(), key=lambda k: int(k))
        except Exception:
            ordered_keys = list(data.keys())
        self.media_data = {k: data[k] for k in ordered_keys}
        self.apply_filter()
        self.set_status(f"Loaded {len(self.media_data)} items")

    def apply_filter(self):
        filt = self.filter_var.get().strip()
        items = self.media_data
        if filt and filt != "All":
            items = {k: v for k, v in self.media_data.items() if v.get("category", "").lower() == filt.lower()}
        self.update_list(items)

    def on_search(self):
        q = self.search_var.get().strip()
        if not q:
            self.apply_filter()
            return
        self.set_status(f"Searching for '{q}'...")
        result = self.client.search(q)
        if result is None:
            messagebox.showerror("Connection", "Could not reach backend for search")
            self.set_status("Search failed")
            return
        # Replace media_data with search results; keep order by numeric id
        try:
            ordered = sorted(result.keys(), key=lambda k: int(k))
        except Exception:
            ordered = list(result.keys())
        self.media_data = {k: result[k] for k in ordered}
        self.update_list(self.media_data)
        self.set_status(f"Found {len(self.media_data)} results")

    def update_list(self, items):
        # items: dict id->item in desired order
        self.listbox.delete(0, tk.END)
        self.visible_ids = []
        for k, v in items.items():
            # display: Title only
            title = v.get("name", "Untitled")
            display = title
            self.listbox.insert(tk.END, display)
            self.visible_ids.append(k)
        self.selected_id = None
        self.details_label.config(text="Select an item to view details")

    def on_list_select(self, evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.visible_ids):
            return
        item_id = self.visible_ids[idx]
        self.selected_id = item_id
        item = self.media_data.get(item_id, {})
        txt = f"Title: {item.get('name','')}\nCreator: {item.get('author','')}\nYear: {item.get('publication_date','')}\nCategory: {item.get('category','')}"
        self.details_label.config(text=txt)

    # -------- Add from left sidebar (quick add) --------
    def add_item_from_sidebar(self):
        name = self.add_title.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Please enter a title")
            return
        author = self.add_author.get().strip() or "Unknown"
        pub = self.add_year.get().strip()
        cat = self.add_category.get().strip() or "Book"
        resp = self.client.create(name, author, pub, cat)
        if resp is None:
            messagebox.showerror("Network", "Could not reach backend to create item")
            return
        # Reset inputs lightly
        self.add_title.delete(0, tk.END)
        self.add_author.delete(0, tk.END)
        self.add_year.delete(0, tk.END)
        # reload to ensure contiguous serials shown
        self.load_all()
        messagebox.showinfo("Added", f"'{name}' added as {cat}")

    # -------- Add modal dialog (more explicit) --------
    def open_add_modal(self):
        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.title("Add Item")
        win.geometry("420x260")
        win.configure(bg=PANEL)
        tk.Label(win, text="Add new item", bg=PANEL, fg=ACCENT, font=(FONT_FAMILY[0], 12, "bold")).pack(anchor="w", padx=12, pady=(12, 6))

        frm = tk.Frame(win, bg=PANEL)
        frm.pack(fill="both", padx=12, pady=6)

        tk.Label(frm, text="Title", bg=PANEL, fg=TEXT).grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar()
        tk.Entry(frm, textvariable=name_var, width=44, bg=CARD, fg=TEXT, insertbackground=TEXT).grid(row=0, column=1, pady=4)

        tk.Label(frm, text="Author", bg=PANEL, fg=TEXT).grid(row=1, column=0, sticky="w")
        author_var = tk.StringVar()
        tk.Entry(frm, textvariable=author_var, width=44, bg=CARD, fg=TEXT, insertbackground=TEXT).grid(row=1, column=1, pady=4)

        tk.Label(frm, text="Year", bg=PANEL, fg=TEXT).grid(row=2, column=0, sticky="w")
        pub_var = tk.StringVar()
        tk.Entry(frm, textvariable=pub_var, width=18, bg=CARD, fg=TEXT, insertbackground=TEXT).grid(row=2, column=1, pady=4, sticky="w")

        tk.Label(frm, text="Category", bg=PANEL, fg=TEXT).grid(row=3, column=0, sticky="w")
        cat_var = tk.StringVar(value="Book")
        cat_menu = ttk.Combobox(frm, textvariable=cat_var, values=["Book", "Magazine"], width=20, state="readonly")
        cat_menu.grid(row=3, column=1, pady=4, sticky="w")

        # Option A removed from modal

        def submit():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Validation", "Title is required")
                return
            author = author_var.get().strip() or "Unknown"
            pub = pub_var.get().strip()
            cat = cat_var.get().strip() or "Book"
            resp = self.client.create(name, author, pub, cat)
            if resp is None:
                messagebox.showerror("Network", "Could not reach backend to create item")
                return
            win.destroy()
            self.load_all()
            messagebox.showinfo("Added", f"'{name}' added")

        tk.Button(win, text="Add Item", bg=BTN_OK, fg="white", relief="flat", command=submit).pack(pady=(8, 12))

    # -------- Delete flow with explicit 'b' confirm --------
    def open_delete_confirm(self):
        if not self.selected_id:
            messagebox.showwarning("No selection", "Please select an item to delete")
            return
        item = self.media_data.get(self.selected_id, {})
        name = item.get("name", "")
        # Open small confirm modal requiring typing 'b'
        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.title("Confirm Delete")
        win.geometry("360x160")
        win.configure(bg=PANEL)
        tk.Label(win, text="Confirm Delete", bg=PANEL, fg=ACCENT, font=(FONT_FAMILY[0], 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(win, text=f"Type the letter 'b' to confirm deletion of:\n'{name}'", bg=PANEL, fg=TEXT, justify="left").pack(anchor="w", padx=12)
        entry_var = tk.StringVar()
        entry = tk.Entry(win, textvariable=entry_var, width=6, bg=CARD, fg=TEXT, insertbackground=TEXT)
        entry.pack(padx=12, pady=(8, 4))
        entry.focus_set()

        def do_delete():
            val = entry_var.get().strip().lower()
            if val != "b":
                messagebox.showwarning("Wrong confirmation", "You must type the letter 'b' to confirm.")
                return
            resp = self.client.delete(self.selected_id)
            if resp is None:
                messagebox.showerror("Network", "Could not reach backend to delete item")
                return
            win.destroy()
            self.load_all()
            messagebox.showinfo("Deleted", f"'{name}' deleted")

        btn_frame = tk.Frame(win, bg=PANEL)
        btn_frame.pack(fill="x", padx=12, pady=(6, 8))
        tk.Button(btn_frame, text="Cancel", bg="#94a3b8", fg="white", relief="flat", command=win.destroy).pack(side="right", padx=(6, 0))
        tk.Button(btn_frame, text="Delete", bg=BTN_DANGER, fg="white", relief="flat", command=do_delete).pack(side="right")

# ---------------- Main ----------------


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Start local mock backend")
    parser.add_argument("--mock-port", type=int, default=DEFAULT_BACKEND_PORT)
    parser.add_argument("--no-gui", action="store_true", help="Run headless smoke test and exit")
    parser.add_argument("--backend-url", type=str, default=None, help="Custom backend URL")
    args = parser.parse_args()

    global BACKEND_URL
    if args.backend_url:
        BACKEND_URL = args.backend_url

    if args.mock:
        try:
            start_mock_backend(port=args.mock_port)
            BACKEND_URL = f"http://{BACKEND_HOST}:{args.mock_port}"
            print(f"Mock backend started at {BACKEND_URL}")
        except Exception as e:
            print("Failed to start mock backend:", e)
            sys.exit(1)

    client = BackendClient(base_url=BACKEND_URL)

    if args.no_gui:
        # headless test
        print("Running headless smoke test...")
        all_before = client.list_all()
        print("Loaded:", len(all_before))
        created = client.create("Smoke Test Book", "Tester", "2025", "Book", option_a=True)
        print("Create:", created)
        created_id = None
        if isinstance(created, dict):
            created_id = created.get("id")
        after = client.list_all()
        print("After create count:", len(after))
        if created_id:
            d = client.delete(created_id)
            print("Delete:", d)
        print("Final count:", len(client.list_all()))
        if args.mock:
            stop_mock_backend()
        return

    # launch GUI
    root = tk.Tk()
    try:
        root.option_add("*Font", "Inter 11")
    except Exception:
        pass
    app = LibraryGUI(root, client)

    def on_close():
        try:
            if args.mock:
                stop_mock_backend()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

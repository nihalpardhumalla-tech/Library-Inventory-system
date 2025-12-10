import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageSequence
import requests
import os

BASE_URL = "http://127.0.0.1:5000"

# ----------------------- Backend Helpers -----------------------

def safe_get(url):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else {}
    except:
        messagebox.showerror("Connection Error", "Could not reach backend server.")
        return {}

def safe_post(url, data):
    try:
        r = requests.post(url, json=data)
        return r.json() if r.status_code == 200 else {}
    except:
        messagebox.showerror("Connection Error", "Could not reach backend server.")
        return {}

def safe_delete(url):
    try:
        r = requests.delete(url)
        return r.json() if r.status_code == 200 else {}
    except:
        messagebox.showerror("Connection Error", "Could not reach backend server.")
        return {}

def load_all_media():
    return safe_get(f"{BASE_URL}/media")

def load_category_media(category):
    return safe_get(f"{BASE_URL}/media/category/{category}")

def search_media(name):
    return safe_get(f"{BASE_URL}/media/search/{name}")

def create_media(name, author, date, category):
    data = {
        "name": name,
        "author": author,
        "publication_date": date,
        "category": category
    }
    return safe_post(f"{BASE_URL}/media/create", data)

def delete_media(item_id):
    return safe_delete(f"{BASE_URL}/media/delete/{item_id}")


# ----------------------- GIF Animation -----------------------

class AnimatedGIFLabel(tk.Label):
    def __init__(self, master, path, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        try:
            if not os.path.exists(path):
                self.sequence = []
                self.config(text="")
                return

            self.sequence = [ImageTk.PhotoImage(img)
                             for img in ImageSequence.Iterator(Image.open(path))]

            if not self.sequence:
                self.config(text="")
                return

            self.index = 0
            self.config(image=self.sequence[0])
            self.animate()
        except:
            self.sequence = []
            self.config(text="")

    def animate(self):
        if not self.sequence:
            return
        self.index = (self.index + 1) % len(self.sequence)
        self.config(image=self.sequence[self.index])
        self.after(100, self.animate)


# ----------------------- Main GUI -----------------------

class LibraryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LegendaryOneApex Library")
        self.root.geometry("800x620")
        self.root.configure(bg="#020617")

        # ---------------- Banner ----------------
        self.banner = AnimatedGIFLabel(root, "library.gif", bg="#020617")
        self.banner.pack(pady=8)

        # ---------------- Title ----------------
        tk.Label(
            root,
            text="Online Library",
            font=("Segoe UI", 28, "bold"),
            bg="#020617",
            fg="#f59e0b"
        ).pack(pady=5)

        # ---------------- Top Controls ----------------
        top_card = tk.Frame(root, bg="#0b1220", bd=0)
        top_card.pack(fill="x", padx=20, pady=12)

        self.category_var = tk.StringVar()
        self.category_menu = ttk.Combobox(
            top_card,
            textvariable=self.category_var,
            values=["Book", "Film", "Magazine"],
            font=("Segoe UI", 11),
            width=14
        )
        self.category_menu.grid(row=0, column=0, padx=8)

        tk.Button(
            top_card,
            text="Filter",
            bg="#38bdf8",
            fg="black",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            command=self.filter_category
        ).grid(row=0, column=1, padx=6)

        self.search_var = tk.StringVar()
        tk.Entry(
            top_card,
            textvariable=self.search_var,
            width=22,
            font=("Segoe UI", 11),
            bg="#020617",
            fg="white",
            insertbackground="white",
            relief="flat"
        ).grid(row=0, column=2, padx=10)

        tk.Button(
            top_card,
            text="Search",
            bg="#38bdf8",
            fg="black",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            command=self.search_item
        ).grid(row=0, column=3, padx=6)

        # ---------------- Listbox ----------------
        self.media_list = tk.Listbox(
            root,
            width=90,
            height=15,
            font=("Segoe UI", 12),
            bg="#020617",
            fg="#e2e8f0",
            selectbackground="#38bdf8",
            selectforeground="black",
            borderwidth=0
        )
        self.media_list.pack(padx=20, pady=10)
        self.media_list.bind("<<ListboxSelect>>", self.show_details)

        # ---------------- Details Card ----------------
        self.details_label = tk.Label(
            root,
            text="Select a media item to view details",
            font=("Segoe UI", 12),
            bg="#0b1220",
            fg="#e2e8f0",
            justify="left",
            padx=10,
            pady=10,
            anchor="w"
        )
        self.details_label.pack(fill="x", padx=20, pady=8)

        # ---------------- Bottom Buttons ----------------
        bottom_card = tk.Frame(root, bg="#0b1220")
        bottom_card.pack(fill="x", padx=20, pady=10)

        tk.Button(
            bottom_card,
            text="➕ Add Book",
            width=14,
            bg="#22c55e",
            fg="black",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            cursor="hand2",
            command=self.add_media_window
        ).grid(row=0, column=0, padx=30)

        # --- Enhanced Delete Button ---
        self.delete_btn = tk.Button(
            bottom_card,
            text="🗑️ Delete Book",
            width=18,
            bg="#ff3b3b",
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            activebackground="#ff6b6b",
            activeforeground="white",
            cursor="hand2",
            command=self.remove_selected
        )
        self.delete_btn.grid(row=0, column=1, padx=30)

        # Hover glow effect
        self.delete_btn.bind("<Enter>", lambda e: self.delete_btn.config(bg="#ff6b6b"))
        self.delete_btn.bind("<Leave>", lambda e: self.delete_btn.config(bg="#ff3b3b"))

        self.media_data = {}
        self.show_all()

    # ---------------- Functions ----------------

    def show_all(self):
        self.media_data = load_all_media()
        self.update_list()

    def filter_category(self):
        category = self.category_var.get().strip()
        if not category:
            messagebox.showwarning("Warning", "Select a category")
            return
        self.media_data = load_category_media(category)
        self.update_list()

    def search_item(self):
        name = self.search_var.get().strip()
        if not name:
            messagebox.showwarning("Warning", "Enter a search term")
            return

        result = search_media(name)

        if not isinstance(result, dict) or not result:
            messagebox.showinfo("Not Found", "No matching book found.")
            return

        self.media_data = result
        self.update_list()

    def update_list(self):
        self.media_list.delete(0, tk.END)
        for item_id, info in self.media_data.items():
            title = info.get("name", "Untitled")
            self.media_list.insert(tk.END, f"{item_id}: {title}")

    def show_details(self, event):
        selection = self.media_list.curselection()
        if not selection:
            return

        index = selection[0]
        item_id = list(self.media_data.keys())[index]
        item = self.media_data[item_id]

        details = (
            f"ID: {item_id}\n"
            f"Name: {item.get('name')}\n"
            f"Author: {item.get('author')}\n"
            f"Publication Date: {item.get('publication_date')}\n"
            f"Category: {item.get('category')}"
        )
        self.details_label.config(text=details)

    # ---------------- Add Book Window ----------------

    def add_media_window(self):
        win = tk.Toplevel(self.root)
        win.title("Add Book")
        win.geometry("340x280")
        win.configure(bg="#020617")

        labels = ["Book Name", "Author", "Publication Date"]
        entries = []

        for text in labels:
            tk.Label(win, text=text, bg="#020617", fg="#e2e8f0", font=("Segoe UI", 10)).pack(pady=4)
            e = tk.Entry(win, font=("Segoe UI", 11), bg="#0b1220", fg="white", insertbackground="white")
            e.pack(pady=3)
            entries.append(e)

        name, author, date = entries
        forced_category = "Book"

        def submit():
            if not name.get().strip() or not author.get().strip():
                messagebox.showwarning("Warning", "Please fill all required fields.")
                return
            create_media(name.get(), author.get(), date.get(), forced_category)
            win.destroy()
            self.show_all()

        tk.Button(
            win,
            text="Add Book",
            bg="#22c55e",
            fg="black",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            command=submit
        ).pack(pady=12)

    # ---------------- Delete Logic ----------------

    def remove_selected(self):
        selection = self.media_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a book to delete.")
            return

        index = selection[0]
        item_id = list(self.media_data.keys())[index]

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this book?\nThis action cannot be undone."
        )
        if not confirm:
            return

        delete_media(item_id)
        self.show_all()


# ----------------------- Run App -----------------------

root = tk.Tk()
app = LibraryGUI(root)
root.mainloop()

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageSequence
import requests
import os

BASE_URL = "http://127.0.0.1:5000"

# ----------------------------- Backend Helpers -----------------------------

def safe_get(url):
    """Safe backend GET request returning dict always."""
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else {}
    except:
        messagebox.showerror("Connection Error", "Could not reach backend server.")
        return {}

def safe_post(url, data):
    """Safe backend POST request."""
    try:
        r = requests.post(url, json=data)
        return r.json() if r.status_code == 200 else {}
    except:
        messagebox.showerror("Connection Error", "Could not reach backend server.")
        return {}

def safe_delete(url):
    """Safe backend DELETE request."""
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


# ----------------------------- GIF Animation -----------------------------

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


# ----------------------------- Main GUI -----------------------------

class LibraryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Online Library")
        self.root.geometry("750x550")
        self.root.configure(bg="black")

        # ---------------- Banner ----------------
        self.banner = AnimatedGIFLabel(root, "library.gif", bg="black")
        self.banner.pack(pady=5)

        # ---------------- Title ----------------
        tk.Label(
            root,
            text="Online Library",
            font=("Helvetica Neue", 26, "bold"),
            bg="black",
            fg="white"
        ).pack(pady=10)

        # ---------------- Top Controls ----------------
        btn_frame = tk.Frame(root, bg="black")
        btn_frame.pack(pady=5)

        self.category_var = tk.StringVar()
        category_menu = ttk.Combobox(
            btn_frame,
            textvariable=self.category_var,
            values=["Book", "Film", "Magazine"],
            width=15,
            font=("Helvetica", 11)
        )
        category_menu.grid(row=0, column=0, padx=6)

        tk.Button(
            btn_frame,
            text="Filter",
            width=10,
            bg="#4da6ff",
            fg="black",
            command=self.filter_category
        ).grid(row=0, column=1, padx=5)

        # Search Entry
        self.search_var = tk.StringVar()
        tk.Entry(
            btn_frame,
            textvariable=self.search_var,
            width=20,
            font=("Helvetica", 11),
            bg="#1a1a1a",
            fg="white",
            insertbackground="white"
        ).grid(row=0, column=2, padx=6)

        tk.Button(
            btn_frame,
            text="Search",
            width=10,
            bg="#4da6ff",
            fg="black",
            command=self.search_item
        ).grid(row=0, column=3, padx=5)

        # ---------------- Media List ----------------
        self.media_list = tk.Listbox(
            root,
            width=75,
            height=15,
            font=("Helvetica", 12),
            bg="#1a1a1a",
            fg="white",
            selectbackground="#4da6ff",
            selectforeground="black",
            borderwidth=0
        )
        self.media_list.pack(pady=10)
        self.media_list.bind("<<ListboxSelect>>", self.show_details)

        # ---------------- Details Label ----------------
        self.details_label = tk.Label(
            root,
            text="Select a media item to view details",
            font=("Helvetica", 12),
            bg="black",
            fg="white"
        )
        self.details_label.pack(pady=5)

        # ---------------- Bottom Buttons ----------------
        bottom_frame = tk.Frame(root, bg="black")
        bottom_frame.pack(pady=10)

        tk.Button(
            bottom_frame,
            text="Add Book",
            width=12,
            bg="#4da6ff",
            fg="black",
            command=self.add_media_window
        ).grid(row=0, column=0, padx=15)

        tk.Button(
            bottom_frame,
            text="Delete Book",
            width=12,
            bg="#ff4d4d",
            fg="white",
            command=self.remove_selected
        ).grid(row=0, column=1, padx=15)

        self.media_data = {}
        self.show_all()

    # ---------------- Core Functions ----------------

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
            messagebox.showwarning("Warning", "Enter a name to search")
            return

        result = search_media(name)

        # Fix: Ensure result always becomes a dictionary
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

    # ---------------- Add Book ----------------

    def add_media_window(self):
        win = tk.Toplevel(self.root)
        win.title("Add Book")
        win.geometry("320x250")
        win.configure(bg="black")

        labels = ["Book Name", "Author", "Publication Date"]
        entries = []

        for text in labels:
            tk.Label(win, text=text, bg="black", fg="white").pack(pady=3)
            e = tk.Entry(win, font=("Helvetica", 11), bg="#1a1a1a", fg="white", insertbackground="white")
            e.pack()
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

        tk.Button(win, text="Add Book", bg="#4da6ff", fg="black", command=submit).pack(pady=10)

    # ---------------- Delete Book ----------------

    def remove_selected(self):
        selection = self.media_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select an item to delete")
            return

        index = selection[0]
        item_id = list(self.media_data.keys())[index]

        delete_media(item_id)
        self.show_all()


# ----------------------------- Run App -----------------------------
root = tk.Tk()
app = LibraryGUI(root)
root.mainloop()

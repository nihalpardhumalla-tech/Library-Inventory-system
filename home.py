import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageSequence
import requests
import os

BASE_URL = "http://127.0.0.1:5000"  # Backend URL

# ----------------------------------------------------------
# Helper functions to call backend API
# ----------------------------------------------------------

def load_all_media():
    try:
        r = requests.get(f"{BASE_URL}/media", timeout=3)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect to backend: {e}")
        return {}

def load_category_media(category):
    try:
        r = requests.get(f"{BASE_URL}/media/category/{category}", timeout=3)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect to backend: {e}")
        return {}

def search_media(name):
    try:
        r = requests.get(f"{BASE_URL}/media/search/{name}", timeout=3)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect to backend: {e}")
        return {}

def create_media(name, author, date, category):
    data = {
        "name": name,
        "author": author,
        "publication_date": date,
        "category": category
    }
    try:
        r = requests.post(f"{BASE_URL}/media/create", json=data, timeout=3)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect to backend: {e}")
        return {}

def delete_media(item_id):
    try:
        r = requests.delete(f"{BASE_URL}/media/delete/{item_id}", timeout=3)
        return r.json()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot connect to backend: {e}")
        return {}

# ----------------------------------------------------------
# Animated GIF Label (with graceful fallback)
# ----------------------------------------------------------

class AnimatedGIFLabel(tk.Label):
    """Label that can display an animated GIF, with fallback for missing files"""
    def __init__(self, master, path=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.sequence = []
        self.image_index = 0
        
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
                self.sequence = [ImageTk.PhotoImage(frame) for frame in frames]
                if self.sequence:
                    self.config(image=self.sequence[0])
                    self.after(100, self.animate)
            except Exception:
                # GIF loading failed, leave as blank label
                pass

    def animate(self):
        if not self.sequence:
            return
        self.image_index = (self.image_index + 1) % len(self.sequence)
        try:
            self.config(image=self.sequence[self.image_index])
        except Exception:
            return
        self.after(100, self.animate)

# ----------------------------------------------------------
# GUI Application
# ----------------------------------------------------------

class LibraryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📚 Online Library")
        self.root.geometry("750x550")
        self.root.configure(bg="#fef9f9")  # light pastel background

        # ---------- Animated banner (optional) ----------
        self.banner = AnimatedGIFLabel(root, "library.gif", bg="#fef9f9")
        self.banner.pack(pady=5)

        # ---------- Title ----------
        title = tk.Label(root, text="Online Library", font=("Helvetica Neue", 22, "bold"), bg="#fef9f9", fg="#4B4B4B")
        title.pack(pady=10)

        # ---------- Buttons & Search ----------
        btn_frame = tk.Frame(root, bg="#fef9f9")
        btn_frame.pack(pady=5)

        self.style_buttons(btn_frame)

        # Category Dropdown
        self.category_var = tk.StringVar()
        category_menu = ttk.Combobox(btn_frame, textvariable=self.category_var, values=["Book", "Magazine"], width=15, font=("Helvetica", 11))
        category_menu.grid(row=0, column=1, padx=5)

        tk.Button(btn_frame, text="Filter", width=10, command=self.filter_category, bg="#ffdfba", fg="#333").grid(row=0, column=2)

        # Search box
        self.search_var = tk.StringVar()
        tk.Entry(btn_frame, textvariable=self.search_var, width=20, font=("Helvetica", 11)).grid(row=0, column=3, padx=5)
        tk.Button(btn_frame, text="Search", command=self.search_item, bg="#baffc9", fg="#333").grid(row=0, column=4)

        # ---------- Media List ----------
        self.media_list = tk.Listbox(root, width=75, height=15, font=("Helvetica", 12), bg="#fff2f2", fg="#333", selectbackground="#ffcccc")
        self.media_list.pack(pady=10)
        self.media_list.bind("<<ListboxSelect>>", self.show_details)

        # ---------- Details area ----------
        self.details_label = tk.Label(root, text="Select a media to see details", font=("Helvetica Neue", 12), bg="#fef9f9", fg="#333")
        self.details_label.pack(pady=5)

        # ---------- Add / Delete ----------
        bottom_frame = tk.Frame(root, bg="#fef9f9")
        bottom_frame.pack(pady=10)

        tk.Button(bottom_frame, text="Add Book", command=self.add_media_window, bg="#c1f0f6", fg="#333").grid(row=0, column=0, padx=10)
        tk.Button(bottom_frame, text="Delete Book", command=self.remove_selected, bg="#f7c6c7", fg="#333").grid(row=0, column=1, padx=10)

        self.media_data = {}
        
        # Load initial data
        try:
            self.show_all()
        except Exception:
            pass

    # ---------- Button Styling ----------
    def style_buttons(self, frame):
        for widget in frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(bg="#d4f1f9", fg="#333", font=("Helvetica", 11), relief="flat", activebackground="#aee1f9", activeforeground="#000")

    # ----------------------------------------------------
    # Functions for actions
    # ----------------------------------------------------

    def show_all(self):
        self.media_data = load_all_media()
        self.update_list()

    def filter_category(self):
        category = self.category_var.get()
        if not category:
            messagebox.showwarning("Warning", "Select a category")
            return
        self.media_data = load_category_media(category)
        self.update_list()

    def search_item(self):
        name = self.search_var.get()
        if not name:
            messagebox.showwarning("Warning", "Enter a name to search")
            return
        result = search_media(name)
        if "error" in result:
            messagebox.showinfo("Not Found", "Media not found")
        else:
            self.media_data = result
            self.update_list()

    def update_list(self):
        self.media_list.delete(0, tk.END)
        for item_id, info in self.media_data.items():
            self.media_list.insert(tk.END, f"{info['name']} ({info['category']})")

    def show_details(self, event):
        selection = self.media_list.curselection()
        if not selection:
            return
        index = selection[0]
        item_id = list(self.media_data.keys())[index]
        item = self.media_data[item_id]

        details = (
            f"ID: {item_id}\n"
            f"Name: {item['name']}\n"
            f"Author: {item['author']}\n"
            f"Publication Date: {item['publication_date']}\n"
            f"Category: {item['category']}"
        )
        self.details_label.config(text=details)

    def add_media_window(self):
        win = tk.Toplevel(self.root)
        win.title("Add Book")
        win.geometry("320x240")
        win.configure(bg="#fef9f9")

        tk.Label(win, text="Book Name", bg="#fef9f9").pack(pady=2)
        name = tk.Entry(win, font=("Helvetica", 11))
        name.pack()

        tk.Label(win, text="Author", bg="#fef9f9").pack(pady=2)
        author = tk.Entry(win, font=("Helvetica", 11))
        author.pack()

        tk.Label(win, text="Publication Date", bg="#fef9f9").pack(pady=2)
        date = tk.Entry(win, font=("Helvetica", 11))
        date.pack()

        category = "Book"

        def submit():
            if not name.get().strip() or not author.get().strip():
                messagebox.showwarning("Warning", "Please provide both Book Name and Author")
                return
            create_media(name.get(), author.get(), date.get(), category)
            win.destroy()
            self.show_all()
            messagebox.showinfo("Success", "Book added successfully!")

        tk.Button(win, text="Add Book", command=submit, bg="#c1f0f6", font=("Helvetica", 11)).pack(pady=10)

    def remove_selected(self):
        selection = self.media_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "No item selected")
            return
        index = selection[0]
        item_id = list(self.media_data.keys())[index]
        delete_media(item_id)
        self.show_all()
        messagebox.showinfo("Success", "Book deleted successfully!")


# ----------------------------------------------------------
# Run GUI
# ----------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryGUI(root)
    root.mainloop()

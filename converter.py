"""Unified GUI: PDF <-> Images

Provides a small Tkinter application with two tabs:
- "PDF -> Images": pick a PDF, optionally point to Poppler, and extract pages as PNGs.
- "Images -> PDF": pick a folder or files and combine them into a single PDF.

"""
from __future__ import annotations

import os
import threading
import traceback
import sys
from typing import List, Optional, Sequence

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception:  # pragma: no cover - UI requires tkinter
    print("tkinter is required to run the GUI.")
    raise

try:
    from PIL import Image
except Exception:  # pragma: no cover - runtime error will be shown in GUI
    Image = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None


def convert_pdf_to_images(pdf_path: str, poppler_path: Optional[str], output_dir: str) -> int:
    pdf_path = os.path.abspath(pdf_path)
    output_dir = os.path.abspath(output_dir)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    if convert_from_path is None:
        raise RuntimeError("pdf2image is not installed")

    pages = convert_from_path(pdf_path=pdf_path, poppler_path=poppler_path)
    counter = 1
    for page in pages:
        img_name = f"page_{counter}.png"
        page.save(os.path.join(output_dir, img_name), "PNG")
        counter += 1
    return counter - 1


def images_to_pdf(images_dir: str, output_pdf: str, exts: Sequence[str]) -> str:
    images_dir = os.path.abspath(images_dir)
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Input directory not found: {images_dir}")

    files = [f for f in os.listdir(images_dir) if f.lower().endswith(tuple(exts))]
    if not files:
        raise FileNotFoundError(f"No images found in {images_dir} with extensions {exts}")

    files.sort()
    imgs: List[Image.Image] = []
    for fname in files:
        path = os.path.join(images_dir, fname)
        im = Image.open(path)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "RGBA":
                bg.paste(im, mask=im.split()[3])
            else:
                bg.paste(im)
            im = bg
        else:
            im = im.convert("RGB")
        imgs.append(im)

    output_pdf = os.path.abspath(output_pdf)
    output_dir = os.path.dirname(output_pdf)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    first, rest = imgs[0], imgs[1:]
    first.save(output_pdf, "PDF", resolution=100.0, save_all=True, append_images=rest)
    return output_pdf


def images_to_pdf_from_files(file_paths: Sequence[str], output_pdf: str) -> str:
    if not file_paths:
        raise FileNotFoundError("No image files provided")
    imgs: List[Image.Image] = []
    for path in file_paths:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "RGBA":
                bg.paste(im, mask=im.split()[3])
            else:
                bg.paste(im)
            im = bg
        else:
            im = im.convert("RGB")
        imgs.append(im)

    output_pdf = os.path.abspath(output_pdf)
    output_dir = os.path.dirname(output_pdf)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    first, rest = imgs[0], imgs[1:]
    first.save(output_pdf, "PDF", resolution=100.0, save_all=True, append_images=rest)
    return output_pdf


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Arnold Tools — PDF/Image Utilities")

        nb = ttk.Notebook(root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # --- Tab 1: PDF -> Images ---
        tab1 = ttk.Frame(nb)
        nb.add(tab1, text="PDF → Images")

        ttk.Label(tab1, text="PDF file:").grid(row=0, column=0, sticky=tk.W)
        self.pdf_entry = tk.Entry(tab1, width=60)
        self.pdf_entry.grid(row=0, column=1, padx=6, pady=4)
        ttk.Button(tab1, text="Browse...", command=self.browse_pdf).grid(row=0, column=2, padx=4)

        ttk.Label(tab1, text="Poppler bin (required):").grid(row=1, column=0, sticky=tk.W)
        self.poppler_entry = tk.Entry(tab1, width=60)
        self.poppler_entry.grid(row=1, column=1, padx=6, pady=4)
        ttk.Button(tab1, text="Browse...", command=self.browse_poppler).grid(row=1, column=2, padx=4)

        ttk.Label(tab1, text="Output folder:").grid(row=2, column=0, sticky=tk.W)
        self.out_folder_entry = tk.Entry(tab1, width=60)
        self.out_folder_entry.grid(row=2, column=1, padx=6, pady=4)
        ttk.Button(tab1, text="Browse...", command=self.browse_out_folder).grid(row=2, column=2, padx=4)

        self.open_out_var1 = tk.BooleanVar(value=True)
        ttk.Checkbutton(tab1, text="Open folder when done", variable=self.open_out_var1).grid(row=3, column=1, sticky=tk.W)

        self.status1 = tk.StringVar(value="Ready")
        ttk.Label(tab1, textvariable=self.status1).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(6,0))

        ttk.Button(tab1, text="Convert", command=self.start_pdf_to_images).grid(row=3, column=2, padx=4)





        # --- Tab 2: Images -> PDF ---
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="Images → PDF")

        ttk.Label(tab2, text="Input folder or files:").grid(row=0, column=0, sticky=tk.W)
        self.input_entry = tk.Entry(tab2, width=60)
        self.input_entry.grid(row=0, column=1, padx=6, pady=4)
        #ttk.Button(tab2, text="Browse folder", command=self.browse_images_folder).grid(row=0, column=2, padx=4)
        ttk.Button(tab2, text="Browse files", command=self.browse_images_files).grid(row=0, column=2, padx=4)

        ttk.Label(tab2, text="Output PDF:").grid(row=2, column=0, sticky=tk.W)
        self.output_pdf_entry = tk.Entry(tab2, width=60)
        self.output_pdf_entry.grid(row=2, column=1, padx=6, pady=4)
        ttk.Button(tab2, text="Browse...", command=self.browse_output_pdf).grid(row=2, column=2, padx=4)

        self.open_out_var2 = tk.BooleanVar(value=True)
        ttk.Checkbutton(tab2, text="Open folder when done", variable=self.open_out_var2).grid(row=3, column=1, sticky=tk.W)

        self.status2 = tk.StringVar(value="Ready")
        ttk.Label(tab2, textvariable=self.status2).grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(6,0))

        ttk.Button(tab2, text="Convert", command=self.start_images_to_pdf).grid(row=3, column=2, padx=4)

        # sensible defaults
        here = os.path.dirname(os.path.abspath(__file__))
        default_pdf = os.path.join(os.path.dirname(here), "SAMPLE PAGE.pdf")
        default_out_folder = os.path.join(here, "Converted images")
        default_output_pdf = os.path.join(here, "combined_images.pdf")

        if os.path.exists(default_pdf):
            self.pdf_entry.insert(0, default_pdf)
        self.out_folder_entry.insert(0, default_out_folder)
        self.output_pdf_entry.insert(0, default_output_pdf)

    # --- Browsers ---
    def browse_pdf(self) -> None:
        p = filedialog.askopenfilename(title="Select PDF file", filetypes=[("PDF files", "*.pdf")])
        if p:
            self.pdf_entry.delete(0, tk.END)
            self.pdf_entry.insert(0, p)

    def browse_poppler(self) -> None:
        p = filedialog.askdirectory(title="Select Poppler 'bin' folder (contains DLLs)")
        if p:
            self.poppler_entry.delete(0, tk.END)
            self.poppler_entry.insert(0, p)

    def browse_out_folder(self) -> None:
        p = filedialog.askdirectory(title="Select output folder for images")
        if p:
            self.out_folder_entry.delete(0, tk.END)
            self.out_folder_entry.insert(0, p)

    def browse_images_folder(self) -> None:
        p = filedialog.askdirectory(title="Select folder containing images")
        if p:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, p)

    def browse_images_files(self) -> None:
        files = filedialog.askopenfilenames(title="Select image files",
                                            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff")])
        if files:
            self.input_entry.delete(0, tk.END)
            # store semicolon-separated list
            self.input_entry.insert(0, ";".join(files))

    def browse_output_pdf(self) -> None:
        p = filedialog.asksaveasfilename(title="Select output PDF", defaultextension=".pdf",
                                         filetypes=[("PDF file", "*.pdf")])
        if p:
            self.output_pdf_entry.delete(0, tk.END)
            self.output_pdf_entry.insert(0, p)

    # --- Actions (background threads) ---
    def start_pdf_to_images(self) -> None:
        pdf = self.pdf_entry.get().strip()
        poppler = self.poppler_entry.get().strip() or None
        out = self.out_folder_entry.get().strip()
        open_when_done = bool(self.open_out_var1.get())

        if not pdf:
            messagebox.showerror("Error", "Please select a PDF file.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output folder.")
            return

        self.status1.set("Converting...")
        self.root.update_idletasks()

        def worker():
            try:
                count = convert_pdf_to_images(pdf, poppler, out)
                self.status1.set(f"Done — {count} pages saved to {out}")
                if open_when_done:
                    try:
                        os.startfile(out)
                    except Exception:
                        pass
            except Exception as exc:
                traceback.print_exc()
                messagebox.showerror("Error", f"Conversion failed: {exc}")
                self.status1.set(f"Error: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def start_images_to_pdf(self) -> None:
        inp = self.input_entry.get().strip()
        out = self.output_pdf_entry.get().strip()
        open_when_done = bool(self.open_out_var2.get())

        if not inp:
            messagebox.showerror("Error", "Please select an input folder or files.")
            return
        if not out:
            messagebox.showerror("Error", "Please select an output PDF path.")
            return

        self.status2.set("Converting...")
        self.root.update_idletasks()

        def worker():
            try:
                if os.path.isdir(inp):
                    result = images_to_pdf(inp, out, [".png", ".jpg", ".jpeg"])
                else:
                    files = [p for p in inp.split(';') if p]
                    files = [f for f in files if os.path.isfile(f)]
                    if not files:
                        raise FileNotFoundError("No valid image files found")
                    result = images_to_pdf_from_files(files, out)

                self.status2.set(f"Done — wrote PDF: {result}")
                if open_when_done:
                    try:
                        os.startfile(os.path.dirname(result) or os.getcwd())
                    except Exception:
                        pass
            except Exception as exc:
                traceback.print_exc()
                messagebox.showerror("Error", f"Conversion failed: {exc}")
                self.status2.set(f"Error: {exc}")

        threading.Thread(target=worker, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

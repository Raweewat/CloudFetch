import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    import tkinter as tk
    from gui.main_window import MainWindow

    root = tk.Tk()
    root.title("CloudFetch — Cloud Storage Downloader")

    width, height = 980, 820
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{(sw - width) // 2}+{(sh - height) // 2}")
    root.minsize(820, 650)

    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

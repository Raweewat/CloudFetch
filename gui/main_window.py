import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import queue
import os
from datetime import datetime

from gui.styles import COLORS, FONTS
from core.download_manager import DownloadManager


# ---------------------------------------------------------------------------
# Small reusable widget helpers
# ---------------------------------------------------------------------------

class _Btn(tk.Button):
    """Flat coloured button with hover effect."""

    def __init__(self, parent, text, command, bg, hover, fg="white", **kw):
        font = kw.pop("font", FONTS["button"])
        padx = kw.pop("padx", 14)
        pady = kw.pop("pady", 7)
        super().__init__(
            parent, text=text, command=command,
            bg=bg, fg=fg, font=font,
            relief="flat", cursor="hand2",
            padx=padx, pady=pady,
            activebackground=hover, activeforeground=fg,
            **kw,
        )
        self.bg, self.hover = bg, hover
        self.bind("<Enter>", lambda _: self.config(bg=self.hover))
        self.bind("<Leave>", lambda _: self.config(bg=self.bg))

    def set_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        bg = self.bg if enabled else COLORS["disabled"]
        self.config(state=state, bg=bg)
        self.hover = self.bg if enabled else COLORS["disabled"]


class _SectionFrame(tk.LabelFrame):
    """Styled LabelFrame for each config section."""

    def __init__(self, parent, title, **kw):
        super().__init__(
            parent, text=f"  {title}  ",
            font=FONTS["heading"],
            fg=COLORS["primary"],
            bg=COLORS["bg"],
            bd=1, relief="solid",
            padx=10, pady=6,
            **kw,
        )


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.configure(bg=COLORS["bg"])

        # --- state ---
        self.cloud_var = tk.StringVar(value="azure")
        self.sim_var = tk.BooleanVar(value=True)
        self.output_dir_var = tk.StringVar(value=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Azure credentials
        self.az_mode_var = tk.StringVar(value="connstr")
        self.az_connstr_var = tk.StringVar()
        self.az_account_var = tk.StringVar()
        self.az_key_var = tk.StringVar()

        # Huawei credentials
        self.hw_ak_var = tk.StringVar()
        self.hw_sk_var = tk.StringVar()
        self.hw_endpoint_var = tk.StringVar()

        self.task_rows: list = []
        self.var_rows: list = []

        self._log_q: queue.Queue = queue.Queue()
        self._prog_q: queue.Queue = queue.Queue()
        self._manager = None

        self._build_ui()
        self._add_task_row()           # start with one blank task
        self._process_queues()         # start queue poller

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()

        # Central pane: scrollable config (top) + log (bottom)
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        # log/progress at bottom (pack before config so it anchors bottom)
        self._build_progress_section(body)
        self._build_control_bar(body)

        # scrollable config fills rest
        self._build_scrollable_config(body)

    # --- header ---

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=COLORS["header_bg"], height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(
            hdr, text="☁  CloudFetch",
            font=FONTS["title"],
            fg=COLORS["header_text"], bg=COLORS["header_bg"],
        ).pack(side="left", padx=18, pady=10)

        tk.Label(
            hdr, text="Cloud Storage Download Tool  v1.0",
            font=FONTS["subtitle"],
            fg="#90CAF9", bg=COLORS["header_bg"],
        ).pack(side="left", pady=10)

        # Simulation badge
        sim_chk = tk.Checkbutton(
            hdr, text="  Simulation Mode",
            variable=self.sim_var,
            font=FONTS["label"],
            fg="#FFE082", bg=COLORS["header_bg"],
            selectcolor=COLORS["header_bg"],
            activebackground=COLORS["header_bg"],
            activeforeground="#FFE082",
            cursor="hand2",
        )
        sim_chk.pack(side="right", padx=20)

    # --- scrollable config area ---

    def _build_scrollable_config(self, parent):
        container = tk.Frame(parent, bg=COLORS["bg"])
        container.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(container, orient="vertical")
        sb.pack(side="right", fill="y")

        self._canvas = tk.Canvas(
            container, bg=COLORS["bg"],
            yscrollcommand=sb.set, highlightthickness=0,
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        sb.config(command=self._canvas.yview)

        self._inner = tk.Frame(self._canvas, bg=COLORS["bg"])
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw"
        )

        self._inner.bind(
            "<Configure>",
            lambda _: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")
            ),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(self._win_id, width=e.width),
        )
        self._canvas.bind("<MouseWheel>", self._scroll_canvas)

        # --- build config sections ---
        self._build_cloud_section(self._inner)
        self._build_variables_section(self._inner)
        self._build_tasks_section(self._inner)
        self._build_output_section(self._inner)

        # padding at bottom of scroll area
        tk.Frame(self._inner, bg=COLORS["bg"], height=12).pack()

        # bind scroll to all child widgets after layout is done
        self.root.after(150, self._rebind_scroll)

    # --- Cloud & Credentials ---

    def _build_cloud_section(self, parent):
        sec = _SectionFrame(parent, "☁  Cloud & Credentials")
        sec.pack(fill="x", padx=14, pady=(12, 4))

        top = tk.Frame(sec, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 8))

        tk.Label(top, text="Cloud Provider:", font=FONTS["label_bold"],
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(side="left", padx=(0, 10))

        self._az_btn = tk.Radiobutton(
            top, text="  Azure Blob Storage  ",
            variable=self.cloud_var, value="azure",
            command=self._on_cloud_change,
            font=FONTS["button"],
            fg="white", bg=COLORS["azure"],
            selectcolor=COLORS["azure_hover"],
            activebackground=COLORS["azure_hover"], activeforeground="white",
            indicator=0, relief="flat",
            padx=10, pady=6, cursor="hand2",
        )
        self._az_btn.pack(side="left", padx=(0, 6))

        self._hw_btn = tk.Radiobutton(
            top, text="  Huawei OBS  ",
            variable=self.cloud_var, value="huawei",
            command=self._on_cloud_change,
            font=FONTS["button"],
            fg=COLORS["text"], bg=COLORS["surface"],
            selectcolor=COLORS["huawei"],
            activebackground=COLORS["surface"], activeforeground=COLORS["text"],
            indicator=0, relief="flat",
            bd=1, padx=10, pady=6, cursor="hand2",
        )
        self._hw_btn.pack(side="left")

        # dynamic credentials frame
        self._cred_frame = tk.Frame(sec, bg=COLORS["bg"])
        self._cred_frame.pack(fill="x")
        self._build_azure_credentials(self._cred_frame)

    def _build_azure_credentials(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        # Mode toggle
        mode_row = tk.Frame(parent, bg=COLORS["bg"])
        mode_row.pack(fill="x", pady=(0, 6))

        for text, val in [("Connection String", "connstr"), ("Account Name + Key", "key")]:
            tk.Radiobutton(
                mode_row, text=text,
                variable=self.az_mode_var, value=val,
                command=self._on_az_mode_change,
                font=FONTS["small"], fg=COLORS["text_secondary"],
                bg=COLORS["bg"], selectcolor=COLORS["primary_light"],
                activebackground=COLORS["bg"], cursor="hand2",
            ).pack(side="left", padx=(0, 14))

        self._az_cred_inner = tk.Frame(parent, bg=COLORS["bg"])
        self._az_cred_inner.pack(fill="x")
        self._on_az_mode_change()

    def _on_az_mode_change(self):
        for w in self._az_cred_inner.winfo_children():
            w.destroy()

        if self.az_mode_var.get() == "connstr":
            self._lbl_entry(
                self._az_cred_inner,
                "Connection String:", self.az_connstr_var,
                show=None, hint="DefaultEndpointsProtocol=https;AccountName=…",
            )
        else:
            self._lbl_entry(self._az_cred_inner, "Account Name:", self.az_account_var,
                            hint="mystorageaccount")
            self._lbl_entry(self._az_cred_inner, "Account Key:", self.az_key_var,
                            show="*", hint="Base64-encoded key…")

    def _build_huawei_credentials(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        self._lbl_entry(parent, "Access Key (AK):", self.hw_ak_var,
                        hint="AKIAIOSFODNN7EXAMPLE")
        self._lbl_entry(parent, "Secret Key (SK):", self.hw_sk_var,
                        show="*", hint="wJalrXUtnFEMI/K7MDENG/…")
        self._lbl_entry(parent, "Endpoint:", self.hw_endpoint_var,
                        hint="obs.ap-southeast-1.myhuaweicloud.com")

    def _on_cloud_change(self):
        cloud = self.cloud_var.get()
        # update button visual states
        if cloud == "azure":
            self._az_btn.config(fg="white", bg=COLORS["azure"])
            self._hw_btn.config(fg=COLORS["text"], bg=COLORS["surface"])
            self._build_azure_credentials(self._cred_frame)
        else:
            self._hw_btn.config(fg="white", bg=COLORS["huawei"])
            self._az_btn.config(fg=COLORS["text"], bg=COLORS["surface"])
            self._build_huawei_credentials(self._cred_frame)

    # --- Variables section ---

    def _build_variables_section(self, parent):
        sec = _SectionFrame(parent, "📌  Variables  (ตัวแปรสำหรับใช้ใน Pattern เช่น {date})")
        sec.pack(fill="x", padx=14, pady=4)

        hdr = tk.Frame(sec, bg=COLORS["bg"])
        hdr.pack(fill="x", pady=(0, 4))

        tk.Label(hdr, text="กำหนดตัวแปรเพื่อใช้ใน Filename Pattern เช่น  date=20240101  แล้วใช้  {date}  ใน Task",
                 font=FONTS["small"], fg=COLORS["text_secondary"],
                 bg=COLORS["bg"]).pack(side="left")

        _Btn(hdr, "+ Add Variable", self._add_variable_row,
             bg=COLORS["primary"], hover=COLORS["primary_hover"],
             font=FONTS["small"], padx=10, pady=4,
             ).pack(side="right")

        self._var_container = tk.Frame(sec, bg=COLORS["bg"])
        self._var_container.pack(fill="x")

    # --- Tasks section ---

    def _build_tasks_section(self, parent):
        self._task_sec = _SectionFrame(parent, "📥  Download Tasks")
        self._task_sec.pack(fill="x", padx=14, pady=4)

        hdr = tk.Frame(self._task_sec, bg=COLORS["bg"])
        hdr.pack(fill="x", pady=(0, 6))

        tip = ("Filename Pattern รองรับ * Wildcard และ {variable}  "
               "เช่น:  report_{date}.csv  หรือ  data_*_{date}.parquet  "
               "หรือเว้นว่างไว้เพื่อโหลดทุกไฟล์ใน Path")
        tk.Label(hdr, text=tip, font=FONTS["small"],
                 fg=COLORS["text_secondary"], bg=COLORS["bg"],
                 wraplength=700, justify="left").pack(side="left")

        _Btn(hdr, "+ Add Task", self._add_task_row,
             bg=COLORS["primary"], hover=COLORS["primary_hover"],
             font=FONTS["small"], padx=10, pady=4,
             ).pack(side="right")

        self._task_container = tk.Frame(self._task_sec, bg=COLORS["bg"])
        self._task_container.pack(fill="x")

    # --- Output section ---

    def _build_output_section(self, parent):
        sec = _SectionFrame(parent, "📁  Output Directory")
        sec.pack(fill="x", padx=14, pady=4)

        row = tk.Frame(sec, bg=COLORS["bg"])
        row.pack(fill="x")

        tk.Label(row, text="บันทึกไฟล์ไปที่:", font=FONTS["label"],
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(side="left", padx=(0, 8))

        e = tk.Entry(row, textvariable=self.output_dir_var,
                     font=FONTS["input_bold"], fg=COLORS["text"],
                     relief="solid", bd=1, bg=COLORS["surface"])
        e.pack(side="left", fill="x", expand=True)

        _Btn(row, "Browse…", self._browse_output,
             bg=COLORS["primary"], hover=COLORS["primary_hover"],
             font=FONTS["small"], padx=10, pady=4,
             ).pack(side="left", padx=(8, 0))

        tk.Label(
            sec,
            text="ไฟล์จะถูกจัดเก็บใน:  <Output Dir> / Result / DDMMYYYY / Path_As_Folder /   เช่น  C:\\CloudFetch / Result / 07052026 / Data_EDW_05062026 /",
            font=FONTS["small"], fg=COLORS["text_secondary"], bg=COLORS["bg"],
        ).pack(anchor="w", pady=(4, 0))

    # --- Control bar ---

    def _build_control_bar(self, parent):
        bar = tk.Frame(parent, bg=COLORS["surface"], bd=0)
        bar.pack(fill="x", side="bottom")

        sep = tk.Frame(bar, bg=COLORS["border"], height=1)
        sep.pack(fill="x")

        inner = tk.Frame(bar, bg=COLORS["surface"])
        inner.pack(pady=8, padx=16, fill="x")

        self._run_btn = _Btn(
            inner, "▶  Run Download", self._run_download,
            bg=COLORS["primary"], hover=COLORS["primary_hover"],
            font=FONTS["button_lg"], padx=24, pady=10,
        )
        self._run_btn.pack(side="left")

        self._stop_btn = _Btn(
            inner, "■  Stop", self._stop_download,
            bg=COLORS["stop"], hover=COLORS["stop_hover"],
            font=FONTS["button"], padx=14, pady=10,
        )
        self._stop_btn.pack(side="left", padx=(10, 0))
        self._stop_btn.set_enabled(False)

        self._status_lbl = tk.Label(
            inner, text="Ready", font=FONTS["label"],
            fg=COLORS["text_secondary"], bg=COLORS["surface"],
        )
        self._status_lbl.pack(side="right", padx=4)

    # --- Progress + Log ---

    def _build_progress_section(self, parent):
        pane = tk.Frame(parent, bg=COLORS["surface"])
        pane.pack(fill="x", side="bottom")

        tk.Frame(pane, bg=COLORS["border"], height=1).pack(fill="x")

        prog_row = tk.Frame(pane, bg=COLORS["surface"])
        prog_row.pack(fill="x", padx=14, pady=(6, 2))

        tk.Label(prog_row, text="Progress:", font=FONTS["label"],
                 bg=COLORS["surface"], fg=COLORS["text"]).pack(side="left")

        self._prog_bar = ttk.Progressbar(
            prog_row, orient="horizontal", mode="determinate", length=300
        )
        self._prog_bar.pack(side="left", padx=(8, 12))

        self._prog_lbl = tk.Label(prog_row, text="0%", font=FONTS["small"],
                                  bg=COLORS["surface"], fg=COLORS["text_secondary"])
        self._prog_lbl.pack(side="left")

        log_frame = tk.Frame(pane, bg=COLORS["surface"])
        log_frame.pack(fill="both", expand=False, padx=14, pady=(0, 8))

        self._log_text = scrolledtext.ScrolledText(
            log_frame, height=9,
            font=FONTS["mono"],
            bg="#1E1E2E", fg="#CDD6F4",
            insertbackground="white",
            relief="flat", bd=0,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True)

        # colour tags
        self._log_text.tag_config("info", foreground="#CDD6F4")
        self._log_text.tag_config("success", foreground="#A6E3A1")
        self._log_text.tag_config("warning", foreground="#FAB387")
        self._log_text.tag_config("error", foreground="#F38BA8")

    # -----------------------------------------------------------------------
    # Dynamic row builders
    # -----------------------------------------------------------------------

    def _add_variable_row(self, name="", value=""):
        row = {"name_var": tk.StringVar(value=name), "value_var": tk.StringVar(value=value)}

        f = tk.Frame(self._var_container, bg=COLORS["bg"])
        f.pack(fill="x", pady=2)
        row["frame"] = f

        tk.Label(f, text="Name:", font=FONTS["label"], bg=COLORS["bg"],
                 fg=COLORS["text"]).pack(side="left", padx=(0, 4))
        e1 = self._hint_entry(f, row["name_var"], hint="ชื่อตัวแปร เช่น date", width=18)
        e1.pack(side="left", padx=(0, 6))

        tk.Label(f, text="=  Value:", font=FONTS["label"], bg=COLORS["bg"],
                 fg=COLORS["text"]).pack(side="left", padx=(0, 4))
        e2 = self._hint_entry(f, row["value_var"], hint="ค่า เช่น 20240101", width=22)
        e2.pack(side="left", padx=(0, 6))

        del_btn = _Btn(f, "✕", lambda r=row: self._delete_variable_row(r),
                       bg=COLORS["error"], hover="#B71C1C",
                       font=FONTS["small"], padx=6, pady=3)
        del_btn.pack(side="left")

        self.var_rows.append(row)
        self.root.after(50, self._rebind_scroll)

    def _delete_variable_row(self, row):
        row["frame"].destroy()
        self.var_rows.remove(row)

    def _add_task_row(self, bucket="", path="", filename=""):
        num = len(self.task_rows) + 1
        row = {
            "bucket_var": tk.StringVar(value=bucket),
            "path_var": tk.StringVar(value=path),
            "filename_var": tk.StringVar(value=filename),
        }

        outer = tk.Frame(
            self._task_container, bg=COLORS["surface"],
            relief="solid", bd=1,
        )
        outer.pack(fill="x", pady=(0, 6))
        row["frame"] = outer

        # title bar
        title_bar = tk.Frame(outer, bg=COLORS["primary_light"])
        title_bar.pack(fill="x")

        self._task_num_lbl = tk.Label(
            title_bar, text=f"  Task #{num}",
            font=FONTS["label_bold"], fg=COLORS["primary"],
            bg=COLORS["primary_light"],
        )
        self._task_num_lbl.pack(side="left", pady=3)

        del_btn = _Btn(
            title_bar, "✕ Remove", lambda r=row: self._delete_task_row(r),
            bg=COLORS["error"], hover="#B71C1C",
            font=FONTS["small"], padx=8, pady=3,
        )
        del_btn.pack(side="right", padx=4, pady=2)

        # inputs
        fields = tk.Frame(outer, bg=COLORS["surface"])
        fields.pack(fill="x", padx=10, pady=8)

        # Row 1: Bucket + Path
        r1 = tk.Frame(fields, bg=COLORS["surface"])
        r1.pack(fill="x", pady=(0, 4))
        self._field(r1, "Bucket / Container:", row["bucket_var"],
                    hint="my-container", width=22)
        tk.Frame(r1, bg=COLORS["surface"], width=12).pack(side="left")
        self._field(r1, "Cloud Path / Prefix:", row["path_var"],
                    hint="data/reports/2024/", fill=True)

        # Row 2: Filename Pattern
        r2 = tk.Frame(fields, bg=COLORS["surface"])
        r2.pack(fill="x")
        self._field(r2, "Filename Pattern:", row["filename_var"],
                    hint="report_{date}.csv  หรือ  *_{date}.parquet  หรือเว้นว่าง = ทั้งหมด",
                    fill=True)

        self.task_rows.append(row)
        self._renumber_tasks()
        self.root.after(50, self._rebind_scroll)

    def _delete_task_row(self, row):
        row["frame"].destroy()
        self.task_rows.remove(row)
        self._renumber_tasks()

    def _renumber_tasks(self):
        # rebuild task numbers isn't straightforward with internal label refs;
        # we keep it simple and don't renumber here.
        pass

    # -----------------------------------------------------------------------
    # Utility widget builders
    # -----------------------------------------------------------------------

    def _lbl_entry(self, parent, label, var, show=None, hint=""):
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, font=FONTS["label"], bg=COLORS["bg"],
                 fg=COLORS["text"], width=20, anchor="w").pack(side="left")
        e = self._hint_entry(row, var, hint=hint, show=show)
        e.pack(side="left", fill="x", expand=True)

    def _field(self, parent, label, var, hint="", width=None, fill=False):
        tk.Label(parent, text=label, font=FONTS["label"],
                 bg=parent.cget("bg"), fg=COLORS["text"]).pack(side="left", padx=(0, 4))
        kw = {}
        if width:
            kw["width"] = width
        e = self._hint_entry(parent, var, hint=hint, **kw)
        if fill:
            e.pack(side="left", fill="x", expand=True)
        else:
            e.pack(side="left")

    def _hint_entry(self, parent, var, hint="", show=None, **kw):
        """
        Entry widget ที่แสดง placeholder hint สีอ่อน (font ปกติ) เมื่อว่าง
        และแสดง text ที่ user พิมพ์เป็นตัวหนา (Bold) สีเข้ม
        ไม่ใช้ textvariable เพื่อแยก hint ออกจากค่าจริง
        """
        base_font = FONTS["input"]
        bold_font = FONTS["input_bold"]

        e = tk.Entry(parent, font=base_font, relief="solid", bd=1,
                     bg=COLORS["surface"], **kw)

        initial = var.get()
        if initial:
            if show:
                e.config(show=show)
            e.insert(0, initial)
            e.config(fg=COLORS["text"], font=bold_font)
        elif hint:
            e.insert(0, hint)
            e.config(fg=COLORS["disabled"], font=base_font)

        def _is_hint():
            return bool(hint) and e.get() == hint and not var.get()

        def on_focus_in(event):
            if _is_hint():
                e.delete(0, "end")
                if show:
                    e.config(show=show)
                e.config(fg=COLORS["text"], font=bold_font)

        def on_focus_out(event):
            val = e.get().strip()
            if not val:
                var.set("")
                if show:
                    e.config(show="")
                if hint:
                    e.delete(0, "end")
                    e.insert(0, hint)
                e.config(fg=COLORS["disabled"], font=base_font)
            else:
                var.set(val)
                e.config(fg=COLORS["text"], font=bold_font)

        def on_key(event):
            val = e.get()
            if val:
                e.config(fg=COLORS["text"], font=bold_font)
                var.set(val)
            else:
                var.set("")

        e.bind("<FocusIn>", on_focus_in)
        e.bind("<FocusOut>", on_focus_out)
        e.bind("<KeyRelease>", on_key)
        return e

    def _scroll_canvas(self, event):
        self._canvas.yview_scroll(int(-1 * event.delta / 120), "units")

    def _rebind_scroll(self, widget=None):
        """Bind MouseWheel recursively to all widgets inside the scrollable area."""
        target = widget if widget is not None else self._inner
        try:
            target.bind("<MouseWheel>", self._scroll_canvas)
        except Exception:
            pass
        for child in target.winfo_children():
            self._rebind_scroll(child)

    # -----------------------------------------------------------------------
    # Action handlers
    # -----------------------------------------------------------------------

    def _browse_output(self):
        d = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if d:
            self.output_dir_var.set(d)

    def _get_config(self) -> dict:
        variables = {
            r["name_var"].get().strip(): r["value_var"].get().strip()
            for r in self.var_rows
            if r["name_var"].get().strip()
        }
        tasks = [
            {
                "bucket": r["bucket_var"].get().strip(),
                "path": r["path_var"].get().strip(),
                "filename": r["filename_var"].get().strip(),
            }
            for r in self.task_rows
            if r["bucket_var"].get().strip()
        ]

        cloud = self.cloud_var.get()
        if cloud == "azure":
            if self.az_mode_var.get() == "connstr":
                credentials = {"connection_string": self.az_connstr_var.get().strip()}
            else:
                credentials = {
                    "account_name": self.az_account_var.get().strip(),
                    "account_key": self.az_key_var.get().strip(),
                }
        else:
            credentials = {
                "access_key": self.hw_ak_var.get().strip(),
                "secret_key": self.hw_sk_var.get().strip(),
                "endpoint": self.hw_endpoint_var.get().strip(),
            }

        return {
            "cloud_type": cloud,
            "credentials": credentials,
            "variables": variables,
            "tasks": tasks,
            "output_dir": self.output_dir_var.get().strip(),
            "simulation": self.sim_var.get(),
        }

    def _validate_config(self, cfg: dict) -> str:
        if not cfg["tasks"]:
            return "กรุณาเพิ่มอย่างน้อย 1 Task พร้อมระบุ Bucket ก่อนรัน"
        if not cfg["output_dir"]:
            return "กรุณาระบุ Output Directory"
        if not cfg["simulation"]:
            c = cfg["credentials"]
            if cfg["cloud_type"] == "azure":
                has = c.get("connection_string") or (c.get("account_name") and c.get("account_key"))
                if not has:
                    return "กรุณาระบุ Azure Credentials (Connection String หรือ Account Name+Key)"
            else:
                if not (c.get("access_key") and c.get("secret_key") and c.get("endpoint")):
                    return "กรุณาระบุ Huawei OBS Credentials ให้ครบ (AK, SK, Endpoint)"
        return ""

    def _run_download(self):
        cfg = self._get_config()
        err = self._validate_config(cfg)
        if err:
            messagebox.showwarning("Validation Error", err)
            return

        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

        self._prog_bar["value"] = 0
        self._prog_lbl.config(text="0%")

        mode = "SIMULATION" if cfg["simulation"] else cfg["cloud_type"].upper()
        self._append_log(
            f"=== CloudFetch started [{mode}] @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===",
            "info",
        )

        self._run_btn.set_enabled(False)
        self._stop_btn.set_enabled(True)
        self._status_lbl.config(text="Running…", fg=COLORS["primary"])

        self._manager = DownloadManager(
            config=cfg,
            log_callback=lambda msg, lvl="info": self._log_q.put((msg, lvl)),
            progress_callback=lambda pct, st: self._prog_q.put((pct, st)),
            done_callback=lambda result: self._log_q.put(("__DONE__", result)),
        )
        self._manager.run_in_thread()

    def _stop_download(self):
        if self._manager:
            self._manager.stop()
        self._stop_btn.set_enabled(False)
        self._status_lbl.config(text="Stopping…", fg=COLORS["warning"])

    # -----------------------------------------------------------------------
    # Queue processor (runs on main thread via after())
    # -----------------------------------------------------------------------

    def _process_queues(self):
        # progress queue
        while not self._prog_q.empty():
            pct, status = self._prog_q.get_nowait()
            self._prog_bar["value"] = pct
            self._prog_lbl.config(text=f"{int(pct)}%")
            self._status_lbl.config(text=status, fg=COLORS["text_secondary"])

        # log queue
        while not self._log_q.empty():
            item = self._log_q.get_nowait()
            if item[0] == "__DONE__":
                self._on_download_done(item[1])
            else:
                self._append_log(*item)

        self.root.after(80, self._process_queues)

    def _append_log(self, message: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        self._log_text.config(state="normal")
        self._log_text.insert("end", line, level)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _on_download_done(self, result: dict):
        self._run_btn.set_enabled(True)
        self._stop_btn.set_enabled(False)
        self._status_lbl.config(text="Complete", fg=COLORS["success"])

        total_dl = result.get("total_dl", 0)
        total_fail = result.get("total_fail", 0)
        failed_paths = result.get("failed_paths", [])
        report_path = result.get("report_path")
        result_dir = result.get("result_dir", "")

        self._append_log(
            f"\n=== Download Complete ===  Downloaded: {total_dl}  |  Failed: {total_fail}",
            "success" if total_fail == 0 else "warning",
        )

        self._show_notification(total_dl, total_fail, failed_paths, report_path, result_dir)

    def _show_notification(self, total_dl, total_fail, failed_paths, report_path, result_dir):
        # Try system notification via plyer
        try:
            from plyer import notification
            notification.notify(
                title="CloudFetch — Download Complete",
                message=(
                    f"Downloaded: {total_dl} file(s)\n"
                    f"Failed: {total_fail} file(s)"
                ),
                app_name="CloudFetch",
                timeout=8,
            )
        except Exception:
            pass  # fall through to messagebox

        # Always show summary dialog
        lines = [f"✅  Downloaded  :  {total_dl} file(s)"]

        if total_fail:
            lines.append(f"❌  Failed       :  {total_fail} file(s)")
            lines.append(f"⚠️  Affected Paths : {len(failed_paths)}")
            for p in failed_paths[:5]:
                lines.append(f"     • {p}")
            if len(failed_paths) > 5:
                lines.append(f"     … and {len(failed_paths) - 5} more")
            if report_path:
                lines.append(f"\n📄  Report saved:\n    {report_path}")
        else:
            lines.append("🎉  All files downloaded successfully!")

        if result_dir:
            lines.append(f"\n📁  Output folder:\n    {result_dir}")

        messagebox.showinfo("CloudFetch — Complete", "\n".join(lines))

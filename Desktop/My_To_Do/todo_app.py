# Neon CLI To-Do with Calendar
# Requires: tkcalendar (pip install tkcalendar)

import csv
import json
import random
import shlex
import shutil
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import font as tkfont

try:
    from tkcalendar import Calendar
except ImportError as exc:
    raise SystemExit(
        "tkcalendar is required. Install it with: pip install tkcalendar"
    ) from exc


COLOR_BG = "#050505"
NEON_GREEN = "#39ff14"
NEON_PINK = "#ff2dfd"
NEON_BLUE = "#00e5ff"
NEON_YELLOW = "#faff00"
NEON_ORANGE = "#ff8c00"
DIM_TEXT = "#8cffc1"
ERROR_RED = "#ff4d4d"
DATA_FILE = Path("tasks.json")
STATS_FILE = Path("stats.json")
AUTOSYNC_DIR = Path("autosync")
CSV_DEFAULT = Path("tasks.csv")
PRIORITY_ORDER = {"high": 0, "med": 1, "low": 2, None: 3}
THEMES = {
    "cyber": {
        "bg": "#050505",
        "green": "#39ff14",
        "pink": "#ff2dfd",
        "blue": "#00e5ff",
        "yellow": "#faff00",
        "orange": "#ff8c00",
        "dim": "#8cffc1",
        "error": "#ff4d4d",
    },
    "toxic": {
        "bg": "#040907",
        "green": "#7CFF00",
        "pink": "#00FFD5",
        "blue": "#00B4FF",
        "yellow": "#A6FF00",
        "orange": "#4DFF8A",
        "dim": "#6BFFB2",
        "error": "#FF5858",
    },
    "ember": {
        "bg": "#0a0604",
        "green": "#FF6A00",
        "pink": "#FF1E56",
        "blue": "#FFB347",
        "yellow": "#FFDD55",
        "orange": "#FF7A00",
        "dim": "#FFB199",
        "error": "#FF3B3B",
    },
}


class TaskManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Neon To-Do CLI + Calendar")
        self.geometry("1150x720")
        self.minsize(980, 640)
        self.configure(bg=COLOR_BG)

        self.tasks = []
        self.next_id = 1
        self.view_mode = "all"
        self.view_value = None
        self.visible_tasks = []
        self.text_filter = ""
        self.sort_key = "due"
        self.sort_reverse = False
        self.hide_completed = False
        self.undo_stack = []
        self.redo_stack = []
        self.notified = set()
        self._resize_job = None
        self._matrix_job = None
        self._glass_canvases = {}
        self.theme_name = "cyber"
        self._theme_widgets = []
        self._calendar_widgets = []
        self._cal_tooltip = None
        self._cal_tooltip_label = None
        self._hover_job = None
        self.calendar_mode = "month"
        self.drag_task = None
        self.focus_mode = False
        self.stats = {"completed_dates": [], "daily_goal": 3}
        self.pomo_task_id = None
        self.pomo_remaining = 0
        self.pomo_job = None

        self._init_fonts()
        self._load_stats()
        self._load_tasks()
        self._build_ui()
        self._bind_events()
        self._refresh_all("Ready. Type 'help' for commands.")
        self._schedule_reminders()
        self._start_effects()

    def _init_fonts(self):
        preferred = ["Orbitron", "Press Start 2P", "Share Tech Mono", "Consolas", "Courier New"]
        available = set(tkfont.families(self))
        family = next((f for f in preferred if f in available), "Courier New")

        self.font_title = tkfont.Font(family=family, size=14, weight="bold")
        self.font_text = tkfont.Font(family=family, size=11)
        self.font_small = tkfont.Font(family=family, size=9)
        self.font_completed = tkfont.Font(family=family, size=11, overstrike=1)

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.bg_canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0, bd=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bg_canvas.tk.call("lower", self.bg_canvas._w)

        hud_frame = tk.Frame(
            self,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        self.hud_frame = hud_frame
        hud_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        hud_frame.grid_columnconfigure(0, weight=1)
        hud_frame.grid_columnconfigure(1, weight=0)

        self.hud_label = tk.Label(
            hud_frame,
            text="SYS // NEON TASK CORE :: ACTIVE",
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        self.hud_label.grid(row=0, column=0, sticky="w", padx=8, pady=6)

        hud_right = tk.Frame(hud_frame, bg=COLOR_BG)
        hud_right.grid(row=0, column=1, sticky="e", padx=8, pady=4)

        self.led_canvas = tk.Canvas(
            hud_right, width=60, height=18, bg=COLOR_BG, highlightthickness=0
        )
        self.led_canvas.grid(row=0, column=0, padx=(0, 10))

        self.signal_canvas = tk.Canvas(
            hud_right, width=60, height=18, bg=COLOR_BG, highlightthickness=0
        )
        self.signal_canvas.grid(row=0, column=1, padx=(0, 10))

        self.progress_canvas = tk.Canvas(
            hud_right, width=28, height=28, bg=COLOR_BG, highlightthickness=0
        )
        self.progress_canvas.grid(row=0, column=2, padx=(0, 10))

        self.time_label = tk.Label(
            hud_right,
            text="--:--:--",
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_PINK,
        )
        self.time_label.grid(row=0, column=3, sticky="e")

        self.streak_label = tk.Label(
            hud_frame,
            text="STREAK 0 | GOAL 0/0",
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
        )
        self.streak_label.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

        self.pomo_label = tk.Label(
            hud_frame,
            text="POMO --:--",
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_YELLOW,
        )
        self.pomo_label.grid(row=1, column=1, sticky="e", padx=8, pady=(0, 6))

        main = tk.Frame(self, bg=COLOR_BG)
        self.main_frame = main
        main.grid(row=1, column=0, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)

        cal_frame = tk.Frame(
            main,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        self.cal_frame = cal_frame
        cal_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=12, pady=12)
        cal_frame.grid_rowconfigure(1, weight=1)
        cal_frame.grid_columnconfigure(0, weight=1)

        cal_title = tk.Label(
            cal_frame,
            text="[ CALENDAR ]",
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        cal_title.grid(row=0, column=0, sticky="ew", pady=(6, 4))

        cal_controls = tk.Frame(cal_frame, bg=COLOR_BG)
        cal_controls.grid(row=0, column=1, sticky="e", padx=6)
        cal_controls.grid_columnconfigure(0, weight=1)
        self._create_button(cal_controls, "DAY", lambda: self._set_calendar_mode("day"), NEON_BLUE).grid(
            row=0, column=0, padx=2
        )
        self._create_button(cal_controls, "WEEK", lambda: self._set_calendar_mode("week"), NEON_BLUE).grid(
            row=0, column=1, padx=2
        )
        self._create_button(cal_controls, "MONTH", lambda: self._set_calendar_mode("month"), NEON_BLUE).grid(
            row=0, column=2, padx=2
        )

        today = date.today()
        self.calendar = Calendar(
            cal_frame,
            selectmode="day",
            year=today.year,
            month=today.month,
            day=today.day,
            font=self.font_small,
            background=COLOR_BG,
            foreground=NEON_GREEN,
            bordercolor=NEON_BLUE,
            headersbackground=COLOR_BG,
            headersforeground=NEON_PINK,
            selectbackground=NEON_PINK,
            selectforeground=COLOR_BG,
            normalbackground=COLOR_BG,
            normalforeground=NEON_GREEN,
            weekendbackground=COLOR_BG,
            weekendforeground=NEON_ORANGE,
            othermonthbackground=COLOR_BG,
            othermonthforeground=NEON_BLUE,
            disableddaybackground=COLOR_BG,
            disableddayforeground=DIM_TEXT,
            showweeknumbers=False,
        )
        self.calendar.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.calendar.tag_config("task", background=NEON_PINK, foreground=COLOR_BG)
        self.calendar.tag_config("today", background=NEON_BLUE, foreground=COLOR_BG)

        self.selected_date_label = tk.Label(
            cal_frame,
            text=f"Selected: {self._format_date(today)}",
            font=self.font_small,
            bg=COLOR_BG,
            fg=DIM_TEXT,
        )
        self.selected_date_label.grid(row=2, column=0, sticky="ew", pady=(2, 8))

        tasks_frame = tk.Frame(
            main,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_GREEN,
        )
        self.tasks_frame = tasks_frame
        tasks_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=(12, 6))
        tasks_frame.grid_rowconfigure(2, weight=1)
        tasks_frame.grid_columnconfigure(0, weight=1)

        tasks_title = tk.Label(
            tasks_frame,
            text="[ TASKS ]",
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_GREEN,
        )
        tasks_title.grid(row=0, column=0, sticky="ew", pady=(6, 4))

        control_frame = tk.Frame(tasks_frame, bg=COLOR_BG)
        self.control_frame = control_frame
        control_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        control_frame.grid_columnconfigure(1, weight=1)

        self.stats_label = tk.Label(
            control_frame,
            text="Stats: --",
            font=self.font_small,
            bg=COLOR_BG,
            fg=DIM_TEXT,
        )
        self.stats_label.grid(row=0, column=0, sticky="w")

        self.countdown_label = tk.Label(
            control_frame,
            text="Next due: --",
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_YELLOW,
        )
        self.countdown_label.grid(row=1, column=0, sticky="w")

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            control_frame,
            textvariable=self.search_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(10, 6))

        self._create_button(control_frame, "TODAY", self._cmd_today, NEON_BLUE).grid(
            row=0, column=2, padx=2
        )
        self._create_button(control_frame, "WEEK", self._cmd_week, NEON_BLUE).grid(
            row=0, column=3, padx=2
        )
        self._create_button(control_frame, "OVERDUE", self._cmd_overdue, NEON_PINK).grid(
            row=0, column=4, padx=2
        )
        self._create_button(control_frame, "ALL", self._cmd_list, NEON_GREEN).grid(
            row=0, column=5, padx=2
        )
        self._create_button(control_frame, "HIDE DONE", self._toggle_hide_completed, NEON_YELLOW).grid(
            row=0, column=6, padx=2
        )
        self._create_button(control_frame, "FOCUS", self._cmd_focus, NEON_BLUE).grid(
            row=1, column=6, padx=2, pady=(4, 0)
        )

        self.timeline_canvas = tk.Canvas(
            control_frame,
            height=24,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        self.timeline_canvas.grid(row=2, column=0, columnspan=7, sticky="ew", pady=(6, 0))

        task_body = tk.Frame(tasks_frame, bg=COLOR_BG)
        self.task_body = task_body
        task_body.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        task_body.grid_rowconfigure(0, weight=1)
        task_body.grid_columnconfigure(0, weight=1)

        self.task_text = tk.Text(
            task_body,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            font=self.font_text,
            wrap="word",
            bd=0,
            highlightthickness=0,
            selectbackground=NEON_BLUE,
            selectforeground=COLOR_BG,
        )
        self.task_text.tag_config("pending", foreground=NEON_GREEN)
        self.task_text.tag_config("completed", foreground=NEON_BLUE, font=self.font_completed)
        self.task_text.tag_config("header", foreground=NEON_PINK)
        self.task_text.tag_config("priority", foreground=NEON_YELLOW)
        self.task_text.tag_config("priority", foreground=NEON_YELLOW)
        self.task_text.grid(row=0, column=0, sticky="nsew")
        self.task_text.configure(state="disabled")

        task_scroll = tk.Scrollbar(task_body, command=self.task_text.yview)
        task_scroll.grid(row=0, column=1, sticky="ns")
        self.task_text.configure(yscrollcommand=task_scroll.set)

        log_frame = tk.Frame(
            main,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_PINK,
        )
        self.log_frame = log_frame
        log_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 12), pady=(6, 12))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_title = tk.Label(
            log_frame,
            text="[ CONSOLE ]",
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_PINK,
        )
        log_title.grid(row=0, column=0, sticky="ew", pady=(6, 4))

        log_body = tk.Frame(log_frame, bg=COLOR_BG)
        self.log_body = log_body
        log_body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        log_body.grid_rowconfigure(0, weight=1)
        log_body.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_body,
            bg=COLOR_BG,
            fg=DIM_TEXT,
            insertbackground=NEON_GREEN,
            font=self.font_small,
            wrap="word",
            bd=0,
            highlightthickness=0,
            height=8,
            selectbackground=NEON_BLUE,
            selectforeground=COLOR_BG,
        )
        self.log_text.tag_config("info", foreground=DIM_TEXT)
        self.log_text.tag_config("cmd", foreground=NEON_YELLOW)
        self.log_text.tag_config("success", foreground=NEON_GREEN)
        self.log_text.tag_config("error", foreground=ERROR_RED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        self.log_text.configure(state="disabled")

        log_scroll = tk.Scrollbar(log_body, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        input_frame = tk.Frame(
            self,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        self.input_frame = input_frame
        input_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        input_frame.grid_columnconfigure(1, weight=1)

        cmd_label = tk.Label(
            input_frame,
            text="CMD >",
            font=self.font_text,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        cmd_label.grid(row=0, column=0, padx=(10, 6), pady=10, sticky="w")

        self.command_var = tk.StringVar()
        self.command_entry = tk.Entry(
            input_frame,
            textvariable=self.command_var,
            font=self.font_text,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=0,
        )
        self.command_entry.grid(row=0, column=1, sticky="ew", pady=10)

        btn_frame = tk.Frame(input_frame, bg=COLOR_BG)
        btn_frame.grid(row=0, column=2, padx=8, pady=6)

        self._create_button(btn_frame, "HELP", self._print_help, NEON_BLUE).grid(
            row=0, column=0, padx=4
        )
        self._create_button(btn_frame, "LIST", self._cmd_list, NEON_GREEN).grid(
            row=0, column=1, padx=4
        )
        self._create_button(btn_frame, "CLEAR", self._cmd_clear, NEON_PINK).grid(
            row=0, column=2, padx=4
        )

        self._header_labels = [cal_title, tasks_title, log_title]
        self._border_targets = [cal_frame, tasks_frame, log_frame, input_frame, hud_frame]
        self._calendar_title = cal_title

        # Ensure interactive layers sit above background canvas.
        hud_frame.lift()
        main.lift()
        input_frame.lift()

        for panel in (hud_frame, cal_frame, tasks_frame, log_frame, input_frame, control_frame):
            self._apply_glass(panel)

    def _bind_events(self):
        self.command_entry.bind("<Return>", self._on_command_enter)
        self.calendar.bind("<<CalendarSelected>>", self._on_calendar_selected)
        self.calendar.bind("<Motion>", self._on_calendar_hover)
        self.calendar.bind("<Leave>", self._hide_calendar_tooltip)
        self.search_entry.bind("<KeyRelease>", self._on_search_change)
        self.task_text.bind("<Button-1>", self._on_task_click)
        self.after(100, self.command_entry.focus_set)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Control-n>", self._shortcut_add)
        self.bind("<Control-f>", self._shortcut_search)
        self.bind("<Control-z>", self._shortcut_undo)
        self.bind("<Control-y>", self._shortcut_redo)

    def _create_button(self, parent, text, command, accent):
        if accent == NEON_BLUE:
            accent_role = "blue"
        elif accent == NEON_PINK:
            accent_role = "pink"
        elif accent == NEON_GREEN:
            accent_role = "green"
        elif accent == NEON_YELLOW:
            accent_role = "yellow"
        else:
            accent_role = "blue"
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.font_small,
            bg=COLOR_BG,
            fg=accent,
            activebackground=self._blend(COLOR_BG, accent, 0.35),
            activeforeground=COLOR_BG,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=accent,
            cursor="hand2",
            padx=10,
            pady=4,
        )
        btn._accent_role = accent_role
        if not hasattr(self, "_buttons"):
            self._buttons = []
        self._buttons.append(btn)
        btn.bind("<Enter>", lambda e: self._hover_button(btn, btn._accent_role, True))
        btn.bind("<Leave>", lambda e: self._hover_button(btn, btn._accent_role, False))
        return btn

    def _apply_glass(self, frame):
        canvas = tk.Canvas(frame, bg=COLOR_BG, highlightthickness=0, bd=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        canvas.tk.call("lower", canvas._w)
        self._glass_canvases[frame] = canvas
        frame.bind(
            "<Configure>",
            lambda _event, c=canvas: self._draw_panel_grid(c),
        )
        self._draw_panel_grid(canvas)

    def _draw_panel_grid(self, canvas):
        canvas.delete("grid")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2 or height <= 2:
            return
        grid_color = "#0f2b2b"
        for x in range(0, width, 18):
            canvas.create_line(x, 0, x, height, fill=grid_color, tags="grid")
        for y in range(0, height, 18):
            canvas.create_line(0, y, width, y, fill=grid_color, tags="grid")
        corner = 18
        for (x, y) in ((4, 4), (width - 4, 4), (4, height - 4), (width - 4, height - 4)):
            x0 = x - corner if x > width // 2 else x + corner
            y0 = y - corner if y > height // 2 else y + corner
            canvas.create_line(x, y, x0, y, fill=NEON_BLUE, tags="grid")
            canvas.create_line(x, y, x, y0, fill=NEON_BLUE, tags="grid")

    def _hover_button(self, btn, accent_role, entering):
        accent = {
            "blue": NEON_BLUE,
            "pink": NEON_PINK,
            "green": NEON_GREEN,
            "yellow": NEON_YELLOW,
        }.get(accent_role, NEON_BLUE)
        start = btn.cget("background")
        end = self._blend(COLOR_BG, accent, 0.35) if entering else COLOR_BG
        self._animate_bg(btn, start, end, steps=6, delay=18)

    def _animate_bg(self, widget, start, end, steps=6, delay=18):
        colors = self._interpolate_colors(start, end, steps)

        def step(i=0):
            if i >= len(colors):
                return
            widget.configure(background=colors[i])
            widget.after(delay, step, i + 1)

        step()

    @staticmethod
    def _hex_to_rgb(value):
        value = value.lstrip("#")
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _blend(self, a, b, t):
        ra, ga, ba = self._hex_to_rgb(a)
        rb, gb, bb = self._hex_to_rgb(b)
        r = int(ra + (rb - ra) * t)
        g = int(ga + (gb - ga) * t)
        b = int(ba + (bb - ba) * t)
        return self._rgb_to_hex((r, g, b))

    def _interpolate_colors(self, start, end, steps):
        if steps <= 1:
            return [end]
        return [self._blend(start, end, i / (steps - 1)) for i in range(steps)]

    def _format_date(self, value):
        if not value:
            return "--.--"
        return value.strftime("%d.%m.%Y")

    def _format_time(self, value):
        return value if value else "--:--"

    def _parse_hhmm(self, raw):
        if not raw:
            return None
        parts = raw.split(":")
        if len(parts) != 2:
            return None
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return None
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return None
        return f"{hour:02d}:{minute:02d}"

    def _parse_date(self, raw, base_date=None):
        if not raw:
            return None
        parts = raw.split(".")
        if len(parts) not in (2, 3):
            return None
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else None
        except ValueError:
            return None
        if year is None:
            if base_date is None:
                base_date = self._get_selected_date() or date.today()
            year = base_date.year
        try:
            return date(year, month, day)
        except ValueError:
            return None

    def _tag_color(self, tag):
        palette = [NEON_BLUE, NEON_PINK, NEON_YELLOW, NEON_GREEN, NEON_ORANGE]
        return palette[abs(hash(tag)) % len(palette)]

    def _ensure_tag_style(self, tag):
        style = f"tag:{tag}"
        if style not in self.task_text.tag_names():
            color = self._tag_color(tag)
            self.task_text.tag_config(style, foreground=color)
        return style

    def _update_stats(self):
        active = [t for t in self.tasks if not t.get("archived")]
        total = len(active)
        completed = sum(1 for t in active if t["status"] == "completed")
        pending = total - completed
        today = date.today()
        overdue = sum(
            1
            for t in active
            if t["due"] and t["due"] < today and t["status"] != "completed"
        )
        due_today = sum(
            1
            for t in active
            if t["due"] == today and t["status"] != "completed"
        )
        self.stats_label.configure(
            text=f"Stats: total {total} | pending {pending} | done {completed} | overdue {overdue} | today {due_today}"
        )
        completed_today = sum(
            1 for t in active if t.get("completed_at") == today and t["status"] == "completed"
        )
        goal = int(self.stats.get("daily_goal", 3) or 0)
        streak = self._compute_streak()
        self.streak_label.configure(text=f"STREAK {streak} | GOAL {completed_today}/{goal}")
        ratio = (completed / total) if total else 0
        self._draw_progress_ring(ratio)

    def _log_completion(self, completed_date):
        try:
            value = completed_date.isoformat()
        except AttributeError:
            value = str(completed_date)
        history = set(self.stats.get("completed_dates", []))
        history.add(value)
        self.stats["completed_dates"] = sorted(history)
        self._save_stats()

    def _compute_streak(self):
        dates = set(self.stats.get("completed_dates", []))
        if not dates:
            return 0
        streak = 0
        cursor = date.today()
        while cursor.isoformat() in dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    def _draw_progress_ring(self, ratio):
        canvas = self.progress_canvas
        canvas.delete("ring")
        size = 24
        pad = 2
        canvas.create_oval(
            pad,
            pad,
            pad + size,
            pad + size,
            outline="#1b2b2b",
            width=3,
            tags="ring",
        )
        angle = 360 * ratio
        canvas.create_arc(
            pad,
            pad,
            pad + size,
            pad + size,
            start=90,
            extent=-angle,
            style="arc",
            outline=NEON_GREEN,
            width=3,
            tags="ring",
        )

    def _update_timeline(self):
        canvas = self.timeline_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2 or height <= 2:
            return
        # Baseline
        canvas.create_line(6, height // 2, width - 6, height // 2, fill=NEON_BLUE)
        # Hour ticks
        for h in range(0, 25, 6):
            x = 6 + (width - 12) * (h / 24)
            canvas.create_line(x, 4, x, height - 4, fill="#123233")
        today = date.today()
        tasks = [
            t
            for t in self.tasks
            if t.get("due") == today and t.get("time") and not t.get("archived")
        ]
        for task in tasks:
            parts = task["time"].split(":")
            mins = int(parts[0]) * 60 + int(parts[1])
            x = 6 + (width - 12) * (mins / (24 * 60))
            color = self._tag_color(task.get("tag") or task.get("priority", "med"))
            canvas.create_oval(x - 3, height // 2 - 3, x + 3, height // 2 + 3, fill=color, outline=color)

    def _serialize_task(self, task):
        return {
            "id": task["id"],
            "name": task["name"],
            "due": task["due"].isoformat() if task["due"] else None,
            "status": task["status"],
            "priority": task.get("priority", "med"),
            "recurrence": task.get("recurrence"),
            "time": task.get("time"),
            "tag": task.get("tag"),
            "category": task.get("category"),
            "archived": bool(task.get("archived")),
            "completed_at": task.get("completed_at"),
        }

    def _deserialize_task(self, raw):
        due = None
        if raw.get("due"):
            try:
                due = date.fromisoformat(raw["due"])
            except ValueError:
                due = None
        return {
            "id": int(raw.get("id", 0)),
            "name": str(raw.get("name", "")).strip() or "Untitled task",
            "due": due,
            "status": raw.get("status", "pending"),
            "priority": raw.get("priority", "med"),
            "recurrence": raw.get("recurrence"),
            "time": raw.get("time"),
            "tag": raw.get("tag"),
            "category": raw.get("category"),
            "archived": bool(raw.get("archived")),
            "completed_at": raw.get("completed_at"),
        }

    def _save_tasks(self):
        payload = [self._serialize_task(task) for task in self.tasks]
        DATA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self._autosync()

    def _load_tasks(self):
        if not DATA_FILE.exists():
            return
        try:
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        tasks = []
        for item in raw if isinstance(raw, list) else []:
            task = self._deserialize_task(item)
            if task["id"] > 0:
                tasks.append(task)
        self.tasks = tasks
        self.next_id = max([t["id"] for t in tasks], default=0) + 1

    def _load_stats(self):
        if not STATS_FILE.exists():
            return
        try:
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if isinstance(data, dict):
            self.stats.update(data)

    def _save_stats(self):
        STATS_FILE.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")
        self._autosync()

    def _autosync(self):
        try:
            AUTOSYNC_DIR.mkdir(exist_ok=True)
            if DATA_FILE.exists():
                shutil.copyfile(DATA_FILE, AUTOSYNC_DIR / DATA_FILE.name)
            if STATS_FILE.exists():
                shutil.copyfile(STATS_FILE, AUTOSYNC_DIR / STATS_FILE.name)
        except OSError:
            pass

    def _get_selected_date(self):
        try:
            return self.calendar.selection_get()
        except Exception:
            return None

    def _parse_ddmm(self, raw, base_date=None):
        return self._parse_date(raw, base_date=base_date)

    def _log(self, message, tag="info"):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _push_undo(self):
        snapshot = {
            "tasks": [self._serialize_task(t) for t in self.tasks],
            "next_id": self.next_id,
        }
        self.undo_stack.append(snapshot)
        self.redo_stack.clear()

    def _restore_snapshot(self, snapshot):
        tasks = [self._deserialize_task(t) for t in snapshot.get("tasks", [])]
        self.tasks = tasks
        self.next_id = int(snapshot.get("next_id", 1))
        self._save_tasks()
        self._refresh_all("State restored.", "success")

    def _refresh_all(self, message=None, tag="info"):
        self._update_task_view()
        self._update_calendar_events()
        self._update_stats()
        self._update_timeline()
        if message:
            self._log(message, tag)

    def _set_theme(self, name):
        if name not in THEMES:
            self._log("Theme not found. Options: cyber, toxic, ember", "error")
            return
        global COLOR_BG, NEON_GREEN, NEON_PINK, NEON_BLUE, NEON_YELLOW, NEON_ORANGE, DIM_TEXT, ERROR_RED
        data = THEMES[name]
        COLOR_BG = data["bg"]
        NEON_GREEN = data["green"]
        NEON_PINK = data["pink"]
        NEON_BLUE = data["blue"]
        NEON_YELLOW = data["yellow"]
        NEON_ORANGE = data["orange"]
        DIM_TEXT = data["dim"]
        ERROR_RED = data["error"]
        self.theme_name = name
        self._apply_theme()
        self._refresh_all(f"Theme set: {name}", "success")

    def _apply_theme(self):
        self.configure(bg=COLOR_BG)
        self.bg_canvas.configure(bg=COLOR_BG)
        for frame in (
            self.hud_frame,
            self.main_frame,
            self.cal_frame,
            self.tasks_frame,
            self.log_frame,
            self.input_frame,
            self.control_frame,
            self.task_body,
            self.log_body,
        ):
            frame.configure(bg=COLOR_BG)
        self.hud_label.configure(bg=COLOR_BG, fg=NEON_BLUE)
        self.time_label.configure(bg=COLOR_BG, fg=NEON_PINK)
        self.streak_label.configure(bg=COLOR_BG, fg=NEON_GREEN)
        self.pomo_label.configure(bg=COLOR_BG, fg=NEON_YELLOW)
        self.stats_label.configure(bg=COLOR_BG, fg=DIM_TEXT)
        self.countdown_label.configure(bg=COLOR_BG, fg=NEON_YELLOW)
        self.search_entry.configure(
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            highlightbackground=NEON_BLUE,
        )
        self.timeline_canvas.configure(
            bg=COLOR_BG,
            highlightbackground=NEON_BLUE,
        )
        self.command_entry.configure(
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
        )
        self.task_text.configure(
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            selectbackground=NEON_BLUE,
            selectforeground=COLOR_BG,
        )
        self.task_text.tag_config("pending", foreground=NEON_GREEN)
        self.task_text.tag_config("completed", foreground=NEON_BLUE, font=self.font_completed)
        self.task_text.tag_config("header", foreground=NEON_PINK)
        self.log_text.configure(
            bg=COLOR_BG,
            fg=DIM_TEXT,
            insertbackground=NEON_GREEN,
            selectbackground=NEON_BLUE,
            selectforeground=COLOR_BG,
        )
        self.log_text.tag_config("info", foreground=DIM_TEXT)
        self.log_text.tag_config("cmd", foreground=NEON_YELLOW)
        self.log_text.tag_config("success", foreground=NEON_GREEN)
        self.log_text.tag_config("error", foreground=ERROR_RED)
        self.calendar.configure(
            background=COLOR_BG,
            foreground=NEON_GREEN,
            bordercolor=NEON_BLUE,
            headersbackground=COLOR_BG,
            headersforeground=NEON_PINK,
            selectbackground=NEON_PINK,
            selectforeground=COLOR_BG,
            normalbackground=COLOR_BG,
            normalforeground=NEON_GREEN,
            weekendbackground=COLOR_BG,
            weekendforeground=NEON_ORANGE,
            othermonthbackground=COLOR_BG,
            othermonthforeground=NEON_BLUE,
            disableddaybackground=COLOR_BG,
            disableddayforeground=DIM_TEXT,
        )
        self.calendar.tag_config("task", background=NEON_PINK, foreground=COLOR_BG)
        self.calendar.tag_config("today", background=NEON_BLUE, foreground=COLOR_BG)
        for btn in getattr(self, "_buttons", []):
            role = getattr(btn, "_accent_role", "blue")
            accent = {
                "blue": NEON_BLUE,
                "pink": NEON_PINK,
                "green": NEON_GREEN,
                "yellow": NEON_YELLOW,
            }.get(role, NEON_BLUE)
            btn.configure(
                bg=COLOR_BG,
                fg=accent,
                activebackground=self._blend(COLOR_BG, accent, 0.35),
                activeforeground=COLOR_BG,
                highlightbackground=accent,
            )
        for canvas in (self.led_canvas, self.signal_canvas, self.progress_canvas):
            canvas.configure(bg=COLOR_BG)
        self._draw_scanlines()
        for canvas in self._glass_canvases.values():
            canvas.configure(bg=COLOR_BG)
            self._draw_panel_grid(canvas)

    def _start_effects(self):
        self._update_clock()
        self._blink_cursor()
        self._pulse_borders()
        self._pulse_calendar()
        self._animate_hud()
        self._glitch_tick()
        self._init_matrix()
        self._draw_scanlines()

    def _update_clock(self):
        now = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=now)
        self.after(1000, self._update_clock)

    def _blink_cursor(self):
        current = self.command_entry.cget("insertbackground")
        next_color = COLOR_BG if current != COLOR_BG else NEON_GREEN
        self.command_entry.configure(insertbackground=next_color)
        self.after(500, self._blink_cursor)

    def _pulse_borders(self, step=0):
        palette = [NEON_BLUE, NEON_PINK, NEON_GREEN, NEON_YELLOW]
        color = palette[step % len(palette)]
        for frame in self._border_targets:
            frame.configure(highlightbackground=color)
        self.after(800, self._pulse_borders, step + 1)

    def _pulse_calendar(self, step=0):
        colors = [NEON_GREEN, NEON_PINK, NEON_BLUE, NEON_YELLOW]
        fg = colors[step % len(colors)]
        sel = colors[(step + 1) % len(colors)]
        self.calendar.configure(
            headersforeground=fg,
            foreground=fg,
            selectbackground=sel,
            weekendforeground=sel,
        )
        self.after(900, self._pulse_calendar, step + 1)

    def _animate_hud(self, step=0):
        self.led_canvas.delete("led")
        self.signal_canvas.delete("sig")
        colors = [NEON_GREEN, NEON_BLUE, NEON_PINK, NEON_YELLOW]
        for i in range(3):
            color = colors[(step + i) % len(colors)]
            x0 = 4 + i * 18
            self.led_canvas.create_oval(
                x0, 4, x0 + 10, 14, fill=color, outline=color, tags="led"
            )
        bars = (step % 4) + 1
        for i in range(4):
            height = (i + 1) * 3
            x0 = 4 + i * 10
            y0 = 16 - height
            color = NEON_GREEN if i < bars else "#0a2a1a"
            self.signal_canvas.create_rectangle(
                x0, y0, x0 + 6, 16, fill=color, outline=color, tags="sig"
            )
        self.after(700, self._animate_hud, step + 1)

    def _glitch_tick(self):
        label = random.choice(self._header_labels + [self._calendar_title])
        original = label.cget("text")
        if len(original) >= 3:
            glitched = list(original)
            for _ in range(2):
                idx = random.randrange(len(glitched))
                glitched[idx] = random.choice("@#$%&*+-=/\\")
            label.configure(text="".join(glitched))
            self.after(120, lambda: label.configure(text=original))
        self.after(1400, self._glitch_tick)

    def _on_resize(self, _event=None):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(120, self._apply_resize)

    def _apply_resize(self):
        self._resize_job = None
        self._draw_scanlines()
        self._init_matrix()

    def _draw_scanlines(self):
        self.bg_canvas.delete("scanline")
        width = self.bg_canvas.winfo_width()
        height = self.bg_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        for y in range(0, height, 4):
            self.bg_canvas.create_line(
                0,
                y,
                width,
                y,
                fill="#0b0b0b",
                tags="scanline",
            )

    def _init_matrix(self):
        width = self.bg_canvas.winfo_width()
        height = self.bg_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        cols = max(1, width // 20)
        self.matrix_streams = []
        for i in range(cols):
            x = i * 20 + 10
            self.matrix_streams.append(
                {
                    "x": x,
                    "y": random.randint(0, height),
                    "speed": random.randint(3, 9),
                }
            )
        if self._matrix_job is None:
            self._matrix_tick()

    def _matrix_tick(self):
        if not hasattr(self, "matrix_streams"):
            return
        self.bg_canvas.delete("matrix")
        height = self.bg_canvas.winfo_height()
        for stream in self.matrix_streams:
            stream["y"] += stream["speed"]
            if stream["y"] > height:
                stream["y"] = random.randint(-200, 0)
            char = random.choice("01#$%")
            self.bg_canvas.create_text(
                stream["x"],
                stream["y"],
                text=char,
                fill="#0aff64",
                font=self.font_small,
                tags="matrix",
            )
        self._matrix_job = self.after(120, self._matrix_tick)

    def _update_calendar_events(self):
        for event_id in self.calendar.get_calevents():
            self.calendar.calevent_remove(event_id)
        due_dates = {}
        for task in self.tasks:
            if task["due"] and not task.get("archived"):
                due_dates.setdefault(task["due"], 0)
                due_dates[task["due"]] += 1
        today = date.today()
        self.calendar.calevent_create(today, "today", "today")
        for due_date, count in due_dates.items():
            label = f"{count} task" if count == 1 else f"{count} tasks"
            self.calendar.calevent_create(due_date, label, "task")

    def _update_task_view(self):
        tasks = [t for t in self.tasks if self._matches_view(t)]
        if self.text_filter:
            keyword = self.text_filter.lower()
            tasks = [
                t
                for t in tasks
                if keyword in t["name"].lower()
                or (t["due"] and keyword in self._format_date(t["due"]))
                or keyword in (t.get("priority") or "").lower()
                or keyword in (t.get("time") or "").lower()
                or keyword in (t.get("tag") or "").lower()
                or keyword in (t.get("category") or "").lower()
            ]
            header = f"Filter: {self.text_filter}"
        else:
            header = self._view_title()

        tasks = self._sort_tasks(tasks)
        self.visible_tasks = tasks
        self._line_to_task_index = {}

        self.task_text.configure(state="normal")
        self.task_text.delete("1.0", "end")
        self.task_text.insert("end", header + "\n", "header")
        self.task_text.insert("end", "=" * max(10, len(header)) + "\n\n", "header")

        if not tasks:
            self.task_text.insert("end", "No tasks found.\n", "pending")
        else:
            current_category = None
            line_no = 4
            for idx, task in enumerate(tasks, start=1):
                category = task.get("category") or "Uncategorized"
                if category != current_category:
                    current_category = category
                    self.task_text.insert("end", f"[ {category} ]\n", "header")
                    line_no += 1
                status_symbol = "[x+]" if task["status"] == "completed" else "[+]"
                due_text = self._format_date(task["due"]) if task["due"] else "--.--"
                time_text = self._format_time(task.get("time"))
                repeat_text = f" | {task['recurrence']}" if task.get("recurrence") else ""
                status_tag = "completed" if task["status"] == "completed" else "pending"
                self.task_text.insert("end", f"{status_symbol} {idx}. ", status_tag)
                self.task_text.insert(
                    "end",
                    f"[{task.get('priority','med')}] ",
                    ("priority", status_tag),
                )
                if task.get("tag"):
                    tag_style = self._ensure_tag_style(task["tag"])
                    self.task_text.insert(
                        "end",
                        f"[{task['tag']}] ",
                        (tag_style, status_tag),
                    )
                self.task_text.insert(
                    "end",
                    f"{task['name']}  (due {due_text} {time_text}{repeat_text})\n",
                    status_tag,
                )
                self._line_to_task_index[line_no] = idx - 1
                line_no += 1

        self.task_text.configure(state="disabled")

    def _matches_view(self, task):
        if self.view_mode == "archive":
            return task.get("archived")
        if task.get("archived") and self.view_mode != "archive":
            return False
        if self.hide_completed and task["status"] == "completed":
            return False
        today = date.today()
        if self.view_mode == "due" and self.view_value:
            return task["due"] == self.view_value
        if self.view_mode == "today":
            return task["due"] == today
        if self.view_mode == "week":
            if not task["due"]:
                return False
            start = today
            end = today + timedelta(days=6)
            return start <= task["due"] <= end
        if self.view_mode == "overdue":
            return task["due"] and task["due"] < today and task["status"] != "completed"
        return True

    def _view_title(self):
        if self.view_mode == "due" and self.view_value:
            return f"Tasks due {self._format_date(self.view_value)}"
        if self.view_mode == "today":
            return "Tasks due today"
        if self.view_mode == "week":
            return "Tasks due this week"
        if self.view_mode == "overdue":
            return "Overdue tasks"
        if self.view_mode == "archive":
            return "Archived tasks"
        return "All tasks"

    def _sort_tasks(self, tasks):
        if self.sort_key == "name":
            key = lambda t: t["name"].lower()
        elif self.sort_key == "status":
            key = lambda t: 0 if t["status"] == "pending" else 1
        elif self.sort_key == "priority":
            key = lambda t: PRIORITY_ORDER.get(t.get("priority"), 3)
        else:
            key = lambda t: (
                t["due"] is None,
                t["due"] or date.max,
                t.get("time") or "99:99",
            )
        return sorted(tasks, key=key, reverse=self.sort_reverse)

    def _on_calendar_selected(self, _event=None):
        selected = self.calendar.selection_get()
        self.selected_date_label.configure(text=f"Selected: {self._format_date(selected)}")
        if self.drag_task is not None:
            self._push_undo()
            self.drag_task["due"] = selected
            self._save_tasks()
            self._refresh_all("Task rescheduled via calendar.", "success")
            self.drag_task = None
            return
        self.view_mode = "due"
        self.view_value = selected
        self._update_task_view()
        self._log(f"Showing tasks due {self._format_date(selected)}.", "info")
        self._show_day_popup(selected)

    def _on_calendar_hover(self, event):
        if self._hover_job:
            self.after_cancel(self._hover_job)
        self._hover_job = self.after(120, lambda: self._show_calendar_tooltip(event))

    def _show_calendar_tooltip(self, event):
        self._hover_job = None
        widget = self.calendar.winfo_containing(event.x_root, event.y_root)
        if widget is None or not hasattr(widget, "cget"):
            self._hide_calendar_tooltip()
            return
        try:
            day = int(widget.cget("text"))
        except (ValueError, tk.TclError):
            self._hide_calendar_tooltip()
            return
        try:
            month, year = self.calendar.get_displayed_month()
        except Exception:
            self._hide_calendar_tooltip()
            return
        try:
            hover_date = date(year, month, day)
        except ValueError:
            self._hide_calendar_tooltip()
            return
        tasks = [t for t in self.tasks if t["due"] == hover_date and not t.get("archived")]
        if not tasks:
            self._hide_calendar_tooltip()
            return
        if self._cal_tooltip is None:
            self._cal_tooltip = tk.Toplevel(self)
            self._cal_tooltip.configure(bg=COLOR_BG)
            self._cal_tooltip.overrideredirect(True)
            self._cal_tooltip.attributes("-topmost", True)
            self._cal_tooltip.attributes("-alpha", 0.95)
            self._cal_tooltip_label = tk.Label(
                self._cal_tooltip,
                text="",
                font=self.font_small,
                bg=COLOR_BG,
                fg=NEON_GREEN,
                padx=8,
                pady=4,
                justify="left",
            )
            self._cal_tooltip_label.pack()
        lines = [f"{self._format_date(hover_date)}"]
        for task in tasks[:6]:
            time_text = self._format_time(task.get("time"))
            lines.append(f"- {task['name']} @ {time_text}")
        if len(tasks) > 6:
            lines.append(f"... +{len(tasks) - 6} more")
        self._cal_tooltip_label.configure(text="\n".join(lines))
        x = event.x_root + 12
        y = event.y_root + 12
        self._cal_tooltip.geometry(f"+{x}+{y}")

    def _hide_calendar_tooltip(self, _event=None):
        if self._hover_job:
            self.after_cancel(self._hover_job)
            self._hover_job = None
        if self._cal_tooltip:
            self._cal_tooltip.destroy()
            self._cal_tooltip = None
            self._cal_tooltip_label = None

    def _on_search_change(self, _event=None):
        self.text_filter = self.search_var.get().strip()
        self._update_task_view()

    def _on_task_click(self, event):
        index = self.task_text.index(f"@{event.x},{event.y}")
        line_no = int(index.split(".")[0])
        task_index = self._task_index_from_line(line_no)
        if task_index is None:
            return
        task = self.visible_tasks[task_index]
        if task.get("archived"):
            self._log("Archived task. Use 'archive restore' to edit.", "info")
            return
        if event.state & 0x0004:
            self.drag_task = task
            self._log("Task selected for calendar move. Click a date.", "info")
            return
        self._show_edit_popup(task)

    def _task_index_from_line(self, line_no):
        if not hasattr(self, "_line_to_task_index"):
            return None
        return self._line_to_task_index.get(line_no)

    def _show_edit_popup(self, task):
        popup = tk.Toplevel(self)
        popup.title("EDIT TASK")
        popup.configure(bg=COLOR_BG)
        popup.geometry("520x340")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.attributes("-alpha", 0.96)

        border = tk.Frame(
            popup,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        border.pack(fill="both", expand=True, padx=10, pady=10)

        title = tk.Label(
            border,
            text="[ EDIT TASK ]",
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        title.pack(pady=(8, 10))

        form = tk.Frame(border, bg=COLOR_BG)
        form.pack(fill="both", expand=True, padx=12)
        form.grid_columnconfigure(1, weight=1)

        def label(text, row):
            tk.Label(
                form, text=text, font=self.font_small, bg=COLOR_BG, fg=NEON_GREEN
            ).grid(row=row, column=0, sticky="w", pady=4)

        name_var = tk.StringVar(value=task["name"])
        date_var = tk.StringVar(value=self._format_date(task.get("due")))
        time_var = tk.StringVar(value=self._format_time(task.get("time")))
        tag_var = tk.StringVar(value=task.get("tag") or "")
        priority_var = tk.StringVar(value=task.get("priority", "med"))
        repeat_var = tk.StringVar(value=task.get("recurrence") or "")
        status_var = tk.StringVar(value=task.get("status", "pending"))

        label("Name", 0)
        tk.Entry(
            form,
            textvariable=name_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=0, column=1, sticky="ew", pady=4)

        label("Due (dd.mm)", 1)
        tk.Entry(
            form,
            textvariable=date_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=1, column=1, sticky="ew", pady=4)

        label("Time (HH:MM)", 2)
        tk.Entry(
            form,
            textvariable=time_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=2, column=1, sticky="ew", pady=4)

        label("Tag", 3)
        tk.Entry(
            form,
            textvariable=tag_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=3, column=1, sticky="ew", pady=4)

        label("Priority", 4)
        tk.Entry(
            form,
            textvariable=priority_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=4, column=1, sticky="ew", pady=4)

        label("Repeat", 5)
        tk.Entry(
            form,
            textvariable=repeat_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=5, column=1, sticky="ew", pady=4)

        label("Status", 6)
        tk.Entry(
            form,
            textvariable=status_var,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            insertbackground=NEON_GREEN,
            relief="flat",
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        ).grid(row=6, column=1, sticky="ew", pady=4)

        btn_row = tk.Frame(border, bg=COLOR_BG)
        btn_row.pack(pady=(6, 10))

        def save():
            name = name_var.get().strip()
            if not name:
                self._log("Task name required.", "error")
                return
            due_text = date_var.get().strip()
            due_val = None
            if due_text and due_text != "--.--":
                due_val = self._parse_ddmm(due_text)
                if due_val is None:
                    self._log("Invalid date format. Use dd.mm", "error")
                    return
            time_text = time_var.get().strip()
            time_val = None
            if time_text and time_text != "--:--":
                time_val = self._parse_hhmm(time_text)
                if time_val is None:
                    self._log("Invalid time format. Use HH:MM", "error")
                    return
            priority = priority_var.get().strip().lower() or "med"
            if priority not in ("low", "med", "high"):
                self._log("Priority must be low, med, or high.", "error")
                return
            repeat = repeat_var.get().strip().lower() or None
            if repeat and repeat not in ("daily", "weekly", "monthly"):
                self._log("Repeat must be daily, weekly, or monthly.", "error")
                return
            status = status_var.get().strip().lower() or "pending"
            if status not in ("pending", "completed"):
                self._log("Status must be pending or completed.", "error")
                return
            self._push_undo()
            task["name"] = name
            task["due"] = due_val
            task["time"] = time_val
            task["tag"] = tag_var.get().strip() or None
            task["priority"] = priority
            task["recurrence"] = repeat
            task["status"] = status
            if task.get("recurrence") and task.get("due") is None:
                self._log("Repeat requires a due date.", "error")
                return
            self._save_tasks()
            self._refresh_all("Task updated.", "success")
            popup.destroy()

        tk.Button(
            btn_row,
            text="SAVE",
            command=save,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_BLUE,
            activebackground=self._blend(COLOR_BG, NEON_BLUE, 0.35),
            activeforeground=COLOR_BG,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
            cursor="hand2",
            padx=12,
            pady=4,
        ).pack(side="left", padx=6)

        tk.Button(
            btn_row,
            text="CLOSE",
            command=popup.destroy,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_PINK,
            activebackground=self._blend(COLOR_BG, NEON_PINK, 0.35),
            activeforeground=COLOR_BG,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=NEON_PINK,
            cursor="hand2",
            padx=12,
            pady=4,
        ).pack(side="left", padx=6)

    def _shortcut_add(self, _event=None):
        self.command_entry.focus_set()
        self.command_var.set("add ")
        self.command_entry.icursor("end")

    def _shortcut_search(self, _event=None):
        self.search_entry.focus_set()
        self.search_entry.icursor("end")

    def _shortcut_undo(self, _event=None):
        self._cmd_undo()

    def _shortcut_redo(self, _event=None):
        self._cmd_redo()

    def _on_command_enter(self, _event=None):
        command_line = self.command_var.get().strip()
        if not command_line:
            return
        self.command_var.set("")
        self._log(f"> {command_line}", "cmd")
        self._execute_command(command_line)

    def _execute_command(self, command_line):
        try:
            tokens = shlex.split(command_line)
        except ValueError:
            self._log("Invalid command format.", "error")
            return
        if not tokens:
            return

        cmd = tokens[0].lower()
        args = tokens[1:]

        cmd_aliases = {
            "a": "add",
            "rm": "remove",
            "c": "complete",
            "ls": "list",
            "u": "update",
            "du": "due",
            "fl": "filter",
            "cl": "clear",
            "ref": "refresh",
            "th": "theme",
            "ar": "archive",
            "fo": "focus",
            "cap": "capture",
            "rs": "reschedule",
            "ics": "exportics",
            "pomo": "pomodoro",
            "-h": "help",
            "--help": "help",
        }
        cmd = cmd_aliases.get(cmd, cmd)
        args = self._expand_short_flags(args)

        handlers = {
            "add": self._cmd_add,
            "remove": self._cmd_remove,
            "complete": self._cmd_complete,
            "list": self._cmd_list,
            "due": self._cmd_due,
            "update": self._cmd_update,
            "filter": self._cmd_filter,
            "clear": self._cmd_clear,
            "help": self._cmd_help,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "sort": self._cmd_sort,
            "today": self._cmd_today,
            "week": self._cmd_week,
            "overdue": self._cmd_overdue,
            "export": self._cmd_export,
            "import": self._cmd_import,
            "hide": self._toggle_hide_completed,
            "refresh": self._cmd_refresh,
            "theme": self._cmd_theme,
            "archive": self._cmd_archive,
            "focus": self._cmd_focus,
            "capture": self._cmd_capture,
            "goal": self._cmd_goal,
            "reschedule": self._cmd_reschedule,
            "exportics": self._cmd_exportics,
            "pomodoro": self._cmd_pomodoro,
            "short": self._cmd_short_help,
        }

        handler = handlers.get(cmd)
        if not handler:
            self._log("Unknown command. Type 'help' for options.", "error")
            return
        handler(args)

    def _expand_short_flags(self, args):
        if not args:
            return args
        mapping = {
            "-d": "--time",
            "-a": "--at",
            "-g": "--tag",
            "-p": "--priority",
            "-r": "--repeat",
            "-c": "--category",
        }
        expanded = []
        for token in args:
            expanded.append(mapping.get(token, token))
        return expanded

    def _parse_flags(self, tokens, multi_flags=None):
        multi_flags = set(multi_flags or [])
        args = []
        flags = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                flag = token
                i += 1
                if flag in multi_flags:
                    value_parts = []
                    while i < len(tokens) and not tokens[i].startswith("--"):
                        value_parts.append(tokens[i])
                        i += 1
                    flags[flag] = " ".join(value_parts) if value_parts else None
                else:
                    value = None
                    if i < len(tokens) and not tokens[i].startswith("--"):
                        value = tokens[i]
                        i += 1
                    flags[flag] = value
            else:
                args.append(token)
                i += 1
        return args, flags

    def _get_task_by_index(self, index):
        if index < 1 or index > len(self.visible_tasks):
            return None
        return self.visible_tasks[index - 1]

    def _cmd_add(self, args):
        if not args:
            self._log(
                "Usage: add [task name] --time [dd.mm.yyyy] [hh:mm] --at [HH:MM] --tag [label] --category [label] --priority [low|med|high] --repeat [daily|weekly|monthly]",
                "error",
            )
            return
        name_parts, flags = self._parse_flags(args, multi_flags={"--time"})
        name = " ".join(name_parts).strip()
        if not name:
            self._log("Task name is required.", "error")
            return

        due = None
        clock = None
        if "--time" in flags:
            raw_time = flags.get("--time")
            if raw_time is None:
                self._log("Invalid date format. Use dd.mm.yyyy", "error")
                return
            if str(raw_time).lower() in ("none", "clear"):
                due = None
            else:
                parts = str(raw_time).split()
                due = self._parse_date(parts[0])
                if due is None:
                    self._log("Invalid date format. Use dd.mm.yyyy", "error")
                    return
                if len(parts) > 1:
                    clock = self._parse_hhmm(parts[1])
                    if clock is None:
                        self._log("Invalid time format. Use HH:MM", "error")
                        return
        else:
            due = self._get_selected_date()

        if "--at" in flags:
            clock = self._parse_hhmm(flags.get("--at"))
            if clock is None:
                self._log("Invalid time format. Use HH:MM", "error")
                return

        tag = None
        if "--tag" in flags:
            tag = flags.get("--tag")
            if tag:
                tag = str(tag).strip()
        category = None
        if "--category" in flags:
            category = flags.get("--category")
            if category:
                category = str(category).strip()

        priority = (flags.get("--priority") or "med").lower()
        if priority not in ("low", "med", "high"):
            self._log("Priority must be low, med, or high.", "error")
            return
        recurrence = flags.get("--repeat")
        if recurrence:
            recurrence = recurrence.lower()
            if recurrence not in ("daily", "weekly", "monthly"):
                self._log("Repeat must be daily, weekly, or monthly.", "error")
                return
            if due is None:
                self._log("Repeat requires a due date. Use --time [dd.mm].", "error")
                return

        self._push_undo()
        task = {
            "id": self.next_id,
            "name": name,
            "due": due,
            "status": "pending",
            "priority": priority,
            "recurrence": recurrence,
            "time": clock,
            "tag": tag,
            "category": category,
            "archived": False,
            "completed_at": None,
        }
        self.next_id += 1
        self.tasks.append(task)
        self._save_tasks()
        self._refresh_all("Task added.", "success")

    def _cmd_remove(self, args):
        if len(args) != 1 or not args[0].isdigit():
            self._log("Usage: remove [task number]", "error")
            return
        index = int(args[0])
        task = self._get_task_by_index(index)
        if not task:
            self._log("Task number not found in current view.", "error")
            return
        self._push_undo()
        self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
        self._save_tasks()
        self._refresh_all("Task removed.", "success")

    def _cmd_complete(self, args):
        if len(args) != 1 or not args[0].isdigit():
            self._log("Usage: complete [task number]", "error")
            return
        index = int(args[0])
        task = self._get_task_by_index(index)
        if not task:
            self._log("Task number not found in current view.", "error")
            return
        self._push_undo()
        task["status"] = "completed"
        task["completed_at"] = date.today().isoformat()
        self._log_completion(date.today())
        if task.get("recurrence") and task.get("due"):
            next_due = self._next_due(task["due"], task["recurrence"])
            if next_due:
                self.tasks.append(
                    {
                        "id": self.next_id,
                        "name": task["name"],
                        "due": next_due,
                        "status": "pending",
                        "priority": task.get("priority", "med"),
                        "recurrence": task.get("recurrence"),
                        "time": task.get("time"),
                        "tag": task.get("tag"),
                        "archived": False,
                        "completed_at": None,
                    }
                )
                self.next_id += 1
        self._save_tasks()
        self._refresh_all(f"Task completed: {task['name']}.", "success")

    def _cmd_list(self, _args=None):
        self.view_mode = "all"
        self.view_value = None
        self.text_filter = ""
        self.search_var.set("")
        self._update_task_view()
        self._log("Listing all tasks.", "info")

    def _cmd_due(self, args):
        if len(args) != 1:
            self._log("Usage: due [dd.mm]", "error")
            return
        due = self._parse_ddmm(args[0])
        if due is None:
            self._log("Invalid date format. Use dd.mm", "error")
            return
        self.view_mode = "due"
        self.view_value = due
        self.calendar.selection_set(due)
        self.selected_date_label.configure(text=f"Selected: {self._format_date(due)}")
        self._update_task_view()
        self._log(f"Showing tasks due {self._format_date(due)}.", "info")

    def _cmd_update(self, args):
        if len(args) < 1 or not args[0].isdigit():
            self._log(
                "Usage: update [task number] --name [new name] --time [dd.mm.yyyy] [hh:mm] --at [HH:MM] --tag [label] --category [label] --priority [low|med|high] --repeat [daily|weekly|monthly]",
                "error",
            )
            return
        index = int(args[0])
        task = self._get_task_by_index(index)
        if not task:
            self._log("Task number not found in current view.", "error")
            return

        name_parts, flags = self._parse_flags(args[1:], multi_flags={"--name"})
        if name_parts:
            self._log("Use flags: --name and/or --time", "error")
            return

        new_name = flags.get("--name")
        new_time = flags.get("--time")
        new_clock = flags.get("--at")
        new_priority = flags.get("--priority")
        new_tag = flags.get("--tag")
        new_category = flags.get("--category")
        new_repeat = flags.get("--repeat")

        if (
            new_name is None
            and new_time is None
            and new_clock is None
            and new_priority is None
            and new_tag is None
            and new_category is None
            and new_repeat is None
        ):
            self._log("Nothing to update. Provide --name, --time, --at, --tag, --category, --priority, or --repeat", "error")
            return

        candidate_due = task.get("due")
        candidate_clock = task.get("time")
        if new_time is not None:
            if str(new_time).lower() in ("none", "clear"):
                candidate_due = None
            else:
                parts = str(new_time).split()
                due = self._parse_date(parts[0])
                if due is None:
                    self._log("Invalid date format. Use dd.mm.yyyy", "error")
                    return
                candidate_due = due
                if len(parts) > 1:
                    clock = self._parse_hhmm(parts[1])
                    if clock is None:
                        self._log("Invalid time format. Use HH:MM", "error")
                        return
                    candidate_clock = clock

        if new_clock is not None:
            if str(new_clock).lower() in ("none", "clear"):
                candidate_clock = None
            else:
                clock = self._parse_hhmm(new_clock)
                if clock is None:
                    self._log("Invalid time format. Use HH:MM", "error")
                    return
                candidate_clock = clock

        candidate_repeat = task.get("recurrence")
        if new_repeat is not None:
            if str(new_repeat).lower() in ("none", "clear"):
                candidate_repeat = None
            else:
                repeat = new_repeat.lower()
                if repeat not in ("daily", "weekly", "monthly"):
                    self._log("Repeat must be daily, weekly, or monthly.", "error")
                    return
                candidate_repeat = repeat

        if candidate_repeat and candidate_due is None:
            self._log("Repeat requires a due date.", "error")
            return

        if new_priority is not None:
            priority = new_priority.lower()
            if priority not in ("low", "med", "high"):
                self._log("Priority must be low, med, or high.", "error")
                return

        self._push_undo()

        if new_name is not None:
            task["name"] = new_name

        task["due"] = candidate_due
        task["recurrence"] = candidate_repeat
        task["time"] = candidate_clock

        if new_priority is not None:
            task["priority"] = new_priority.lower()
        if new_tag is not None:
            if str(new_tag).lower() in ("none", "clear"):
                task["tag"] = None
            else:
                task["tag"] = str(new_tag).strip()
        if new_category is not None:
            if str(new_category).lower() in ("none", "clear"):
                task["category"] = None
            else:
                task["category"] = str(new_category).strip()
        if task["status"] == "completed" and not task.get("completed_at"):
            task["completed_at"] = date.today().isoformat()
            self._log_completion(date.today())
        if task["status"] != "completed":
            task["completed_at"] = None

        self._save_tasks()
        self._refresh_all("Task updated.", "success")

    def _cmd_filter(self, args):
        if not args:
            self._log("Usage: filter [keyword]", "error")
            return
        keyword = " ".join(args).strip()
        if not keyword:
            self._log("Keyword required.", "error")
            return
        self.text_filter = keyword
        self.search_var.set(keyword)
        self._update_task_view()
        self._log(f"Filtering tasks by '{keyword}'.", "info")

    def _cmd_clear(self, _args=None):
        self._push_undo()
        self.tasks = []
        self.visible_tasks = []
        self.view_mode = "all"
        self.view_value = None
        self.text_filter = ""
        self.search_var.set("")
        self._save_tasks()
        self._refresh_all("All tasks cleared.", "success")

    def _cmd_help(self, _args=None):
        self._print_help()
        self._print_short_help()

    def _print_help(self):
        help_text = (
            "Commands:\n"
            "  add [task name] --time [dd.mm.yyyy] [hh:mm] --at [HH:MM] --tag [label] --category [label] --priority [low|med|high] --repeat [daily|weekly|monthly]\n"
            "  remove [task number]\n"
            "  complete [task number]\n"
            "  list\n"
            "  due [dd.mm]\n"
            "  update [task number] --name [new name] --time [dd.mm.yyyy] [hh:mm] --at [HH:MM] --tag [label] --category [label] --priority [low|med|high] --repeat [daily|weekly|monthly]\n"
            "  filter [keyword]\n"
            "  clear\n"
            "  today | week | overdue\n"
            "  hide  (toggle hide completed)\n"
            "  refresh\n"
            "  theme [cyber|toxic|ember]\n"
            "  archive [view|restore]\n"
            "  focus\n"
            "  capture [task name]\n"
            "  goal [number]\n"
            "  reschedule overdue\n"
            "  exportics [filename.ics]\n"
            "  pomodoro start [task number] [minutes]\n"
            "  pomodoro stop | status\n"
            "  sort [name|due|priority|status] [asc|desc]\n"
            "  sort --priority | --due-date | --completed\n"
            "  undo | redo\n"
            "  export [filename.csv]\n"
            "  import [filename.csv]\n"
        )
        self._log(help_text, "info")

    def _print_short_help(self):
        short_text = (
            "Short commands:\n"
            "  a add | rm remove | c complete | ls list | u update | du due | fl filter | cl clear\n"
            "  ref refresh | th theme | ar archive | fo focus | cap capture | rs reschedule | ics exportics | pomo pomodoro\n"
            "Short flags:\n"
            "  -d date | -a time | -g tag | -c category | -p priority | -r repeat\n"
        )
        self._log(short_text, "info")

    def _cmd_short_help(self, _args=None):
        self._print_short_help()

    def _next_due(self, due, recurrence):
        if recurrence == "daily":
            return due + timedelta(days=1)
        if recurrence == "weekly":
            return due + timedelta(days=7)
        if recurrence == "monthly":
            month = due.month + 1
            year = due.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(due.day, 28)
            return date(year, month, day)
        return None

    def _cmd_today(self, _args=None):
        self.view_mode = "today"
        self.view_value = None
        self._update_task_view()
        self._log("Showing tasks due today.", "info")

    def _cmd_week(self, _args=None):
        self.view_mode = "week"
        self.view_value = None
        self._update_task_view()
        self._log("Showing tasks due this week.", "info")

    def _cmd_overdue(self, _args=None):
        self.view_mode = "overdue"
        self.view_value = None
        self._update_task_view()
        self._log("Showing overdue tasks.", "info")

    def _cmd_refresh(self, _args=None):
        self._refresh_all("View refreshed.", "info")

    def _cmd_focus(self, _args=None):
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            self.cal_frame.grid_remove()
            self.log_frame.grid_remove()
            self.tasks_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=12, pady=12)
            self.main_frame.grid_columnconfigure(0, weight=1)
            self.main_frame.grid_columnconfigure(1, weight=0)
            self.view_mode = "today"
            self._update_task_view()
            self._log("Focus mode ON (today view).", "info")
        else:
            self.cal_frame.grid()
            self.log_frame.grid()
            self.tasks_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=(12, 6))
            self.main_frame.grid_columnconfigure(0, weight=1)
            self.main_frame.grid_columnconfigure(1, weight=2)
            self._log("Focus mode OFF.", "info")
        self._refresh_all()

    def _cmd_capture(self, args):
        if not args:
            self._log("Usage: capture [task name]", "error")
            return
        name = " ".join(args).strip()
        if not name:
            self._log("Task name required.", "error")
            return
        self._push_undo()
        task = {
            "id": self.next_id,
            "name": name,
            "due": date.today(),
            "status": "pending",
            "priority": "med",
            "recurrence": None,
            "time": None,
            "tag": "inbox",
            "archived": False,
            "completed_at": None,
        }
        self.next_id += 1
        self.tasks.append(task)
        self._save_tasks()
        self._refresh_all("Captured to inbox (today).", "success")

    def _cmd_goal(self, args):
        if not args or not args[0].isdigit():
            self._log("Usage: goal [number]", "error")
            return
        self.stats["daily_goal"] = int(args[0])
        self._save_stats()
        self._refresh_all("Daily goal updated.", "success")

    def _cmd_reschedule(self, args):
        if not args or args[0].lower() != "overdue":
            self._log("Usage: reschedule overdue", "error")
            return
        today = date.today()
        moved = 0
        self._push_undo()
        for task in self.tasks:
            if task.get("archived"):
                continue
            if task["due"] and task["due"] < today and task["status"] != "completed":
                task["due"] = today
                moved += 1
        if moved == 0:
            self._log("No overdue tasks to reschedule.", "error")
            return
        self._save_tasks()
        self._refresh_all(f"Rescheduled {moved} overdue tasks to today.", "success")

    def _cmd_exportics(self, args):
        target = Path(args[0]) if args else Path("tasks.ics")
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//NeonToDo//EN",
        ]
        for task in self.tasks:
            if task.get("archived"):
                continue
            if not task.get("due"):
                continue
            uid = f"{task['id']}@neon-todo"
            due = task["due"]
            if task.get("time"):
                hh, mm = task["time"].split(":")
                dt = datetime(due.year, due.month, due.day, int(hh), int(mm))
                stamp = dt.strftime("%Y%m%dT%H%M%S")
                lines.extend(
                    [
                        "BEGIN:VEVENT",
                        f"UID:{uid}",
                        f"DTSTAMP:{stamp}",
                        f"DTSTART:{stamp}",
                        f"SUMMARY:{task['name']}",
                        "END:VEVENT",
                    ]
                )
            else:
                stamp = due.strftime("%Y%m%d")
                lines.extend(
                    [
                        "BEGIN:VEVENT",
                        f"UID:{uid}",
                        f"DTSTAMP:{stamp}",
                        f"DTSTART;VALUE=DATE:{stamp}",
                        f"SUMMARY:{task['name']}",
                        "END:VEVENT",
                    ]
                )
        lines.append("END:VCALENDAR")
        target.write_text("\n".join(lines), encoding="utf-8")
        self._log(f"Exported ICS to {target}.", "success")

    def _cmd_theme(self, args):
        if not args:
            self._log("Usage: theme [cyber|toxic|ember]", "error")
            return
        self._set_theme(args[0].lower())

    def _cmd_archive(self, args):
        if args and args[0].lower() == "view":
            self.view_mode = "archive"
            self._update_task_view()
            self._log("Showing archived tasks.", "info")
            return
        if args and args[0].lower() == "restore":
            archived = [t for t in self.tasks if t.get("archived")]
            if not archived:
                self._log("No archived tasks to restore.", "error")
                return
            self._push_undo()
            for task in archived:
                task["archived"] = False
            self._save_tasks()
            self._refresh_all("Archived tasks restored.", "success")
            return

        completed = [t for t in self.tasks if t["status"] == "completed" and not t.get("archived")]
        if not completed:
            self._log("No completed tasks to archive.", "error")
            return
        self._push_undo()
        for task in completed:
            task["archived"] = True
        self._save_tasks()
        self._refresh_all("Completed tasks archived.", "success")

    def _cmd_pomodoro(self, args):
        if not args:
            self._log("Usage: pomodoro start [task number] [minutes] | stop | status", "error")
            return
        action = args[0].lower()
        if action == "stop":
            if self.pomo_job:
                self.after_cancel(self.pomo_job)
                self.pomo_job = None
            self.pomo_task_id = None
            self.pomo_remaining = 0
            self.pomo_label.configure(text="POMO --:--")
            self._log("Pomodoro stopped.", "info")
            return
        if action == "status":
            if not self.pomo_task_id:
                self._log("Pomodoro idle.", "info")
                return
            mins, secs = divmod(self.pomo_remaining, 60)
            self._log(f"Pomodoro running: {mins:02d}:{secs:02d}", "info")
            return
        if action != "start":
            self._log("Usage: pomodoro start [task number] [minutes]", "error")
            return
        if len(args) < 2 or not args[1].isdigit():
            self._log("Pomodoro requires a task number.", "error")
            return
        minutes = 25
        if len(args) > 2 and args[2].isdigit():
            minutes = int(args[2])
        task = self._get_task_by_index(int(args[1]))
        if not task:
            self._log("Task number not found in current view.", "error")
            return
        if self.pomo_job:
            self.after_cancel(self.pomo_job)
        self.pomo_task_id = task["id"]
        self.pomo_remaining = minutes * 60
        self._tick_pomodoro(task["name"])

    def _tick_pomodoro(self, task_name):
        if self.pomo_remaining <= 0:
            self.pomo_label.configure(text="POMO DONE")
            self._show_popup("POMODORO", f"Pomodoro complete for: {task_name}")
            self.pomo_task_id = None
            self.pomo_job = None
            return
        mins, secs = divmod(self.pomo_remaining, 60)
        self.pomo_label.configure(text=f"POMO {mins:02d}:{secs:02d}")
        self.pomo_remaining -= 1
        self.pomo_job = self.after(1000, self._tick_pomodoro, task_name)

    def _toggle_hide_completed(self, _args=None):
        self.hide_completed = not self.hide_completed
        self._update_task_view()
        state = "ON" if self.hide_completed else "OFF"
        self._log(f"Hide completed: {state}", "info")

    def _cmd_sort(self, args):
        if not args:
            self._log("Usage: sort [name|due|priority|status] [asc|desc]", "error")
            return
        key = args[0].lower()
        if key in ("--priority",):
            key = "priority"
        elif key in ("--due-date", "--duedate"):
            key = "due"
        elif key in ("--completed", "--status"):
            key = "status"
        if key not in ("name", "due", "priority", "status"):
            self._log("Sort key must be name, due, priority, or status.", "error")
            return
        order = args[1].lower() if len(args) > 1 else "asc"
        if order not in ("asc", "desc"):
            self._log("Sort order must be asc or desc.", "error")
            return
        self.sort_key = key
        self.sort_reverse = order == "desc"
        self._update_task_view()
        self._log(f"Sorting by {key} ({order}).", "info")

    def _cmd_undo(self, _args=None):
        if not self.undo_stack:
            self._log("Nothing to undo.", "error")
            return
        snapshot = self.undo_stack.pop()
        redo_snapshot = {
            "tasks": [self._serialize_task(t) for t in self.tasks],
            "next_id": self.next_id,
        }
        self.redo_stack.append(redo_snapshot)
        self._restore_snapshot(snapshot)

    def _cmd_redo(self, _args=None):
        if not self.redo_stack:
            self._log("Nothing to redo.", "error")
            return
        snapshot = self.redo_stack.pop()
        undo_snapshot = {
            "tasks": [self._serialize_task(t) for t in self.tasks],
            "next_id": self.next_id,
        }
        self.undo_stack.append(undo_snapshot)
        self._restore_snapshot(snapshot)

    def _cmd_export(self, args):
        target = CSV_DEFAULT if not args else Path(args[0])
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "name",
                    "due",
                    "time",
                    "status",
                    "priority",
                    "recurrence",
                    "tag",
                    "category",
                    "archived",
                ],
            )
            writer.writeheader()
            for task in self.tasks:
                writer.writerow(
                    {
                        "name": task["name"],
                        "due": task["due"].isoformat() if task["due"] else "",
                        "time": task.get("time") or "",
                        "status": task["status"],
                        "priority": task.get("priority", "med"),
                        "recurrence": task.get("recurrence") or "",
                        "tag": task.get("tag") or "",
                        "category": task.get("category") or "",
                        "archived": "1" if task.get("archived") else "0",
                    }
                )
        self._log(f"Exported tasks to {target}.", "success")

    def _cmd_import(self, args):
        target = CSV_DEFAULT if not args else Path(args[0])
        if not target.exists():
            self._log("CSV file not found.", "error")
            return
        with target.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        if not rows:
            self._log("CSV file is empty.", "error")
            return
        self._push_undo()
        for row in rows:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            due = None
            raw_due = (row.get("due") or "").strip()
            if raw_due:
                try:
                    due = date.fromisoformat(raw_due)
                except ValueError:
                    due = self._parse_ddmm(raw_due)
            time_val = None
            raw_time = (row.get("time") or "").strip()
            if raw_time:
                time_val = self._parse_hhmm(raw_time) or raw_time
            status = (row.get("status") or "pending").strip().lower()
            if status not in ("pending", "completed"):
                status = "pending"
            priority = (row.get("priority") or "med").strip().lower()
            if priority not in ("low", "med", "high"):
                priority = "med"
            recurrence = (row.get("recurrence") or "").strip().lower() or None
            if recurrence and recurrence not in ("daily", "weekly", "monthly"):
                recurrence = None
            tag = (row.get("tag") or "").strip() or None
            category = (row.get("category") or "").strip() or None
            archived = (row.get("archived") or "").strip() in ("1", "true", "yes")
            self.tasks.append(
                {
                    "id": self.next_id,
                    "name": name,
                    "due": due,
                    "time": time_val,
                    "status": status,
                    "priority": priority,
                    "recurrence": recurrence,
                    "tag": tag,
                    "category": category,
                    "archived": archived,
                }
            )
            self.next_id += 1
        self._save_tasks()
        self._refresh_all("Imported tasks.", "success")

    def _schedule_reminders(self):
        self._tick_reminders()
        self.after(60000, self._schedule_reminders)

    def _tick_reminders(self):
        today = date.today()
        upcoming = [
            t
            for t in self.tasks
            if t["due"] and t["status"] != "completed" and not t.get("archived")
        ]
        if not upcoming:
            self.countdown_label.configure(text="Next due: --")
            return
        next_task = min(upcoming, key=lambda t: t["due"])
        days = (next_task["due"] - today).days
        if days < 0:
            self.countdown_label.configure(
                text=f"Next due: overdue by {abs(days)}d ({next_task['name']})"
            )
            key = ("overdue", next_task["id"], next_task["due"])
            if key not in self.notified:
                self.notified.add(key)
                self._log(
                    f"Overdue: {next_task['name']} ({self._format_date(next_task['due'])})",
                    "error",
                )
        elif days == 0:
            self.countdown_label.configure(
                text=f"Next due: today ({next_task['name']})"
            )
            key = (next_task["id"], next_task["due"])
            if key not in self.notified:
                self.notified.add(key)
                self._show_popup(
                    "TASK DUE TODAY",
                    f"{next_task['name']} is due today ({self._format_date(next_task['due'])}).",
                )
        else:
            self.countdown_label.configure(
                text=f"Next due: in {days}d ({next_task['name']})"
            )

    def _show_popup(self, title, message):
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.configure(bg=COLOR_BG)
        popup.geometry("420x180")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.attributes("-alpha", 0.94)

        border = tk.Frame(
            popup,
            bg=COLOR_BG,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
        )
        border.pack(fill="both", expand=True, padx=8, pady=8)

        header = tk.Label(
            border,
            text=title,
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        header.pack(pady=(12, 6))

        body = tk.Label(
            border,
            text=message,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            wraplength=360,
            justify="center",
        )
        body.pack(pady=(0, 10))

        btn = tk.Button(
            border,
            text="ACKNOWLEDGE",
            command=popup.destroy,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_BLUE,
            activebackground=self._blend(COLOR_BG, NEON_BLUE, 0.35),
            activeforeground=COLOR_BG,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=NEON_BLUE,
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn.pack(pady=(0, 12))

        popup.after(50, lambda: popup.focus_force())

    def _show_day_popup(self, selected):
        tasks = [t for t in self.tasks if t["due"] == selected and not t.get("archived")]
        popup = tk.Toplevel(self)
        popup.title("DAY VIEW")
        popup.configure(bg=COLOR_BG)
        popup.geometry("460x260")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.attributes("-alpha", 0.96)

        glass = tk.Canvas(popup, bg=COLOR_BG, highlightthickness=0, bd=0)
        glass.pack(fill="both", expand=True)
        self._draw_panel_grid(glass)

        header = tk.Label(
            glass,
            text=f"[ {self._format_date(selected)} ]",
            font=self.font_title,
            bg=COLOR_BG,
            fg=NEON_BLUE,
        )
        header.place(relx=0.5, rely=0.12, anchor="center")

        body = tk.Text(
            glass,
            bg=COLOR_BG,
            fg=NEON_GREEN,
            font=self.font_small,
            wrap="word",
            bd=0,
            highlightthickness=0,
        )
        body.place(relx=0.08, rely=0.22, relwidth=0.84, relheight=0.6)
        body.configure(state="normal")
        body.delete("1.0", "end")
        if not tasks:
            body.insert("end", "No tasks for this day.\n")
        else:
            for task in tasks:
                status = "x" if task["status"] == "completed" else " "
                time_text = self._format_time(task.get("time"))
                cat = task.get("category") or "Uncategorized"
                body.insert("end", f"[{status}] {task['name']}  {time_text} ({cat})\n")
        body.configure(state="disabled")

        btn = tk.Button(
            glass,
            text="CLOSE",
            command=popup.destroy,
            font=self.font_small,
            bg=COLOR_BG,
            fg=NEON_PINK,
            activebackground=self._blend(COLOR_BG, NEON_PINK, 0.35),
            activeforeground=COLOR_BG,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=NEON_PINK,
            cursor="hand2",
            padx=12,
            pady=4,
        )
        btn.place(relx=0.5, rely=0.88, anchor="center")


if __name__ == "__main__":
    app = TaskManagerApp()
    app.mainloop()

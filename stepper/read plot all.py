import csv
import io
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


def read_table(filename):
    """Read CSV/TXT tables, including old recordings without a header."""
    with open(filename, "rb") as stream:
        raw = stream.read()
    # Check byte-order marks before trying a legacy encoding, which can decode
    # UTF-16 bytes successfully but leave embedded NUL characters in the text.
    if raw.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encodings = ("utf-32",)
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings = ("utf-16",)
    elif b"\x00" in raw:
        # UTF-16 exported without a BOM needs explicit byte order. CSV headers
        # and separators provide ASCII bytes whose other byte is normally NUL.
        sample_bytes = raw[:4096]
        even = sample_bytes[0::2]
        odd = sample_bytes[1::2]
        even_nulls = even.count(0) / max(1, len(even))
        odd_nulls = odd.count(0) / max(1, len(odd))
        if odd_nulls > 0.3 and even_nulls < 0.1:
            encodings = ("utf-16-le",)
        elif even_nulls > 0.3 and odd_nulls < 0.1:
            encodings = ("utf-16-be",)
        else:
            raise ValueError("檔案含有無法辨識的空位元組，請另存為 UTF-8 CSV/TXT。")
    else:
        encodings = ("utf-8-sig", "cp950")
    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            break
        except UnicodeError:
            continue
    else:
        raise ValueError("無法辨識文字編碼，請使用 UTF-8 儲存檔案。")

    sample = "\n".join(text.splitlines()[:30])
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        # Detect from the header even when some data cells are missing.
        header = next((line for line in text.splitlines() if line.strip()), "")
        delimiter = next((sep for sep in (",", "\t", ";", "|") if sep in header), None)
    read_options = dict(sep=delimiter or r"\s+", engine="python")
    first = pd.read_csv(io.StringIO(text), header=None, nrows=1, dtype=str, **read_options)
    first_values = first.iloc[0].fillna("").str.strip().tolist()
    # A numeric/timestamp first cell indicates an old headerless recording.
    has_header = parse_time_column(pd.Series([first_values[0]])) is None
    df = pd.read_csv(io.StringIO(text), header=0 if has_header else None, **read_options)
    df.columns = ([str(column).strip() for column in df.columns] if has_header
                  else [f"Column {i + 1}" for i in range(len(df.columns))])
    df.attrs.update(has_header=has_header,
                    first_values=dict(zip(df.columns, first_values)))
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty or len(df.columns) < 2:
        raise ValueError("檔案需要至少一筆資料及兩個欄位。")
    return df


def parse_time_column(series):
    """Return numeric seconds, display label kind, and original timestamp strings."""
    raw = series.astype("string").str.strip()
    numeric = pd.to_numeric(raw, errors="coerce").astype(float)
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    present = raw.notna() & raw.ne("")
    count = int(present.sum())
    if not count:
        return None
    if numeric.notna().sum() >= max(1, count * 0.8):
        return numeric, "seconds", raw.fillna("").tolist()
    clock_mask = raw.str.fullmatch(
        r"(?:[01]?\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?", na=False)
    if clock_mask.sum() >= max(1, count * 0.8):
        seconds = pd.to_timedelta(raw.where(clock_mask), errors="coerce").dt.total_seconds()
        offsets = (seconds.dropna().diff() < -12 * 3600).cumsum() * 86400
        seconds = seconds + offsets.reindex(seconds.index, fill_value=0)
    else:
        # Require a date and clock, rather than interpreting arbitrary text as dates.
        date_mask = raw.str.contains(r"\d{2,4}[-/]\d{1,2}[-/]\d{1,4}.*\d{1,2}:\d{2}", na=False)
        if date_mask.sum() < max(1, count * 0.8):
            return None
        dates = pd.to_datetime(raw.where(date_mask), format="mixed", errors="coerce", utc=True)
        if not dates.notna().any():
            return None
        seconds = (dates - dates.dropna().iloc[0]).dt.total_seconds()
    if not seconds.notna().any():
        return None
    return seconds - seconds.dropna().iloc[0], "elapsed seconds", raw.fillna("").tolist()


def prepare_data(filename):
    """Detect named times first; otherwise inspect the first five columns."""
    df = read_table(filename)
    aliases = {"time", "t", "dt", "timestamp", "datetime", "date", "rel_time",
               "elapsed", "elapsed_time", "seconds", "second", "sec", "時間"}
    named = [col for col in df.columns if col.casefold() in aliases]
    candidates = {}
    for column in dict.fromkeys(named + list(df.columns[:5])):
        parsed = parse_time_column(df[column])
        if parsed is None:
            continue
        seconds, kind, strings = parsed
        if column not in named and kind == "seconds":
            if named:
                continue
            # Numeric sensor readings can resemble seconds. Prefer a steadily
            # increasing sequence when no time header is given. Allow logger
            # jitter rather than requiring perfectly uniform sampling.
            valid = seconds.dropna()
            steps = valid.diff().dropna()
            paired_clock = (not df.attrs["has_header"] and column == df.columns[0]
                            and any(parse_time_column(df[other]) is not None
                                    and parse_time_column(df[other])[1] != "seconds"
                                    for other in df.columns[1:5]))
            if len(valid) < 3:
                if not paired_clock or valid.empty:
                    continue
            elif (not (steps >= 0).all() or (steps > 0).mean() < 0.95
                  or steps.quantile(0.9) > steps.median() * 3):
                continue
        display_name = (column if df.attrs["has_header"]
                        else df.attrs["first_values"][column])
        candidates[column] = {"values": seconds, "label": f"{display_name} ({kind})",
                              "display_name": display_name, "strings": strings}
    numeric = {}
    for column in df.columns:
        values = pd.to_numeric(df[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        if values.notna().any():
            numeric[column] = values
    columns = [column for column in numeric if column not in candidates]
    # Ambiguous unnamed numeric ramps may all look like clocks. Keep them
    # available as signals instead of rejecting an otherwise usable table.
    if not columns and not named:
        columns = list(numeric)
    if not columns:
        raise ValueError("沒有可繪製的數值欄位。")
    for column in columns:
        df[column] = numeric[column]
    df.attrs.update(time_candidates=candidates, data_columns=columns)
    return df


def x_data(df, column):
    if column is None:
        return pd.Series(np.arange(1, len(df) + 1), index=df.index), "Sample number (1-based)"
    candidate = df.attrs["time_candidates"][column]
    return candidate["values"], candidate["label"]


def add_x_controls(parent, df, selected, callback):
    """Use separate option IDs so a column name cannot collide with sample mode."""
    frame = tk.LabelFrame(parent, text="X 軸選擇")
    frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=3)
    options = [None] + list(df.attrs["time_candidates"])
    variable = tk.IntVar(master=frame, value=options.index(selected))
    for index, column in enumerate(options):
        label = ("資料數（第 1 筆起）" if column is None
                 else f"時間：{df.attrs['time_candidates'][column]['display_name']}")
        tk.Radiobutton(frame, text=label, variable=variable, value=index,
                       command=lambda col=column: callback(col)).grid(
                           row=index // 4, column=index % 4, sticky="w", padx=5)
    return frame, variable


class SeismicViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Seismic Viewer")
        self.root.geometry("1200x900")
        self.df = None
        self.cursors = []
        self.annotations = []
        self.cursor_dots = []
        self.config_file = "last_dir.json"
        self.data_dir = os.path.dirname(os.path.abspath(__file__))
        self.load_config()

        self.left = tk.Frame(root, width=260)
        self.left.pack(side=tk.LEFT, fill=tk.Y)
        self.right = tk.Frame(root)
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Button(self.left, text="選擇資料夾", command=self.select_folder).pack(pady=5)
        self.file_listbox = tk.Listbox(self.left, width=35)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(self.left, command=self.file_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        self.x_controls = None
        self.x_column = None
        self.fig, ax = plt.subplots()
        self.axs = [ax]
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.right)
        self.toolbar.update()
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.axis_buttons = tk.Frame(self.right)
        self.axis_buttons.pack()
        self.load_files()

    def load_config(self):
        try:
            with open(self.config_file, encoding="utf8") as stream:
                directory = json.load(stream).get("last_data_dir")
            if directory and os.path.isdir(directory):
                self.data_dir = directory
        except (OSError, ValueError):
            pass

    def save_config(self):
        with open(self.config_file, "w", encoding="utf8") as stream:
            json.dump({"last_data_dir": self.data_dir}, stream, indent=2, ensure_ascii=False)

    def load_files(self):
        self.file_listbox.delete(0, tk.END)
        self.files = sorted((entry.path for entry in os.scandir(self.data_dir)
                             if entry.is_file() and os.path.splitext(entry.name)[1].lower() in (".csv", ".txt")),
                            reverse=True)
        if not self.files:
            self.file_listbox.insert(tk.END, "No CSV/TXT files")
            return
        for filename in self.files:
            self.file_listbox.insert(tk.END, os.path.basename(filename))
        self.file_listbox.selection_set(0)
        self.on_file_select(None)

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.data_dir)
        if folder:
            self.data_dir = folder
            self.save_config()
            self.load_files()

    def read_data(self, filename):
        return prepare_data(filename)

    def on_file_select(self, event):
        selected = self.file_listbox.curselection()
        if not selected or selected[0] >= len(self.files):
            return
        filename = self.files[selected[0]]
        try:
            df = self.read_data(filename)
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            messagebox.showerror("讀取失敗", f"{os.path.basename(filename)}\n{exc}")
            return
        self.df = df
        self.plot_name = os.path.basename(filename)
        self.x_column = next(iter(df.attrs["time_candidates"]), None)
        if self.x_controls is not None:
            self.x_controls.destroy()
        self.x_controls, self.x_variable = add_x_controls(
            self.right, df, self.x_column, self.change_x_axis)
        # Keep the selector above the expanding chart.
        self.x_controls.pack_configure(before=self.canvas.get_tk_widget())
        self.plot_data(self.plot_name)

    def change_x_axis(self, column):
        self.x_column = column
        self.plot_data(self.plot_name)

    def plot_data(self, name):
        df = self.df
        columns = df.attrs["data_columns"]
        times, time_label = x_data(df, self.x_column)
        self.fig.clear()
        self.axs = self.fig.subplots(len(columns), 1, sharex=True, squeeze=False)[:, 0]
        self.cursors, self.annotations, self.cursor_dots = [], [], []
        for index, (ax, column) in enumerate(zip(self.axs, columns)):
            ax.plot(times, df[column], color=f"C{index % 10}", lw=1)
            ax.set_ylabel(column)
            ax.grid(True)
            line = ax.axvline(times.dropna().iloc[0], color="black", linestyle=":", visible=False)
            txt = ax.text(0.01, 0.7, "", transform=ax.transAxes, visible=False,
                          bbox=dict(boxstyle="round", fc="white", alpha=0.5))
            dot, = ax.plot([], [], "o", color="black", visible=False)
            self.cursors.append(line)
            self.annotations.append(txt)
            self.cursor_dots.append(dot)
        self.axs[0].set_title(name)
        self.axs[-1].set_xlabel(time_label)
        self.fig.tight_layout()
        self.toolbar.update()
        for button in self.axis_buttons.winfo_children():
            button.destroy()
        for index, column in enumerate(columns):
            tk.Button(self.axis_buttons, text=column,
                      command=lambda col=column: self.open_single_axis(col)).grid(
                          row=index // 6, column=index % 6, padx=5, pady=2)
        self.canvas.draw()

    @staticmethod
    def cursor_text(df, index, column, time_column):
        label = f"Sample: {index + 1}"
        if time_column is not None:
            original = df.attrs["time_candidates"][time_column]["strings"][index]
            label += f"  {time_column}: {original}"
        return f"{label}\n{column}: {df[column].iloc[index]:.6g}"

    def on_mouse_move(self, event):
        if self.df is None or event.xdata is None:
            for artist in self.cursors + self.annotations + self.cursor_dots:
                artist.set_visible(False)
        else:
            times, _ = x_data(self.df, self.x_column)
            index = int(np.nanargmin(np.abs(times - event.xdata)))
            time = times.iloc[index]
            for column, line, txt, dot in zip(self.df.attrs["data_columns"], self.cursors,
                                               self.annotations, self.cursor_dots):
                line.set_xdata([time, time])
                dot.set_data([time], [self.df[column].iloc[index]])
                txt.set_text(self.cursor_text(self.df, index, column, self.x_column))
                for artist in (line, dot, txt):
                    artist.set_visible(True)
        self.canvas.draw_idle()

    @staticmethod
    def zoom(ax, event):
        if event.xdata is None:
            return
        factor = 1 / 1.1 if event.step > 0 else 1.1
        xmin, xmax = ax.get_xlim()
        ax.set_xlim(event.xdata + (xmin - event.xdata) * factor,
                    event.xdata + (xmax - event.xdata) * factor)

    def on_scroll(self, event):
        # Shared axes propagate the limit change to all panels automatically.
        self.zoom(self.axs[0], event)
        self.canvas.draw_idle()

    def open_single_axis(self, axis):
        if self.df is None:
            return
        # Capture this dataset so changing the main selection does not alter this window.
        df = self.df
        win = tk.Toplevel(self.root)
        win.title(axis)
        win.geometry("900x600")
        selected_column = self.x_column
        times, time_label = x_data(df, selected_column)

        def change_axis(column):
            nonlocal selected_column, times
            selected_column = column
            times, label = x_data(df, column)
            signal.set_xdata(times)
            ax.set_xlabel(label)
            ax.relim()
            ax.set_autoscalex_on(True)
            ax.autoscale_view()
            for artist in (line, dot, txt):
                artist.set_visible(False)
            toolbar.update()
            canvas.draw_idle()

        controls, variable = add_x_controls(win, df, selected_column, change_axis)
        fig, ax = plt.subplots()
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, win)
        signal, = ax.plot(times, df[axis])
        ax.set_xlabel(time_label)
        ax.set_ylabel(axis)
        ax.grid(True)
        line = ax.axvline(times.dropna().iloc[0], color="black", linestyle=":", visible=False)
        dot, = ax.plot([], [], "o", color="black", visible=False)
        txt = ax.text(0.02, 0.9, "", transform=ax.transAxes, visible=False,
                      bbox=dict(boxstyle="round", fc="white", alpha=0.5))

        def on_move(event):
            visible = event.xdata is not None
            if visible:
                index = int(np.nanargmin(np.abs(times - event.xdata)))
                time = times.iloc[index]
                line.set_xdata([time, time])
                dot.set_data([time], [df[axis].iloc[index]])
                txt.set_text(self.cursor_text(df, index, axis, selected_column))
            for artist in (line, dot, txt):
                artist.set_visible(visible)
            canvas.draw_idle()

        def on_scroll(event):
            self.zoom(ax, event)
            canvas.draw_idle()

        def on_close():
            plt.close(fig)
            win.destroy()

        win.x_variable = variable
        win.protocol("WM_DELETE_WINDOW", on_close)
        canvas.mpl_connect("motion_notify_event", on_move)
        canvas.mpl_connect("scroll_event", on_scroll)
        canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = SeismicViewerApp(root)
    root.mainloop()

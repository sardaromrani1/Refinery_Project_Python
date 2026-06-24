"""
projects_form.py
────────────────
Full CRUD Tkinter form for the PROJECTT table in Refinery_Project.

Table schema
────────────
CREATE TABLE PROJECTT (
    Project_ID INT IDENTITY(1,1) PRIMARY KEY,
    Project_Name VARCHAR(150) NOT NULL,
    Start_Date DATE,
    End_Date DATE,
    Status VARCHAR(30)
);

Fixes applied vs. the original attempt
────────────────────────────────────────
1. Tuple bug – row values accessed with row[index], not the whole tuple.
2. Input validation – required field and date-format checks before any DB call.
3. Field clearing – all entry widgets reset after every successful operation.
4. Confirmation dialogs – Update / Delete now ask "Are you sure?" first.
5. Error handling – every DB call is wrapped in try/except with user-visible messages.
6. Treeview selection – clicking a row populates the form for easy edit/delete.
7. Status dropdown – uses ttk.Combobox with fixed choices to prevent typos.
8. Column-scoped search – user picks which column to search (ID, Project Name,
   Start Date, End Date, Status) via a dropdown next to the search box.
9. Calendar date pickers – Start Date / End Date fields in the details panel use
   a clickable calendar (tkcalendar.DateEntry) instead of free-typed text.
10. Date-range search – selecting "Start Date" or "End Date" in the search
    dropdown swaps the keyword box for two calendar pickers ("From" / "To")
    so you can search a date range instead of a single keyword.

Requires the 'tkcalendar' package:
    pip install tkcalendar
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from tkcalendar import DateEntry

from db_connection import get_connection

# ── Allowed status values (must match your CHECK constraint if any) ──────────
STATUS_OPTIONS = ["Planning", "In Progress", "On Hold", "Completed", "Cancelled"]
DATE_FMT = "%Y-%m-%d" # format expected by SQL Server DATE columns

# ── Search column options: display label -> actual SQL column name ──────────
SEARCH_COLUMNS = {
    "Project ID": "Project_ID",
    "Project Name": "Project_Name",
    "Start Date": "Start_Date",
    "End Date": "End_Date",
    "Status": "Status",
}

# Columns that use a date-range search (From / To calendars) instead of a keyword box
DATE_RANGE_COLUMNS = {"Start Date": "Start_Date", "End Date": "End_Date"}


# ────────────────────────────────────────────────────────────────────────────
class ProjectsForm(tk.Frame):
    """
    A dark-themed frame with:
      • A data-entry panel (top/left) with calendar date pickers
      • CRUD buttons
      • A searchable, sortable Treeview listing all projects
      • Column-scoped search: keyword search for text columns, date-range
        search (From/To calendars) for Start Date / End Date
    """

    # ── colours ──────────────────────────────────────────────────────────────
    BG = "#1e2327"
    PANEL_BG = "#252b30"
    FG = "#e0e0e0"
    ACCENT = "#00b4d8"
    BTN_BG = "#00b4d8"
    BTN_FG = "#ffffff"
    ENTRY_BG = "#2e3540"
    SEL_BG = "#00b4d8"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, bg=self.BG, *args, **kwargs)
        self._selected_id = None # Project_ID of the currently selected row
        self._build_ui()
        self.load_projects()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(
            self, text="Projects Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar (column selector + dynamic keyword/date-range area) ───
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search by:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_column_var = tk.StringVar(value="Project Name")
        search_column_combo = ttk.Combobox(
            search_frame, textvariable=self.search_column_var,
            values=list(SEARCH_COLUMNS.keys()), state="readonly",
            font=("Segoe UI", 10), width=14
        )
        search_column_combo.pack(side=tk.LEFT, padx=(0, 10))
        # Rebuild the search input area (keyword box vs. date-range pickers)
        # whenever the chosen column changes, then re-run the search.
        search_column_combo.bind("<<ComboboxSelected>>", self._on_search_column_change)

        # Container that holds either the keyword Entry OR the From/To DateEntry pair.
        # Its contents are swapped dynamically by _on_search_column_change().
        self.search_input_frame = tk.Frame(search_frame, bg=self.BG)
        self.search_input_frame.pack(side=tk.LEFT)

        # Keyword search variable (used for text columns: ID, Name, Status)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_projects())

        # Date-range widgets are created on demand in _build_keyword_search() /
        # _build_date_range_search(); references stored here once created.
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

        # Build the initial search input (default column is "Project Name" -> keyword box)
        self._build_keyword_search()

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Project Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        labels = ["Project Name *", "Start Date", "End Date", "Status"]
        self._entries = {}

        for i, lbl in enumerate(labels):
            tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                     font=("Segoe UI", 10), anchor="w").grid(
                row=i, column=0, sticky="w", padx=14, pady=5
            )

            if lbl == "Status":
                widget = ttk.Combobox(
                    panel, values=STATUS_OPTIONS, state="readonly",
                    font=("Segoe UI", 10), width=28
                )
                widget.set(STATUS_OPTIONS[0])
            elif lbl in ("Start Date", "End Date"):
                # Calendar date picker. date_pattern controls the .get() string format.
                widget = DateEntry(
                    panel, date_pattern="yyyy-mm-dd",
                    font=("Segoe UI", 10), width=27,
                    background=self.ACCENT, foreground="#ffffff",
                    borderwidth=0, state="readonly"
                )
                # Blank by default — DateEntry defaults to "today"; we want the
                # form to start empty since dates are optional for a project.
                widget.delete(0, tk.END)
            else:
                widget = tk.Entry(
                    panel, bg=self.ENTRY_BG, fg=self.FG,
                    insertbackground=self.FG, relief=tk.FLAT,
                    font=("Segoe UI", 10), width=30
                )
            widget.grid(row=i, column=1, padx=14, pady=5, sticky="w")
            self._entries[lbl] = widget

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add", self.add_project),
            ("✏️ Update", self.update_project),
            ("🗑️ Delete", self.delete_project),
            ("🔄 Refresh", self.load_projects),
            ("✖ Clear", self.clear_fields),
        ]
        for text, cmd in buttons:
            tk.Button(
                btn_frame, text=text, command=cmd,
                bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
                relief=tk.FLAT, font=("Segoe UI", 10, "bold"),
                width=11, cursor="hand2"
            ).pack(side=tk.LEFT, padx=5)

        # ── Treeview ──────────────────────────────────────────────────────────
        tree_frame = tk.Frame(self, bg=self.BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))

        cols = ("ID", "Project Name", "Start Date", "End Date", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 selectmode="browse")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=self.PANEL_BG, foreground=self.FG,
                        rowheight=26, fieldbackground=self.PANEL_BG,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading",
                        background=self.ACCENT, foreground="#ffffff",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", self.SEL_BG)])

        col_widths = {"ID": 55, "Project Name": 260, "Start Date": 110,
                      "End Date": 110, "Status": 120}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ── Search-input builders ──────────────────────────────────────────────
    def _clear_search_input_frame(self):
        for child in self.search_input_frame.winfo_children():
            child.destroy()
        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

    def _build_keyword_search(self):
        """Show a single keyword Entry (used for ID / Name / Status search)."""
        self._clear_search_input_frame()

        tk.Label(self.search_input_frame, text="Keyword:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_var.set("") # reset previous keyword
        self._search_keyword_entry = tk.Entry(
            self.search_input_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        )
        self._search_keyword_entry.pack(side=tk.LEFT)

    def _build_date_range_search(self):
        """Show two calendar pickers: 'From' and 'To' (used for date-column search)."""
        self._clear_search_input_frame()

        tk.Label(self.search_input_frame, text="From:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._search_date_from = DateEntry(
            self.search_input_frame, date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 10), width=12,
            background=self.ACCENT, foreground="#ffffff",
            borderwidth=0, state="readonly"
        )
        self._search_date_from.delete(0, tk.END) # start blank
        self._search_date_from.pack(side=tk.LEFT, padx=(0, 10))
        self._search_date_from.bind("<<DateEntrySelected>>", lambda _e: self.load_projects())

        tk.Label(self.search_input_frame, text="To:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self._search_date_to = DateEntry(
            self.search_input_frame, date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 10), width=12,
            background=self.ACCENT, foreground="#ffffff",
            borderwidth=0, state="readonly"
        )
        self._search_date_to.delete(0, tk.END) # start blank
        self._search_date_to.pack(side=tk.LEFT)
        self._search_date_to.bind("<<DateEntrySelected>>", lambda _e: self.load_projects())

        # Small "Clear dates" button so the user can reset without retyping
        tk.Button(
            self.search_input_frame, text="✖", command=self._clear_date_range,
            bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
            relief=tk.FLAT, font=("Segoe UI", 9, "bold"), width=2, cursor="hand2"
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _clear_date_range(self):
        if self._search_date_from is not None:
            self._search_date_from.delete(0, tk.END)
        if self._search_date_to is not None:
            self._search_date_to.delete(0, tk.END)
        self.load_projects()

    def _on_search_column_change(self, _event=None):
        column_label = self.search_column_var.get()
        if column_label in DATE_RANGE_COLUMNS:
            self._build_date_range_search()
        else:
            self._build_keyword_search()
        self.load_projects()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        widget = self._entries[label]
        return widget.get().strip()

    def _validate_inputs(self) -> bool:
        name = self._get_field("Project Name *")
        if not name:
            messagebox.showwarning("Validation", "Project Name is required.")
            return False

        # DateEntry already enforces yyyy-mm-dd formatting via the calendar,
        # but we still guard against a manually-cleared/blank field here.
        for lbl in ("Start Date", "End Date"):
            val = self._get_field(lbl)
            if val:
                try:
                    datetime.strptime(val, DATE_FMT)
                except ValueError:
                    messagebox.showwarning(
                        "Validation",
                        f"'{lbl}' must be in YYYY-MM-DD format (e.g. 2025-01-31)."
                    )
                    return False

        start = self._get_field("Start Date")
        end = self._get_field("End Date")
        if start and end and start > end:
            messagebox.showwarning("Validation", "Start Date cannot be after End Date.")
            return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set(STATUS_OPTIONS[0])
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _set_date_field(self, label: str, value):
        """Set a DateEntry field's text directly (value may be a date string or empty)."""
        widget = self._entries[label]
        widget.delete(0, tk.END)
        if value:
            widget.insert(0, value)

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (ID, Project_Name, Start_Date, End_Date, Status)
        self._selected_id = int(values[0])

        self._entries["Project Name *"].delete(0, tk.END)
        self._entries["Project Name *"].insert(0, values[1])

        self._set_date_field("Start Date", values[2] if values[2] else "")
        self._set_date_field("End Date", values[3] if values[3] else "")

        self._entries["Status"].set(values[4] if values[4] else STATUS_OPTIONS[0])

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_projects(self, *_):
        """Read projects, filtered by the selected column, into the treeview.

        Text columns (ID / Project Name / Status) use a keyword LIKE search.
        Date columns (Start Date / End Date) use a From/To range search.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)

        column_label = self.search_column_var.get()
        sql_column = SEARCH_COLUMNS.get(column_label, "Project_Name")
        keyword_active = False

        try:
            conn = get_connection()
            cursor = conn.cursor()

            if column_label in DATE_RANGE_COLUMNS:
                date_from = self._search_date_from.get().strip() if self._search_date_from else ""
                date_to = self._search_date_to.get().strip() if self._search_date_to else ""

                conditions, params = [], []
                if date_from:
                    conditions.append(f"{sql_column} >= ?")
                    params.append(date_from)
                if date_to:
                    conditions.append(f"{sql_column} <= ?")
                    params.append(date_to)

                where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
                cursor.execute(
                    "SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                    "FROM PROJECTT" + where_clause + " ORDER BY Project_ID DESC",
                    params
                )
                keyword_active = bool(conditions)

            else:
                keyword = self.search_var.get().strip()
                keyword_active = bool(keyword)

                if keyword:
                    if sql_column == "Project_ID":
                        if keyword.isdigit():
                            cursor.execute(
                                "SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                                "FROM PROJECTT WHERE Project_ID = ? "
                                "ORDER BY Project_ID DESC",
                                (int(keyword),)
                            )
                        else:
                            conn.close()
                            messagebox.showinfo("Search", "Project ID must be a number.")
                            return
                    else:
                        cursor.execute(
                            f"SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                            f"FROM PROJECTT WHERE {sql_column} LIKE ? "
                            f"ORDER BY Project_ID DESC",
                            (f"%{keyword}%",)
                        )
                else:
                    cursor.execute(
                        "SELECT Project_ID, Project_Name, Start_Date, End_Date, Status "
                        "FROM PROJECTT ORDER BY Project_ID DESC"
                    )

            rows = cursor.fetchall()
            for row in rows:
                # row[0]=Project_ID row[1]=Project_Name row[2]=Start_Date
                # row[3]=End_Date row[4]=Status
                start = str(row[2])[:10] if row[2] else ""
                end = str(row[3])[:10] if row[3] else ""
                self.tree.insert("", tk.END, values=(row[0], row[1], start, end, row[4] or ""))

            conn.close()

            if keyword_active and not rows:
                messagebox.showinfo("Search", "No projects matched your search criteria.")

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load projects:\n{exc}")

    def add_project(self):
        if not self._validate_inputs():
            return

        name = self._get_field("Project Name *")
        start = self._none_if_empty(self._get_field("Start Date"))
        end = self._none_if_empty(self._get_field("End Date"))
        status = self._get_field("Status")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO PROJECTT (Project_Name, Start_Date, End_Date, Status) "
                "VALUES (?, ?, ?, ?)",
                (name, start, end, status)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Project '{name}' added successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add project:\n{exc}")

    def update_project(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a project from the list first.")
            return
        if not self._validate_inputs():
            return

        name = self._get_field("Project Name *")
        start = self._none_if_empty(self._get_field("Start Date"))
        end = self._none_if_empty(self._get_field("End Date"))
        status = self._get_field("Status")

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Project ID {self._selected_id}?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE PROJECTT "
                "SET Project_Name=?, Start_Date=?, End_Date=?, Status=? "
                "WHERE Project_ID=?",
                (name, start, end, status, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Project updated successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update project:\n{exc}")

    def delete_project(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a project from the list first.")
            return

        name = self._get_field("Project Name *")
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Project ID {self._selected_id}"
                                   f" – '{name}'?\nThis cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM PROJECTT WHERE Project_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Project deleted successfully.")
            self.clear_fields()
            self.load_projects()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete project:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Projects Form")
    root.geometry("950x640")
    root.configure(bg="#1e2327")
    ProjectsForm(root)
    root.mainloop()
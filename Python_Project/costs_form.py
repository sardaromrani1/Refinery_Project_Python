"""
costs_form.py
─────────────
Full CRUD Tkinter form for the COSTS table in Refinery_Project.

Table schema
────────────
CREATE TABLE COSTS (
    Cost_ID VARCHAR(20) PRIMARY KEY,
    Activity_ID VARCHAR(20),
    Cost_Type VARCHAR(50),
    Budgeted_Amount DECIMAL(15,2),
    Actual_Amount DECIMAL(15,2),
    Date_Recorded DATE,
    CONSTRAINT fk_costs_activity FOREIGN KEY (Activity_ID)
        REFERENCES WBS_ACTIVITIES(Activity_ID)
);

Notes
─────
• Cost_ID is a user-supplied VARCHAR primary key (not auto-generated).
• Activity_ID is a FK dropdown loaded from WBS_ACTIVITIES at startup.
• Budgeted_Amount and Actual_Amount validated as non-negative decimals.
• Date_Recorded uses a clickable calendar (tkcalendar.DateEntry) instead of
  free-typed text.
• Variance (Actual - Budgeted) is calculated and shown read-only in the treeview.
• Search bar has a "Search by" column dropdown. Text columns (Cost ID,
  Activity ID, Cost Type) use a keyword box; Date Recorded swaps the keyword
  box for a "From" / "To" calendar range picker.

Requires the 'tkcalendar' package:
    pip install tkcalendar
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal, InvalidOperation

from tkcalendar import DateEntry

from db_connection import get_connection

COST_TYPE_OPTIONS = [
    "Labour", "Equipment", "Material", "Subcontract",
    "Engineering", "Procurement", "Construction", "Other"
]
DATE_FMT = "%Y-%m-%d"

# ── Search column options: display label -> actual SQL column name ──────────
SEARCH_COLUMNS = {
    "Cost ID": "Cost_ID",
    "Activity ID": "Activity_ID",
    "Cost Type": "Cost_Type",
    "Date Recorded": "Date_Recorded",
}

# Columns that use a date-range search (From / To calendars) instead of a keyword box
DATE_RANGE_COLUMNS = {"Date Recorded": "Date_Recorded"}


class CostsForm(tk.Frame):

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
        self._selected_id = None # Cost_ID of currently selected row
        self._build_ui()
        self.load_costs()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            self, text="Costs Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar (column selector + dynamic keyword/date-range area) ───
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search by:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))

        self.search_column_var = tk.StringVar(value="Cost ID")
        search_column_combo = ttk.Combobox(
            search_frame, textvariable=self.search_column_var,
            values=list(SEARCH_COLUMNS.keys()), state="readonly",
            font=("Segoe UI", 10), width=14
        )
        search_column_combo.pack(side=tk.LEFT, padx=(0, 10))
        search_column_combo.bind("<<ComboboxSelected>>", self._on_search_column_change)

        # Container that holds either the keyword Entry OR the From/To DateEntry pair.
        self.search_input_frame = tk.Frame(search_frame, bg=self.BG)
        self.search_input_frame.pack(side=tk.LEFT)

        # Keyword search variable (used for text columns)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_costs())

        self._search_keyword_entry = None
        self._search_date_from = None
        self._search_date_to = None

        self._build_keyword_search()

        # Entry panel – two columns
        panel = tk.LabelFrame(
            self, text=" Cost Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        # Left column fields
        left_fields = [
            ("Cost ID *", "entry"),
            ("Activity ID", "combo_db"), # FK from WBS_ACTIVITIES
            ("Cost Type", "combo"),
        ]
        # Right column fields
        right_fields = [
            ("Budgeted Amount", "entry"),
            ("Actual Amount", "entry"),
            ("Date Recorded", "date"),
        ]

        self._entries = {}

        for col_offset, field_group in enumerate([left_fields, right_fields]):
            for row_idx, (lbl, wtype) in enumerate(field_group):
                tk.Label(panel, text=lbl, bg=self.PANEL_BG, fg=self.FG,
                         font=("Segoe UI", 10), anchor="w").grid(
                    row=row_idx, column=col_offset * 2,
                    sticky="w", padx=14, pady=6
                )
                if wtype == "combo":
                    widget = ttk.Combobox(
                        panel, values=COST_TYPE_OPTIONS, state="readonly",
                        font=("Segoe UI", 10), width=22
                    )
                    widget.set(COST_TYPE_OPTIONS[0])
                elif wtype == "combo_db":
                    widget = ttk.Combobox(
                        panel, values=[], state="readonly",
                        font=("Segoe UI", 10), width=22
                    )
                elif wtype == "date":
                    # Calendar date picker. date_pattern controls the .get() string format.
                    widget = DateEntry(
                        panel, date_pattern="yyyy-mm-dd",
                        font=("Segoe UI", 10), width=21,
                        background=self.ACCENT, foreground="#ffffff",
                        borderwidth=0, state="readonly"
                    )
                    # Blank by default — DateEntry defaults to "today"; the date
                    # is optional at record-creation time.
                    widget.delete(0, tk.END)
                else:
                    widget = tk.Entry(
                        panel, bg=self.ENTRY_BG, fg=self.FG,
                        insertbackground=self.FG, relief=tk.FLAT,
                        font=("Segoe UI", 10), width=24
                    )
                widget.grid(row=row_idx, column=col_offset * 2 + 1,
                            padx=14, pady=6, sticky="w")
                self._entries[lbl] = widget

        # Load FK dropdown
        self._load_activity_ids()

        # Button row
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)
        for text, cmd in [
            ("➕ Add", self.add_cost),
            ("✏️ Update", self.update_cost),
            ("🗑️ Delete", self.delete_cost),
            ("🔄 Refresh", self.load_costs),
            ("✖ Clear", self.clear_fields),
        ]:
            tk.Button(
                btn_frame, text=text, command=cmd,
                bg=self.BTN_BG, fg=self.BTN_FG, activebackground="#0096c7",
                relief=tk.FLAT, font=("Segoe UI", 10, "bold"),
                width=11, cursor="hand2"
            ).pack(side=tk.LEFT, padx=5)

        # Treeview
        tree_frame = tk.Frame(self, bg=self.BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))

        cols = ("Cost ID", "Activity ID", "Cost Type",
                "Budgeted", "Actual", "Variance", "Date Recorded")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                 show="headings", selectmode="browse")

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

        col_widths = {
            "Cost ID": 100, "Activity ID": 100, "Cost Type": 120,
            "Budgeted": 110, "Actual": 110, "Variance": 110,
            "Date Recorded": 110
        }
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
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
        """Show a single keyword Entry (used for Cost ID / Activity ID / Cost Type)."""
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
        """Show two calendar pickers: 'From' and 'To' (used for Date Recorded search)."""
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
        self._search_date_from.bind("<<DateEntrySelected>>", lambda _e: self.load_costs())

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
        self._search_date_to.bind("<<DateEntrySelected>>", lambda _e: self.load_costs())

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
        self.load_costs()

    def _on_search_column_change(self, _event=None):
        column_label = self.search_column_var.get()
        if column_label in DATE_RANGE_COLUMNS:
            self._build_date_range_search()
        else:
            self._build_keyword_search()
        self.load_costs()

    # ── FK dropdown loader ────────────────────────────────────────────────────
    def _load_activity_ids(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Activity_ID FROM WBS_ACTIVITIES ORDER BY Activity_ID"
            )
            ids = [r[0] for r in cursor.fetchall()]
            conn.close()
            self._entries["Activity ID"]["values"] = ids
            if ids:
                self._entries["Activity ID"].set(ids[0])
        except Exception:
            pass # table may not exist yet; leave dropdown empty

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _none_if_empty(self, val: str):
        return val if val else None

    def _parse_decimal(self, val: str, label: str):
        """Return Decimal or None; show warning and return False on bad input."""
        if not val:
            return None
        try:
            d = Decimal(val)
            if d < 0:
                raise InvalidOperation
            return d
        except InvalidOperation:
            messagebox.showwarning(
                "Validation",
                f"'{label}' must be a non-negative number (e.g. 12500.00)."
            )
            return False # sentinel – distinct from None

    def _validate_inputs(self) -> bool:
        if not self._get("Cost ID *"):
            messagebox.showwarning("Validation", "Cost ID is required.")
            return False

        for lbl in ("Budgeted Amount", "Actual Amount"):
            result = self._parse_decimal(self._get(lbl), lbl)
            if result is False:
                return False

        # DateEntry already enforces yyyy-mm-dd formatting via the calendar,
        # but we still guard against a manually-cleared/blank field here.
        date_val = self._get("Date Recorded")
        if date_val:
            try:
                datetime.strptime(date_val, DATE_FMT)
            except ValueError:
                messagebox.showwarning(
                    "Validation",
                    "Date Recorded must be in YYYY-MM-DD format (e.g. 2025-06-30)."
                )
                return False

        return True

    def clear_fields(self):
        self._selected_id = None
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                vals = widget["values"]
                widget.set(vals[0] if vals else "")
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
        v = self.tree.item(selected[0], "values")
        # v = (Cost_ID, Activity_ID, Cost_Type, Budgeted, Actual, Variance, Date_Recorded)
        self._selected_id = v[0]

        self._entries["Cost ID *"].delete(0, tk.END)
        self._entries["Cost ID *"].insert(0, v[0] or "")

        self._entries["Activity ID"].set(v[1] or "")
        self._entries["Cost Type"].set(v[2] or COST_TYPE_OPTIONS[0])

        self._entries["Budgeted Amount"].delete(0, tk.END)
        self._entries["Budgeted Amount"].insert(0, v[3] or "")

        self._entries["Actual Amount"].delete(0, tk.END)
        self._entries["Actual Amount"].insert(0, v[4] or "")

        # v[5] is the computed, read-only Variance column — not editable, skip.

        self._set_date_field("Date Recorded", v[6] if v[6] else "")

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0].replace(",", ""))
                      if t[0] else 0, reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    @staticmethod
    def _fmt_decimal(val) -> str:
        """Format a DB decimal value as a 2-dp string, or empty string."""
        if val is None:
            return ""
        try:
            return f"{Decimal(str(val)):.2f}"
        except Exception:
            return str(val)

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_costs(self, *_):
        """Read costs, filtered by the selected search column, into the treeview.

        Text columns (Cost ID / Activity ID / Cost Type) use a keyword LIKE
        search. Date Recorded uses a From/To range search.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)

        column_label = self.search_column_var.get()
        sql_column = SEARCH_COLUMNS.get(column_label, "Cost_ID")
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
                    "SELECT Cost_ID, Activity_ID, Cost_Type, "
                    "Budgeted_Amount, Actual_Amount, Date_Recorded "
                    "FROM COSTS" + where_clause + " ORDER BY Cost_ID",
                    params
                )
                keyword_active = bool(conditions)

            else:
                keyword = self.search_var.get().strip()
                keyword_active = bool(keyword)

                if keyword:
                    cursor.execute(
                        f"SELECT Cost_ID, Activity_ID, Cost_Type, "
                        f"Budgeted_Amount, Actual_Amount, Date_Recorded "
                        f"FROM COSTS WHERE {sql_column} LIKE ? "
                        f"ORDER BY Cost_ID",
                        (f"%{keyword}%",)
                    )
                else:
                    cursor.execute(
                        "SELECT Cost_ID, Activity_ID, Cost_Type, "
                        "Budgeted_Amount, Actual_Amount, Date_Recorded "
                        "FROM COSTS ORDER BY Cost_ID"
                    )

            rows = cursor.fetchall()
            for row in rows:
                budgeted = self._fmt_decimal(row[3])
                actual = self._fmt_decimal(row[4])
                # Variance = Actual - Budgeted
                try:
                    variance = f"{Decimal(str(row[4] or 0)) - Decimal(str(row[3] or 0)):.2f}"
                except Exception:
                    variance = ""
                date_val = str(row[5])[:10] if row[5] else ""

                self.tree.insert("", tk.END, values=(
                    row[0] or "", # Cost_ID
                    row[1] or "", # Activity_ID
                    row[2] or "", # Cost_Type
                    budgeted,
                    actual,
                    variance,
                    date_val,
                ))
            conn.close()

            if keyword_active and not rows:
                messagebox.showinfo("Search", "No cost records matched your search criteria.")

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to load costs:\n{exc}")

    def add_cost(self):
        if not self._validate_inputs():
            return

        cost_id = self._get("Cost ID *")
        act_id = self._none_if_empty(self._get("Activity ID"))
        cost_type= self._none_if_empty(self._get("Cost Type"))
        budgeted = self._parse_decimal(self._get("Budgeted Amount"), "Budgeted Amount")
        actual = self._parse_decimal(self._get("Actual Amount"), "Actual Amount")
        date_rec = self._none_if_empty(self._get("Date Recorded"))

        if budgeted is False or actual is False:
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO COSTS "
                "(Cost_ID, Activity_ID, Cost_Type, Budgeted_Amount, "
                " Actual_Amount, Date_Recorded) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cost_id, act_id, cost_type,
                 float(budgeted) if budgeted is not None else None,
                 float(actual) if actual is not None else None,
                 date_rec)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success",
                                f"Cost record '{cost_id}' added successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to add cost:\n{exc}")

    def update_cost(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a cost record from the list first.")
            return
        if not self._validate_inputs():
            return

        act_id = self._none_if_empty(self._get("Activity ID"))
        cost_type= self._none_if_empty(self._get("Cost Type"))
        budgeted = self._parse_decimal(self._get("Budgeted Amount"), "Budgeted Amount")
        actual = self._parse_decimal(self._get("Actual Amount"), "Actual Amount")
        date_rec = self._none_if_empty(self._get("Date Recorded"))

        if budgeted is False or actual is False:
            return

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Cost ID '{self._selected_id}'?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE COSTS SET "
                "Activity_ID=?, Cost_Type=?, Budgeted_Amount=?, "
                "Actual_Amount=?, Date_Recorded=? "
                "WHERE Cost_ID=?",
                (act_id, cost_type,
                 float(budgeted) if budgeted is not None else None,
                 float(actual) if actual is not None else None,
                 date_rec, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Cost record updated successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to update cost:\n{exc}")

    def delete_cost(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection",
                                   "Please select a cost record from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Cost ID "
                                   f"'{self._selected_id}'?\n"
                                   f"This cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM COSTS WHERE Cost_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Cost record deleted successfully.")
            self.clear_fields()
            self.load_costs()

        except Exception as exc:
            messagebox.showerror("Database Error",
                                 f"Failed to delete cost:\n{exc}")


# ── Stand-alone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Costs Form")
    root.geometry("1000x640")
    root.configure(bg="#1e2327")
    CostsForm(root)
    root.mainloop()

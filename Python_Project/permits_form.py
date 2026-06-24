"""
permits_form.py
─────────────────
Full CRUD Tkinter form for the PERMITS table in Refinery_Project.

Table schema
────────────
CREATE TABLE PERMITS (
    Permit_ID VARCHAR(20) PRIMARY KEY,
    Activity_ID VARCHAR(20),
    Permit_Type VARCHAR(50),
    Issue_Date DATE,
    Expiray_Date DATE, -- NOTE: spelled exactly this way in the DB schema
    Status VARCHAR(30),

    CONSTRAINT fk_permits_activity FOREIGN KEY (Activity_ID)
        REFERENCES WBS_ACTIVITIES (Activity_ID)
);

Notes
─────
• Permit_ID is a user-entered VARCHAR PK, editable on Add, locked once a row
  is selected for Update/Delete.
• Activity_ID is a foreign key, presented as a read-only Combobox populated
  live from WBS_ACTIVITIES ("Activity_ID - Activity_Name"), optional.
• The "Expiray_Date" column name is kept exactly as defined in the schema
  (it is misspelled in the database itself) so INSERT/UPDATE statements work
  without modification.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db_connection import get_connection

DATE_FMT = "%Y-%m-%d"

PERMIT_TYPE_OPTIONS = ["Hot Work", "Confined Space", "Excavation",
                       "Working at Height", "Electrical", "Environmental",
                       "Construction", "Other"]
STATUS_OPTIONS = ["Pending", "Approved", "Active", "Expired",
                  "Rejected", "Revoked"]


# ────────────────────────────────────────────────────────────────────────────
class PermitsForm(tk.Frame):
    """
    Dark-themed frame with:
      • A data-entry panel (top)
      • CRUD buttons
      • A searchable, sortable Treeview listing all permits
    """

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
        self._selected_id = None # Permit_ID of the currently selected row
        self._activity_display_to_id = {}
        self._activity_id_to_display = {}
        self._build_ui()
        self._refresh_activity_options()
        self.load_permits()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self, text="Permits Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar ────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_permits())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Permit Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        self._entries = {}

        col0_fields = [
            ("Permit_ID *", "entry"),
            ("Activity_ID", "fk_activity"),
            ("Permit_Type", "combo_type"),
        ]
        col1_fields = [
            ("Issue_Date (YYYY-MM-DD)", "entry"),
            ("Expiray_Date (YYYY-MM-DD)", "entry"),
            ("Status", "combo_status"),
        ]

        for i, (lbl, kind) in enumerate(col0_fields):
            self._make_field(panel, lbl, kind, row=i, col=0)
        for i, (lbl, kind) in enumerate(col1_fields):
            self._make_field(panel, lbl, kind, row=i, col=2)

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add", self.add_permit),
            ("✏️ Update", self.update_permit),
            ("🗑️ Delete", self.delete_permit),
            ("🔄 Refresh", self._refresh_all),
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

        cols = ("Permit_ID", "Activity_ID", "Permit_Type", "Issue_Date",
                "Expiray_Date", "Status")
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

        col_widths = {"Permit_ID": 100, "Activity_ID": 100, "Permit_Type": 140,
                      "Issue_Date": 100, "Expiray_Date": 100, "Status": 110}
        for col in cols:
            self.tree.heading(col, text=col.replace("_", " "),
                              command=lambda c=col: self._sort_tree(c, False))
            self.tree.column(col, width=col_widths[col], anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    def _make_field(self, panel, label, kind, row, col):
        tk.Label(panel, text=label, bg=self.PANEL_BG, fg=self.FG,
                 font=("Segoe UI", 10), anchor="w").grid(
            row=row, column=col, sticky="w", padx=14, pady=5
        )

        if kind == "entry":
            widget = tk.Entry(
                panel, bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
                relief=tk.FLAT, font=("Segoe UI", 10), width=28
            )
        elif kind == "fk_activity":
            widget = ttk.Combobox(panel, values=[""], state="readonly",
                                  font=("Segoe UI", 10), width=26)
            widget.set("")
        elif kind == "combo_type":
            widget = ttk.Combobox(panel, values=PERMIT_TYPE_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
        elif kind == "combo_status":
            widget = ttk.Combobox(panel, values=STATUS_OPTIONS, state="normal",
                                  font=("Segoe UI", 10), width=26)
            widget.set(STATUS_OPTIONS[0])
        else:
            raise ValueError(f"Unknown field kind: {kind}")

        widget.grid(row=row, column=col + 1, padx=14, pady=5, sticky="w")
        self._entries[label] = widget

    # ── FK loading ───────────────────────────────────────────────────────────
    def _refresh_activity_options(self):
        self._activity_display_to_id = {}
        self._activity_id_to_display = {}
        rows = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Activity_ID, Activity_Name FROM WBS_ACTIVITIES ORDER BY Activity_ID"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load WBS Activities:\n{exc}")

        values = [""]
        for r in rows:
            display = f"{r[0]} - {r[1]}"
            self._activity_display_to_id[display] = r[0]
            self._activity_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Activity_ID"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_all(self):
        self._refresh_activity_options()
        self.load_permits()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _activity_id_from_field(self):
        display = self._get_field("Activity_ID")
        if not display:
            return None
        return self._activity_display_to_id.get(display, display)

    def _validate_inputs(self, is_add: bool) -> bool:
        if is_add and not self._get_field("Permit_ID *"):
            messagebox.showwarning("Validation", "Permit_ID is required.")
            return False

        for lbl in ("Issue_Date (YYYY-MM-DD)", "Expiray_Date (YYYY-MM-DD)"):
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

        issue = self._get_field("Issue_Date (YYYY-MM-DD)")
        expiry = self._get_field("Expiray_Date (YYYY-MM-DD)")
        if issue and expiry and issue > expiry:
            messagebox.showwarning("Validation", "Issue Date cannot be after Expiry Date.")
            return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        self._entries["Permit_ID *"].configure(state="normal")
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                if lbl == "Status":
                    widget.set(STATUS_OPTIONS[0])
                else:
                    widget.set("")
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (Permit_ID, Activity_ID, Permit_Type, Issue_Date,
        # Expiray_Date, Status)
        self._selected_id = values[0]

        self._entries["Permit_ID *"].configure(state="normal")
        self._entries["Permit_ID *"].delete(0, tk.END)
        self._entries["Permit_ID *"].insert(0, values[0])
        self._entries["Permit_ID *"].configure(state="disabled")

        activity_id = values[1]
        self._entries["Activity_ID"].set(
            self._activity_id_to_display.get(activity_id, "") if activity_id else ""
        )

        self._entries["Permit_Type"].set(values[2] if values[2] else "")

        self._entries["Issue_Date (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Issue_Date (YYYY-MM-DD)"].insert(0, values[3] if values[3] else "")

        self._entries["Expiray_Date (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Expiray_Date (YYYY-MM-DD)"].insert(0, values[4] if values[4] else "")

        self._entries["Status"].set(values[5] if values[5] else STATUS_OPTIONS[0])

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_permits(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if keyword:
                cursor.execute(
                    "SELECT Permit_ID, Activity_ID, Permit_Type, Issue_Date, "
                    "Expiray_Date, Status FROM PERMITS "
                    "WHERE Permit_Type LIKE ? OR Status LIKE ? "
                    "ORDER BY Permit_ID",
                    (f"%{keyword}%", f"%{keyword}%")
                )
            else:
                cursor.execute(
                    "SELECT Permit_ID, Activity_ID, Permit_Type, Issue_Date, "
                    "Expiray_Date, Status FROM PERMITS ORDER BY Permit_ID"
                )

            for row in cursor.fetchall():
                issue = str(row[3])[:10] if row[3] else ""
                expiry = str(row[4])[:10] if row[4] else ""
                self.tree.insert("", tk.END, values=(
                    row[0], row[1] or "", row[2] or "", issue, expiry, row[5] or ""
                ))

            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load permits:\n{exc}")

    def add_permit(self):
        if not self._validate_inputs(is_add=True):
            return

        permit_id = self._get_field("Permit_ID *")
        activity_id = self._activity_id_from_field()
        permit_type = self._none_if_empty(self._get_field("Permit_Type"))
        issue = self._none_if_empty(self._get_field("Issue_Date (YYYY-MM-DD)"))
        expiry = self._none_if_empty(self._get_field("Expiray_Date (YYYY-MM-DD)"))
        status = self._none_if_empty(self._get_field("Status"))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO PERMITS (Permit_ID, Activity_ID, Permit_Type, "
                "Issue_Date, Expiray_Date, Status) VALUES (?, ?, ?, ?, ?, ?)",
                (permit_id, activity_id, permit_type, issue, expiry, status)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Permit '{permit_id}' added successfully.")
            self.clear_fields()
            self.load_permits()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add permit:\n{exc}")

    def update_permit(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a permit from the list first.")
            return
        if not self._validate_inputs(is_add=False):
            return

        activity_id = self._activity_id_from_field()
        permit_type = self._none_if_empty(self._get_field("Permit_Type"))
        issue = self._none_if_empty(self._get_field("Issue_Date (YYYY-MM-DD)"))
        expiry = self._none_if_empty(self._get_field("Expiray_Date (YYYY-MM-DD)"))
        status = self._none_if_empty(self._get_field("Status"))

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Permit '{self._selected_id}'?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE PERMITS SET Activity_ID=?, Permit_Type=?, Issue_Date=?, "
                "Expiray_Date=?, Status=? WHERE Permit_ID=?",
                (activity_id, permit_type, issue, expiry, status, self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Permit updated successfully.")
            self.clear_fields()
            self.load_permits()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update permit:\n{exc}")

    def delete_permit(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a permit from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Permit '{self._selected_id}'?"
                                   f"\nThis cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM PERMITS WHERE Permit_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Permit deleted successfully.")
            self.clear_fields()
            self.load_permits()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete permit:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Permits Form")
    root.geometry("1000x650")
    root.configure(bg="#1e2327")
    PermitsForm(root)
    root.mainloop()

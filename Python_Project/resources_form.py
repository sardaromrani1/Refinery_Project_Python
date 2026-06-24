"""
resources_form.py
───────────────────
Full CRUD Tkinter form for the RESOURCES table in Refinery_Project.

Table schema
────────────
CREATE TABLE RESOURCES (
    Resource_ID VARCHAR(20) PRIMARY KEY,
    Activity_ID VARCHAR(20),
    Contractor_ID VARCHAR(20),
    Name VARCHAR(100),
    Role VARCHAR(100),
    Certification VARCHAR(100),
    Assigned_From DATE,
    Assigned_To DATE,

    CONSTRAINT fk_resources_activity FOREIGN KEY (Activity_ID)
        REFERENCES WBS_ACTIVITIES (Activity_ID),
    CONSTRAINT fk_resources_contractor FOREIGN KEY (Contractor_ID)
        REFERENCES CONTRACTORS (Contractor_ID)
);

Notes
─────
• Resource_ID is a user-entered VARCHAR PK, editable on Add, locked once a
  row is selected for Update/Delete.
• Activity_ID and Contractor_ID are foreign keys, presented as read-only
  Comboboxes populated live from WBS_ACTIVITIES and CONTRACTORS, optional.
• IMPORTANT: the Contractor dropdown assumes your CONTRACTORS table has a
  human-readable name column called "Contractor_Name". If your contractors_form.py
  uses a different column name for that, update the SELECT statement in
  `_refresh_contractor_options()` below to match.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db_connection import get_connection

DATE_FMT = "%Y-%m-%d"


# ────────────────────────────────────────────────────────────────────────────
class ResourcesForm(tk.Frame):
    """
    Dark-themed frame with:
      • A data-entry panel (top)
      • CRUD buttons
      • A searchable, sortable Treeview listing all resources
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
        self._selected_id = None # Resource_ID of the currently selected row
        self._activity_display_to_id = {}
        self._activity_id_to_display = {}
        self._contractor_display_to_id = {}
        self._contractor_id_to_display = {}
        self._build_ui()
        self._refresh_activity_options()
        self._refresh_contractor_options()
        self.load_resources()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self, text="Resources Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar ────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_resources())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" Resource Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        self._entries = {}

        col0_fields = [
            ("Resource_ID *", "entry"),
            ("Activity_ID", "fk_activity"),
            ("Contractor_ID", "fk_contractor"),
            ("Name *", "entry"),
        ]
        col1_fields = [
            ("Role", "entry"),
            ("Certification", "entry"),
            ("Assigned_From (YYYY-MM-DD)", "entry"),
            ("Assigned_To (YYYY-MM-DD)", "entry"),
        ]

        for i, (lbl, kind) in enumerate(col0_fields):
            self._make_field(panel, lbl, kind, row=i, col=0)
        for i, (lbl, kind) in enumerate(col1_fields):
            self._make_field(panel, lbl, kind, row=i, col=2)

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add", self.add_resource),
            ("✏️ Update", self.update_resource),
            ("🗑️ Delete", self.delete_resource),
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

        cols = ("Resource_ID", "Activity_ID", "Contractor_ID", "Name", "Role",
                "Certification", "Assigned_From", "Assigned_To")
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

        col_widths = {"Resource_ID": 100, "Activity_ID": 95, "Contractor_ID": 100,
                      "Name": 130, "Role": 110, "Certification": 120,
                      "Assigned_From": 105, "Assigned_To": 105}
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
        elif kind in ("fk_activity", "fk_contractor"):
            widget = ttk.Combobox(panel, values=[""], state="readonly",
                                  font=("Segoe UI", 10), width=26)
            widget.set("")
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

    def _refresh_contractor_options(self):
        self._contractor_display_to_id = {}
        self._contractor_id_to_display = {}
        rows = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # NOTE: adjust "Contractor_Name" below if your CONTRACTORS table
            # uses a different column for the display name.
            cursor.execute(
                "SELECT Contractor_ID, Contractor_Name FROM CONTRACTORS "
                "ORDER BY Contractor_ID"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load Contractors:\n{exc}")

        values = [""]
        for r in rows:
            label = r[1] if r[1] else ""
            display = f"{r[0]} - {label}" if label else r[0]
            self._contractor_display_to_id[display] = r[0]
            self._contractor_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Contractor_ID"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_all(self):
        self._refresh_activity_options()
        self._refresh_contractor_options()
        self.load_resources()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _activity_id_from_field(self):
        display = self._get_field("Activity_ID")
        if not display:
            return None
        return self._activity_display_to_id.get(display, display)

    def _contractor_id_from_field(self):
        display = self._get_field("Contractor_ID")
        if not display:
            return None
        return self._contractor_display_to_id.get(display, display)

    def _validate_inputs(self, is_add: bool) -> bool:
        if is_add and not self._get_field("Resource_ID *"):
            messagebox.showwarning("Validation", "Resource_ID is required.")
            return False
        if not self._get_field("Name *"):
            messagebox.showwarning("Validation", "Name is required.")
            return False

        for lbl in ("Assigned_From (YYYY-MM-DD)", "Assigned_To (YYYY-MM-DD)"):
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

        start = self._get_field("Assigned_From (YYYY-MM-DD)")
        end = self._get_field("Assigned_To (YYYY-MM-DD)")
        if start and end and start > end:
            messagebox.showwarning("Validation", "Assigned From cannot be after Assigned To.")
            return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        self._entries["Resource_ID *"].configure(state="normal")
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (Resource_ID, Activity_ID, Contractor_ID, Name, Role,
        # Certification, Assigned_From, Assigned_To)
        self._selected_id = values[0]

        self._entries["Resource_ID *"].configure(state="normal")
        self._entries["Resource_ID *"].delete(0, tk.END)
        self._entries["Resource_ID *"].insert(0, values[0])
        self._entries["Resource_ID *"].configure(state="disabled")

        activity_id = values[1]
        self._entries["Activity_ID"].set(
            self._activity_id_to_display.get(activity_id, "") if activity_id else ""
        )

        contractor_id = values[2]
        self._entries["Contractor_ID"].set(
            self._contractor_id_to_display.get(contractor_id, "") if contractor_id else ""
        )

        self._entries["Name *"].delete(0, tk.END)
        self._entries["Name *"].insert(0, values[3])

        self._entries["Role"].delete(0, tk.END)
        self._entries["Role"].insert(0, values[4] if values[4] else "")

        self._entries["Certification"].delete(0, tk.END)
        self._entries["Certification"].insert(0, values[5] if values[5] else "")

        self._entries["Assigned_From (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Assigned_From (YYYY-MM-DD)"].insert(0, values[6] if values[6] else "")

        self._entries["Assigned_To (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Assigned_To (YYYY-MM-DD)"].insert(0, values[7] if values[7] else "")

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_resources(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if keyword:
                cursor.execute(
                    "SELECT Resource_ID, Activity_ID, Contractor_ID, Name, Role, "
                    "Certification, Assigned_From, Assigned_To FROM RESOURCES "
                    "WHERE Name LIKE ? OR Role LIKE ? OR Certification LIKE ? "
                    "ORDER BY Resource_ID",
                    (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
                )
            else:
                cursor.execute(
                    "SELECT Resource_ID, Activity_ID, Contractor_ID, Name, Role, "
                    "Certification, Assigned_From, Assigned_To FROM RESOURCES "
                    "ORDER BY Resource_ID"
                )

            for row in cursor.fetchall():
                a_from = str(row[6])[:10] if row[6] else ""
                a_to = str(row[7])[:10] if row[7] else ""
                self.tree.insert("", tk.END, values=(
                    row[0], row[1] or "", row[2] or "", row[3] or "",
                    row[4] or "", row[5] or "", a_from, a_to
                ))

            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load resources:\n{exc}")

    def add_resource(self):
        if not self._validate_inputs(is_add=True):
            return

        resource_id = self._get_field("Resource_ID *")
        activity_id = self._activity_id_from_field()
        contractor_id = self._contractor_id_from_field()
        name = self._get_field("Name *")
        role = self._none_if_empty(self._get_field("Role"))
        cert = self._none_if_empty(self._get_field("Certification"))
        a_from = self._none_if_empty(self._get_field("Assigned_From (YYYY-MM-DD)"))
        a_to = self._none_if_empty(self._get_field("Assigned_To (YYYY-MM-DD)"))

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO RESOURCES (Resource_ID, Activity_ID, Contractor_ID, Name, "
                "Role, Certification, Assigned_From, Assigned_To) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (resource_id, activity_id, contractor_id, name, role, cert, a_from, a_to)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Resource '{resource_id}' added successfully.")
            self.clear_fields()
            self.load_resources()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add resource:\n{exc}")

    def update_resource(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a resource from the list first.")
            return
        if not self._validate_inputs(is_add=False):
            return

        activity_id = self._activity_id_from_field()
        contractor_id = self._contractor_id_from_field()
        name = self._get_field("Name *")
        role = self._none_if_empty(self._get_field("Role"))
        cert = self._none_if_empty(self._get_field("Certification"))
        a_from = self._none_if_empty(self._get_field("Assigned_From (YYYY-MM-DD)"))
        a_to = self._none_if_empty(self._get_field("Assigned_To (YYYY-MM-DD)"))

        if not messagebox.askyesno("Confirm Update",
                                   f"Update Resource '{self._selected_id}'?"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE RESOURCES SET Activity_ID=?, Contractor_ID=?, Name=?, Role=?, "
                "Certification=?, Assigned_From=?, Assigned_To=? WHERE Resource_ID=?",
                (activity_id, contractor_id, name, role, cert, a_from, a_to,
                 self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Resource updated successfully.")
            self.clear_fields()
            self.load_resources()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update resource:\n{exc}")

    def delete_resource(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a resource from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete Resource '{self._selected_id}'?"
                                   f"\nThis cannot be undone."):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM RESOURCES WHERE Resource_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Resource deleted successfully.")
            self.clear_fields()
            self.load_resources()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete resource:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – Resources Form")
    root.geometry("1050x650")
    root.configure(bg="#1e2327")
    ResourcesForm(root)
    root.mainloop()
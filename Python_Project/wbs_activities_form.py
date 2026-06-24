"""
wbs_activities_form.py
────────────────────────
Full CRUD Tkinter form for the WBS_ACTIVITIES table in Refinery_Project.
This is the central table linking every other module to the project schedule.

Table schema
────────────
CREATE TABLE WBS_ACTIVITIES(
    Activity_ID       VARCHAR(20) PRIMARY KEY,
    Project_ID        INT NOT NULL,
    Activity_Name     VARCHAR(150) NOT NULL,
    Planned_Start     DATE,
    Planned_Finish    DATE,
    Actual_Start      DATE,
    Actual_Finish     DATE,
    Percent_Complete  DECIMAL(5, 2) DEFAULT 0,
    Predecessor_ID    VARCHAR(20),

    CONSTRAINT fk_wbs_project FOREIGN KEY (Project_ID)
        REFERENCES dbo.PROJECTT (Project_ID),
    CONSTRAINT fk_wbs_predecessor FOREIGN KEY (Predecessor_ID)
        REFERENCES WBS_ACTIVITIES (Activity_ID)
);

Notes
─────
• Activity_ID is a user-entered VARCHAR PK, editable on Add, locked once a
  row is selected for Update/Delete.
• Project_ID is a required foreign key, presented as a read-only Combobox
  populated live from PROJECTT ("Project_ID - Project_Name").
• Predecessor_ID is a self-referencing, optional foreign key, presented as a
  read-only Combobox populated from WBS_ACTIVITIES itself. When editing a
  row, that row is excluded from its own Predecessor list to prevent an
  activity from being its own predecessor.
• Percent_Complete is validated as a number between 0 and 100.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from db_connection import get_connection

DATE_FMT = "%Y-%m-%d"


# ────────────────────────────────────────────────────────────────────────────
class WbsActivitiesForm(tk.Frame):
    """
    Dark-themed frame with:
      • A data-entry panel (top)
      • CRUD buttons
      • A searchable, sortable Treeview listing all WBS activities
    """

    BG       = "#1e2327"
    PANEL_BG = "#252b30"
    FG       = "#e0e0e0"
    ACCENT   = "#00b4d8"
    BTN_BG   = "#00b4d8"
    BTN_FG   = "#ffffff"
    ENTRY_BG = "#2e3540"
    SEL_BG   = "#00b4d8"

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, bg=self.BG, *args, **kwargs)
        self._selected_id = None          # Activity_ID of the currently selected row
        self._project_display_to_id = {}
        self._project_id_to_display = {}
        self._activity_display_to_id = {}
        self._activity_id_to_display = {}
        self._build_ui()
        self._refresh_project_options()
        self._refresh_predecessor_options()
        self.load_activities()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self, text="WBS Activities Management", bg=self.BG, fg=self.ACCENT,
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(18, 6))

        # ── Search bar ────────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=self.BG)
        search_frame.pack(fill=tk.X, padx=20, pady=(0, 6))

        tk.Label(search_frame, text="Search:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.load_activities())
        tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=self.ENTRY_BG, fg=self.FG, insertbackground=self.FG,
            relief=tk.FLAT, font=("Segoe UI", 10), width=30
        ).pack(side=tk.LEFT)

        # ── Entry panel ───────────────────────────────────────────────────────
        panel = tk.LabelFrame(
            self, text=" WBS Activity Details ", bg=self.PANEL_BG, fg=self.ACCENT,
            font=("Segoe UI", 10, "bold"), bd=1, relief=tk.GROOVE
        )
        panel.pack(fill=tk.X, padx=20, pady=6)

        self._entries = {}

        col0_fields = [
            ("Activity_ID *",   "entry"),
            ("Project_ID *",    "fk_project"),
            ("Activity_Name *", "entry"),
            ("Predecessor_ID",  "fk_predecessor"),
            ("Percent_Complete (0-100)", "entry"),
        ]
        col1_fields = [
            ("Planned_Start (YYYY-MM-DD)",  "entry"),
            ("Planned_Finish (YYYY-MM-DD)", "entry"),
            ("Actual_Start (YYYY-MM-DD)",   "entry"),
            ("Actual_Finish (YYYY-MM-DD)",  "entry"),
        ]

        for i, (lbl, kind) in enumerate(col0_fields):
            self._make_field(panel, lbl, kind, row=i, col=0)
        for i, (lbl, kind) in enumerate(col1_fields):
            self._make_field(panel, lbl, kind, row=i, col=2)

        # ── Button row ────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(pady=8)

        buttons = [
            ("➕ Add",     self.add_activity),
            ("✏️ Update",  self.update_activity),
            ("🗑️ Delete",  self.delete_activity),
            ("🔄 Refresh", self._refresh_all),
            ("✖ Clear",   self.clear_fields),
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

        cols = ("Activity_ID", "Project_ID", "Activity_Name", "Planned_Start",
                "Planned_Finish", "Actual_Start", "Actual_Finish",
                "Percent_Complete", "Predecessor_ID")
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

        col_widths = {"Activity_ID": 95, "Project_ID": 75, "Activity_Name": 170,
                      "Planned_Start": 100, "Planned_Finish": 100,
                      "Actual_Start": 95, "Actual_Finish": 95,
                      "Percent_Complete": 80, "Predecessor_ID": 100}
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
        elif kind in ("fk_project", "fk_predecessor"):
            widget = ttk.Combobox(panel, values=[""], state="readonly",
                                  font=("Segoe UI", 10), width=26)
            widget.set("")
        else:
            raise ValueError(f"Unknown field kind: {kind}")

        widget.grid(row=row, column=col + 1, padx=14, pady=5, sticky="w")
        self._entries[label] = widget

    # ── FK loading ───────────────────────────────────────────────────────────
    def _refresh_project_options(self):
        self._project_display_to_id = {}
        self._project_id_to_display = {}
        rows = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Project_ID, Project_Name FROM PROJECTT ORDER BY Project_ID"
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load Projects:\n{exc}")

        values = [""]
        for r in rows:
            display = f"{r[0]} - {r[1]}"
            self._project_display_to_id[display] = r[0]
            self._project_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Project_ID *"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_predecessor_options(self):
        """Populate Predecessor_ID combobox from WBS_ACTIVITIES, excluding the
        currently selected activity (an activity cannot be its own predecessor)."""
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
            if self._selected_id is not None and r[0] == self._selected_id:
                continue  # skip self
            display = f"{r[0]} - {r[1]}"
            self._activity_display_to_id[display] = r[0]
            self._activity_id_to_display[r[0]] = display
            values.append(display)

        widget = self._entries["Predecessor_ID"]
        widget["values"] = values
        if widget.get() not in values:
            widget.set("")

    def _refresh_all(self):
        self._refresh_project_options()
        self._refresh_predecessor_options()
        self.load_activities()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get_field(self, label: str) -> str:
        return self._entries[label].get().strip()

    def _project_id_from_field(self):
        display = self._get_field("Project_ID *")
        if not display:
            return None
        return self._project_display_to_id.get(display, display)

    def _predecessor_id_from_field(self):
        display = self._get_field("Predecessor_ID")
        if not display:
            return None
        return self._activity_display_to_id.get(display, display)

    def _validate_inputs(self, is_add: bool) -> bool:
        if is_add and not self._get_field("Activity_ID *"):
            messagebox.showwarning("Validation", "Activity_ID is required.")
            return False
        if not self._get_field("Activity_Name *"):
            messagebox.showwarning("Validation", "Activity_Name is required.")
            return False
        if not self._get_field("Project_ID *"):
            messagebox.showwarning("Validation", "Project_ID is required.")
            return False

        for lbl in ("Planned_Start (YYYY-MM-DD)", "Planned_Finish (YYYY-MM-DD)",
                    "Actual_Start (YYYY-MM-DD)", "Actual_Finish (YYYY-MM-DD)"):
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

        p_start = self._get_field("Planned_Start (YYYY-MM-DD)")
        p_finish = self._get_field("Planned_Finish (YYYY-MM-DD)")
        if p_start and p_finish and p_start > p_finish:
            messagebox.showwarning("Validation", "Planned Start cannot be after Planned Finish.")
            return False

        a_start = self._get_field("Actual_Start (YYYY-MM-DD)")
        a_finish = self._get_field("Actual_Finish (YYYY-MM-DD)")
        if a_start and a_finish and a_start > a_finish:
            messagebox.showwarning("Validation", "Actual Start cannot be after Actual Finish.")
            return False

        pct = self._get_field("Percent_Complete (0-100)")
        if pct:
            try:
                pct_val = float(pct)
            except ValueError:
                messagebox.showwarning("Validation", "Percent_Complete must be a number.")
                return False
            if pct_val < 0 or pct_val > 100:
                messagebox.showwarning("Validation", "Percent_Complete must be between 0 and 100.")
                return False

        return True

    def _none_if_empty(self, val: str):
        return val if val else None

    def clear_fields(self):
        self._selected_id = None
        self._entries["Activity_ID *"].configure(state="normal")
        for lbl, widget in self._entries.items():
            if isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())
        self._refresh_predecessor_options()  # un-exclude any previously selected row

    def _on_row_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        # values = (Activity_ID, Project_ID, Activity_Name, Planned_Start,
        #           Planned_Finish, Actual_Start, Actual_Finish,
        #           Percent_Complete, Predecessor_ID)
        self._selected_id = values[0]
        self._refresh_predecessor_options()  # exclude self from predecessor list

        self._entries["Activity_ID *"].configure(state="normal")
        self._entries["Activity_ID *"].delete(0, tk.END)
        self._entries["Activity_ID *"].insert(0, values[0])
        self._entries["Activity_ID *"].configure(state="disabled")

        project_id = str(values[1])
        self._entries["Project_ID *"].set(
            self._project_id_to_display.get(project_id, "") if project_id else ""
        )

        self._entries["Activity_Name *"].delete(0, tk.END)
        self._entries["Activity_Name *"].insert(0, values[2])

        self._entries["Planned_Start (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Planned_Start (YYYY-MM-DD)"].insert(0, values[3] if values[3] else "")

        self._entries["Planned_Finish (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Planned_Finish (YYYY-MM-DD)"].insert(0, values[4] if values[4] else "")

        self._entries["Actual_Start (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Actual_Start (YYYY-MM-DD)"].insert(0, values[5] if values[5] else "")

        self._entries["Actual_Finish (YYYY-MM-DD)"].delete(0, tk.END)
        self._entries["Actual_Finish (YYYY-MM-DD)"].insert(0, values[6] if values[6] else "")

        self._entries["Percent_Complete (0-100)"].delete(0, tk.END)
        self._entries["Percent_Complete (0-100)"].insert(0, values[7] if values[7] else "0")

        predecessor_id = values[8]
        self._entries["Predecessor_ID"].set(
            self._activity_id_to_display.get(predecessor_id, "") if predecessor_id else ""
        )

    def _sort_tree(self, col: str, reverse: bool):
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)
        self.tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    # ── CRUD ──────────────────────────────────────────────────────────────────
    def load_activities(self, *_):
        for row in self.tree.get_children():
            self.tree.delete(row)

        keyword = self.search_var.get().strip()
        try:
            conn   = get_connection()
            cursor = conn.cursor()

            if keyword:
                cursor.execute(
                    "SELECT Activity_ID, Project_ID, Activity_Name, Planned_Start, "
                    "Planned_Finish, Actual_Start, Actual_Finish, Percent_Complete, "
                    "Predecessor_ID FROM WBS_ACTIVITIES "
                    "WHERE Activity_Name LIKE ? OR Activity_ID LIKE ? "
                    "ORDER BY Activity_ID",
                    (f"%{keyword}%", f"%{keyword}%")
                )
            else:
                cursor.execute(
                    "SELECT Activity_ID, Project_ID, Activity_Name, Planned_Start, "
                    "Planned_Finish, Actual_Start, Actual_Finish, Percent_Complete, "
                    "Predecessor_ID FROM WBS_ACTIVITIES ORDER BY Activity_ID"
                )

            for row in cursor.fetchall():
                p_start  = str(row[3])[:10] if row[3] else ""
                p_finish = str(row[4])[:10] if row[4] else ""
                a_start  = str(row[5])[:10] if row[5] else ""
                a_finish = str(row[6])[:10] if row[6] else ""
                pct      = row[7] if row[7] is not None else 0
                self.tree.insert("", tk.END, values=(
                    row[0], row[1], row[2], p_start, p_finish, a_start, a_finish,
                    pct, row[8] or ""
                ))

            conn.close()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to load WBS activities:\n{exc}")

    def add_activity(self):
        if not self._validate_inputs(is_add=True):
            return

        activity_id    = self._get_field("Activity_ID *")
        project_id     = self._project_id_from_field()
        activity_name  = self._get_field("Activity_Name *")
        planned_start  = self._none_if_empty(self._get_field("Planned_Start (YYYY-MM-DD)"))
        planned_finish = self._none_if_empty(self._get_field("Planned_Finish (YYYY-MM-DD)"))
        actual_start   = self._none_if_empty(self._get_field("Actual_Start (YYYY-MM-DD)"))
        actual_finish  = self._none_if_empty(self._get_field("Actual_Finish (YYYY-MM-DD)"))
        pct            = self._get_field("Percent_Complete (0-100)")
        pct_val        = float(pct) if pct else 0
        predecessor_id = self._predecessor_id_from_field()

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO WBS_ACTIVITIES (Activity_ID, Project_ID, Activity_Name, "
                "Planned_Start, Planned_Finish, Actual_Start, Actual_Finish, "
                "Percent_Complete, Predecessor_ID) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (activity_id, project_id, activity_name, planned_start, planned_finish,
                 actual_start, actual_finish, pct_val, predecessor_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"WBS Activity '{activity_id}' added successfully.")
            self.clear_fields()
            self.load_activities()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to add WBS activity:\n{exc}")

    def update_activity(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a WBS activity from the list first.")
            return
        if not self._validate_inputs(is_add=False):
            return

        project_id     = self._project_id_from_field()
        activity_name  = self._get_field("Activity_Name *")
        planned_start  = self._none_if_empty(self._get_field("Planned_Start (YYYY-MM-DD)"))
        planned_finish = self._none_if_empty(self._get_field("Planned_Finish (YYYY-MM-DD)"))
        actual_start   = self._none_if_empty(self._get_field("Actual_Start (YYYY-MM-DD)"))
        actual_finish  = self._none_if_empty(self._get_field("Actual_Finish (YYYY-MM-DD)"))
        pct            = self._get_field("Percent_Complete (0-100)")
        pct_val        = float(pct) if pct else 0
        predecessor_id = self._predecessor_id_from_field()

        if predecessor_id == self._selected_id:
            messagebox.showwarning("Validation", "An activity cannot be its own predecessor.")
            return

        if not messagebox.askyesno("Confirm Update",
                                   f"Update WBS Activity '{self._selected_id}'?"):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE WBS_ACTIVITIES SET Project_ID=?, Activity_Name=?, "
                "Planned_Start=?, Planned_Finish=?, Actual_Start=?, Actual_Finish=?, "
                "Percent_Complete=?, Predecessor_ID=? WHERE Activity_ID=?",
                (project_id, activity_name, planned_start, planned_finish,
                 actual_start, actual_finish, pct_val, predecessor_id,
                 self._selected_id)
            )
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "WBS Activity updated successfully.")
            self.clear_fields()
            self.load_activities()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to update WBS activity:\n{exc}")

    def delete_activity(self):
        if self._selected_id is None:
            messagebox.showwarning("Selection", "Please select a WBS activity from the list first.")
            return

        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete WBS Activity '{self._selected_id}'?\n"
                                   f"This cannot be undone, and will fail if other records "
                                   f"(Documents, Equipment, Permits, Resources, or successor "
                                   f"Activities) still reference it."):
            return

        try:
            conn   = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM WBS_ACTIVITIES WHERE Activity_ID=?",
                           (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "WBS Activity deleted successfully.")
            self.clear_fields()
            self.load_activities()

        except Exception as exc:
            messagebox.showerror("Database Error", f"Failed to delete WBS activity:\n{exc}")


# ── Stand-alone test runner ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Refinery Project – WBS Activities Form")
    root.geometry("1100x680")
    root.configure(bg="#1e2327")
    WbsActivitiesForm(root)
    root.mainloop()

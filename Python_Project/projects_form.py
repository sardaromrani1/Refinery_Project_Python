import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from db_connection import get_connection


class ProjectsForm:

    def __init__(self, root):
        self.root = root
        self.root.title("Projects Management")

        self.selected_id = None

        # Labels
        tk.Label(root, text="Project Name").grid(
            row=0, column=0, padx=5, pady=5, sticky="e"
        )

        tk.Label(root, text="Start Date (YYYY-MM-DD)").grid(
            row=1, column=0, padx=5, pady=5, sticky="e"
        )

        tk.Label(root, text="End Date (YYYY-MM-DD)").grid(
            row=2, column=0, padx=5, pady=5, sticky="e"
        )

        tk.Label(root, text="Status").grid(
            row=3, column=0, padx=5, pady=5, sticky="e"
        )

        # Entry fields
        self.project_name = tk.Entry(root, width=30)
        self.start_date = tk.Entry(root, width=30)
        self.end_date = tk.Entry(root, width=30)
        self.status = tk.Entry(root, width=30)

        self.project_name.grid(row=0, column=1, padx=5, pady=5)
        self.start_date.grid(row=1, column=1, padx=5, pady=5)
        self.end_date.grid(row=2, column=1, padx=5, pady=5)
        self.status.grid(row=3, column=1, padx=5, pady=5)

        # Buttons
        tk.Button(
            root,
            text="Add",
            width=10,
            command=self.add_project
        ).grid(row=4, column=0, pady=8)

        tk.Button(
            root,
            text="Update",
            width=10,
            command=self.update_project
        ).grid(row=4, column=1, pady=8)

        tk.Button(
            root,
            text="Delete",
            width=10,
            command=self.delete_project
        ).grid(row=4, column=2, pady=8)

        tk.Button(
            root,
            text="Clear",
            width=10,
            command=self.clear_fields
        ).grid(row=4, column=3, pady=8)

        # Treeview
        self.tree = ttk.Treeview(
            root,
            columns=("ID", "Name", "Start", "End", "Status"),
            show="headings"
        )

        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Project Name")
        self.tree.heading("Start", text="Start Date")
        self.tree.heading("End", text="End Date")
        self.tree.heading("Status", text="Status")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=200)
        self.tree.column("Start", width=110, anchor="center")
        self.tree.column("End", width=110, anchor="center")
        self.tree.column("Status", width=100, anchor="center")

        self.tree.grid(
            row=5,
            column=0,
            columnspan=4,
            padx=10,
            pady=10
        )

        self.tree.bind("<<TreeviewSelect>>", self.select_record)

        self.load_projects()

    # ==================================================
    # Helper Methods
    # ==================================================

    def clear_fields(self):
        self.project_name.delete(0, tk.END)
        self.start_date.delete(0, tk.END)
        self.end_date.delete(0, tk.END)
        self.status.delete(0, tk.END)

        self.selected_id = None

    def _validate_inputs(self):

        if not self.project_name.get().strip():
            messagebox.showwarning(
                "Validation",
                "Project Name is required."
            )
            return False

        return True

    def _selection_required(self):

        if self.selected_id is None:
            messagebox.showwarning(
                "Selection",
                "Please select a record first."
            )
            return False

        return True

    # ==================================================
    # Load Data
    # ==================================================

    def load_projects(self):

        try:
            # Clear existing rows
            for row in self.tree.get_children():
                self.tree.delete(row)

            conn = get_connection()

            print(conn)
            print(type(conn))

            cursor = conn.cursor()

            cursor.execute("SELECT * FROM PROJECTT")

            rows = cursor.fetchall()

            conn.close()

            for row in rows:
                self.tree.insert("", tk.END, values=row)

        except Exception as e:
            print("ERROR:", e)
            messagebox.showerror(
                "Database Error",
                str(e)
            )

    # ==================================================
    # Create
    # ==================================================

    def add_project(self):

        if not self._validate_inputs():
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO PROJECTT
                (
                    Project_Name,
                    Start_Date,
                    End_Date,
                    Status
                )
                VALUES (?, ?, ?, ?)
            """,
            (
                
                self.project_name.get().strip(),
                self.start_date.get().strip(),
                self.end_date.get().strip(),
                self.status.get().strip()
            ))

            conn.commit()
            conn.close()

            self.load_projects()
            self.clear_fields()

            messagebox.showinfo(
                "Success",
                "Project added successfully."
            )

        except Exception as e:
            messagebox.showerror(
                "Database Error",
                str(e)
            )

    # ==================================================
    # Select Record
    # ==================================================

    def select_record(self, event):

        selected = self.tree.focus()

        if not selected:
            return

        data = self.tree.item(selected)

        row = data["values"]

        if row:

            self.selected_id = row[0]

            self.project_name.delete(0, tk.END)
            self.project_name.insert(0, row[1])

            self.start_date.delete(0, tk.END)
            self.start_date.insert(0, row[2])

            self.end_date.delete(0, tk.END)
            self.end_date.insert(0, row[3])

            self.status.delete(0, tk.END)
            self.status.insert(0, row[4])

    # ==================================================
    # Update
    # ==================================================

    def update_project(self):

        if not self._selection_required():
            return

        if not self._validate_inputs():
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE PROJECTT
                SET
                    Project_Name = ?,
                    Start_Date = ?,
                    End_Date = ?,
                    Status = ?
                WHERE Project_ID = ?
            """,
            (
                self.project_name.get().strip(),
                self.start_date.get().strip(),
                self.end_date.get().strip(),
                self.status.get().strip(),
                self.selected_id
            ))

            conn.commit()
            conn.close()

            self.load_projects()
            self.clear_fields()

            messagebox.showinfo(
                "Success",
                "Project updated successfully."
            )

        except Exception as e:
            messagebox.showerror(
                "Database Error",
                str(e)
            )

    # ==================================================
    # Delete
    # ==================================================

    def delete_project(self):

        if not self._selection_required():
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete Project ID {self.selected_id}?"
        )

        if not confirm:
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM PROJECTT WHERE Project_ID = ?",
                (self.selected_id,)
            )

            conn.commit()
            conn.close()

            self.load_projects()
            self.clear_fields()

            messagebox.showinfo(
                "Success",
                "Project deleted successfully."
            )

        except Exception as e:
            messagebox.showerror(
                "Database Error",
                str(e)
            )
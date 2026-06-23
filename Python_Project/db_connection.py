import pyodbc

def get_connection():

    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=DESKTOP-M079PML\\SQLEXPRESS01, 14330;"
        "DATABASE=Refinery_Project;"
        "Trusted_Connection=yes;"
    )

    return conn

if __name__ == "__main__":
    conn = get_connection()
    print(conn)
    print(type(conn))
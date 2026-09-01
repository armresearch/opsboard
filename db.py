import sqlite3

def connect():
    return sqlite3.connect("tool.db")

def query(sql):
    con = connect()
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()

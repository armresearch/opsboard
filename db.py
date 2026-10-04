import sqlite3

def connect():
    return sqlite3.connect("tool.db")

def query(sql, params=()):
    con = connect()
    try:
        cur = con.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        con.close()

def query_one(sql):
    rows = query(sql)
    return rows[0] if rows else None

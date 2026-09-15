from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name("finance.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK(type IN ('income','expense')),
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC").fetchall()
    summary = conn.execute("""
        SELECT
          COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0) income,
          COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) expense
        FROM transactions
    """).fetchone()
    conn.close()
    balance = summary["income"] - summary["expense"]
    return render_template("index.html", transactions=rows,
                           income=summary["income"], expense=summary["expense"],
                           balance=balance)

@app.route("/add", methods=["POST"])
def add():
    tx_type = request.form.get("type")
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "อื่นๆ")
    amount = request.form.get("amount", "0")
    date = request.form.get("date")
    note = request.form.get("note", "").strip()

    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    if tx_type in ("income", "expense") and title and amount > 0 and date:
        conn = get_db()
        conn.execute(
            "INSERT INTO transactions(type,title,amount,category,date,note) VALUES(?,?,?,?,?,?)",
            (tx_type, title, amount, category, date, note)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

@app.route("/delete/<int:tx_id>", methods=["POST"])
def delete(tx_id):
    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/api/chart")
def chart():
    conn = get_db()
    rows = conn.execute("""
        SELECT date,
          SUM(CASE WHEN type='income' THEN amount ELSE 0 END) income,
          SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) expense
        FROM transactions
        GROUP BY date
        ORDER BY date
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/categories")
def categories():
    conn = get_db()
    rows = conn.execute("""
        SELECT category, SUM(amount) total
        FROM transactions
        WHERE type='expense'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

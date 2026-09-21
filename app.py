from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DATABASE = "budget.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            id INTEGER PRIMARY KEY,
            amount REAL NOT NULL
        )
    """)

    existing_budget = conn.execute(
        "SELECT * FROM budget WHERE id = 1"
    ).fetchone()

    if existing_budget is None:
        conn.execute(
            "INSERT INTO budget (id, amount) VALUES (1, ?)",
            (10000,)
        )

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    conn = get_db_connection()

    expenses = conn.execute("""
        SELECT * FROM expenses
        ORDER BY expense_date DESC, id DESC
    """).fetchall()

    conn.close()

    return jsonify([
        {
            "id": expense["id"],
            "item": expense["item"],
            "category": expense["category"],
            "amount": expense["amount"],
            "date": expense["expense_date"]
        }
        for expense in expenses
    ])


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json()

    item = data.get("item", "").strip()
    category = data.get("category", "").strip()
    amount = data.get("amount")
    expense_date = data.get("date", "").strip()

    if not item or not category or amount is None or not expense_date:
        return jsonify({
            "success": False,
            "message": "Please fill all fields."
        }), 400

    try:
        amount = float(amount)

        if amount <= 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Amount must be greater than zero."
        }), 400

    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid date."
        }), 400

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO expenses
        (item, category, amount, expense_date)
        VALUES (?, ?, ?, ?)
    """, (
        item,
        category,
        amount,
        expense_date
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Expense added successfully."
    })


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db_connection()

    cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "Expense not found."
        }), 404

    return jsonify({
        "success": True,
        "message": "Expense deleted."
    })


@app.route("/api/expenses", methods=["DELETE"])
def clear_expenses():
    conn = get_db_connection()

    conn.execute("DELETE FROM expenses")

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "All expenses cleared."
    })


@app.route("/api/budget", methods=["GET"])
def get_budget():
    conn = get_db_connection()

    budget = conn.execute(
        "SELECT amount FROM budget WHERE id = 1"
    ).fetchone()

    conn.close()

    return jsonify({
        "amount": budget["amount"] if budget else 0
    })


@app.route("/api/budget", methods=["POST"])
def update_budget():
    data = request.get_json()

    amount = data.get("amount")

    try:
        amount = float(amount)

        if amount < 0:
            raise ValueError

    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid budget amount."
        }), 400

    conn = get_db_connection()

    conn.execute("""
        UPDATE budget
        SET amount = ?
        WHERE id = 1
    """, (amount,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Budget updated successfully."
    })


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        debug=True,
        host="0.0.0.0",
        port=port
    )
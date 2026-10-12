
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "budget.db")

# Render uses PostgreSQL when DATABASE_URL is configured.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

USE_POSTGRES = bool(DATABASE_URL)


def get_db_connection():
    if USE_POSTGRES:
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row,
            connect_timeout=10
        )

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def execute(conn, sql, params=()):
    # SQLite uses ?; PostgreSQL uses %s.
    if USE_POSTGRES:
        sql = sql.replace("?", "%s")

    return conn.execute(sql, params)


def init_db():
    conn = get_db_connection()

    try:
        if USE_POSTGRES:
            execute(conn, """
                CREATE TABLE IF NOT EXISTS expenses (
                    id BIGSERIAL PRIMARY KEY,
                    item TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount DOUBLE PRECISION NOT NULL,
                    expense_date TEXT NOT NULL
                )
            """)

            execute(conn, """
                CREATE TABLE IF NOT EXISTS budget (
                    id INTEGER PRIMARY KEY,
                    amount DOUBLE PRECISION NOT NULL
                )
            """)
        else:
            execute(conn, """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    expense_date TEXT NOT NULL
                )
            """)

            execute(conn, """
                CREATE TABLE IF NOT EXISTS budget (
                    id INTEGER PRIMARY KEY,
                    amount REAL NOT NULL
                )
            """)

        execute(
            conn,
            "INSERT INTO budget (id, amount) VALUES (1, ?) "
            "ON CONFLICT(id) DO NOTHING",
            (10000,)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    conn = get_db_connection()

    try:
        expenses = execute(conn, """
            SELECT * FROM expenses
            ORDER BY expense_date DESC, id DESC
        """).fetchall()

        return jsonify([
            {
                "id": e["id"],
                "item": e["item"],
                "category": e["category"],
                "amount": e["amount"],
                "date": e["expense_date"]
            }
            for e in expenses
        ])
    finally:
        conn.close()


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(silent=True) or {}

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

    try:
        execute(conn, """
            INSERT INTO expenses
                (item, category, amount, expense_date)
            VALUES (?, ?, ?, ?)
        """, (item, category, amount, expense_date))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Expense added successfully."
        })
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db_connection()

    try:
        cursor = execute(
            conn,
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "success": False,
                "message": "Expense not found."
            }), 404

        return jsonify({
            "success": True,
            "message": "Expense deleted."
        })
    finally:
        conn.close()


@app.route("/api/expenses", methods=["DELETE"])
def clear_expenses():
    conn = get_db_connection()

    try:
        execute(conn, "DELETE FROM expenses")
        conn.commit()

        return jsonify({
            "success": True,
            "message": "All expenses cleared."
        })
    finally:
        conn.close()


@app.route("/api/budget", methods=["GET"])
def get_budget():
    conn = get_db_connection()

    try:
        budget = execute(
            conn,
            "SELECT amount FROM budget WHERE id = 1"
        ).fetchone()

        return jsonify({
            "amount": budget["amount"] if budget else 0
        })
    finally:
        conn.close()


@app.route("/api/budget", methods=["POST"])
def update_budget():
    data = request.get_json(silent=True) or {}
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

    try:
        cursor = execute(
            conn,
            "UPDATE budget SET amount = ? WHERE id = 1",
            (amount,)
        )

        if cursor.rowcount == 0:
            execute(
                conn,
                "INSERT INTO budget (id, amount) VALUES (1, ?)",
                (amount,)
            )

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Budget updated successfully."
        })
    finally:
        conn.close()


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(
        debug=not bool(os.environ.get("RENDER")),
        host="0.0.0.0",
        port=port
    )

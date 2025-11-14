import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "dev"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dog_links.db"

dog_links = [
    {
        "id": 1,
        "title": "30 Fun and Fascinating Dog Facts",
        "url": "https://www.akc.org/expert-advice/lifestyle/dog-facts/",
        "score": 10,
        "hidden": False,
    },
    {
        "id": 2,
        "title": "Why Do Dogs Tilt Their Heads?",
        "url": "https://www.sciencefocus.com/nature/why-do-dogs-tilt-their-head-when-you-speak-to-them",
        "score": 5,
        "hidden": False,
    },
    {
        "id": 3,
        "title": "r/dogs — top posts",
        "url": "https://www.reddit.com/r/dogs/",
        "score": 3,
        "hidden": False,
    },
    {
        "id": 4,
        "title": "Basic Dog Training Guide",
        "url": "https://www.animalhumanesociety.org/resource/how-get-most-out-training-your-dog",
        "score": 2,
        "hidden": False,
    },
    {
        "id": 5,
        "title": "The Dogist (photo stories)",
        "url": "https://thedogist.com/",
        "score": 1,
        "hidden": False,
    },
]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    score INTEGER NOT NULL,
    hidden INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        current_count = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        if current_count == 0:
            conn.executemany(
                "INSERT INTO posts (id, title, url, score, hidden) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        link["id"],
                        link["title"],
                        link["url"],
                        link["score"],
                        int(link.get("hidden", False)),
                    )
                    for link in dog_links
                ],
            )


def fetch_posts(hidden):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, url, score, hidden FROM posts WHERE hidden = ? ORDER BY score DESC, created_at DESC",
            (1 if hidden else 0,),
        ).fetchall()
    return [dict(row) for row in rows]


def post_exists(post_id):
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM posts WHERE id = ?", (post_id,)).fetchone()
    return row is not None


init_db()


@app.get("/")
def homepage():
    visible_links = fetch_posts(hidden=False)
    hidden_links = fetch_posts(hidden=True)
    return render_template(
        "index.html",
        visible_links=visible_links,
        hidden_links=hidden_links,
    )


@app.post("/posts")
def create_post():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()

    if not title:
        flash("Title is required to submit a post.")
        return redirect(url_for("homepage"))

    if not url.lower().startswith("http"):
        flash("URL must start with http or https.")
        return redirect(url_for("homepage"))

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO posts (title, url, score, hidden) VALUES (?, ?, ?, 0)",
            (title, url, 1),
        )
    return redirect(url_for("homepage"))


@app.post("/posts/<int:link_id>/<action>")
def vote(link_id, action):
    if action not in {"upvote", "downvote"}:
        flash("Unknown action.")
        return redirect(url_for("homepage"))

    if not post_exists(link_id):
        flash("Post could not be found.")
        return redirect(url_for("homepage"))

    change = 1 if action == "upvote" else -1
    with get_connection() as conn:
        conn.execute("UPDATE posts SET score = score + ? WHERE id = ?", (change, link_id))

    return redirect(url_for("homepage"))


@app.post("/posts/<int:link_id>/toggle_hide")
def toggle_hide(link_id):
    if not post_exists(link_id):
        flash("Post could not be found.")
        return redirect(url_for("homepage"))

    with get_connection() as conn:
        conn.execute(
            "UPDATE posts SET hidden = CASE hidden WHEN 0 THEN 1 ELSE 0 END WHERE id = ?",
            (link_id,),
        )
    return redirect(url_for("homepage"))

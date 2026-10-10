
from flask import Flask, request, jsonify, render_template, session
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path
from datetime import datetime, timezone
import os
import json
import threading

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError(
        "يجب إعداد SECRET_KEY قبل تشغيل التطبيق لحماية الجلسات."
    )

chat_password = os.environ.get("CHAT_PASSWORD")
if not chat_password:
    raise RuntimeError(
        "يجب إعداد CHAT_PASSWORD قبل تشغيل التطبيق."
    )

PASSWORD_HASH = generate_password_hash(chat_password)

DATA_FILE = Path(__file__).with_name("messages.json")
file_lock = threading.Lock()


def read_messages():
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        app.logger.exception("تعذرت قراءة ملف الرسائل")
        return []


def save_messages(messages):
    temporary_file = DATA_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(messages, file, ensure_ascii=False, indent=2)

    temporary_file.replace(DATA_FILE)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")

    if not isinstance(password, str):
        return jsonify({"success": False}), 400

    if check_password_hash(PASSWORD_HASH, password):
        session["logged_in"] = True
        session.permanent = False
        return jsonify({"success": True})

    return jsonify({"success": False}), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/messages", methods=["GET", "POST"])
def messages():
    if not session.get("logged_in"):
        return jsonify({"error": "غير مصرح"}), 401

    if request.method == "GET":
        with file_lock:
            return jsonify({"messages": read_messages()})

    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not isinstance(text, str):
        return jsonify({"error": "الرسالة غير صحيحة"}), 400

    text = text.strip()

    if not text or len(text) > 2000:
        return jsonify({"error": "يجب أن تكون الرسالة بين حرف واحد و2000 حرف"}), 400

    message = {
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    with file_lock:
        all_messages = read_messages()
        all_messages.append(message)
        save_messages(all_messages)

    return jsonify({"success": True, "message": message}), 201


if __name__ == "__main__":
    app.run(debug=False)

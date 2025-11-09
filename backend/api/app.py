# backend/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from models import (
    init_db, create_user, validate_user, list_verified_users,
    create_chat_request, set_chat_request_status, list_incoming_requests,
    is_chat_allowed, create_group, list_groups, create_group_request,
    list_group_requests_for_admin, accept_group_request
)

app = Flask(__name__)
CORS(app)
init_db()

@app.post("/signup")
def signup():
    data = request.get_json(force=True)
    try:
        create_user(data["username"], data["password"])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

@app.post("/login")
def login():
    data = request.get_json(force=True)
    if validate_user(data["username"], data["password"]):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401

@app.get("/users")
def users():
    me = request.args.get("me")
    return jsonify({"users": list_verified_users(exclude=me)})

@app.get("/chat/requests/incoming")
def incoming():
    me = request.args.get("me")
    return jsonify({"requests": list_incoming_requests(me)})

@app.post("/chat/request")
def chat_request():
    data = request.get_json(force=True)
    req_id = create_chat_request(data["from_user"], data["to_user"])
    return jsonify({"ok": True, "request_id": req_id})

@app.post("/chat/accept")
def chat_accept():
    data = request.get_json(force=True)
    set_chat_request_status(data["request_id"], "accepted")
    return jsonify({"ok": True})

@app.get("/chat/allowed")
def chat_allowed():
    u1 = request.args.get("u1")
    u2 = request.args.get("u2")
    return jsonify({"allowed": is_chat_allowed(u1, u2)})

@app.post("/group/create")
def group_create():
    data = request.get_json(force=True)
    gid = create_group(data["name"], data["created_by"])
    return jsonify({"ok": True, "group_id": gid})

@app.get("/groups")
def groups_list():
    return jsonify({"groups": list_groups()})

@app.post("/group/join-request")
def group_join_request():
    data = request.get_json(force=True)
    rid = create_group_request(data["group_id"], data["user"])
    return jsonify({"ok": True, "request_id": rid})

@app.get("/group/requests")
def group_requests():
    admin = request.args.get("admin")
    return jsonify({"requests": list_group_requests_for_admin(admin)})

@app.post("/group/accept")
def group_accept():
    data = request.get_json(force=True)
    ok = accept_group_request(data["request_id"])
    return jsonify({"ok": ok})

@app.get("/group/members")
def group_members():
    gid = request.args.get("group_id", type=int)
    if not gid:
        return jsonify({"members": []})
    from models import list_group_members
    return jsonify({"members": list_group_members(gid)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=7000, debug=True)

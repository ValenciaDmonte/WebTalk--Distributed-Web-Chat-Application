WebTalk/
│
├── backend/
│   ├── api/
│   │   ├── app.py
│   │   ├── models.py
│   │   └── webtalk.sqlite
│   │
│   ├── database/
│   │   ├── backup.sqlite
│   │   └── chat_backup.sqlite (if used)
│   │
│   ├── backup_server.py
│   ├── bully_election.py
│   ├── chat_server_primary.py
│   ├── chat_server_replica.py
│   ├── lamport.py
│   ├── load_balancer.py
│   └── ...
│
├── frontend/
│   ├── app.py
│   └── templates/
│       ├── index.html
│       ├── signup.html
│       ├── chat.html
│
└── start_all.ps1   ← runs all components




Run this command in your WebTalk root folder:

pip install flask flask-cors flask-socketio requests werkzeug eventlet


All database files are auto-created in:

backend/api/webtalk.sqlite     ← main application data
backend/database/backup.sqlite ← message replication backup


Run Instructions
🧩 1️⃣ Option A – Run manually (development)

Open 6 PowerShell terminals (or tabs) and run these in order:

# Terminal 1
cd backend\api
python app.py

# Terminal 2
cd backend
python backup_server.py

# Terminal 3
cd backend
python chat_server_primary.py

# Terminal 4
cd backend
python chat_server_replica.py

# Terminal 5
cd backend
python load_balancer.py

# Terminal 6
cd frontend
python app.py


Then open in browser:
👉 http://127.0.0.1:8080

🧩 2️⃣ Option B – Run all at once (recommended)

If you’re on Windows with PowerShell:

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd C:\Users\Valencia\Downloads\WebTalk
.\start_all.ps1




nexora-python/
├── app.py              ← Flask app (all routes + API)
├── check_db.py         ← Run this FIRST to verify everything works
├── requirements.txt    ← pip install -r requirements.txt
├── .env                ← Your credentials (edit this)
├── setup.sql           ← Creates database + users table (run once)
└── templates/
    ├── index.html      ← Homepage with login / signup modals
    └── dashboard.html  ← Protected page after login# database_connection_example

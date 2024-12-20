# firebase.py
from firebase_admin import credentials, firestore, initialize_app

# Initialize Firebase Admin
cred = credentials.Certificate(r"G:\Discord Bots\NexioDevBot\nexio-discord-firebase-adminsdk-69kfk-4637335efd.json")
try:
    initialize_app(cred)  # Only call once
except ValueError:
    pass  # Ignore if already initialized

db = firestore.client()  # Shared Firestore client

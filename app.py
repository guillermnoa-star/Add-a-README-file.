
import os
from flask import Flask, redirect, request

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
      <body style="background:#111;color:white;text-align:center;padding:80px;font-family:Arial">
        <h1 style="color:#ff334f">IZIIX</h1>
        <p>Connecte ton compte TikTok à ta communauté.</p>
        <a href="/login" style="background:#ff334f;color:white;padding:15px 25px;text-decoration:none;border-radius:8px">
          Se connecter avec TikTok
        </a>
      </body>
    </html>
    """

@app.route("/login")
def login():
    return "Connexion TikTok en cours de configuration."

@app.route("/callback")
def callback():
    return "Retour de connexion TikTok."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

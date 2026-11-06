
import os
import secrets
import html
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, request, session, url_for, Response

app = Flask(__name__)

# =====================================
# CONFIGURATION
# =====================================

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")

REDIRECT_URI = "https://iziix-login.onrender.com/callback"

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY manquante dans Render.")

if not CLIENT_KEY or not CLIENT_SECRET:
    raise RuntimeError("Clés TikTok manquantes dans Render.")


# =====================================
# VERIFICATION DU SITE PAR TIKTOK
# =====================================

@app.route("/tiktokX3eKnyn0WFTuJ5m2FzHWkVwz60bnyzOh.txt")
def tiktok_verification():
    content = (
        "tiktok-developers-site-verification="
        "X3eKnyn0WFTuJ5m2FzHWkVwz60bnyzOh"
    )

    return Response(content, mimetype="text/plain")


# =====================================
# DESIGN DU SITE
# =====================================

def page(content):
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>IZIIX</title>

        <style>
            body {{
                background: #101010;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 60px 15px;
            }}

            .card {{
                background: #1c1c1c;
                border: 1px solid #333;
                border-radius: 15px;
                padding: 30px;
                max-width: 430px;
                margin: auto;
            }}

            h1 {{
                color: #ff334f;
            }}

            a.button {{
                display: inline-block;
                background: #ff334f;
                color: white;
                padding: 14px 25px;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 15px;
            }}

            img {{
                width: 100px;
                height: 100px;
                border-radius: 50%;
                object-fit: cover;
            }}
        </style>
    </head>

    <body>
        <div class="card">
            <h1>IZIIX</h1>
            {content}
        </div>
    </body>
    </html>
    """


# =====================================
# PAGE D'ACCUEIL
# =====================================

@app.route("/")
def home():

    if session.get("tiktok_profile"):
        return redirect(url_for("profile"))

    return page("""
        <h2>Connecte ton compte TikTok</h2>

        <p>
            Rejoins la communauté IZIIX.
        </p>

        <a class="button" href="/login">
            Se connecter avec TikTok
        </a>
    """)


# =====================================
# CONNEXION TIKTOK
# =====================================

@app.route("/login")
def login():

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_key": CLIENT_KEY,
        "response_type": "code",
        "scope": "user.info.basic",
        "redirect_uri": REDIRECT_URI,
        "state": state
    }

    authorization_url = AUTHORIZE_URL + "?" + urlencode(params)

    return redirect(authorization_url)


# =====================================
# RETOUR DE TIKTOK
# =====================================

@app.route("/callback")
def callback():

    if request.args.get("error"):

        error = html.escape(
            request.args.get(
                "error_description",
                "Connexion refusée"
            )
        )

        return page(
            f"<h2>Connexion refusée</h2><p>{error}</p>"
        )

    returned_state = request.args.get("state")
    saved_state = session.pop("oauth_state", None)

    if not saved_state or not returned_state:

        return page(
            "<h2>Erreur de sécurité</h2><p>Réessaie.</p>"
        ), 400

    if not secrets.compare_digest(
        saved_state,
        returned_state
    ):

        return page(
            "<h2>Vérification de sécurité échouée.</h2>"
        ), 400

    code = request.args.get("code")

    if not code:

        return page(
            "<h2>Code TikTok manquant.</h2>"
        ), 400

    # Récupération du jeton TikTok

    try:

        token_response = requests.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI
            },
            timeout=20
        )

        token_data = token_response.json()

    except (requests.RequestException, ValueError):

        return page(
            "<h2>Erreur de connexion à TikTok.</h2>"
        ), 502

    access_token = token_data.get("access_token")

    if token_response.status_code != 200 or not access_token:

        return page(
            "<h2>Connexion impossible</h2>"
            "<p>Vérifie la configuration de ton application TikTok.</p>"
        ), 400

    # Récupération du profil TikTok

    try:

        user_response = requests.get(
            USER_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            params={
                "fields": "open_id,avatar_url,display_name"
            },
            timeout=20
        )

        user_data = user_response.json()

    except (requests.RequestException, ValueError):

        return page(
            "<h2>Impossible de récupérer ton profil.</h2>"
        ), 502

    if user_response.status_code != 200:

        return page(
            "<h2>Erreur de récupération du profil TikTok.</h2>"
        ), 400

    profile_data = user_data.get(
        "data", {}
    ).get("user", {})

    if not profile_data.get("open_id"):

        return page(
            "<h2>Profil TikTok introuvable.</h2>"
        ), 400

    # Enregistrement des informations du profil

    session.clear()

    session["tiktok_profile"] = {
        "open_id": profile_data.get("open_id"),
        "display_name": profile_data.get(
            "display_name",
            "Utilisateur TikTok"
        ),
        "avatar_url": profile_data.get("avatar_url", "")
    }

    return redirect(url_for("profile"))


# =====================================
# PROFIL UTILISATEUR
# =====================================

@app.route("/profile")
def profile():

    user = session.get("tiktok_profile")

    if not user:
        return redirect(url_for("home"))

    name = html.escape(user["display_name"])
    avatar = html.escape(
        user["avatar_url"],
        quote=True
    )

    avatar_html = ""

    if avatar.startswith("https://"):

        avatar_html = (
            f'<img src="{avatar}" alt="Photo de profil">'
        )

    return page(f"""
        <h2>Connexion réussie !</h2>

        {avatar_html}

        <h3>{name}</h3>

        <p>Ton compte TikTok est connecté à IZIIX.</p>

        <a class="button" href="/logout">
            Déconnexion
        </a>
    """)


# =====================================
# DECONNEXION
# =====================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =====================================
# VERIFICATION DU SERVEUR
# =====================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "application": "IZIIX"
    }


# =====================================
# DEMARRAGE
# =====================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )

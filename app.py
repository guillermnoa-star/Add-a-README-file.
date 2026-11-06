
import os
import secrets
import requests

from urllib.parse import urlencode
from flask import (
    Flask,
    redirect,
    request,
    session,
    url_for,
    render_template_string
)

app = Flask(__name__)

# ==================================================
# CONFIGURATION IZIIX
# ==================================================

app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY manquant sur Render.")

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET")

REDIRECT_URI = "https://iziix-login.onrender.com/callback"

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"

# ==================================================
# PAGE D'ACCUEIL
# ==================================================

@app.route("/")
def home():

    if session.get("user"):
        return redirect(url_for("profile"))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>IZIIX - Connexion TikTok</title>

        <style>
            body {
                background: #101010;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 80px 20px;
            }

            h1 {
                color: #ff3030;
                font-size: 48px;
            }

            a {
                display: inline-block;
                background: #ff3030;
                color: white;
                padding: 15px 30px;
                border-radius: 8px;
                text-decoration: none;
                margin-top: 20px;
            }
        </style>
    </head>

    <body>
        <h1>IZIIX</h1>
        <p>Connecte ton compte TikTok à IZIIX.</p>
        <a href="/login">Se connecter avec TikTok</a>
    </body>
    </html>
    """)

# ==================================================
# CONNEXION TIKTOK
# ==================================================

@app.route("/login")
def login():

    if not CLIENT_KEY or not CLIENT_SECRET:
        return "Configuration TikTok manquante sur Render.", 500

    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    params = {
        "client_key": CLIENT_KEY,
        "scope": "user.info.basic",
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": state
    }

    return redirect(AUTHORIZE_URL + "?" + urlencode(params))

# ==================================================
# RETOUR TIKTOK / CALLBACK
# ==================================================

@app.route("/callback")
def callback():

    if request.args.get("error"):
        return (
            "Connexion TikTok refusée : "
            + request.args.get("error"),
            400
        )

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        return "Code de connexion TikTok manquant.", 400

    if not state or state != session.get("oauth_state"):
        return "Erreur de sécurité OAuth.", 400

    session.pop("oauth_state", None)

    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "client_key": CLIENT_KEY,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            timeout=20
        )

        token_data = token_response.json()

        if token_response.status_code != 200:
            return "Erreur TikTok : " + str(token_data), 400

        access_token = token_data.get("access_token")

        if not access_token:
            return "Token TikTok introuvable.", 400

        user_response = requests.get(
            USER_INFO_URL,
            params={
                "fields": "open_id,avatar_url,display_name"
            },
            headers={
                "Authorization": "Bearer " + access_token
            },
            timeout=20
        )

        user_data = user_response.json()

        if user_response.status_code != 200:
            return "Erreur profil TikTok : " + str(user_data), 400

        user = user_data.get("data", {}).get("user")

        if not user:
            return "Impossible de récupérer le profil TikTok.", 400

        session["user"] = {
            "open_id": user.get("open_id"),
            "display_name": user.get("display_name"),
            "avatar_url": user.get("avatar_url")
        }

        return redirect(url_for("profile"))

    except requests.RequestException:
        return "Impossible de contacter TikTok. Réessaie plus tard.", 500

    except ValueError:
        return "Réponse TikTok invalide.", 500

# ==================================================
# PROFIL UTILISATEUR
# ==================================================

@app.route("/profile")
def profile():

    user = session.get("user")

    if not user:
        return redirect(url_for("home"))

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Profil IZIIX</title>

        <style>
            body {
                background: #101010;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 60px 20px;
            }

            h1 {
                color: #ff3030;
            }

            img {
                width: 110px;
                height: 110px;
                border-radius: 50%;
            }

            a {
                color: white;
                background: #ff3030;
                padding: 12px 25px;
                border-radius: 7px;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }
        </style>
    </head>

    <body>
        <h1>IZIIX</h1>

        {% if user.avatar_url %}
            <img src="{{ user.avatar_url }}" alt="Photo de profil">
        {% endif %}

        <h2>{{ user.display_name }}</h2>
        <p>Ton compte TikTok est connecté.</p>

        <a href="/logout">Se déconnecter</a>
    </body>
    </html>
    """, user=user)

# ==================================================
# DECONNEXION
# ==================================================

@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("home"))

# ==================================================
# CONDITIONS D'UTILISATION
# ==================================================

@app.route("/terms")
@app.route("/terms/")
def terms():

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Conditions d'utilisation - IZIIX</title>
    </head>

    <body style="font-family:Arial;max-width:850px;margin:40px auto;padding:20px;line-height:1.6">

        <h1>Conditions d'utilisation - IZIIX</h1>
        <p>Dernière mise à jour : novembre 2026</p>

        <h2>1. Présentation</h2>
        <p>IZIIX est un service communautaire permettant aux utilisateurs
        de connecter leur compte TikTok et de rejoindre la communauté IZIIX.</p>

        <h2>2. Utilisation du service</h2>
        <p>L'utilisateur s'engage à utiliser IZIIX de manière légale
        et à respecter les autres membres.</p>

        <h2>3. Connexion TikTok</h2>
        <p>La connexion TikTok permet de récupérer certaines informations
        de profil autorisées par TikTok et acceptées par l'utilisateur.</p>

        <h2>4. Services tiers</h2>
        <p>IZIIX utilise des services tiers. Leur disponibilité
        et leur fonctionnement ne dépendent pas uniquement d'IZIIX.</p>

        <h2>5. Contact</h2>
        <p>Pour toute question : guillermnoa@gmail.com</p>

    </body>
    </html>
    """)

# ==================================================
# POLITIQUE DE CONFIDENTIALITE
# ==================================================

@app.route("/privacy")
@app.route("/privacy/")
def privacy():

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Politique de confidentialité - IZIIX</title>
    </head>

    <body style="font-family:Arial;max-width:850px;margin:40px auto;padding:20px;line-height:1.6">

        <h1>Politique de confidentialité - IZIIX</h1>
        <p>Dernière mise à jour : novembre 2026</p>

        <h2>1. Informations collectées</h2>
        <p>Lors de la connexion TikTok, IZIIX reçoit les informations
        de profil autorisées, notamment l'identifiant TikTok,
        le nom affiché et la photo de profil.</p>

        <h2>2. Utilisation des informations</h2>
        <p>Ces informations servent à identifier l'utilisateur
        et à afficher son profil sur IZIIX.</p>

        <h2>3. Conservation</h2>
        <p>Les informations de profil sont conservées dans la session
        de connexion du navigateur. Elles sont supprimées lorsque
        l'utilisateur se déconnecte ou lorsque la session expire.</p>

        <h2>4. Partage des informations</h2>
        <p>IZIIX ne vend pas les informations personnelles des utilisateurs.
        Les services tiers utilisés restent soumis à leurs propres
        politiques de confidentialité.</p>

        <h2>5. Droits des utilisateurs</h2>
        <p>Pour toute question concernant les données personnelles,
        les utilisateurs peuvent contacter IZIIX à l'adresse suivante :
        guillermnoa@gmail.com</p>

    </body>
    </html>
    """)

# ==================================================
# VERIFICATION TIKTOK - CONDITIONS D'UTILISATION
# ==================================================

@app.route("/terms/tiktokkespsfwSl9qHM44EEvkoWVdyPi84iZVF.txt")
def tiktok_terms_verification():

    return (
        "tiktok-developers-site-verification=kespsfwSl9qHM44EEvkoWVdyPi84iZVF",
        200,
        {"Content-Type": "text/plain; charset=utf-8"}
    )

# ==================================================
# VERIFICATION TIKTOK - POLITIQUE DE CONFIDENTIALITE
# ==================================================

@app.route("/privacy/tiktokRa8ANSlFc3s4QD37A9gE4GMxfWPfAzkf.txt")
def tiktok_privacy_verification():

    return (
        "tiktok-developers-site-verification=Ra8ANSlFc3s4QD37A9gE4GMxfWPfAzkf",
        200,
        {"Content-Type": "text/plain; charset=utf-8"}
    )

# ==================================================
# ANCIENNE VERIFICATION TIKTOK
# ==================================================

@app.route("/tiktokX3eKnyn0WFTUJ5m2FzHWkVwz60bnyzOh.txt")
def old_tiktok_verification():

    return (
        "tiktok-developers-site-verification=X3eKnyn0WFTuJ5m2FzHWkVwz60bnyzOh",
        200,
        {"Content-Type": "text/plain; charset=utf-8"}
    )

# ==================================================
# TEST DU SERVEUR
# ==================================================

@app.route("/health")
def health():
    return "IZIIX OK", 200

# ==================================================
# DEMARRAGE LOCAL
# ==================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )

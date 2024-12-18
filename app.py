# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import matplotlib.pyplot as plt
import os
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import concurrent.futures
from googletrans import Translator
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd

app = Flask(__name__)
app.secret_key = "chave_super_secreta"

# Configuração do banco de dados PostgreSQL com encoding explícito
db_params = {
    'host': 'localhost',
    'port': '5432',
    'database': 'anime_recommender',
    'user': 'postgres',
    'password': 'Natan2020'
}

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{db_params['user']}:{db_params['password']}@"
    f"{db_params['host']}:{db_params['port']}/{db_params['database']}"
    "?client_encoding=utf8&options=-csearch_path%3Dpublic"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Add engine options
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "connect_args": {
        "options": "-c client_encoding=utf8"
    }
}

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Modelo de Usuário
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    search_history = db.Column(db.String, nullable=True)
    clicked_animes = db.relationship("ClickedAnime", backref="user", lazy=True)


# Modelo de Animes Clicados
class ClickedAnime(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    anime_id = db.Column(db.Integer, nullable=False)
    anime_title = db.Column(db.String(200), nullable=False)
    anime_url = db.Column(db.String, nullable=False)
    anime_image_url = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# Dicionário de tradução para as categorias com IDs dos gêneros
CATEGORY_TRANSLATION = {
    "ação": 1,
    "action": 1,
    "aventura": 2,
    "adventure": 2,
    "carros": 3,
    "cars": 3,
    "comédia": 4,
    "comedy": 4,
    "drama": 8,
    "fantasia": 10,
    "fantasy": 10,
    "terror": 14,
    "horror": 14,
    "mistério": 7,
    "mystery": 7,
    "romance": 22,
    "ficção científica": 24,
    "sci-fi": 24,
    "esporte": 30,
    "sports": 30,
    "sobrenatural": 37,
    "supernatural": 37,
}

# Função de verificação de login
def is_logged_in():
    return "user_id" in session

# Create a list to track Tkinter variables and images
_tk_objects = []

def cleanup_tk_objects():
    """Clean up Tkinter objects before shutdown"""
    global _tk_objects
    for obj in _tk_objects:
        try:
            if hasattr(obj, 'destroy'):
                obj.destroy()
        except:
            pass
    _tk_objects.clear()

# Modify matplotlib usage to avoid Tkinter window creation
import matplotlib
matplotlib.use('Agg')  # Use Agg backend instead of TkAgg

# Função para gerar gráficos baseados nos animes clicados pelo usuário
def generate_user_charts(user_id):
    """Generate charts for user statistics"""
    try:
        clicked_animes = ClickedAnime.query.filter_by(user_id=user_id).all()
        titles, episodes, scores = [], [], []
        
        for anime in clicked_animes:
            response = requests.get(f"https://api.jikan.moe/v4/anime/{anime.anime_id}")
            if response.status_code == 200:
                data = response.json()["data"]
                title = anime.anime_title
                episode_count = data.get("episodes")
                score = data.get("score")

                if episode_count is not None and score is not None:
                    titles.append(title)
                    episodes.append(episode_count)
                    scores.append(score)

        if titles:
            plt.figure(figsize=(10, 5))
            plt.bar(titles, episodes, color="skyblue")
            plt.xlabel("Animes")
            plt.ylabel("Quantidade de Episódios")
            plt.xticks(rotation=45, ha="right")
            plt.title("Quantidade de Episódios por Anime")
            plt.tight_layout()
            episodes_chart_path = os.path.join("static", "episodes_chart.png")
            plt.savefig(episodes_chart_path)
            plt.close()

            plt.figure(figsize=(10, 5))
            plt.bar(titles, scores, color="lightgreen")
            plt.xlabel("Animes")
            plt.ylabel("Nota")
            plt.xticks(rotation=45, ha="right")
            plt.title("Nota dos Animes")
            plt.tight_layout()
            scores_chart_path = os.path.join("static", "scores_chart.png")
            plt.savefig(scores_chart_path)
            plt.close()
    except Exception as e:
        print(f"Error generating charts: {e}")

# Rota inicial
@app.route("/")
def index():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# Rota de registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(
            request.form["password"], method="pbkdf2:sha256", salt_length=16
        )
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


# Rota de login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
    return render_template("login.html")


# Função para buscar animes por nome usando Jikan API
def search_animes_by_name(name):
    url = f"https://api.jikan.moe/v4/anime?q={name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("data", [])
    return []

# Rota para o dashboard do usuário
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    username = session.get("username", "Usuário")
    animes = []

    if request.method == "POST":
        search_type = request.form.get("search_type", "category")
        if search_type == "category":
            category = request.form["category"]
            animes = search_animes(category)
            session["last_search"] = category
        else:
            name = request.form["anime_name"]
            animes = search_animes_by_name(name)
            session["last_search"] = name

    return render_template("dashboard.html", animes=animes, username=username)


# Rota para detalhes do anime
@app.route("/anime/<int:anime_id>")
def anime(anime_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    url = f"https://api.jikan.moe/v4/anime/{anime_id}"
    response = requests.get(url)
    if response.status_code == 200:
        anime_details = response.json()["data"]
        
        # Traduzir a sinopse para português
        if anime_details.get("synopsis"):
            translator = Translator()
            try:
                translated = translator.translate(anime_details["synopsis"], dest="pt")
                anime_details["synopsis"] = translated.text
            except:
                # Em caso de erro na tradução, mantém a sinopse original
                pass

        user_id = session["user_id"]

        # Verificar se o anime já foi clicado
        if not ClickedAnime.query.filter_by(user_id=user_id, anime_id=anime_id).first():
            clicked_anime = ClickedAnime(
                anime_id=anime_id,
                anime_title=anime_details["title"],
                anime_url=anime_details["url"],
                anime_image_url=anime_details["images"]["jpg"]["image_url"],
                user_id=user_id,
            )
            db.session.add(clicked_anime)
            db.session.commit()

        return render_template(
            "anime.html", anime=anime_details, username=session["username"]
        )
    return redirect(url_for("dashboard"))


# Rota para deletar anime do histórico
@app.route("/delete_anime/<int:anime_id>", methods=["POST"])
def delete_anime(anime_id):
    if not is_logged_in():
        return redirect(url_for("login"))

    anime_to_delete = ClickedAnime.query.filter_by(
        id=anime_id, user_id=session["user_id"]
    ).first()
    if anime_to_delete:
        db.session.delete(anime_to_delete)
        db.session.commit()

    return redirect(url_for("user"))


# Rota para limpar todo o histórico de animes
@app.route("/clear_history", methods=["POST"])
def clear_history():
    if not is_logged_in():
        return redirect(url_for("login"))

    ClickedAnime.query.filter_by(user_id=session["user_id"]).delete()
    db.session.commit()

    return redirect(url_for("user"))


# Função para recomendar animes com base nos animes clicados pelo usuário
def recommend_animes(user_id):
    clicked_animes = ClickedAnime.query.filter_by(user_id=user_id).all()
    clicked_categories = set()

    # Buscar categorias em paralelo para melhorar eficiência
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                requests.get, f"https://api.jikan.moe/v4/anime/{clicked.anime_id}"
            )
            for clicked in clicked_animes
        ]
        for future in concurrent.futures.as_completed(futures):
            response = future.result()
            if response.status_code == 200:
                genres = response.json()["data"].get("genres", [])
                for genre in genres:
                    clicked_categories.add(genre["name"].lower())

    recommended_animes = []
    for category in clicked_categories:
        translated_category = CATEGORY_TRANSLATION.get(category, category)
        url = f"https://api.jikan.moe/v4/anime?genres={translated_category}"
        response = requests.get(url)
        if response.status_code == 200:
            recommended_animes.extend(response.json().get("data", []))

    clicked_anime_ids = {clicked.anime_id for clicked in clicked_animes}
    unique_recommendations = [
        anime
        for anime in recommended_animes
        if anime["mal_id"] not in clicked_anime_ids
    ]

    return unique_recommendations[:10]

def perform_clustering(user_id):
    clicked_animes = ClickedAnime.query.filter_by(user_id=user_id).all()
    anime_data = []
    
    for anime in clicked_animes:
        response = requests.get(f"https://api.jikan.moe/v4/anime/{anime.anime_id}")
        if response.status_code == 200:
            data = response.json()["data"]
            genres = [genre["name"] for genre in data.get("genres", [])]
            genre_str = ", ".join(genres)
            episodes = data.get("episodes", 0)
            score = data.get("score", 0)
            
            anime_data.append({
                'title': anime.anime_title,
                'genres': genre_str,
                'episodes': episodes,
                'score': score
            })
    
    if len(anime_data) < 2:
        return None
        
    df = pd.DataFrame(anime_data)
    
    # Prepare features for clustering
    X = df[['episodes', 'score']].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Determine optimal number of clusters (max 5)
    n_clusters = min(5, len(anime_data))
    
    # Perform K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Add ranking based on score and episodes
    df['rank_score'] = df['cluster'] + 1
    
    # Sort by score within each cluster
    df = df.sort_values(['cluster', 'score'], ascending=[True, False])
    
    return df.to_dict('records')

# Rota para o histórico de animes clicados do usuário, incluindo recomendações
@app.route("/user")
def user():
    if not is_logged_in():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    clicked_animes = ClickedAnime.query.filter_by(user_id=user_id).all()
    recommended_animes = recommend_animes(user_id)
    
    # Get clustering results
    clustering_results = perform_clustering(user_id)

    # Gerar gráficos para os animes clicados pelo usuário
    generate_user_charts(user_id)

    return render_template(
        "user.html",
        username=session["username"],
        clicked_animes=clicked_animes,
        recommended_animes=recommended_animes,
        clustering_results=clustering_results
    )


# Função para buscar animes pela categoria usando Jikan API
def search_animes(category):
    category_id = CATEGORY_TRANSLATION.get(category.lower())
    if category_id:
        url = f"https://api.jikan.moe/v4/anime?genres={category_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("data", [])
    return []


# Rota para adicionar anime recomendado ao histórico
@app.route("/add_recommended_anime", methods=["POST"])
def add_recommended_anime():
    if not is_logged_in():
        return redirect(url_for("login"))

    anime_id = int(request.form["anime_id"])
    user_id = session["user_id"]

    # Verificar se o anime já existe no histórico
    existing_anime = ClickedAnime.query.filter_by(user_id=user_id, anime_id=anime_id).first()
    if not existing_anime:
        clicked_anime = ClickedAnime(
            anime_id=anime_id,
            anime_title=request.form["anime_title"],
            anime_url=request.form["anime_url"],
            anime_image_url=request.form["anime_image"],
            user_id=user_id,
        )
        db.session.add(clicked_anime)
        db.session.commit()

    return redirect(url_for("user"))

# Rota para logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Register cleanup function to run at exit
import atexit
atexit.register(cleanup_tk_objects)

if __name__ == "__main__":
    with app.app_context():
        try:
            if not os.path.exists('static'):
                os.makedirs('static')
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
            raise

    # Run the Flask app with cleanup handling
    try:
        app.run(debug=True)
    finally:
        cleanup_tk_objects()

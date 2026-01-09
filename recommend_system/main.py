# uvicorn main:app --reload --host 0.0.0.0 --port 8000

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
import os

data = pd.read_csv("dataset_movies_users.csv")
# ид_п, ид_ф, название, жанр, год, рейтинг

# модели данных
class MovieTitles(BaseModel):
    titles: List[str]


class MovieTitleWithStats(BaseModel):
    Название: str
    w_score: float
    кол_во_оценок: int


class MovieTitlesWithStats(BaseModel):
    films: List[MovieTitleWithStats]


class GenreRequest(BaseModel):
    genre: str


class MovieDetail(BaseModel):
    Название: str
    Жанры: str
    Год: int


class GenreResponse(BaseModel):
    films: List[MovieDetail]
    genre: str


class ContentRequest(BaseModel):
    title: str


class MovieDetailWithScore(BaseModel):
    Название: str
    Рейтинг: float
    Жанры: str
    Год: int
    score: float


class ContentResponse(BaseModel):
    films: List[MovieDetailWithScore]
    base_film: str


class TempUserRating(BaseModel):
    Название: str
    Рейтинг: float


class TempUserRatingsRequest(BaseModel):
    ratings: List[TempUserRating]


# FastAPI и методы
app = FastAPI(title="Movie Recommendation API", version="1.0")

# все фильмы
movies = data[['Id_фильма', 'Название', 'Жанры', 'Год']].drop_duplicates(subset='Id_фильма').reset_index(drop=True)

@app.get("/all-movies")
def get_all_movies():
    all_movie_titles = movies['Название'].dropna().unique().tolist()
    return {"movies": all_movie_titles}

# взвешенный рейтинг (для топ фильмов)
avg_ratings = data.groupby('Название')['Рейтинг'].mean().reset_index().rename(columns={'Рейтинг': 'Сред_рейтинг'})
count_ratings = data.groupby('Название')['Рейтинг'].count().reset_index().rename(columns={'Рейтинг': 'кол-во_оценок'})
popularite = avg_ratings.merge(count_ratings, on='Название')

v = popularite['кол-во_оценок']
R = popularite['Сред_рейтинг']
m = v.quantile(0.90)
c = R.mean()
popularite['w_score'] = (v * R + m * c) / (v + m)
pop_sort = popularite.sort_values('w_score', ascending=False).reset_index(drop=True)

@app.get('/top-{n}')
def get_top_n(n: int = 10):
    top_n = pop_sort.head(n)[['Название', 'w_score', 'кол-во_оценок']].rename(
        columns={'кол-во_оценок': 'кол_во_оценок'}).to_dict('records')
    return {"films": top_n}


# все жанры
@app.get('/genres')
def get_all_genres():
    all_genres = []
    for genres_str in movies['Жанры'].dropna():
        for g in genres_str.split(','):
            genre = g.strip()
            if genre not in all_genres:
                all_genres.append(genre)
    return {"genres": all_genres}


# рекомендации по жанру
@app.post('/recommendations/genre-details', response_model=GenreResponse)
def get_recommend_by_genre_details(request: GenreRequest):
    genre = request.genre

    filtered = movies[movies['Жанры'].str.contains(genre)]
    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"Жанр '{genre}' не найден.")

    k = min(10, len(filtered))
    sample = filtered.sample(n=k)[['Название', 'Жанры', 'Год']]
    films = sample.to_dict('records')
    return GenreResponse(films=films, genre=genre)

# разреженная матрица!
data_for_matrix = data[['Название', 'Id_пользователя', 'Рейтинг']].dropna()

unique_movies = data_for_matrix['Название'].unique()
unique_users = data_for_matrix['Id_пользователя'].unique()

movie_to_idx = {movie: idx for idx, movie in enumerate(unique_movies)}
user_to_idx = {user: idx for idx, user in enumerate(unique_users)}

rows = data_for_matrix['Название'].map(movie_to_idx).values
cols = data_for_matrix['Id_пользователя'].map(user_to_idx).values
ratings = data_for_matrix['Рейтинг'].values

n_movies = len(unique_movies) # размер матрицы
n_users = len(unique_users)
movie_user_matrix_sparse = csr_matrix((ratings, (rows, cols)), shape=(n_movies, n_users))  # разреженная матрица

print(f"Фильмов (строки): {movie_user_matrix_sparse.shape[0]}")
print(f"Пользователей (столбцы): {movie_user_matrix_sparse.shape[1]}")

idx_to_movie = {idx: movie for movie, idx in movie_to_idx.items()}
movie_titles_list = list(unique_movies)

# обучение модели
model_knn = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=11)
model_knn.fit(movie_user_matrix_sparse)

# рекомендации по названию
@app.post('/recommendations/content', response_model=ContentResponse)
def get_recommend_by_content(request: ContentRequest):
    title = request.title

    idx = movie_to_idx[title]

    distances, indices = model_knn.kneighbors(movie_user_matrix_sparse[idx], n_neighbors=11)
    similar_indices = indices[0][1:]
    similarity_scores = 1 - distances[0][1:]  # косинусное расстояние

    similar_titles = []
    for i in similar_indices:
        similar_titles.append(idx_to_movie[i])

    # данные о фильмах и метрика
    recommended_movies = movies[movies['Название'].isin(similar_titles)].copy()

    title_to_score = dict(zip(similar_titles, similarity_scores))
    recommended_movies['score'] = recommended_movies['Название'].map(title_to_score)

    recommended_movies = recommended_movies.sort_values('score', ascending=False).head(10) # самые похожие - первые

    recommended_movies = recommended_movies.merge(popularite[['Название', 'Сред_рейтинг']], on='Название')
    recommended_movies.rename(columns={'Сред_рейтинг': 'Рейтинг'}, inplace=True)

    films = recommended_movies[['Название', 'Рейтинг', 'Жанры', 'Год', 'score']].to_dict('records')

    return ContentResponse(films=films, base_film=title)


# оценки определенного пользователя
@app.get('/user/{user_id}')
def get_user_ratings(user_id: int):
    user_data = data[data['Id_пользователя'] == user_id]

    if user_data.empty:
        return {"error": f"Пользователь не найден или нет оценок!!"}

    top_rated = (
        user_data[['Название', 'Рейтинг', 'Жанры']]
        .dropna(subset=['Рейтинг'])
        .sort_values('Рейтинг', ascending=False)
        .head(10)
    )

    films_list = top_rated.to_dict('records')
    return {"films": films_list}

# --- Глобальная матрица для user-based CF (пользователи × фильмы) ---
user_movie_matrix_sparse = csr_matrix((ratings, (cols, rows)), shape=(n_users, n_movies))  # ← cols, rows!
model_knn_user = NearestNeighbors(metric='cosine', algorithm='brute', n_neighbors=11)
model_knn_user.fit(user_movie_matrix_sparse)

# рекомендации для определенного пользователя
@app.post('/recommendations/user/{user_id}', response_model=GenreResponse)
def get_recommend_by_user(user_id: int):
    if user_id not in user_to_idx:
        raise HTTPException(status_code=404, detail=f"Пользователь {user_id} не найден.")

    user_idx = user_to_idx[user_id]

    distances, indices = model_knn_user.kneighbors(user_movie_matrix_sparse[user_idx], n_neighbors=11)
    similar_user_indices = indices[0][1:]

    current_user_rated = set(data[data['Id_пользователя'] == user_id]['Название'])

    recommended_titles = set()
    for idx in similar_user_indices:
        similar_user_id = unique_users[idx]
        rated_by_similar = set(data[data['Id_пользователя'] == similar_user_id]['Название'])
        new_recommendations = rated_by_similar - current_user_rated
        recommended_titles.update(new_recommendations)

    recommended_titles = list(recommended_titles)[:10]

    if not recommended_titles:
        raise HTTPException(status_code=404, detail="Нет рекомендаций — похожие пользователи не оценили новых фильмов.")

    recommended_movies = movies[movies['Название'].isin(recommended_titles)][['Название', 'Жанры', 'Год']]
    films = recommended_movies.to_dict('records')
    return GenreResponse(films=films, genre=str(user_id))

# временные оценки новых пользователей
temp_user_ratings = {}

# рекомендации для нового пользователя
@app.post("/recommendations/new-user")
def recommend_for_new_user(request: TempUserRatingsRequest):
    import time
    temp_user_id = f"temp_{int(time.time() * 360)}"  # временный ид пользователя

    temp_user_ratings[temp_user_id] = request.ratings

    # рекомендации для него и отбираем только высокорейтинговые фильмы
    liked_movies = []
    for rating in request.ratings:
        if rating.Рейтинг >= 4.0:
            liked_movies.append(rating.Название)

    if not liked_movies:
        raise HTTPException(status_code=400, detail="Оцените хотя бы один фильм на 4+ для рекомендаций.")

    # сбор рекомендаций по каждому понравившемуся фильму
    all_recommended = []
    for title in liked_movies:
        if title in movie_to_idx:
            idx = movie_to_idx[title]
            distances, indices = model_knn.kneighbors(movie_user_matrix_sparse[idx], n_neighbors=6)
            similar_indices = indices[0][1:]

            for i in similar_indices:
                movie_title = idx_to_movie[i]
                if movie_title not in all_recommended:
                    all_recommended.append(movie_title)

    already_rated = {r.Название for r in request.ratings}

    recommendations = []
    for movie in all_recommended:
        if movie not in already_rated:
            recommendations.append(movie)
    recommendations = list(recommendations)[:10]

    rec_movies = movies[movies['Название'].isin(recommendations)][['Название', 'Жанры', 'Год']].to_dict('records')
    return GenreResponse(films=rec_movies, genre="new_user")

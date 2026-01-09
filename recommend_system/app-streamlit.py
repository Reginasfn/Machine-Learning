# streamlit run app_streamlit.py

import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

def main():
    st.set_page_config(page_title="🎬 Рекомендация фильмов", layout="wide")
    st.title("🎬 Рекомендация фильмов")

    menu = st.sidebar.selectbox(
        'Выберите действие',
        ['Топ-фильмов по взвешенному рейтингу', 'Рекомендации по жанру', 'Рекомендации по названию',
         'Рекомендации по пользователю', 'Рекомендации для нового пользователя']
    )

    if menu == 'Топ-фильмов по взвешенному рейтингу':
        st.subheader("Топ фильмов по взвешенному рейтингу (w_score)")
        n_top = st.slider("Выберите кол-во фильмов: ", min_value=5, max_value=30, value=10, step=5)

        with st.spinner('Загрузка топ-фильмов...'):
            try:
                response = requests.get(f"{API_URL}/top-{n_top}", timeout=160)
                if response.status_code == 200:
                    data = response.json()
                    df_top = pd.DataFrame(data["films"])
                    st.markdown("### Рейтинг популярных фильмов")
                    st.dataframe(
                        df_top.style.format({
                            'w_score': '{:.4f}',
                            'кол-во_оценок': '{:,}'
                        }).background_gradient(subset=['w_score'], cmap='Blues').set_properties(**{
                            'text-align': 'left',
                            'padding': '8px'
                        }),
                        width = 'stretch'
                    )
                else:
                    st.error(f"Ошибка сервера: {response.status_code}")
            except Exception as e:
                st.error(f"Ошибка: {e}")

    elif menu == 'Рекомендации по жанру':
        st.subheader("Поиск по жанру")
        with st.spinner("Загрузка списка жанров..."):
            try:
                genres_response = requests.get(f"{API_URL}/genres", timeout=160)
                if genres_response.status_code == 200:
                    all_genres = genres_response.json()["genres"]
                else:
                    all_genres = []
            except:
                all_genres = []

        if all_genres:
            selected_genre = st.selectbox(
                "Выберите жанр:",
                options=sorted(all_genres),
                index=None,
                placeholder="Выберите жанр..."
            )
        else:
            st.warning("Не удалось загрузить жанры.")
            selected_genre = st.text_input("Жанр:")

        if selected_genre and st.button("Получить рекомендации"):
            with st.spinner(f'Поиск фильмов по жанру "{selected_genre}"...'):
                try:
                    response = requests.post(
                        f"{API_URL}/recommendations/genre-details",
                        json={"genre": selected_genre.strip()},
                        timeout=160
                    )
                    if response.status_code == 200:
                        data = response.json()
                        films = data["films"]

                        df_recs = pd.DataFrame(films)
                        st.dataframe(
                            df_recs.style.set_properties(**{
                                'text-align': 'left',
                                'padding': '8px'
                            }).set_table_styles([
                                {'selector': 'th', 'props': [('background-color', '#f0f2f6'), ('font-weight', 'bold')]},
                                {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#fafafa')]}
                            ]),
                            width='stretch'
                        )
                    else:
                        st.error("Ошибка при получении рекомендаций.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    elif menu == 'Рекомендации по названию':
        st.subheader("Фильмы на основе схожести с оценками пользователей")
        title = st.text_input("Введите название фильма (например: Jumanji, Up, Avatar):")
        if st.button("Получить рекомендации"):
            if not title.strip():
                st.warning("Введите название фильма!!!!!")
            else:
                with st.spinner(f'Поиск похожих фильмов на "{title}"...'):
                    try:
                        response = requests.post(
                            f"{API_URL}/recommendations/content",
                            json={"title": title.strip()},
                            timeout=160
                        )
                        if response.status_code == 200:
                            data = response.json()
                            films = data["films"]
                            base_title = data["base_film"]

                            df_recs = pd.DataFrame(films)
                            st.success(f"Найдено {len(films)} фильмов, похожих на «{base_title}»:")

                            st.dataframe(
                                df_recs.style.format({
                                    'Рейтинг': '{:.1f}',
                                    'score': '{:.4f}'
                                }).set_properties(**{
                                    'text-align': 'left',
                                    'padding': '8px'
                                }).set_table_styles([
                                    {'selector': 'th',
                                     'props': [('background-color', '#f0f2f6'), ('font-weight', 'bold')]},
                                    {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#fafafa')]}
                                ]).background_gradient(subset=['score'], cmap='Blues'),
                                width='stretch'
                            )
                        elif response.status_code == 404:
                            st.error(f"Фильм '{title}' не найден.")
                        else:
                            st.error("Ошибка при получении рекомендаций.")
                    except Exception as e:
                        st.error(f"Ошибка подключения: {e}")

    elif menu == 'Рекомендации по пользователю':
        st.subheader("Персонализированные рекомендации")

        user_id_input = st.text_input("Введите ID пользователя (например: 1, 66666):")

        if user_id_input.strip():
            try:
                user_id = int(user_id_input.strip())
            except ValueError:
                st.warning("Введите корректный числовой ID пользователя.")
                user_id = None
        else:
            user_id = None

        if user_id and st.button("Показать оценки и рекомендации"):
            with st.spinner(f'Загрузка данных для пользователя {user_id}...'):
                try:
                    ratings_response = requests.get(f"{API_URL}/user/{user_id}", timeout=160)
                    if ratings_response.status_code == 200:
                        ratings_data = ratings_response.json()
                        df_ratings = pd.DataFrame(ratings_data["films"])
                        st.markdown("### 10 оценок пользователя")
                        st.dataframe(
                            df_ratings.style.format({
                                'Рейтинг': '{:.1f}'
                            }).set_properties(**{
                                'text-align': 'left',
                                'padding': '8px'
                            }),
                            width='stretch'
                        )
                    else:
                        st.error(f"Пользователь {user_id} не найден!!!")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            with st.spinner(f'Поиск рекомендаций для пользователя {user_id}...'):
                try:
                    recs_response = requests.post(f"{API_URL}/recommendations/user/{user_id}", timeout=60)
                    if recs_response.status_code == 200:
                        recs_data = recs_response.json()
                        films = recs_data["films"]

                        df_recs = pd.DataFrame(films)
                        st.markdown("### Рекомендованные фильмы для пользователя")
                        st.dataframe(
                            df_recs.style.set_properties(**{
                                'text-align': 'left',
                                'padding': '8px'
                            }).set_table_styles([
                                {'selector': 'th', 'props': [('background-color', '#f0f2f6'), ('font-weight', 'bold')]},
                                {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#fafafa')]}
                            ]),
                            width = 'stretch'
                        )
                    elif recs_response.status_code == 404:
                        st.error(f"Нет рекомендаций для пользователя {user_id}.")
                    else:
                        st.error("Ошибка при получении рекомендаций.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    elif menu == 'Рекомендации для нового пользователя':
        all_films = []
        with st.spinner("Загрузка списка фильмов..."):
            try:
                films_resp = requests.get(f"{API_URL}/all-movies", timeout=160)
                if films_resp.status_code == 200:
                    all_films = films_resp.json()["movies"]
            except Exception as e:
                st.error(f"Ошибка: {e}")
                return

        st.write("Выберите фильмы и поставьте оценки:")

        # Оценивание
        ratings_input = []
        for i in range(5):
            col1, col2 = st.columns([3, 1])
            film = col1.selectbox(f"Фильм {i + 1}", options=all_films, key=f"film_{i}")
            rating = col2.slider(f"Оценка", 1, 5, 1, key=f"rating_{i}")
            ratings_input.append({"Название": film, "Рейтинг": float(rating)})

        if st.button("Получить рекомендации"):
            seen = set()
            unique_ratings = []
            for r in ratings_input:
                if r["Название"] not in seen:
                    unique_ratings.append(r)
                    seen.add(r["Название"])

            with st.spinner("Генерация рекомендаций..."):
                try:
                    response = requests.post(
                        f"{API_URL}/recommendations/new-user",
                        json={"ratings": unique_ratings},
                        timeout=160
                    )
                    if response.status_code == 200:
                        data = response.json()
                        films = data["films"]
                        df = pd.DataFrame(films)
                        st.success("Ваши персональные рекомендации:")
                        st.dataframe(df, width='stretch')
                    else:
                        st.error(f"Ошибка: {response.json().get('detail', 'Неизвестная ошибка')}")
                except Exception as e:
                    st.error(f"Ошибка подключения: {e}")


if __name__ == "__main__":
    main()
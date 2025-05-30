import streamlit as st
import pickle
from rapidfuzz import process, fuzz
import pandas as pd
import re
import requests
import time
from typing import Optional

similarity = pickle.load(open('similarity.pkl', 'rb'))
movie_dict = pickle.load(open('movie_dict.pkl', 'rb'))
movies = pd.DataFrame(movie_dict)

TMDB_API_KEY = "f051c86bbadfc948e984e55fc71f009e"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w200"

st.title('Movies Paglu 🎬')
name = st.text_input("Search a Movie:")
poster_cache = {}

@st.cache_data(show_spinner=False)
def get_movie_poster_cached(movie_id: int) -> Optional[str]:
    if movie_id in poster_cache:
        return poster_cache[movie_id]

    for attempt in range(5):
        try:
            time.sleep(1.75)
            response = requests.get(
                f"{TMDB_BASE_URL}/movie/{movie_id}",
                params={"api_key": TMDB_API_KEY}
            )
            response.raise_for_status()
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                poster_url = TMDB_IMAGE_BASE_URL + poster_path
                poster_cache[movie_id] = poster_url
                return poster_url
            else:
                poster_cache[movie_id] = None
                return None
        except requests.RequestException:
            if attempt == 2:
                poster_cache[movie_id] = None
                return None
            time.sleep(2 ** attempt)

    poster_cache[movie_id] = None
    return None


def clean_title(title):
    title = title.lower()
    title = re.sub(r'[^a-z0-9]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

movies['clean_title'] = movies['title'].astype(str).apply(clean_title).fillna('')

def recommend(movie):
    cleaned = clean_title(movie)

    clean_titles_list = movies['clean_title'].tolist()
    match = process.extractOne(cleaned, clean_titles_list, scorer=fuzz.token_sort_ratio)  # type: ignore

    if match and match[1] >= 70:
        matched_title = match[0]
        matched_index = movies[movies['clean_title'] == matched_title].index[0]

        original_title = movies.loc[matched_index, 'title']
        original_id = movies.loc[matched_index, 'movie_id']

        distances = similarity[matched_index]
        movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[
                     1:5]

        st.subheader(f"🎥 Recommending movies based on your search '{original_title}':")

        cols = st.columns(5)

        with cols[0]:
            poster_url = get_movie_poster_cached(original_id)
            if poster_url:
                st.image(poster_url, use_container_width=True)
                st.caption(original_title)
            else:
                st.text(original_title)
                st.text("No poster available")

        for idx, i in enumerate(movie_list):
            index = i[0]
            title = movies.iloc[index]['title']
            movie_id = movies.iloc[index]['movie_id']

            poster_url = get_movie_poster_cached(movie_id)

            with cols[idx + 1]:
                if poster_url:
                    st.image(poster_url, use_container_width=True)
                    st.caption(title)
                else:
                    st.text(title)
                    st.text("No poster available")
        st.success("Top 5 Results Based On Your Search!")
    else:
        st.warning("No similar movies found!")


if st.button('Search'):
    if name.strip() != "":
        recommend(name)

    else:
        st.warning("Please enter a movie title!")
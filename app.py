import streamlit as st
import main as backend

# Page Configuration
st.set_page_config(
    page_title="MOODFLIX",
    page_icon="💥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark/Modern Theme & Cards
st.markdown("""
<style>
    /* Dark Theme enhancements */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Card Style for Recommendations */
    .movie-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #41424C;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        animation: fadeIn 0.6s ease-out both;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .movie-card:hover {
        transform: scale(1.05);
        border-color: #E50914;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
    }
    .movie-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #E50914;
        margin-bottom: 5px;
    }
    .movie-meta {
        font-size: 0.9rem;
        color: #A3A8B8;
        margin-bottom: 10px;
    }
    .movie-reason {
        font-size: 0.95rem;
        color: #E0E0E0;
        font-style: italic;
        border-left: 3px solid #E50914;
        padding-left: 10px;
    }
    /* Brand Title Styling */
    .brand-title {
        font-size: 4rem;
        font-weight: 900;
        color: #E50914; /* Netflix Red */
        letter-spacing: -2px;
        margin-bottom: -10px;
        text-transform: uppercase;
        font-family: 'Arial Black', sans-serif;
        text-shadow: 0 0 20px rgba(229, 9, 20, 0.3);
    }
    .brand-subtitle {
        color: #A3A8B8;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }

    /* Custom Button Styling */
    div.stButton > button {
        background-color: #E50914 !important;
        color: white !important;
        border-radius: 5px !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        padding: 0.6rem !important;
        transition: 0.3s !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    div.stButton > button:hover {
        background-color: #ff0f1e !important;
        box-shadow: 0 0 15px rgba(229, 9, 20, 0.6) !important;
        transform: translateY(-2px) !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="Grabbing popcorn-worthy picks🍿")
def get_recommender():
    """
    Load data and initialize recommender only once.
    """
    movies = backend.load_movies_from_csv(backend.CSV_FILE)
    if not movies:
        return None
    return backend.MovieRecommender(movies)

def main():
    # 1. Initialize Session State
    if "liked_movies" not in st.session_state:
        st.session_state["liked_movies"] = []
    if "results" not in st.session_state:
        st.session_state["results"] = []
    if "current_mood" not in st.session_state:
        st.session_state["current_mood"] = ""
    if "discovery_queue" not in st.session_state:
        st.session_state["discovery_queue"] = []
    if "search_active" not in st.session_state:
        st.session_state["search_active"] = False

    # 2. Load Recommender
    recommender = get_recommender()
    if not recommender:
        st.error("Failed to load movie database.")
        return

    # 3. Sidebar Configuration
    with st.sidebar:
        st.title("Movie Preferences")
        
        selected_mood = st.selectbox(
            "What are you in the mood for?",
            options=["Happy", "Sad", "Excited", "Relaxed"],
            index=0
        )
        
    

        st.divider()
        st.markdown("### Your Watch Mode")
        time, day = recommender.get_time_context()
        watch_mode = "Night Binge 🌙" if time.lower() == "night" else "Casual Watch ☀️"
        watch_mood = "Relaxed 🍿" if day.lower() in ["saturday", "sunday"] else "Quick Watch 🎯"

        with st.container(border=True):
            st.caption("Snapshot")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Vibe**\n\n{watch_mood}")
            c2.markdown(f"**Style**\n\n{watch_mode}")
        
        if st.session_state["liked_movies"]:
            st.divider()
            if st.button("🗑️ Clear My Library"):
                st.session_state["liked_movies"] = []
                st.session_state["results"] = []
                st.session_state["discovery_queue"] = []
                st.session_state["search_active"] = False
                st.rerun()

    # 4. Brand Header
    st.markdown('<div class="brand-title">MoodFlix🤙🏻</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-subtitle">Your mood. Your movies.</div>', unsafe_allow_html=True)
    
    # 5. Trending Now (Home View)
    if not st.session_state["search_active"]:
        st.markdown("### 🔥 Trending Now")
        # SOURCE FROM TOP 500 TO ALLOW FOR DRAMATIC SHIFTS
        global_trending = sorted(recommender.movies, key=lambda x: x.get('rating', 0), reverse=True)[:500]
        
        if st.session_state["liked_movies"]:
            liked_objs = [m for m in recommender.movies if m['title'] in st.session_state["liked_movies"]]
            trending_pool = []
            for m in global_trending:
                sim = sum(recommender.calculate_similarity(m, l) for l in liked_objs) / len(liked_objs)
                trending_pool.append({"movie": m, "score": m.get('rating', 0) + (sim * 5)})
            trending_pool.sort(key=lambda x: x['score'], reverse=True)
            display_trending = [x['movie'] for x in trending_pool[:3]]
        else:
            display_trending = global_trending[:3]
        
        cols_t = st.columns(3)
        for i, movie in enumerate(display_trending):
            with cols_t[i]:
                st.markdown(f"""
                <div class="movie-card" style="border-top: 3px solid #E50914;">
                    <div class="movie-title">{movie['title']}</div>
                    <div class="movie-meta">⏱️ {movie['duration']}m | ⭐ {movie.get('rating','N/A')}<br>🎭 {', '.join(movie['genres'][:2])}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"❤️ Like", key=f"trend_{movie['title']}"):
                    if movie['title'] not in st.session_state["liked_movies"]:
                        st.session_state["liked_movies"].append(movie['title'])
                        st.toast(f"Added to Library! 🍿")
                        st.rerun()

        # 6. Dashboard Row 2: ✨ For You (Personalized)
        if st.session_state["liked_movies"]:
            st.write("---")
            st.markdown("### ✨ For You")
            personal_recs = recommender.get_similar_movies(st.session_state["liked_movies"], limit=3)
            if personal_recs:
                cols_p = st.columns(3)
                for i, rec in enumerate(personal_recs):
                    m = rec['movie']
                    with cols_p[i]:
                        st.markdown(f"""
                        <div class="movie-card" style="border-top: 3px solid #2ECC71;">
                            <div class="movie-title">{m['title']}</div>
                            <div class="movie-meta">⏱️ {m['duration']}m | ⭐ {m.get('rating','N/A')}<br>🎭 {', '.join(m['genres'][:2])}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"❤️ Like", key=f"foryou_{m['title']}"):
                            if m['title'] not in st.session_state["liked_movies"]:
                                st.session_state["liked_movies"].append(m['title'])
                                st.toast(f"Added to Library! 🍿")
                                st.rerun()

        # 7. Dashboard Row 3: 🎬 Search & Results Trigger
        st.write("---")
        st.markdown("### 🎬 Lights, Camera, Watch!")
        if st.button("Get Recommendations 🚀", type="primary"):
            st.session_state["search_active"] = True
            st.session_state["current_mood"] = selected_mood
            st.session_state["discovery_queue"] = [] # Clear queue for new search
            with st.spinner("Finding perfect matches..."):
                st.session_state["results"] = recommender.recommend(selected_mood, st.session_state["liked_movies"])
            st.rerun()

    # --- Results View ---
    if st.session_state["search_active"]:
        st.write("---")
        st.markdown(f"### 🎬 Lights, Camera, Watch! ({st.session_state['current_mood']})")
        
        # --- INSTANT DISCOVERY (More Like Your Recent Likes) ---
        if st.session_state["discovery_queue"]:
            st.markdown("#### ✨ Instant Discoveries (Because you liked that!)")
            cols_d = st.columns(3)
            for i, movie in enumerate(st.session_state["discovery_queue"][:3]):
                with cols_d[i]:
                    st.markdown(f"""
                    <div class="movie-card" style="border-top: 3px solid #E50914;">
                        <div class="movie-title">{movie['title']}</div>
                        <div class="movie-meta">⏱️ {movie['duration']}m | ⭐ {movie.get('rating','N/A')}<br>🎭 {', '.join(movie['genres'][:2])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"❤️ Like", key=f"discovery_{movie['title']}"):
                        if movie['title'] not in st.session_state["liked_movies"]:
                            st.session_state["liked_movies"].append(movie['title'])
                            st.toast(f"Added to Library! 🍿")
                            # Recurse discovery!
                            new_sims = recommender.get_similar_movies([movie['title']], limit=3)
                            for ns in new_sims:
                                if ns['movie']['title'] not in [m['title'] for m in st.session_state["discovery_queue"]]:
                                    st.session_state["discovery_queue"].insert(0, ns['movie'])
                            st.rerun()
            st.write("---")

        if st.button("⬅️ Back to Home"):
            st.session_state["search_active"] = False
            st.rerun()

        selected_mood = st.session_state["current_mood"]
        top_movies = st.session_state["results"]

        if st.session_state["results"]:
            st.caption(f"Showing results for **{st.session_state['current_mood']}** mood")
            cols_r = st.columns(3)
            for i, item in enumerate(st.session_state["results"]):
                movie = item["movie"]
                reasons = item["reasons"]
                with cols_r[i % 3]:
                    st.markdown(f"""
                    <div class="movie-card">
                        <div class="movie-title">{movie['title']}</div>
                        <div class="movie-meta">⏱️ {movie['duration']}m | ⭐ {movie.get('rating','N/A')}<br>🎭 {', '.join(movie['genres'][:3])}</div>
                        <div class="movie-reason">"{" ".join(reasons)}"</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"❤️ Like", key=f"res_{movie['title']}"):
                        if movie['title'] not in st.session_state["liked_movies"]:
                            st.session_state["liked_movies"].append(movie['title'])
                            st.toast(f"Saved to Library! 🍿")
                            # EXTRACT PROPERTIES INSTANTLY
                            new_sims = recommender.get_similar_movies([movie['title']], limit=3)
                            for ns in new_sims:
                                 if ns['movie']['title'] not in [m['title'] for m in st.session_state["discovery_queue"]]:
                                    st.session_state["discovery_queue"].insert(0, ns['movie'])
                            
                            # Update results in background to reflect boost
                            st.session_state["results"] = recommender.recommend(st.session_state["current_mood"], st.session_state["liked_movies"])
                            st.rerun()

if __name__ == "__main__":
    main()

import datetime
import os
import csv
import ast
import sys

# Configuration: Prefer mini dataset for fast deployment
CSV_FILE = "movies_mini.csv" if os.path.exists("movies_mini.csv") else "TMDB_movie_dataset_v11.csv"
# Increase field size limit for large CSV fields
# On Windows, sys.maxsize can exceed C long limit, so we use a safe 32-bit int
csv.field_size_limit(10**8)

def load_movies_from_csv(filepath):
    """
    Loads movies from the TMDB CSV file using standard libraries.
    Parses 'genres' and 'keywords' from stringified JSON-like format.
    Filters strictly for quality to save memory.
    """


    movies = []
    count = 0
    
    try:
        with open(filepath, mode='r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # 1. Basic Checks (Filter early for speed)
                    if not row['title'] or not row['genres'] or not row['runtime']:
                        continue
                        
                    vote_count = int(float(row['vote_count'])) if row['vote_count'] else 0
                    if vote_count < 150: # Strict filter to reduce dataset size
                        continue

                    # 2. Parse Genres
                    raw_genres = row['genres']
                    genres = []
                    if raw_genres.startswith('['):
                        # Safe eval for JSON-like strings
                        try:
                            genres = [g['name'] for g in ast.literal_eval(raw_genres)]
                        except:
                            pass
                    else:
                        genres = [g.strip() for g in raw_genres.split(',') if g.strip()]
                    
                    if not genres:
                        continue

                    # 3. Parse Keywords
                    raw_keywords = row['keywords']
                    keywords = []
                    if raw_keywords and raw_keywords.startswith('['):
                        try:
                            keywords = [k['name'] for k in ast.literal_eval(raw_keywords)]
                        except:
                            pass
                    
                    # 4. Check Duration
                    try:
                        duration = int(float(row['runtime']))
                    except ValueError:
                        continue
                        
                    movies.append({
                        "title": row['title'],
                        "genres": genres,
                        "duration": duration,
                        "keywords": keywords,
                        "rating": float(row['vote_average']) if row['vote_average'] else 0.0
                    })
                    
                    count += 1
                    if count % 5000 == 0:
                        print(f"Loaded {count} popular movies...")

                except (ValueError, SyntaxError) as e:
                    continue # Skip malformed rows
                
        print(f"Successfully loaded {len(movies)} high-quality movies.")
        return movies

    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return []
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []

class MovieRecommender:
    def __init__(self, movie_database):
        self.movies = movie_database
        
        # Mood to Genre/Keyword Mapping Rules
        # We expanded the knowledge base slightly for better matches with real data
        self.mood_rules = {
            "Happy": {
                "genres": ["Comedy", "Animation", "Family", "Music", "Adventure"],
                "keywords": ["funny", "friends", "holiday", "magic", "musical", "feel good", "optimism"],
                "mood_description": "uplifting and fun content"
            },
            "Sad": {
                "genres": ["Drama", "Romance", "History", "War"],
                "keywords": ["melancholy", "tragedy", "loss", "emotional", "biography", "tearjurker"],
                "mood_description": "stories that resonate with deep emotions"
            },
            "Excited": {
                "genres": ["Action", "Science Fiction", "Thriller", "Horror", "Crime"],
                "keywords": ["chase", "spy", "suspense", "superhero", "explosion", "fight", "survival"],
                "mood_description": "thrilling and high-energy movies"
            },
            "Relaxed": {
                "genres": ["Documentary", "Fantasy", "Romance"],
                "keywords": ["nature", "calm", "philosophical", "slow", "beautiful", "journey"],
                "mood_description": "calm and easy-going viewing"
            }
        }

    def get_time_context(self):
        """
        Determines the current time context (Morning, Afternoon, Evening, Night)
        and Day type (Weekday, Weekend).
        """
        now = datetime.datetime.now()
        hour = now.hour
        weekday = now.weekday() # 0=Mon, 6=Sun

        # Time of day logic
        if 5 <= hour < 12:
            time_of_day = "Morning"
        elif 12 <= hour < 17:
            time_of_day = "Afternoon"
        elif 17 <= hour < 22:
            time_of_day = "Evening"
        else:
            time_of_day = "Night"

        # Day type logic
        is_weekend = weekday >= 5
        day_type = "Weekend" if is_weekend else "Weekday"

        return time_of_day, day_type

    def filter_by_mood(self, mood):
        """
        Filters and scores movies based on the user's selected mood.
        Returns a list of tuples: (movie, score, reason_list)
        """
        if mood not in self.mood_rules:
            return []

        rules = self.mood_rules[mood]
        preferred_genres = rules["genres"]
        preferred_keywords = rules["keywords"]
        
        scored_movies = []

        for movie in self.movies:
            score = 0
            reasons = []
            
            # Optimization: Quick genre check first
            movie_genres_set = set(movie["genres"])
            common_genres = movie_genres_set.intersection(set(preferred_genres))
            
            if not common_genres:
                continue # Skip movies that don't match the mood genres at all

            score += len(common_genres) * 3  # High weight for Genre match
            reasons.append(f"Matches your {mood} mood (Genres: {', '.join(list(common_genres)[:3])})") # Limit text length

            # Keywords Match
            movie_keywords_set = set(movie["keywords"])
            common_keywords = movie_keywords_set.intersection(set(preferred_keywords))
            if common_keywords:
                score += len(common_keywords) * 2
                reasons.append(f"Fits the vibe (Tags: {', '.join(list(common_keywords)[:3])})")

            # Rating Boost (Real data has quality variance)
            if movie["rating"] > 7.5:
                score += 1
            if movie["rating"] > 8.5:
                score += 1 # Bonus for masterpieces

            scored_movies.append({
                "movie": movie,
                "base_score": score,
                "reasons": reasons
            })
        
        return scored_movies

    def apply_context_rules(self, scored_movies, time_of_day, day_type):
        """
        Adjusts scores based on context (Time and Day).
        """
        # We iterate and modify scores.
        # To avoid performance issues on large datasets, we only process the top 200 candidates
        # from the mood filter step.
        scored_movies.sort(key=lambda x: x["base_score"], reverse=True)
        top_candidates = scored_movies[:200]

        for item in top_candidates:
            movie = item["movie"]
            duration = movie["duration"]
            
            # Context Rule 1: Time of Day
            if time_of_day == "Morning":
                # Prefer shorter, lighter movies
                if duration < 110:
                    item["base_score"] += 2
                    item["reasons"].append("Perfect duration for a morning watch")
                if "Horror" in movie["genres"] or "Thriller" in movie["genres"]:
                    item["base_score"] -= 5 # Strongly discourage horror in the morning
            
            elif time_of_day == "Night":
                 # Prefer longer, immersive movies
                if duration > 120:
                    item["base_score"] += 1
                    item["reasons"].append("Immersive runtime for tonight")
            
            # Context Rule 2: Day Type
            if day_type == "Weekday":
                if duration > 160:
                    item["base_score"] -= 3
                    item["reasons"].append("A bit long for a work night")
            elif day_type == "Weekend":
                 item["base_score"] += 0.5 

        return top_candidates

    def calculate_similarity(self, movie1, movie2):
        """
        Calculates Jaccard similarity between two movies based on Genres and Keywords.
        """
        set1 = set(movie1['genres'] + movie1['keywords'])
        set2 = set(movie2['genres'] + movie2['keywords'])
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0

    def get_similar_movies(self, liked_movie_titles, limit=6):
        """
        Suggests movies similar to a list of liked movies (History).
        """
        if not liked_movie_titles:
            return []
            
        # 1. Find the movie objects for the liked titles
        liked_movies = [m for m in self.movies if m['title'] in liked_movie_titles]
        if not liked_movies:
            return []
            
        # 2. Score all other movies based on similarity to the liked ones
        scored_recommendations = []
        for movie in self.movies:
            if movie['title'] in liked_movie_titles:
                continue # Don't recommend what they already liked
                
            # Average similarity score across all liked movies
            total_sim = sum(self.calculate_similarity(movie, liked) for liked in liked_movies)
            avg_sim = total_sim / len(liked_movies)
            
            if avg_sim > 0.05: # Threshold to filter low-quality matches
                scored_recommendations.append({"movie": movie, "sim_score": avg_sim})
        
        # 3. Sort by highest similarity
        scored_recommendations.sort(key=lambda x: x['sim_score'], reverse=True)
        return scored_recommendations[:limit]

    def recommend(self, mood, liked_movies=None):
        """
        Hyper-personalised recommendation logic.
        Combines Mood filtering + Context rules + User History similarity (Hybrid).
        """
        # 1. Get Context
        time_of_day, day_type = self.get_time_context()
        print(f"\n[System Context] It is a {day_type} {time_of_day}.")

        # 2. Filter by Mood
        candidates = self.filter_by_mood(mood)
        if not candidates:
            return []

        # 3. Apply Context Rules
        final_candidates = self.apply_context_rules(candidates, time_of_day, day_type)

        # 4. PERSONALIZATION BOOST (Hybrid Collaborative/Content Component)
        if liked_movies:
            liked_movie_objects = [m for m in self.movies if m['title'] in liked_movies]
            for item in final_candidates:
                movie = item["movie"]
                # Calculate similarity to history
                if liked_movie_objects:
                    sim_boost = sum(self.calculate_similarity(movie, liked) for liked in liked_movie_objects)
                    sim_boost /= len(liked_movie_objects)
                    # Apply substantial boost if similar to history
                    item["base_score"] += (sim_boost * 15)
                    if sim_boost > 0.1:
                        item["reasons"].append(f"Similar to your liked movies (+{int(sim_boost*100)}% match)")

        # 5. Final Sort
        final_candidates.sort(key=lambda x: x["base_score"], reverse=True)
        return final_candidates[:12] # Return top 12

def main():
    print("Initializing System...")
    movies = load_movies_from_csv(CSV_FILE)
    
    if not movies:
        print("Failed to load movie data. Exiting.")
        return

    recommender = MovieRecommender(movies)

    print("\n--- Personalised Movie Recommender (Powered by Real Data) ---")
    print("Available Moods: Happy, Sad, Excited, Relaxed")
    
    # Cold-Start Handling: explicit query
    user_mood = input("How are you feeling right now? ").capitalize()

    if user_mood not in recommender.mood_rules:
        print("Sorry, I don't understand that mood yet. Try: Happy, Sad, Excited, Relaxed.")
        return

    print("Analyzing thousands of movies for you...")
    recommendations = recommender.recommend(user_mood)

    print(f"\nHere are the top recommendations for a '{user_mood}' mood:\n")
    
    for i, item in enumerate(recommendations, 1):
        movie = item["movie"]
        print(f"{i}. {movie['title']} ({movie['duration']} min) [Rating: {movie['rating']}]")
        print(f"   Genres: {', '.join(movie['genres'][:4])}") # Limit genre display
        print(f"   Why? {'; '.join(item['reasons'])}")
        print("-" * 50)

if __name__ == "__main__":
    main()

import csv
import ast
import os

# Configuration
SOURCE_CSV = "TMDB_movie_dataset_v11.csv"
OUTPUT_CSV = "movies_mini.csv"

def distill_data():
    print(f"Reading {SOURCE_CSV}...")
    if not os.path.exists(SOURCE_CSV):
        print(f"Error: {SOURCE_CSV} not found in the current directory.")
        return

    count = 0
    exported = 0
    
    # Increase field size limit for large CSV fields
    import sys
    csv.field_size_limit(10**7)

    with open(SOURCE_CSV, mode='r', encoding='utf-8', errors='replace') as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = ['title', 'genres', 'runtime', 'keywords', 'vote_average', 'vote_count']
        
        with open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                count += 1
                try:
                    # Filter: Only movies with significant votes (quality threshold)
                    # We use a threshold of 150 to keep the most popular ~15k movies
                    vc = int(float(row['vote_count'])) if row['vote_count'] else 0
                    if vc < 150:
                        continue
                        
                    # Filter: Must have title and genres
                    if not row['title'] or not row['genres']:
                        continue
                        
                    # Prepare row for output
                    writer.writerow({
                        'title': row['title'],
                        'genres': row['genres'],
                        'runtime': row['runtime'],
                        'keywords': row['keywords'],
                        'vote_average': row['vote_average'],
                        'vote_count': row['vote_count']
                    })
                    exported += 1
                    
                except:
                    continue
                
                if count % 50000 == 0:
                    print(f"Processed {count} rows...")

    print(f"Finished! Exported {exported} high-quality movies to {OUTPUT_CSV}.")
    print(f"Full dataset size reduction: {os.path.getsize(SOURCE_CSV)/1024/1024:.1f}MB -> {os.path.getsize(OUTPUT_CSV)/1024/1024:.1f}MB")

if __name__ == "__main__":
    distill_data()

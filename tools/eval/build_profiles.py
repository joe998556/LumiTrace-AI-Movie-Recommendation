#!/usr/bin/env python3
"""Generate curated recommendation test profiles from the vector index."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('final_boss_vectors.json', 'r', encoding='utf-8') as f:
    movies = json.load(f)

by_id = {m['id']: m for m in movies if isinstance(m, dict)}
by_title = {}
for m in movies:
    if isinstance(m, dict):
        by_title[m.get('title', '').lower()] = m

def find_by_title(title):
    """Find a movie by approximate title match."""
    t = title.lower()
    if t in by_title:
        return by_title[t]
    for m in movies:
        if isinstance(m, dict) and t in m.get('title', '').lower():
            return m
    return None

def get_ids(titles):
    """Get TMDB IDs for a list of titles, skipping missing."""
    ids = []
    for t in titles:
        m = find_by_title(t)
        if m:
            ids.append(m['id'])
        else:
            print(f"  WARNING: not found in index: {t}")
    return ids

def make_profile(name, desc, titles, fav_genres, fav_langs, avoid_genres=None, overviews=None):
    ids = get_ids(titles)
    user_genre_ids = [by_id[mid].get('genre_ids', []) for mid in ids if mid in by_id]
    fav_years = [int(str(by_id[mid].get('release_date', ''))[:4]) for mid in ids if mid in by_id and by_id[mid].get('release_date')]
    return {
        'name': name,
        'description': desc,
        'overviews': overviews or [desc],
        'collected_movie_ids': ids,
        'favorite_genres': fav_genres,
        'favorite_languages': fav_langs,
        'user_genre_ids': user_genre_ids,
        'favorite_years': fav_years,
        'avoid_genres': avoid_genres or [],
        'expected_directions': [],
        'unexpected_directions': [],
    }

profiles = [
    make_profile('Sci-Fi Lover',
        'High-concept philosophical sci-fi',
        ['Blade Runner 2049', 'Arrival', 'Interstellar', 'Ex Machina', 'Her', 'Annihilation'],
        [878], ['en']),
    make_profile('Hard Sci-Fi Space',
        'Realistic space exploration sci-fi',
        ['2001: A Space Odyssey', 'Gravity', 'The Martian', 'Ad Astra', 'Moon', 'Interstellar'],
        [878, 12], ['en']),
    make_profile('AI Movies',
        'Films about artificial intelligence',
        ['Ex Machina', 'Her', 'The Matrix', 'I, Robot', 'A.I. Artificial Intelligence', 'Blade Runner'],
        [878], ['en']),
    make_profile('Crime Lover',
        'Classic crime and heist films',
        ['Pulp Fiction', 'Heat', 'The Departed', 'Goodfellas', 'Scarface', 'Reservoir Dogs'],
        [80], ['en']),
    make_profile('Gangster Films',
        'Italian-American mafia epics',
        ['The Godfather', 'The Godfather Part II', 'Casino', 'Goodfellas', 'Scarface', 'Carlitos Way'],
        [80, 18], ['en']),
    make_profile('Thriller Fan',
        'Suspenseful twisty thrillers',
        ['Se7en', 'Zodiac', 'The Usual Suspects', 'Primal Fear', 'The Game', 'Gone Girl'],
        [53], ['en']),
    make_profile('Psychological Thriller',
        'Mind-bending psychological films',
        ['Black Swan', 'Shutter Island', 'Memento', 'Fight Club', 'Mulholland Drive', 'The Machinist'],
        [53, 9648], ['en']),
    make_profile('Horror Fan',
        'Supernatural and atmospheric horror',
        ['The Conjuring', 'Hereditary', 'The Ring', 'Insidious', 'It Follows', 'The Babadook'],
        [27], ['en']),
    make_profile('Japanese Korean Cinema',
        'Japanese and Korean masterpieces',
        ['Oldboy', 'Parasite', 'Memories of Murder', 'Audition', 'Battle Royale', 'I Saw the Devil'],
        [18, 53], ['ja', 'ko']),
    make_profile('European Art House',
        'European auteur cinema',
        ['Amelie', 'The Lives of Others', 'Pans Labyrinth', 'Caché', 'Force Majeure', 'The Handmaiden'],
        [18], ['fr', 'de', 'es', 'it']),
    make_profile('Indie Film',
        'American independent cinema',
        ['Moonlight', 'Lady Bird', 'The Florida Project', 'Eighth Grade', 'Short Term 12', 'Beasts of the Southern Wild'],
        [18], ['en']),
    make_profile('Drama Lover',
        'Character-driven dramatic masterpieces',
        ['Forrest Gump', 'The Shawshank Redemption', 'Schindlers List', '12 Angry Men', 'The Green Mile', 'A Beautiful Mind'],
        [18], ['en']),
    make_profile('Romance Fan',
        'Classic and modern love stories',
        ['The Notebook', 'Before Sunrise', 'Casablanca', 'Eternal Sunshine of the Spotless Mind', 'La La Land', 'Pride and Prejudice'],
        [10749], ['en']),
    make_profile('Animation Fan',
        'Animated films for all ages',
        ['Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke', 'Akira', 'WALL-E', 'Inside Out'],
        [16], ['en', 'ja']),
    make_profile('Japanese Animation',
        'Studio Ghibli and anime classics',
        ['Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke', 'Howls Moving Castle', 'Grave of the Fireflies', 'Your Name.'],
        [16], ['ja']),
    make_profile('Superhero Fan',
        'Superhero and comic book films',
        ['The Dark Knight', 'Iron Man', 'Spider-Man 2', 'Logan', 'Avengers: Endgame', 'Batman Begins'],
        [28, 878], ['en']),
    make_profile('War Films',
        'War and military films',
        ['Saving Private Ryan', 'Apocalypse Now', 'Full Metal Jacket', '1917', 'Dunkirk', 'Hacksaw Ridge'],
        [10752], ['en']),
    make_profile('Historical Epic',
        'Historical and period epics',
        ['Gladiator', 'Braveheart', 'Kingdom of Heaven', 'Troy', '300', 'King Arthur'],
        [36, 12], ['en']),
    make_profile('Comedy Fan',
        'Mainstream comedies',
        ['Superbad', 'The Hangover', 'Bridesmaids', 'Step Brothers', 'Anchorman', 'Knocked Up'],
        [35], ['en']),
    make_profile('Dark Humor',
        'Black comedy and dark satire',
        ['In Bruges', 'Fargo', 'The Big Lebowski', 'Burn After Reading', 'Three Billboards Outside Ebbing Missouri', 'Dr. Strangelove'],
        [35, 80], ['en']),
    make_profile('Cult Film Fan',
        'Cult and midnight movies',
        ['Donnie Darko', 'The Rocky Horror Picture Show', 'Fight Club', 'A Clockwork Orange', 'The Big Lebowski', 'Pulp Fiction'],
        [27, 878, 14], ['en']),
    make_profile('A24 Arthouse',
        'Modern A24-style arthouse',
        ['Everything Everywhere All at Once', 'The Lighthouse', 'Midsommar', 'Uncut Gems', 'The Witch', 'Hereditary'],
        [18, 27, 53], ['en']),
    make_profile('Oscar Favorites',
        'Academy Award winners and nominees',
        ['Nomadland', 'Birdman', 'Spotlight', 'The Shape of Water', 'CODA', 'Green Book'],
        [18, 36], ['en']),
    make_profile('Classic Cinema',
        'Pre-1980 cinema masterpieces',
        ['Citizen Kane', 'Casablanca', 'Vertigo', 'Lawrence of Arabia', 'The Third Man', 'Sunset Boulevard'],
        [18, 35], ['en']),
    make_profile('B-Movie Fan',
        'Low-budget genre fun',
        ['The Room', 'Troll 2', 'The Toxic Avenger', 'Plan 9 from Outer Space', 'Sharknado', 'Killer Klowns from Outer Space'],
        [27, 878], ['en']),
    make_profile('Taiwan Cinema',
        'Taiwanese cinema',
        ['A Sun', 'Your Name Engraved Herein', 'Detention', 'The Terrorizers', 'Monga', 'Cape No. 7'],
        [18], ['zh']),
    make_profile('Hong Kong Cinema',
        'Hong Kong action and drama',
        ['Infernal Affairs', 'Chungking Express', 'Kung Fu Hustle', 'Election', 'PTU', 'Hard Boiled'],
        [28, 80, 18], ['zh']),
    make_profile('Chinese Cinema',
        'Mainland Chinese cinema',
        ['Farewell My Concubine', 'Raise the Red Lantern', 'Hero', 'House of Flying Daggers', 'The Mermaid', 'Coming Home'],
        [18, 14, 28], ['zh']),
    make_profile('Mixed Sci-Fi Crime',
        'Sci-fi noir and cyberpunk crime',
        ['Blade Runner', 'Minority Report', 'The Matrix', 'Dark City', 'Ghost in the Shell', 'Total Recall'],
        [878, 80, 53], ['en']),
    make_profile('Villeneuve Fan',
        'Denis Villeneuve filmography',
        ['Arrival', 'Blade Runner 2049', 'Sicario', 'Prisoners', 'Dune', 'Enemy'],
        [878, 53, 18], ['en']),
]

for p in profiles:
    n = len(p['collected_movie_ids'])
    titles = [by_id[mid].get('title', '?') for mid in p['collected_movie_ids'] if mid in by_id]
    print(f'{p["name"]:25s} ({n} movies): {", ".join(titles[:3])}...')

with open('tools/eval/recommendation_profiles.json', 'w', encoding='utf-8') as f:
    json.dump(profiles, f, ensure_ascii=False, indent=2)
print(f'\nWrote {len(profiles)} profiles')

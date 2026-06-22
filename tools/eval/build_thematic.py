#!/usr/bin/env python3
"""Build thematic sets from vector index with correct profile names."""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('final_boss_vectors.json', 'r', encoding='utf-8') as f:
    movies = json.load(f)
with open('tools/eval/recommendation_profiles.json', 'r', encoding='utf-8') as f:
    profiles = json.load(f)

by_title = {}
import re
def normalize(title):
    return re.sub(r'[^a-z0-9]', '', title.lower())

by_title = {}
by_title_norm = {}
for m in movies:
    if isinstance(m, dict):
        by_title[m.get('title', '').lower()] = m
        by_title_norm[normalize(m.get('title', ''))] = m

def find_ids(titles):
    ids = []
    for t in titles:
        m = by_title.get(t.lower())
        if not m:
            m = by_title_norm.get(normalize(t))
        if m:
            ids.append(m['id'])
    return ids

THEMATIC = {
    'Sci-Fi Lover': ['Interstellar', 'Arrival', 'Ex Machina', 'Her', 'Blade Runner 2049', 'Annihilation', 'Moon', 'The Martian', 'Gattaca', 'Primer', 'Under the Skin', 'Solaris', 'Contact', 'The Man from Earth', 'Eternal Sunshine of the Spotless Mind', 'Mr. Nobody', 'I Origins', 'Coherence', 'Predestination', 'Midnight Special'],
    'Hard Sci-Fi Space Explorer': ['2001: A Space Odyssey', 'Gravity', 'The Martian', 'Ad Astra', 'Moon', 'Interstellar', 'Solaris', 'The Right Stuff', 'Apollo 13', 'Europa Report', 'Alien', 'Sunshine', 'Passengers', 'Life', 'Prospect', 'High Life'],
    'AI Movie Enthusiast': ['Ex Machina', 'Her', 'The Matrix', 'Blade Runner', 'Blade Runner 2049', 'A.I. Artificial Intelligence', 'I Robot', 'Transcendence', 'Chappie', 'The Machine', 'Archive', 'Tau', 'Morgan', 'Ghost in the Shell'],
    'Crime Film Connoisseur': ['Pulp Fiction', 'Heat', 'The Departed', 'Goodfellas', 'Scarface', 'Reservoir Dogs', 'City of God', 'A Prophet', 'Sicario', 'No Country for Old Men', 'Hell or High Water', 'Wind River', 'Collateral', 'Training Day'],
    'Gangster Film Devotee': ['The Godfather', 'The Godfather Part II', 'Casino', 'Goodfellas', 'Scarface', 'American Gangster', 'Donnie Brasco', 'A Bronx Tale', 'Once Upon a Time in America', 'The Untouchables', 'Road to Perdition', 'Public Enemies', 'Black Mass'],
    'Thriller Seeker': ['Se7en', 'Zodiac', 'The Usual Suspects', 'Primal Fear', 'The Game', 'Gone Girl', 'Shutter Island', 'The Silence of the Lambs', 'No Country for Old Men', 'Nightcrawler', 'Prisoners', 'Mystic River', 'L.A. Confidential', 'Chinatown'],
    'Psychological Thriller Fan': ['Black Swan', 'Shutter Island', 'Memento', 'Fight Club', 'Mulholland Drive', 'The Machinist', 'Donnie Darko', 'Eternal Sunshine of the Spotless Mind', 'Being John Malkovich', 'The Truman Show', 'A Beautiful Mind', 'Pi', 'Lost Highway'],
    'Horror Aficionado': ['The Conjuring', 'Hereditary', 'The Ring', 'Insidious', 'It Follows', 'The Babadook', 'The Witch', 'Get Out', 'Us', 'Midsommar', 'The Exorcist', 'The Shining', 'Psycho', 'Suspiria', 'The Orphanage', 'Let the Right One In'],
    'Asian Cinema Explorer': ['Oldboy', 'Parasite', 'Memories of Murder', 'Audition', 'Battle Royale', 'I Saw the Devil', 'The Handmaiden', 'Sympathy for Mr. Vengeance', 'Lady Vengeance', 'Thirst', 'Joint Security Area', 'Mother', 'The Host', 'Burning', 'Shoplifters', 'Rashomon', 'Seven Samurai', 'Cure'],
    'European Art House Cinephile': ['The Lives of Others', 'Force Majeure', 'The Handmaiden', 'Amour', 'The Great Beauty', 'The Hunt', 'Ida', 'Son of Saul', 'Toni Erdmann', 'Victoria', 'Persona', 'Wild Strawberries'],
    'Indie Film Enthusiast': ['Moonlight', 'Lady Bird', 'The Florida Project', 'Eighth Grade', 'Short Term 12', 'Beasts of the Southern Wild', 'The Station Agent', 'Napoleon Dynamite', 'Little Miss Sunshine', 'Juno', 'Garden State', 'Lost in Translation', 'Donnie Darko', 'The Spectacular Now'],
    'Classic Drama Lover': ['Forrest Gump', 'The Shawshank Redemption', '12 Angry Men', 'The Green Mile', 'A Beautiful Mind', 'Good Will Hunting', 'The Pursuit of Happyness', 'The Pianist', 'Philadelphia', 'Rain Man', 'Dead Poets Society', 'One Flew Over the Cuckoos Nest'],
    'Romance Film Romantic': ['The Notebook', 'Before Sunrise', 'Before Sunset', 'Before Midnight', 'Casablanca', 'Eternal Sunshine of the Spotless Mind', 'La La Land', 'Titanic', 'Her', 'Lost in Translation', 'Midnight in Paris', 'Once', 'Atonement', 'The English Patient'],
    'Animation Admirer': ['Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke', 'Akira', 'Inside Out', 'Up', 'Finding Nemo', 'The Incredibles', 'Coco', 'Ratatouille', 'Grave of the Fireflies', 'Your Name.', 'The Wind Rises'],
    'Japanese Animation Devotee': ['Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke', 'Grave of the Fireflies', 'Your Name.', 'Akira', 'Ghost in the Shell', 'Paprika', 'Perfect Blue', 'The Girl Who Leapt Through Time', '5 Centimeters per Second', 'A Silent Voice', 'Weathering with You', 'Wolf Children'],
    'Superhero Film Fan': ['The Dark Knight', 'Iron Man', 'Spider-Man 2', 'Logan', 'Avengers: Endgame', 'Batman Begins', 'The Dark Knight Rises', 'Watchmen', 'V for Vendetta', 'Unbreakable', 'Kick-Ass', 'Deadpool', 'X-Men: Days of Future Past'],
    'War Film Veteran': ['Saving Private Ryan', 'Apocalypse Now', 'Full Metal Jacket', '1917', 'Dunkirk', 'Hacksaw Ridge', 'Platoon', 'The Deer Hunter', 'Paths of Glory', 'The Bridge on the River Kwai', 'Das Boot', 'Come and See', 'Letters from Iwo Jima', 'Black Hawk Down', 'The Thin Red Line'],
    'Historical Epic Fan': ['Gladiator', 'Braveheart', 'Kingdom of Heaven', 'Troy', '300', 'Ben-Hur', 'Spartacus', 'Lawrence of Arabia', 'The Last Samurai', 'Alexander', 'Robin Hood'],
    'Comedy Lover': ['Superbad', 'The Hangover', 'Bridesmaids', 'Step Brothers', 'Anchorman', 'Knocked Up', 'The 40-Year-Old Virgin', 'Wedding Crashers', 'Old School', 'Zoolander', 'Mean Girls', 'Clueless', '10 Things I Hate About You', 'Ghostbusters'],
    'Dark Humor Enthusiast': ['In Bruges', 'Fargo', 'The Big Lebowski', 'Burn After Reading', 'Dr. Strangelove', 'American Psycho', 'Fight Club', 'Pulp Fiction', 'Snatch', 'Lock Stock and Two Smoking Barrels', 'The Grand Budapest Hotel', 'Jojo Rabbit', 'Parasite'],
    'Cult Film Collector': ['Donnie Darko', 'Fight Club', 'A Clockwork Orange', 'The Big Lebowski', 'Pulp Fiction', 'Blade Runner', 'Brazil', 'Eraserhead', 'Mulholland Drive', 'The Room', 'Troll 2', 'Evil Dead', 'Army of Darkness', 'Re-Animator', 'Big Trouble in Little China'],
    'A24 Arthouse Fan': ['Everything Everywhere All at Once', 'The Lighthouse', 'Midsommar', 'Uncut Gems', 'The Witch', 'Hereditary', 'Moonlight', 'Lady Bird', 'The Florida Project', 'The Killing of a Sacred Deer', 'Under the Skin', 'A Ghost Story', 'First Reformed', 'Minari', 'The Green Knight'],
    'Oscar Favorites Collector': ['Nomadland', 'Birdman', 'Spotlight', 'The Shape of Water', 'CODA', 'Green Book', 'Parasite', 'The Artist', 'Slumdog Millionaire', 'No Country for Old Men', 'The Departed', 'Chicago'],
    'Classic Cinema Purist': ['Citizen Kane', 'Casablanca', 'Vertigo', 'Lawrence of Arabia', 'The Third Man', 'Sunset Boulevard', 'Rear Window', 'North by Northwest', '12 Angry Men', 'Some Like It Hot', 'The Maltese Falcon', 'Double Indemnity', 'All About Eve', 'The Bridge on the River Kwai'],
    'B-Movie Enthusiast': ['The Room', 'Troll 2', 'The Toxic Avenger', 'Evil Dead', 'Army of Darkness', 'Re-Animator', 'The Blob', 'They Live', 'Big Trouble in Little China', 'Escape from New York', 'Mandy'],
    'Taiwan Cinema Advocate': ['A Sun', 'Your Name Engraved Herein', 'Detention', 'Monga', 'Cape No. 7', 'Eat Drink Man Woman', 'Yi Yi', 'A Brighter Summer Day', 'Stray Dogs', 'The Assassin', 'Rebels of the Neon God'],
    'Hong Kong Cinema Fan': ['Infernal Affairs', 'Chungking Express', 'Kung Fu Hustle', 'Election', 'PTU', 'Hard Boiled', 'The Killer', 'A Better Tomorrow', 'City on Fire', 'Comrades Almost a Love Story', 'In the Mood for Love', '2046', 'Ashes of Time', 'Happy Together'],
    'Chinese Cinema Enthusiast': ['Farewell My Concubine', 'Raise the Red Lantern', 'Hero', 'House of Flying Daggers', 'The Mermaid', 'Coming Home', 'To Live', 'The Blue Kite', 'Not One Less', 'The Road Home', 'A Touch of Sin', 'Mountains May Depart', 'Ash Is Purest White', 'The Wandering Earth', 'Dying to Survive'],
    'Genre Hybrid Explorer': ['Blade Runner', 'Minority Report', 'The Matrix', 'Dark City', 'Ghost in the Shell', 'Total Recall', 'RoboCop', 'Strange Days', 'A Scanner Darkly', 'Looper', 'Inception', 'Tenet', 'The Thirteenth Floor', 'Equilibrium', 'Repo Men'],
    'Denis Villeneuve Admirer': ['Arrival', 'Blade Runner 2049', 'Sicario', 'Prisoners', 'Dune', 'Enemy', 'Incendies', '10 Cloverfield Lane', 'Ex Machina', 'Annihilation', 'Under the Skin', 'The Lobster'],
}

# Build output
lines = ['# Auto-generated thematic sets keyed by actual profile names', '']
lines.append('THEMATIC_SETS_RAW = {')
for name, titles in THEMATIC.items():
    ids = find_ids(titles)
    lines.append(f'    {name!r}: {ids},')
lines.append('}')
lines.append('')
lines.append('def build_thematic_ids(vector_movies):')
lines.append('    valid_ids = {m["id"] for m in vector_movies if isinstance(m, dict)}')
lines.append('    return {name: set(ids) & valid_ids for name, ids in THEMATIC_SETS_RAW.items()}')
lines.append('')

with open('tools/eval/thematic_sets.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

for name, titles in THEMATIC.items():
    ids = find_ids(titles)
    print(f'{name:35s}: {len(ids)} thematic movies')
print(f'\nWrote tools/eval/thematic_sets.py')

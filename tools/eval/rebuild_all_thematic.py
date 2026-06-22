#!/usr/bin/env python3
"""Rebuild all expanded thematic sets with fuzzy title matching."""
import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('final_boss_vectors.json', 'r', encoding='utf-8') as f:
    movies = json.load(f)

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
    'Sci-Fi Lover': find_ids([
        'Interstellar', 'Arrival', 'Ex Machina', 'Her', 'Blade Runner 2049',
        'Annihilation', 'Moon', 'The Martian', 'Gattaca', 'Primer',
        'Under the Skin', 'Solaris', 'Contact', 'The Man from Earth',
        'Eternal Sunshine of the Spotless Mind', 'Mr. Nobody', 'I Origins',
        'Coherence', 'Predestination', 'Midnight Special',
        'Inception', 'Dune', 'Children of Men', 'Sunshine', 'The Prestige',
        'Everything Everywhere All at Once', 'Blade Runner', 'The Matrix',
        'Minority Report', 'Looper', 'Tenet', 'Gravity', 'Ad Astra',
    ]),
    'Hard Sci-Fi Space Explorer': find_ids([
        '2001: A Space Odyssey', 'Gravity', 'The Martian', 'Ad Astra', 'Moon',
        'Interstellar', 'Solaris', 'The Right Stuff', 'Apollo 13',
        'Europa Report', 'Alien', 'Sunshine', 'Passengers', 'Life',
        'Prospect', 'High Life', 'Dune', 'Inception', 'The Abyss',
        'Forbidden Planet', 'Serenity', 'Mad Max: Fury Road', 'Midnight Special',
        'Everything Everywhere All at Once', 'Planet of the Apes',
    ]),
    'AI Movie Enthusiast': find_ids([
        'Ex Machina', 'Her', 'The Matrix', 'Blade Runner', 'Blade Runner 2049',
        'A.I. Artificial Intelligence', 'I Robot', 'Transcendence', 'Chappie',
        'Automata', 'The Machine', 'Archive', 'Tau', 'Morgan', 'Ghost in the Shell',
        'Surrogates', 'Elysium', 'Lucy', 'In Time', 'Terminator Salvation',
        'Arrival', 'Dune', 'Moon', 'Sunshine', 'Passengers', 'Life',
        'Annihilation', 'Under the Skin', 'Prometheus',
    ]),
    'Crime Film Connoisseur': find_ids([
        'Pulp Fiction', 'Heat', 'The Departed', 'Goodfellas', 'Scarface',
        'Reservoir Dogs', 'City of God', 'A Prophet', 'Sicario',
        'No Country for Old Men', 'Hell or High Water', 'Wind River',
        'Collateral', 'Training Day', 'Casino', 'Donnie Brasco',
        'Carlitos Way', 'Once Upon a Time in America', 'Mystic River',
        'The Godfather', 'The Godfather Part II', 'Road to Perdition',
        'American Gangster', 'A Bronx Tale', 'The Untouchables',
        'Black Mass', 'Public Enemies', 'Gomorrah',
    ]),
    'Gangster Film Devotee': find_ids([
        'The Godfather', 'The Godfather Part II', 'Casino', 'Goodfellas',
        'Scarface', 'American Gangster', 'Donnie Brasco', 'A Bronx Tale',
        'Once Upon a Time in America', 'The Untouchables', 'Road to Perdition',
        'Public Enemies', 'Black Mass',
    ]),
    'Thriller Seeker': find_ids([
        'Se7en', 'Zodiac', 'The Usual Suspects', 'Primal Fear', 'The Game',
        'Gone Girl', 'Shutter Island', 'The Silence of the Lambs', 'No Country for Old Men',
        'Nightcrawler', 'Prisoners', 'Mystic River', 'L.A. Confidential', 'Chinatown',
        'Wind River', 'Eastern Promises', 'Presumed Innocent', 'The Girl with the Dragon Tattoo',
        'Sleuth', 'The Batman', 'Lucky Number Slevin', 'Bad Times at the El Royale',
    ]),
    'Psychological Thriller Fan': find_ids([
        'Black Swan', 'Shutter Island', 'Memento', 'Fight Club', 'Mulholland Drive',
        'The Machinist', 'Donnie Darko', 'Eternal Sunshine of the Spotless Mind',
        'Being John Malkovich', 'The Truman Show', 'A Beautiful Mind', 'Pi', 'Lost Highway',
        'Prisoners', 'Nocturnal Animals', 'Nightcrawler', 'Joker', 'Whiplash',
        'Following', 'Take Shelter', 'Room', 'The Departed',
    ]),
    'Horror Aficionado': find_ids([
        'The Conjuring', 'Hereditary', 'The Ring', 'Insidious', 'It Follows',
        'The Babadook', 'The Witch', 'Get Out', 'Us', 'Midsommar',
        'The Exorcist', 'The Shining', 'Psycho', 'Suspiria', 'The Orphanage',
        'Let the Right One In', 'The Endless', 'Sinister', 'Green Room',
        'Take Shelter', 'The Invitation', 'Pearl', 'Orphan', 'Dead End', 'Grave Encounters',
    ]),
    'Asian Cinema Explorer': find_ids([
        'Oldboy', 'Parasite', 'Memories of Murder', 'Audition', 'Battle Royale',
        'I Saw the Devil', 'The Handmaiden', 'Sympathy for Mr. Vengeance',
        'Lady Vengeance', 'Thirst', 'Joint Security Area', 'Mother', 'The Host',
        'Burning', 'Shoplifters', 'Rashomon', 'Seven Samurai', 'Cure',
    ]),
    'European Art House Cinephile': find_ids([
        'The Lives of Others', 'Amour', 'Le Trou', 'La Ceremonie',
        'A Man Escaped', 'I Stand Alone', 'Le Samourai', 'Read My Lips',
        'The Wages of Fear', 'Irreversible', 'Army of Shadows', 'The Conformist',
        'Belle de Jour', 'La Dolce Vita', 'The 400 Blows', 'Breathless',
        'Cache', 'Revanche', 'Europa', 'The White Ribbon', 'Toni Erdmann', 'Victoria',
        'Persona', 'Wild Strawberries', 'The Seventh Seal', 'Fanny and Alexander',
        'Cries and Whispers', 'Scenes from a Marriage',
        'Life Is Beautiful', 'Cinema Paradiso', 'The Great Beauty',
        'The Hunt', 'Force Majeure', 'Ida', 'Son of Saul', 'The Handmaiden',
    ]),
    'Indie Film Enthusiast': find_ids([
        'Moonlight', 'Lady Bird', 'The Florida Project', 'Eighth Grade', 'Short Term 12',
        'Beasts of the Southern Wild', 'The Station Agent', 'Napoleon Dynamite',
        'Little Miss Sunshine', 'Juno', 'Garden State', 'Lost in Translation',
        'Donnie Darko', 'The Spectacular Now', 'The Banshees of Inisherin', 'The Farewell',
        'Blindspotting', 'mid90s', 'Boy', 'Thunder Road', 'The Favourite',
        'Bo Burnham Inside', 'Frances Ha', 'Triangle of Sadness',
    ]),
    'Classic Drama Lover': find_ids([
        'Forrest Gump', 'The Shawshank Redemption', '12 Angry Men', 'The Green Mile',
        'A Beautiful Mind', 'Good Will Hunting', 'The Pursuit of Happyness', 'The Pianist',
        'Philadelphia', 'Rain Man', 'Dead Poets Society', "One Flew Over the Cuckoo's Nest",
        'Scent of a Woman', 'Amadeus', 'Saving Private Ryan', 'Million Dollar Baby',
        'The Sting', 'Mystic River', 'Hotel Rwanda', 'Rear Window', 'The Departed',
        'Goodfellas', 'The Godfather', 'Casablanca', 'Schindlers List',
        'To Kill a Mockingbird', 'Its a Wonderful Life',
        'Atonement', 'The English Patient', 'Gandhi', 'The Kings Speech',
    ]),
    'Romance Film Romantic': find_ids([
        'The Notebook', 'Before Sunrise', 'Before Sunset', 'Before Midnight',
        'Casablanca', 'Eternal Sunshine of the Spotless Mind', 'La La Land',
        'Titanic', 'Her', 'Lost in Translation', 'Midnight in Paris', 'Once',
        'Atonement', 'The English Patient',
        'In the Mood for Love', 'Amelie', 'Cinema Paradiso',
        'Portrait of a Lady on Fire', 'Call Me by Your Name',
        'The Shape of Water', 'Carol', 'Brooklyn',
        'The Fault in Our Stars', 'Me Before You', 'P.S. I Love You',
        'Love Rosie', '500 Days of Summer',
    ]),
    'Animation Admirer': find_ids([
        'Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke', 'Akira',
        'Inside Out', 'Up', 'Finding Nemo', 'The Incredibles', 'Coco',
        'Ratatouille', 'Grave of the Fireflies', 'Your Name.', 'The Wind Rises',
        'Castle in the Sky', "Kiki's Delivery Service", "Howl's Moving Castle",
        'Ponyo', 'Porco Rosso', 'The Secret World of Arrietty', 'Wolf Children',
        'The Boy and the Beast', 'Weathering with You', 'The Tale of The Princess Kaguya',
        'Warriors of the Wind', 'From Up on Poppy Hill', 'A Silent Voice',
    ]),
    'Japanese Animation Devotee': find_ids([
        'Spirited Away', 'My Neighbor Totoro', 'Princess Mononoke',
        'Grave of the Fireflies', 'Your Name.', 'Akira', 'Ghost in the Shell',
        'Paprika', 'Perfect Blue', 'The Girl Who Leapt Through Time',
        '5 Centimeters per Second', 'A Silent Voice', 'Weathering with You',
        'Wolf Children', 'Castle in the Sky', "Kiki's Delivery Service",
        "Howl's Moving Castle", 'The Wind Rises', 'Ponyo', 'Porco Rosso',
        'The Tale of The Princess Kaguya', 'The Secret World of Arrietty',
        'Tokyo Godfathers', 'Metropolis', 'The Boy and the Beast',
        'Whisper of the Heart', 'From Up on Poppy Hill',
    ]),
    'Superhero Film Fan': find_ids([
        'The Dark Knight', 'Iron Man', 'Spider-Man 2', 'Logan', 'Avengers: Endgame',
        'Batman Begins', 'The Dark Knight Rises', 'Watchmen', 'V for Vendetta',
        'Unbreakable', 'Kick-Ass', 'Deadpool', 'X-Men: Days of Future Past',
        'The Avengers', 'Spider-Man', 'Thor: Ragnarok', 'X-Men: First Class',
        'X-Men', 'Captain America: Civil War', 'Spider-Man: No Way Home',
        'Avengers: Infinity War', 'Guardians of the Galaxy',
    ]),
    'War Film Veteran': find_ids([
        'Saving Private Ryan', 'Apocalypse Now', 'Full Metal Jacket', '1917',
        'Dunkirk', 'Hacksaw Ridge', 'Platoon', 'The Deer Hunter', 'Paths of Glory',
        'The Bridge on the River Kwai', 'Das Boot', 'Come and See',
        'Letters from Iwo Jima', 'Black Hawk Down', 'The Thin Red Line',
        'Beasts of No Nation', 'The Hurt Locker', 'Inglourious Basterds', 'Fury', 'Glory',
        'The Great Escape', 'We Were Soldiers',
    ]),
    'Historical Epic Fan': find_ids([
        'Gladiator', 'Braveheart', 'Kingdom of Heaven', 'Troy', '300',
        'Ben-Hur', 'Spartacus', 'Lawrence of Arabia', 'The Last Samurai',
        'Alexander', 'Robin Hood', 'King Arthur', 'The Patriot',
        'The Last of the Mohicans', 'Pearl Harbor', 'Black Hawk Down',
        'Flyboys', 'We Were Soldiers', 'The Messenger', 'Rob Roy', 'Midway',
    ]),
    'Comedy Lover': find_ids([
        'Superbad', 'The Hangover', 'Bridesmaids', 'Step Brothers', 'Anchorman',
        'Knocked Up', 'The 40-Year-Old Virgin', 'Wedding Crashers', 'Old School',
        'Zoolander', 'Mean Girls', 'Clueless', '10 Things I Hate About You',
        'Ghostbusters', 'Ferris Buellers Day Off', 'I Love You Man',
        'Harold Kumar Go to White Castle', '21 Jump Street', 'Super Troopers',
        'Pineapple Express', 'Role Models', 'Talladega Nights', 'Dodgeball',
        'The Other Guys',
    ]),
    'Dark Humor Enthusiast': find_ids([
        'In Bruges', 'Fargo', 'The Big Lebowski', 'Burn After Reading',
        'Dr. Strangelove', 'American Psycho', 'Fight Club', 'Pulp Fiction',
        'Snatch', 'Lock Stock and Two Smoking Barrels', 'The Grand Budapest Hotel',
        'Jojo Rabbit', 'Parasite', 'Adaptation.', 'Four Lions', 'Filth',
        'The Wolf of Wall Street', 'BlacKkKlansman',
        "I Don't Feel at Home in This World Anymore",
        'Logan Lucky', 'Paper Moon', 'Faults', 'Crimes and Misdemeanors', 'The Sting',
        'Blindspotting',
    ]),
    'Cult Film Collector': find_ids([
        'Donnie Darko', 'Fight Club', 'A Clockwork Orange', 'The Big Lebowski',
        'Pulp Fiction', 'Blade Runner', 'Brazil', 'Eraserhead', 'Mulholland Drive',
        'The Room', 'Troll 2', 'Evil Dead', 'Army of Darkness', 'Re-Animator',
        'Big Trouble in Little China', 'Mad God', 'The Call of Cthulhu',
        'Diary of the Dead', 'Southbound', 'Spawn', 'Twilight Zone: The Movie',
        'The Rocky Horror Picture Show', 'Pink Flamingos', 'Repo Man',
        'El Topo', 'The Holy Mountain', 'Videodrome', 'Naked Lunch',
        'The Toxic Avenger', 'They Live', 'Escape from New York',
        'Martyrs', 'Inside', 'High Tension', 'The Wicker Man', 'Phantasm',
        'Tetsuo: The Iron Man', 'Man Bites Dog', 'Visitor Q', 'Ichi the Killer',
        'Audition', 'Hausu', 'Belladonna of Sadness', 'Fantastic Planet',
        'A Girl Walks Home Alone at Night', 'The Love Witch', 'Mandy',
        'Color Out of Space', 'Psycho Goreman', 'Turbo Kid',
    ]),
    'A24 Arthouse Fan': find_ids([
        'Everything Everywhere All at Once', 'The Lighthouse', 'Midsommar',
        'Uncut Gems', 'The Witch', 'Hereditary', 'Moonlight', 'Lady Bird',
        'The Florida Project', 'The Killing of a Sacred Deer', 'Under the Skin',
        'A Ghost Story', 'First Reformed', 'Minari', 'The Green Knight',
        'A Quiet Place', '10 Cloverfield Lane', 'It Comes at Night',
        'The Lobster', 'The Favourite', 'The Farewell', 'Waves',
        'Eighth Grade', 'mid90s', 'The Last Black in San Francisco',
        'Ex Machina', 'Annihilation', 'It Follows', 'The Babadook',
        'Get Out', 'Us', 'Black Swan', 'Swiss Army Man',
    ]),
    'Oscar Favorites Collector': find_ids([
        'Nomadland', 'Birdman', 'Spotlight', 'The Shape of Water', 'CODA',
        'Green Book', 'Parasite', 'The Artist', 'Slumdog Millionaire',
        'No Country for Old Men', 'The Departed', 'Chicago',
        'Marriage Story', 'The Father', 'Minari', 'The Farewell',
        'Sound of Metal', 'Aftersun', 'The Fabelmans', 'Pig',
        'Room', 'Manchester by the Sea', 'Moonlight', 'Lady Bird',
        'The Banshees of Inisherin', 'Blindspotting', 'Whiplash',
    ]),
    'Classic Cinema Purist': find_ids([
        'Citizen Kane', 'Casablanca', 'Vertigo', 'Lawrence of Arabia',
        'The Third Man', 'Sunset Boulevard', 'Rear Window', 'North by Northwest',
        '12 Angry Men', 'Some Like It Hot', 'The Maltese Falcon',
        'Double Indemnity', 'All About Eve', 'The Bridge on the River Kwai',
        'Notorious', 'Laura', 'Witness for the Prosecution', 'Rebecca',
        'Gaslight', 'Anatomy of a Murder', 'In a Lonely Place',
        'The Man Who Knew Too Much', 'Murder My Sweet', 'Singin in the Rain',
    ]),
    'B-Movie Enthusiast': find_ids([
        'The Room', 'Troll 2', 'The Toxic Avenger', 'Evil Dead', 'Army of Darkness',
        'Re-Animator', 'The Blob', 'They Live', 'Big Trouble in Little China',
        'Escape from New York', 'Mandy', 'Slither', 'The Return of the Living Dead',
        'Night of the Creeps', 'Bad Taste', 'Brain Damage', 'The Stuff',
        'The Lost Skeleton of Cadavra', 'Body Bags', 'Critters', 'Undead',
        'Mad God', 'Turbo Kid', 'Psycho Goreman', 'Color Out of Space',
    ]),
    'Taiwan Cinema Advocate': find_ids([
        'A Sun', 'Your Name Engraved Herein', 'Detention', 'Monga',
        'Cape No. 7', 'Eat Drink Man Woman', 'Yi Yi', 'A Brighter Summer Day',
        'Stray Dogs', 'The Assassin', 'Rebels of the Neon God',
        'Black Coal Thin Ice', 'The Wild Goose Lake', 'Secret',
        'The Bold the Corrupt and the Beautiful', 'The Pig the Snake and the Pigeon',
        'The Abandoned', 'Across the Furious Sea', 'Wrath of Silence',
        'Saving Mr. Wu', 'The Great Hypnotist', 'A Touch of Sin',
    ]),
    'Hong Kong Cinema Fan': find_ids([
        'Infernal Affairs', 'Chungking Express', 'Kung Fu Hustle', 'Election',
        'PTU', 'Hard Boiled', 'The Killer', 'A Better Tomorrow', 'City on Fire',
        'Comrades Almost a Love Story', 'In the Mood for Love', '2046',
        'Ashes of Time', 'Happy Together', 'Drug War', 'Fulltime Killer',
        'SPL Kill Zone', 'Iron Monkey', 'Shinjuku Incident', 'Running Out of Time',
        'Crime Story', 'SPL 2 A Time for Consequences', 'Dragon',
    ]),
    'Chinese Cinema Enthusiast': find_ids([
        'Farewell My Concubine', 'Raise the Red Lantern', 'Hero',
        'House of Flying Daggers', 'The Mermaid', 'Coming Home', 'To Live',
        'The Blue Kite', 'Not One Less', 'The Road Home', 'A Touch of Sin',
        'Mountains May Depart', 'Ash Is Purest White', 'The Wandering Earth',
        'Dying to Survive', 'Crouching Tiger Hidden Dragon', 'Red Cliff',
        'Warriors of Heaven and Earth', 'Mulan Rise of a Warrior',
        'Animal World', 'Detective Dee and the Mystery of the Phantom Flame',
        'Flying Swords of Dragon Gate', 'Cloudy Mountain', 'The Storm Riders',
    ]),
    'Genre Hybrid Explorer': find_ids([
        'Blade Runner', 'Minority Report', 'The Matrix', 'Dark City',
        'Ghost in the Shell', 'Total Recall', 'RoboCop', 'Strange Days',
        'A Scanner Darkly', 'Looper', 'Inception', 'Tenet',
        'The Thirteenth Floor', 'Equilibrium', 'Repo Men',
        'Primer', 'Ex Machina', 'Annihilation', 'Source Code',
        'Edge of Tomorrow', 'Predestination', 'Arrival', 'Dune',
        'Children of Men', 'Sunshine', 'Moon', 'Coherence',
        'Frequency', 'V for Vendetta', 'Outland', 'Hotel Artemis',
        'Timecop', 'Virtuosity', 'Retroactive',
    ]),
    'Denis Villeneuve Admirer': find_ids([
        'Arrival', 'Blade Runner 2049', 'Sicario', 'Prisoners', 'Dune', 'Enemy',
        'Incendies', '10 Cloverfield Lane', 'Ex Machina', 'Annihilation',
        'Under the Skin', 'The Lobster', 'Children of Men', 'Tenet',
        'Upgrade', 'Looper', 'V for Vendetta', 'Serenity', 'Aliens',
        'Minority Report', 'The Terminator', 'Equilibrium', 'Inception',
        'The Matrix', 'Dark City', 'Ghost in the Shell', 'Total Recall',
    ]),
}

# Write thematic_sets.py
lines = ['# Auto-generated thematic sets keyed by actual profile names', '', 'THEMATIC_SETS_RAW = {']
for name, ids in sorted(THEMATIC.items()):
    lines.append(f'    {name!r}: {ids},')
lines.append('}')
lines.append('')
lines.append('def build_thematic_ids(vector_movies):')
lines.append('    valid_ids = {m["id"] for m in vector_movies if isinstance(m, dict)}')
lines.append('    return {name: set(ids) & valid_ids for name, ids in THEMATIC_SETS_RAW.items()}')
lines.append('')

with open('tools/eval/thematic_sets.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

for name, ids in sorted(THEMATIC.items()):
    print(f'{name:35s}: {len(ids)} movies')
print(f'\nWrote tools/eval/thematic_sets.py')

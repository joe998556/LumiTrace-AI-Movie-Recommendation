import json
import sys

with open(r'C:\movie\tools\eval\results\benchmark_round_43.json', 'r', encoding='utf-8') as f:
    r43 = json.load(f)

with open(r'C:\movie\tools\eval\results\benchmark_round_44.json', 'r', encoding='utf-8') as f:
    r44 = json.load(f)

scores43 = {p['profile_name']: p['avg_total_score'] for p in r43['profiles']}
scores44 = {p['profile_name']: p['avg_total_score'] for p in r44['profiles']}

names43 = [p['profile_name'] for p in r43['profiles']]
names44 = [p['profile_name'] for p in r44['profiles']]

# Also collect per-profile duplicate_count and genre_mismatch_count
dup43 = {p['profile_name']: p.get('duplicate_count', 0) for p in r43['profiles']}
dup44 = {p['profile_name']: p.get('duplicate_count', 0) for p in r44['profiles']}
gm43 = {p['profile_name']: p.get('genre_mismatch_count', 0) for p in r43['profiles']}
gm44 = {p['profile_name']: p.get('genre_mismatch_count', 0) for p in r44['profiles']}

print("R43 profile count: {}".format(len(names43)))
print("R44 profile count: {}".format(len(names44)))

# Check for duplicate profile names
r43_dup_names = [n for n in names43 if names43.count(n) > 1]
r44_dup_names = [n for n in names44 if names44.count(n) > 1]
print("R43 duplicate profile names: {}".format(r43_dup_names if r43_dup_names else "None"))
print("R44 duplicate profile names: {}".format(r44_dup_names if r44_dup_names else "None"))

set43 = set(names43)
set44 = set(names44)
print("R43 missing in R44: {}".format(set43 - set44 if set43 - set44 else "None"))
print("R44 missing in R43: {}".format(set44 - set43 if set44 - set43 else "None"))
print()
print("R43 global avg_score: {}".format(r43['avg_score']))
print("R44 global avg_score: {}".format(r44['avg_score']))
print("R43 total_duplicates: {}".format(r43.get('total_duplicates', 'N/A')))
print("R44 total_duplicates: {}".format(r44.get('total_duplicates', 'N/A')))
print("R43 total_genre_mismatches: {}".format(r43.get('total_genre_mismatches', 'N/A')))
print("R44 total_genre_mismatches: {}".format(r44.get('total_genre_mismatches', 'N/A')))
print()

# Build table
header = "{:<42} {:>6} {:>6} {:>7} {:>6}".format("Profile", "R43", "R44", "Delta", "Flag")
print(header)
print("-" * 70)

all_names = list(dict.fromkeys(names43 + names44))  # preserve order, dedupe

decreases = []
for name in all_names:
    s43 = scores43.get(name)
    s44 = scores44.get(name)
    if s43 is not None and s44 is not None:
        delta = round(s44 - s43, 2)
        flag = "REGRESSION" if delta < 0 else ""
        if delta < 0:
            decreases.append((name, s43, s44, delta))
        print("{:<42} {:>6.2f} {:>6.2f} {:>+7.2f} {:>6}".format(name, s43, s44, delta, flag))
    elif s43 is not None:
        print("{:<42} {:>6.2f} {:>6} {:>7} {:>6}".format(name, s43, "N/A", "N/A", "MISSING"))
    elif s44 is not None:
        print("{:<42} {:>6} {:>6.2f} {:>7} {:>6}".format(name, "N/A", s44, "N/A", "NEW"))

print()
print("Total profiles with score decrease: {} out of {}".format(len(decreases), len(names43)))

# Check for any profiles with duplicate_count > 0 in either round
dup_issues = []
for name in names43:
    d43 = dup43.get(name, 0)
    d44 = dup44.get(name, 0)
    if d43 > 0 or d44 > 0:
        dup_issues.append((name, d43, d44))
for name in set(names44) - set(names43):
    d44 = dup44.get(name, 0)
    if d44 > 0:
        dup_issues.append((name, 0, d44))

if dup_issues:
    print("\nDuplicate recommendation counts (per-profile duplicate_count > 0):")
    for n, d43, d44 in dup_issues:
        print("  {}: R43={}, R44={}".format(n, d43, d44))
else:
    print("\nNo profiles with duplicate_count > 0 in either round.")

# Check genre mismatches
gm_issues = []
for name in names43:
    g43 = gm43.get(name, 0)
    g44 = gm44.get(name, 0)
    if g43 > 0 or g44 > 0:
        gm_issues.append((name, g43, g44))

if gm_issues:
    print("\nGenre mismatch counts (per-profile genre_mismatch_count > 0):")
    for n, g43, g44 in gm_issues:
        print("  {}: R43={}, R44={}".format(n, g43, g44))
else:
    print("\nNo profiles with genre_mismatch_count > 0 in either round.")

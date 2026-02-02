from thefuzz import fuzz
import pandas as pd

# 1. Test Name Matching
print("--- Name Matching Test ---")
sheet_name = "Anshika Ahuja"
cert_name = "Anshika" # Assuming this is what's on the cert
ratio = fuzz.token_sort_ratio(sheet_name.lower(), cert_name.lower())
partial = fuzz.partial_ratio(sheet_name.lower(), cert_name.lower())
token_set = fuzz.token_set_ratio(sheet_name.lower(), cert_name.lower())

print(f"Sheet: '{sheet_name}' vs Cert: '{cert_name}'")
print(f"Sort Ratio: {ratio} (Threshold: 85)")
print(f"Partial Ratio: {partial}")
print(f"Token Set Ratio: {token_set}")

# 2. Test Column Mapping
print("\n--- Column Mapping Test ---")
columns = [
    "Timestamp", 
    "Email Address", 
    "Full Name of the Student", 
    "Roll Number of the Student", 
    "Coursera completion certificate link  (Coursera Link only, no other text)\n(Certificate must shared in public mode) ",
    "LinkedIn Post Link ( LinkedIn Link only, no other text)\n(Coursera Certificate must be shared on LinkedIn with your learning experience and following HashTags)\n#TIET\n#ThaparUniversity"
]
df = pd.DataFrame(columns=columns)

# Proposed Mapping Logic
name_map = {
    'Full Name of the Student': 'Student Name',
    'Coursera completion certificate link': 'Coursera Link', # Keyword match
    'LinkedIn Post Link': 'LinkedIn Link'
}

new_cols = []
for col in df.columns:
    col_clean = col.strip()
    found = False
    for k, v in name_map.items():
        if k in col_clean:
            new_cols.append(v)
            found = True
            break
    if not found:
        new_cols.append(col)

print("Original:", df.columns.tolist())
print("Mapped:", new_cols)

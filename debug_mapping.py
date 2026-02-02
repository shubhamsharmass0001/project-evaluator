import pandas as pd

# Simulating the exact headers from input_data.csv
columns = [
    "Timestamp", 
    "Email Address", 
    "Full Name of the Student", 
    "Roll Number of the Student", 
    "Coursera completion certificate link\n(stuff)", 
    "LinkedIn Post Link\n(stuff)"
]

df = pd.DataFrame(columns=columns)

print("Original Columns:")
print(df.columns.tolist())

# Current Logic in app.py
name_map = {
    'student': 'Student Name',
    'full name': 'Student Name',
    'name': 'Student Name',
    'coursera': 'Coursera Link',
    'linkedin': 'LinkedIn Link'
}

normalized_cols = []
for col in df.columns:
    col_str = str(col).strip()
    found = False
    # This loop order is non-deterministic in older python, but usually insertion order
    # 'student' is top of list
    for k, v in name_map.items():
        if k.lower() in col_str.lower():
            normalized_cols.append(v)
            found = True
            print(f"Mapped '{col}' -> '{v}' (matched '{k}')")
            break
    if not found:
        normalized_cols.append(col)

print("\nMapped Columns:")
print(normalized_cols)

# Check for duplicates
if len(normalized_cols) != len(set(normalized_cols)):
    print("\n⚠️ DUPLICATE COLUMNS DETECTED!")
    from collections import Counter
    print(Counter(normalized_cols))

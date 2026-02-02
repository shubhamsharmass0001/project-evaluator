import pandas as pd
from evaluator import validate_coursera, validate_linkedin

# Specific names to check
targets = ['Aastha Garg', 'Sarthak Sharma', 'Ayushi Singh']

print("Loading input data...")
df = pd.read_excel('cleaned_input.xlsx')

print(f"Scanning for: {targets}")
matches = df[df['Student Name'].str.contains('|'.join(targets), na=False, case=False)]

print(f"Found {len(matches)} rows. Running validation...")

for index, row in matches.iterrows():
    name = row['Student Name']
    c_link = row['Coursera Link']
    l_link = row['LinkedIn Link']
    
    # Run Validators
    c_res = validate_coursera(c_link, name)
    l_res = validate_linkedin(l_link, name)
    
    print(f"\n--- {name} ---")
    print(f"Coursera: {c_link}")
    print(f"  Valid: {c_res['Coursera Valid']}")
    print(f"  Notes: {c_res['Coursera Notes']}")
    
    print(f"LinkedIn: {l_link}")
    print(f"  Valid: {l_res['LinkedIn Valid']}")
    print(f"  Notes: {l_res['LinkedIn Notes']}")

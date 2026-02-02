import pandas as pd
import sys

def sanitize(input_path, output_path):
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    print("Original Columns:")
    print(df.columns.tolist())

    # Map columns based on keywords
    name_col = next((c for c in df.columns if "Full Name" in c), None)
    coursera_col = next((c for c in df.columns if "Coursera" in c and "link" in c.lower()), None)
    linkedin_col = next((c for c in df.columns if "LinkedIn" in c and "link" in c.lower()), None)
    email_col = next((c for c in df.columns if "Email" in c), 'Email Address')
    roll_col = next((c for c in df.columns if "Roll Number" in c), 'Roll Number of the Student')

    if not all([name_col, coursera_col, linkedin_col]):
        print("Error: Could not automatically map columns.")
        print(f"Identified: Name={name_col}, Coursera={coursera_col}, LinkedIn={linkedin_col}")
        sys.exit(1)

    # Rename and select
    rename_map = {
        name_col: 'Student Name',
        coursera_col: 'Coursera Link',
        linkedin_col: 'LinkedIn Link',
        email_col: 'Email ID',
        roll_col: 'Roll Number'
    }
    
    # Check if optional columns exist
    cols_to_keep = ['Student Name', 'Coursera Link', 'LinkedIn Link']
    if email_col in df.columns:
        cols_to_keep.append('Email ID')
    if roll_col in df.columns:
         cols_to_keep.append('Roll Number')
    
    clean_df = df.rename(columns=rename_map)[cols_to_keep]
    
    # Save as Excel
    clean_df.to_excel(output_path, index=False)
    print(f"Sanitized data saved to {output_path}")

if __name__ == "__main__":
    sanitize(
        '/Users/shubhamsharma/agentic ai/project_evaluator/input_data.csv',
        '/Users/shubhamsharma/agentic ai/project_evaluator/cleaned_input.xlsx'
    )

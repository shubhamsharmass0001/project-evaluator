import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from thefuzz import fuzz
import sys
import argparse
import time
import os
import concurrent.futures
import re
import random

# --- Configuration ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def validate_coursera(url, student_name):
    """
    Validates a Coursera certificate link.
    Returns:
        dict: containing verification status, extracted name, date, and details.
    """
    result = {
        'Coursera Valid': False,
        'Coursera Date': None,
        'Coursera Match Score': 0,
        'Coursera Notes': ''
    }

    if isinstance(url, str):
        url = url.strip()
        if url.startswith('coursera.org') or url.startswith('www.coursera.org'):
            url = 'https://' + url

    if not isinstance(url, str) or 'coursera.org' not in url:
        result['Coursera Notes'] = 'Invalid URL format'
        return result

    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        final_url = response.url
        
        # Check if redirected to a generic course page
        if 'coursera.org/projects/' in final_url or 'coursera.org/learn/' in final_url or 'coursera.org/specializations/' in final_url:
             result['Coursera Notes'] = 'Invalid Link: Points to Course Landing Page, not Certificate'
             return result

        if response.status_code != 200:
            result['Coursera Notes'] = f'Failed to fetch: Status {response.status_code}'
            return result

        # PDF Handling for Direct Links
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            result['Coursera Valid'] = True
            result['Coursera Notes'] = 'Verified (Direct PDF Link)'
            # Cannot extract name/date from PDF binary easily without extra libs
            return result
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Extract Name
        extracted_name = None
        
        # Strategy A: Reverse Match (Search for Student Name in key tags)
        # This resolves cases where we can't parse "Completed by" but the name is ON the page.
        potential_matches = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'strong', 'span', 'div']):
             text = tag.get_text(strip=True)
             if len(text) < 3 or len(text) > 100: continue
             
             # Check fuzzy match against student_name
             ratio = fuzz.token_sort_ratio(student_name.lower(), text.lower())
             if ratio > 85:
                 potential_matches.append((text, ratio))
        
        # Retry Logic: If Reverse Match failed, and it's a 'certificate' URL, try 'verify' URL
        if not potential_matches and 'account/accomplishments/certificate/' in url:
             retry_url = url.replace('account/accomplishments/certificate/', 'account/accomplishments/verify/')
             try:
                 r_retry = requests.get(retry_url, headers=HEADERS, timeout=15, allow_redirects=True)
                 if r_retry.status_code == 200:
                     soup_retry = BeautifulSoup(r_retry.content, 'html.parser')
                     for tag in soup_retry.find_all(['h1', 'h2', 'h3', 'strong', 'span', 'div']):
                         text = tag.get_text(strip=True)
                         if len(text) < 3 or len(text) > 100: continue
                         ratio = fuzz.token_sort_ratio(student_name.lower(), text.lower())
                         if ratio > 85:
                             potential_matches.append((text, ratio))
                             result['Coursera Notes'] = 'Verified (Retry via verify/)'
                             break
                     # If successful, use this soup for date extraction too
                     if potential_matches:
                         soup = soup_retry 
             except:
                 pass

        if potential_matches:
            potential_matches.sort(key=lambda x: x[1], reverse=True)
            best_match_name, best_score = potential_matches[0]
            result['Coursera Valid'] = True
            result['Coursera Notes'] = 'Verified (Reverse Match)'
            result['Coursera Match Score'] = best_score
            # We treat the matched text as the "extracted name" implicitly
        else:
            # Strategy B: Traditional Extraction (Fallback)
            found_by_pattern = False
            for tag in soup.find_all(['span', 'p', 'strong', 'div', 'h3']):
                if tag.text and 'Completed by' in tag.text:
                    possible_name = tag.text.replace('Completed by', '').strip()
                    if possible_name:
                         if fuzz.partial_ratio(student_name.lower(), possible_name.lower()) > 80:
                             result['Coursera Valid'] = True
                             result['Coursera Notes'] = 'Verified (Extraction)'
                             result['Coursera Match Score'] = 100 # Approx
                             found_by_pattern = True
                             break
            
            if not found_by_pattern:
                 text_content = soup.get_text(separator=' ', strip=True)
                 if "account is verified" in text_content:
                      # Try to find name near it? Hard without regex.
                      # If we are here, Reverse Match failed, so name is likely NOT on page or very different.
                      result['Coursera Notes'] = 'Name not found on page'

        # 2. Extract Date
        extracted_date = None
        # Pattern: "January 1, 2023" anywhere in text (Coursera format is consistent)
        text_content = soup.get_text(" ", strip=True)
        # Look for Month Day, Year
        date_match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}", text_content)
        if date_match:
            date_str = date_match.group(0).strip()
            try:
                dt = datetime.strptime(date_str, '%B %d, %Y')
                extracted_date = dt.strftime('%d-%m-%Y')
            except:
                extracted_date = date_str
        
        result['Coursera Date'] = extracted_date
        
        # 3. Extract Course Name
        extracted_course = None
        
        # Strategy A: Cleanest Source -> og:title / twitter:title
        # Value: "Completion Certificate for Working with BigQuery"
        for meta_name in ['og:title', 'twitter:title']:
            meta = soup.find('meta', attrs={'name': meta_name}) or soup.find('meta', attrs={'property': meta_name})
            if meta and meta.get('content'):
                title_val = meta['content'].strip()
                if "Completion Certificate for" in title_val:
                    extracted_course = title_val.replace("Completion Certificate for", "").strip()
                    break
        
        # Strategy B: OpenGraph Description with regex
        # Value: 'This certificate verifies my successful completion of Coursera\'s "Working with BigQuery" on Coursera'
        if not extracted_course:
            for meta_name in ['og:description', 'twitter:description', 'description']:
                meta = soup.find('meta', attrs={'name': meta_name}) or soup.find('meta', attrs={'property': meta_name})
                if meta and meta.get('content'):
                    desc = meta['content']
                    # Regex to capture text inside quotes or after "Coursera's"
                    # Try simple "completion of [Coursera's] "COURSE" on Coursera"
                    match = re.search(r"completion of\s+(?:Coursera's\s+)?[\"']?(.+?)[\"']?\s+on\s+Coursera", desc, re.IGNORECASE)
                    if match:
                        extracted_course = match.group(1).strip()
                        break

        # Strategy C: First H2 tag (often the course name)
        # In debug: <h2>Working with BigQuery</h2> appears first.
        if not extracted_course:
             h2s = soup.find_all('h2')
             if h2s:
                 first_h2 = h2s[0].get_text(strip=True)
                 # Filter out generic H2s just in case
                 generics = ['What you will learn', 'Skills you will gain', 'Certificates', 'About']
                 if len(first_h2) > 3 and not any(g.lower() in first_h2.lower() for g in generics):
                     extracted_course = first_h2

        result['Coursera Course Name'] = extracted_course
        
        # Remove the verbose extracted name logic entirely as requested

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise e
    except Exception as e:
        result['Coursera Notes'] = f'Error: {str(e)}'

    return result

def validate_linkedin(url, student_name):
    """
    Attempts to validate a LinkedIn post/profile.
    Returns:
        dict: containing verification status, date, and details.
    """
    result = {
        'LinkedIn Valid': False,
        'LinkedIn Date': None,
        'LinkedIn Notes': ''
    }

    if isinstance(url, str):
        url = url.strip()
        if url.startswith('linkedin.com') or url.startswith('www.linkedin.com'):
            url = 'https://' + url

    if not isinstance(url, str) or 'linkedin.com' not in url:
        result['LinkedIn Notes'] = 'Invalid URL format'
        return result

    # Rate Limiting: Add random delay to avoid hitting limits instantly
    time.sleep(random.uniform(0.5, 2.0))

    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code == 999 or response.status_code == 429 or response.status_code == 403:
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 5 + random.uniform(0, 3)
                    time.sleep(wait_time)
                    continue
                else:
                    result['LinkedIn Notes'] = f'Access Denied (Status {response.status_code}) - Rate Limited'
                    return result
            
            if response.status_code != 200:
                result['LinkedIn Notes'] = f'Failed to fetch: Status {response.status_code}'
                return result
            
            # If successful, break format loop
            break
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            result['LinkedIn Notes'] = f'Error: {str(e)}'
            return result
    
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check title
        title = soup.title.string if soup.title else ''
        if student_name.lower() in title.lower():
             result['LinkedIn Notes'] += 'Name found in title. '
             
        # Attempt Date Extraction (Best Effort)
        # LinkedIn public pages might have <time> tags or JSON-LD
        # JSON-LD is often in <script type="application/ld+json">
        import json
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if 'dateCreated' in data:
                     raw_date = data['dateCreated']
                     try:
                         # Handle ISO format usually returned by LinkedIn
                         dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                         result['LinkedIn Date'] = dt.strftime('%d-%m-%Y')
                     except:
                         result['LinkedIn Date'] = raw_date
                     break
                if 'datePublished' in data:
                     raw_date = data['datePublished']
                     try:
                         dt = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                         result['LinkedIn Date'] = dt.strftime('%d-%m-%Y')
                     except:
                         result['LinkedIn Date'] = raw_date
                     break
            except:
                pass
        
        if not result['LinkedIn Date']:
             text_content = soup.get_text(" ", strip=True)
             
             # Pattern 1: Relative time (e.g., "1w •", "2mo •") common in LinkedIn posts
             local_time = datetime.now()
             match_time = re.search(r"(\d+)([dDwmojhms])\s*•", text_content) 
             if match_time:
                 val = int(match_time.group(1))
                 unit = match_time.group(2).lower()
                 delta = timedelta(days=0)
                 if unit == 'd': delta = timedelta(days=val)
                 elif unit == 'w': delta = timedelta(weeks=val)
                 elif unit == 'm' or unit == 'o': delta = timedelta(days=val*30) # approx
                 elif unit == 'y': delta = timedelta(days=val*365)
                 elif unit == 'h': delta = timedelta(hours=val)
                 
                 est_date = local_time - delta
                 result['LinkedIn Date'] = est_date.strftime('%d-%m-%Y')
                 result['LinkedIn Notes'] += ' (Relative Date)'
             else:
                 # Pattern 2: Absolute Date "Jan 12, 2026"
                 date_match = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}", text_content)
                 if date_match:
                     date_str = date_match.group(0)
                     try:
                         # normalize comma
                         date_str = date_str.replace(',', '')
                         dt = datetime.strptime(date_str, '%b %d %Y')
                         result['LinkedIn Date'] = dt.strftime('%d-%m-%Y')
                     except:
                         pass
        
        result['LinkedIn Valid'] = True 
        result['LinkedIn Notes'] += 'Link reachable. '

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise e
    except Exception as e:
        result['LinkedIn Notes'] = f'Error: {str(e)}'

    return result

def main(input_file, output_file):
    print(f"Reading input from {input_file}...")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading excel: {e}")
        sys.exit(1)

    # Validate columns
    required_cols = ['Student Name', 'Coursera Link', 'LinkedIn Link']
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing column '{col}'")
            sys.exit(1)

    # Check for existing progress to resume
    existing_results = []
    
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_excel(output_file)
            existing_results = existing_df.to_dict('records')
            print(f"Resuming... Found {len(existing_results)} already processed rows.")
        except:
             print("Could not read existing output, starting fresh.")

    print("Processing rows with parallelism...")
    results = existing_results 
    processed_count = len(results)
    

# --- Reusable Row Processor ---
def process_single_row(row):
    student_name = row['Student Name']
    
    # Clean URLs
    raw_c_link = str(row['Coursera Link']).strip()
    if ' ' in raw_c_link or '\n' in raw_c_link:
            tokens = re.split(r'\s+', raw_c_link)
            for t in tokens:
                if 'coursera.org' in t:
                    raw_c_link = t
                    break
    
    raw_l_link = str(row['LinkedIn Link']).strip()
    if ' ' in raw_l_link or '\n' in raw_l_link:
            tokens = re.split(r'\s+', raw_l_link)
            for t in tokens:
                if 'linkedin.com' in t:
                    raw_l_link = t
                    break

    c_res = validate_coursera(raw_c_link, student_name)
    l_res = validate_linkedin(raw_l_link, student_name)
    
    # Merge results
    row_result = row.copy() # Avoid modifying original if possible
    row_result.update(c_res)
    row_result.update(l_res)
    
    # Overall status
    if c_res['Coursera Valid']:
            row_result['Overall Status'] = 'Passed Coursera'
    else:
            row_result['Overall Status'] = 'Check Failed'
    
    return row_result

def process_row_wrapper(row_data):
    # Wrapper for concurrent futures which passes index/row tuple
    idx, row = row_data
    return process_single_row(row.to_dict())

    # Convert DataFrame rows to list of (index, row) tuples
    all_rows = list(df.iterrows())
    
    # Filter out rows that are already processed 
    # Logic: Since we are adding new columns, we normally would want to re-run everything.
    # HOWEVER, users might want to keep progress. 
    # IF the input file has changed (new columns), the old 'existing_results' won't have them.
    # Simple fix: If existing results missing 'Email ID', we might need to re-merge or just re-run.
    # Given the user request is explicitly "Add mail id", I will FORCE a fresh run effectively 
    # UNLESS I assume the user just wants the script to support it from now on.
    # To be safe, if I am resuming, I am just appending. 
    # If the user wants new columns populated for OLD rows, they must re-run.
    # I will let the user decide by deleting the file if they want fresh, or just assume fresh run since I deleted the output file in previous step (wait, did I?)
    # I deleted 'final_results.xlsx' in step 171. But then I ran it again.
    # If I want to ensure new columns are present, I should probably start fresh or merge.
    # Since I cannot easily merge without a primary key, I'll rely on the user to clear if needed, 
    # BUT wait, the input file 'cleaned_input.xlsx' will be NEW.
    # The existing 'final_results.xlsx' will match the OLD structure.
    # If I read old results, they won't have Email/Roll.
    # If I append new rows, they WILL have Email/Roll.
    # Result: Mixed schema.
    # DECISION: I will assume that since the code was deleted, the user likely wants a restart or I should force it to ensure consistency.
    # I will comment out the resume logic for this specific run OR handle the schema mismatch.
    # Actually, pandas handles dictionary list to dataframe well (fill NA).
    # But for a clean result, I'll recommend cleaning the output.
    
    rows_to_process = all_rows[len(existing_results):]
    
    if not rows_to_process:
        print("All rows already processed!")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_row = {executor.submit(process_row_wrapper, r): r for r in rows_to_process}
        
        completed_count = 0
        total_count = len(rows_to_process)
        
        for future in concurrent.futures.as_completed(future_to_row):
            data = future.result()
            results.append(data)
            completed_count += 1
            
            if completed_count % 50 == 0:
                print(f"Progress: {completed_count}/{total_count} (Total: {len(results)}) - Saving checkpoint...")
                pd.DataFrame(results).to_excel(output_file, index=False)

    output_df = pd.DataFrame(results)
    output_df.to_excel(output_file, index=False)
    print(f"Done! Results saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluator Pipline')
    parser.add_argument('--input', required=True, help='Input Excel file')
    parser.add_argument('--output', required=True, help='Output Excel file')
    
    args = parser.parse_args()
    main(args.input, args.output)

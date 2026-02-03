import requests
from bs4 import BeautifulSoup

url = "https://www.coursera.org/account/accomplishments/verify/Q8417WP3531Y"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print(f"Fetching {url}...")
try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\n--- Title ---")
        if soup.title:
            print(soup.title.string)
        else:
            print("No title tag found")

        print("\n--- Meta Tags ---")
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            if name:
                print(f"{name}: {meta.get('content')}")

        print("\n--- H1/H2/H3 Tags ---")
        for h in soup.find_all(['h1', 'h2', 'h3']):
             print(f"{h.name}: {h.get_text(strip=True)}")
             
        print("\n--- Strong Tags ---")
        for s in soup.find_all('strong'):
             print(f"Strong: {s.get_text(strip=True)}")

except Exception as e:
    print(f"Error: {e}")

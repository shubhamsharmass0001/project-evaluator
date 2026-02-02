from evaluator import validate_coursera
import requests

# Test case: ONE of Ayushi's PDF links
pdf_url = "https://www.coursera.org/api/certificate.v1/pdf/E7BC8CX93OK6"
name = "Ayushi Singh"

print(f"\nTesting PDF Link: {pdf_url}")

# 1. Run current validator
result = validate_coursera(pdf_url, name)
print(f"Validator Result: {result['Coursera Valid']}")
print(f"Validator Notes: {result['Coursera Notes']}")

# 2. Check headers manually
try:
    r = requests.head(pdf_url, allow_redirects=True)
    print(f"Content-Type: {r.headers.get('Content-Type')}")
except Exception as e:
    print(f"Head Request Failed: {e}")

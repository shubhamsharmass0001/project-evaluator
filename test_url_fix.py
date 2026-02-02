from evaluator import validate_coursera

# Test cases from user complaint
test_cases = [
    ("Aastha Garg", "coursera.org/verify/9U3DHHGH8QY9"),
    ("Sarthak Sharma", "coursera.org/verify/20ZDIQKLX7AX")
]

print("Running Unit Tests for URL Auto-Fix...")
for name, url in test_cases:
    print(f"\nTesting: {name} -> {url}")
    result = validate_coursera(url, name)
    print(f"Valid: {result['Coursera Valid']}")
    print(f"Notes: {result['Coursera Notes']}")

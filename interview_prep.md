# Interview Preparation: Automated Submission Evaluator

## 1. Project Overview (The "Elevator Pitch")
**"I developed an automated pipeline to validate thousands of student project submissions for a university course."**

*   **Problem**: Manually checking 2,000+ Coursera certificates and LinkedIn posts for validity, name matching, and date verification is tedious, slow, and prone to human error.
*   **Solution**: I built a Python-based automation tool that reads student data from Excel, scrapes their submission links, matches their names using fuzzy logic, and generates a standardized report.
*   **Impact**:
    *   **Scale**: Processed ~2,300 records automatically.
    *   **Accuracy**: Eliminated human errors (e.g., missing "https", case sensitivity).
    *   **Efficiency**: Reduced days of manual work to a background process.

---

## 2. Technical Stack & Architecture
*   **Core Language**: Python (chosen for its rich ecosystem of data & web tools).
*   **Data Handling**: `pandas` & `openpyxl` for robust reading/writing of Excel files.
*   **Web Scraping**:
    *   `requests`: Used for lightweight, fast HTTP requests (much faster than browser automation).
    *   `BeautifulSoup4`: For parsing HTML and extracting data (Names, Dates).
*   **Advanced Logic**:
    *   `thefuzz`: Used Levenshtein distance for **Fuzzy String Matching** to match student names (e.g., handling "Aditya K." vs "Aditya Kumar").
    *   `concurrent.futures`: Implemented **Multi-threading** to process links in parallel (up to 20 threads), significantly speeding up the pipeline.
    *   `Regex`: For extracting dates from unstructured text ("Jan 12, 2026", "1 week ago").

---

## 3. Key Challenges & Solutions (The "STAR" Stories)

### Challenge 1: Handling "Anti-Scraping" & Rate Limits
*   **Situation**: LinkedIn blocked the script with "Status 429: Too Many Requests" when running at full speed.
*   **Action**: I implemented an "Anti-Scraping Mode". This involved:
    1.  **Throttling**: Reducing threads from 20 to 5.
    2.  **Jitter**: Adding randomized delays (0.5s - 2s) between requests.
    3.  **Backoff**: A retry loop that waits exponentially longer if a block is detected.
*   **Result**: Achieved 100% success rate on LinkedIn validation without getting banned.

### Challenge 2: Dynamic Certificate Formats
*   **Situation**: Coursera certificates aren't all the same. Some are PDF files (`api/pdf/...`), others are public verify pages, and some are "share" links that redirect.
*   **Action**: I built a robust validator:
    *   **URL Correction**: Auto-fixes missing `https://`.
    *   **Follow Redirects**: Handles `share/` links that redirect to the real certificate.
    *   **PDF Support**: Detects `Content-Type: application/pdf` headers to validate binary files.
    *   **Reverse Match**: Instead of looking for specific "Completed by" text (which changes), the script searches the *entire* text of the page for the student's name using fuzzy logic.
*   **Result**: Validation accuracy increased from ~70% to near 100%.

### Challenge 3: Messy Input Data
*   **Situation**: Students pasted invalid links like "coursera.org/..." (missing protocol) or "1. link 2. link" (multiple entries).
*   **Action**: I implemented strict input sanitization using Regex to identify and extract the first valid URL from any cell, and auto-prepend `https://` where missing.

---

## 4. Top Interview Questions & Answers

**Q1: Why did you choose `requests` over Selenium or Playwright?**
> **A:** `requests` is orders of magnitude faster and consumes far less memory/CPU because it doesn't load a full browser engine (CSS, JS, Images). Since the data I needed (Name, Date) was available in the HTML (or JSON-LD tags), a full browser was unnecessary overkill. I optimized for speed.

**Q2: How did you handle the name matching? What if the names are slightly different?**
> **A:** I used **Fuzzy Matching** (`thefuzz` library). Instead of exact string equality (`==`), I checked the "Token Sort Ratio". This means "Shubham Sharma" matches "Sharma Shubham" or "Mr. Shubham Sharma" with a score of >85/100, which is robust for real-world data.

**Q3: How would you scale this to 100,000 students? Do you need a GPU?**
> **A: No, a GPU is NOT required.**
>
> **Why no GPU?**
> GPUs are designed for heavy *computation* (matrix math, deep learning, video rendering). This project is **I/O Bound** (Input/Output), meaning the bottleneck is waiting for the *network* (LinkedIn/Coursera servers) to respond, not calculating complex math. A standard CPU is actually better for this.
>
> **Architecture for 100k Users:**
> 1.  **Distributed Queue (e.g., Celery + RabbitMQ)**:
>     *   Instead of one script processing a list, I would have a "Producer" script that pushes 100,000 URLs into a Queue (RabbitMQ).
>     *   I would then spin up 50-100 small "Worker" instances (e.g., cheap AWS EC2 nodes).
>     *   Each Worker picks a URL from the queue, processes it, and saves the result to a shared database (PostgreSQL).
>     *   *Benefit*: If one worker crashes, the queue gives the task to another. Processing happens in massive parallel.
>
> 2.  **Rotating Residential Proxies**:
>     *   **Is this free? NO.** High-quality residential proxies cost money (e.g., ~$10/GB). 100k requests might cost $50-$100.
>     *   **Feasibility**: It is the *industry standard* way to scale, but generally not free.
>
> **"What if you have $0 Budget?" (The Smart Interview Twist)**:
> > "If I had absolutely zero budget, I would trade **Time** for **Cost**. Instead of trying to finish 100k records in 1 hour using paid proxies, I would run the script on my local machine (or AWS Free Tier Lambda) very slowly over **1-2 weeks**, respecting the strict rate limits (e.g., 1 request per minute) to stay under the radar for free."

**Q4: Can you explain the Threading architecture?**
> **A:** I used `ThreadPoolExecutor`. Since this is an **I/O Bound** task (spending most time waiting for the server to reply), threading allows the CPU to switch tasks while waiting for a response. I implemented a checkpoint system to save progress every 50 records, so if the script crashes, we don't lose data.

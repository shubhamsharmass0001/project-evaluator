# 🎓 Automated Project Evaluator

**Automate the validation of student submissions, Coursera certificates, and LinkedIn activities with ease.**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Status](https://img.shields.io/badge/Status-Active-success)

## 📖 Overview
The **Automated Project Evaluator** is a streamlined Python tool designed to help educators and program managers verify student submissions efficiently. By leveraging web scraping and fuzzy string matching, the tool validates:
- **Coursera Certificates:** specific checks for valid certificate URLs, extracted names, and completion dates.
- **LinkedIn Posts:** checks for post accessibility and verifies content relevance.

The project features a modern **Streamlit** web interface, making it accessible for users without technical expertise.

## ✨ Key Features
- **🚀 One-Click Validation:** Upload your Excel/CSV file and get instant results.
- **🧠 Smart Column Detection:** Automatically identifies "Student Name", "Coursera Link", and "LinkedIn Link" columns using fuzzy matching logic (e.g., recognizes "Candidate Name" as "Student Name").
- **⚡ Parallel Processing:** Multi-threaded execution ensures thousands of records are processed in minutes.
- **🛡️ Anti-Scraping Mode:** Built-in delays and safe-guards to prevent rate-limiting from platforms like LinkedIn.
- **📊 Real-time Metrics:** View live progress bars and validation statistics (Valid vs. Failed) as the data processes.
- **📥 Excel/CSV Support:** Handles both `.xlsx` and `.csv` formats seamlessly.

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- [pip](https://pip.pypa.io/en/stable/)

### Setup Steps
1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/project-evaluator.git
   cd project-evaluator
   ```

2. **Install Dependencies**
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

### Running the App
To start the web interface, run:
```bash
streamlit run app.py
```
This will automatically open the application in your default web browser (usually at `http://localhost:8501`).

### How to Use
1. **Upload Data:** Drag and drop your `.xlsx` or `.csv` file into the uploader.
2. **Column Mapping:** The app will try to auto-detect the necessary columns.
   - If it fails, a manual mapping menu will appear where you can select the correct columns for *Student Name*, *Coursera Link*, and *LinkedIn Link*.
3. **Configure Settings:**
   - **Parallel Threads:** Adjust the slider in the sidebar (higher = faster, but higher risk of rate limits).
   - **Anti-Scraping Mode:** Keep this checked for better reliability with LinkedIn.
4. **Start Evaluation:** Click the **🚀 Start Evaluation** button.
5. **Download Results:** Once complete, download the `final_results.xlsx` file containing the validation status and notes for each student.

## 📂 Input File Format
Your input file should ideally contain the following columns (names can vary slightly):
- **Student Name** (e.g., "Full Name", "Candidate Name")
- **Coursera Link** (e.g., "Certificate URL", "Coursera Completion")
- **LinkedIn Link** (e.g., "Post URL", "Profile Link")

## 🏗️ Project Structure
```
project_evaluator/
├── app.py                # Main Streamlit web application
├── evaluator.py          # Core validation logic & scraping functions
├── requirements.txt      # Python dependencies
├── input_data.csv        # Example input file
├── cleaned_input.xlsx    # Intermediate processed file
├── final_results.xlsx    # Final output with validation results
└── README.md             # Project documentation
```

## ⚙️ Configuration
- **Max Workers:** By default, the app uses 5 threads. You can increase this in the sidebar for faster processing.
- **Timeouts:** Network requests have a default timeout of 15 seconds to prevent hanging on slow links.

## 🤝 Contributing
Contributions are welcome! If you have suggestions for improvements or bug fixes:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes.
4. Push to the branch and open a Pull Request.

## 📝 License
This project is open-source and available for use.

---
*Created by Shubham Sharma*

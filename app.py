import streamlit as st
import pandas as pd
import time
import concurrent.futures
import json
import os
import pickle
import hashlib
import requests

# --- Helper Functions for History ---
HISTORY_FILE = "email_history.json"

def load_email_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_email_history(email):
    if not email: return
    history = load_email_history()
    # Remove if exists to move to top
    if email in history:
        history.remove(email)
    history.insert(0, email) # Prepend
    # Keep top 10
    history = history[:10]
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

# --- Persistence Helpers ---
PROGRESS_FILE = "progress_cache.pkl"
META_FILE = "progress_meta.json"

def compute_file_hash(file_bytes):
    """Compute MD5 hash of file content to identify unique datasets."""
    return hashlib.md5(file_bytes).hexdigest()

def save_progress(file_hash, results_map):
    """Save current progress to a pickle file and metadata to JSON."""
    try:
        data = {
            "file_hash": file_hash,
            "results_map": results_map
        }
        with open(PROGRESS_FILE, "wb") as f:
            pickle.dump(data, f)
            
        # Save lightweight metadata
        meta = {"file_hash": file_hash, "count": len(results_map)}
        with open(META_FILE, "w") as f:
            json.dump(meta, f)
            
    except Exception as e:
        print(f"Error saving progress: {e}")

def load_progress(current_file_hash):
    """
    Load progress if cache exists and matches current file.
    Checks metadata first to avoid loading large pickle if mismatch.
    Returns: (results_map, is_resumed) or ({}, False)
    """
    # 1. Check Metadata first (Fast)
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r") as f:
                meta = json.load(f)
            if meta.get("file_hash") != current_file_hash:
                return {}, False
        except:
             pass # If meta fails, fall back to main file check or just fail
    else:
        if not os.path.exists(PROGRESS_FILE):
             return {}, False

    # 2. Load Pickle (Slow)
    try:
        if not os.path.exists(PROGRESS_FILE):
             return {}, False
             
        with open(PROGRESS_FILE, "rb") as f:
            data = pickle.load(f)
        
        if data.get("file_hash") == current_file_hash:
            return data.get("results_map", {}), True
        else:
            return {}, False 
    except Exception:
        return {}, False

def clear_progress():
    """Delete the progress cache files."""
    for f_path in [PROGRESS_FILE, META_FILE]:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
            except:
                pass
from io import BytesIO
from evaluator import process_single_row
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os


# Helper function to send email with attachment
def send_email_with_attachment(sender, password, recipient, subject, body, attachment_paths, server, port):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject

    # Using 'html' because the body content has HTML tags
    msg.attach(MIMEText(body, 'html'))

    # Helper to attach a single file
    def attach_file(path):
        if not path: return None
        try:
             with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
             encoders.encode_base64(part)
             part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(path)}",
             )
             return part, None
        except Exception as e:
            return None, str(e)

    # Handle list of paths
    if isinstance(attachment_paths, list):
        for path in attachment_paths:
            part, error = attach_file(path)
            if part:
                msg.attach(part)
            elif error:
                return False, f"Could not attach file {path}: {error}"
    else:
        # Fallback for single path
        part, error = attach_file(attachment_paths)
        if part:
             msg.attach(part)
        elif error:
             return False, f"Could not attach file {attachment_paths}: {error}"
    
    # Sanitize password (remove spaces)
    if password:
        password = password.replace(" ", "")

    try:
        with smtplib.SMTP(server, port) as s:
            s.starttls()
            s.login(sender, password)
            s.send_message(msg)
        return True, "Email sent successfully!"
    except smtplib.SMTPAuthenticationError as e:
        err_msg = str(e)
        if "534" in err_msg or "5.7.9" in err_msg:
             return False, "❌ Authentication Failed (Google Security). Please visit: https://accounts.google.com/DisplayUnlockCaptcha to unblock your account, then try again."
        return False, f"Authentication Error: {err_msg}"
    except Exception as e:
        return False, str(e)

# Page Config
st.set_page_config(
    page_title="Project Evaluator",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "ValidatorPro" UI
st.markdown("""
<style>
    /* Import Google Font 'Inter' */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #e0e0e0;
        background-color: #0b0c15; /* Deep Navy Background */
    }
    
    /* Main App Background */
    .stApp {
        background-color: #0b0c15;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #10111a;
        border-right: 1px solid #1f212e;
    }
    
    /* Headings */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }
    
    h1 { font-size: 2.5rem; }
    h2 { font-size: 1.5rem; color: #a1a3b5 !important; font-weight: 500 !important; }

    /* Custom Input Card */
    .input-card {
        background-color: #151725;
        border-radius: 16px;
        padding: 40px;
        border: 1px solid #23263a;
        margin-top: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    /* File Uploader Customization */
    [data-testid="stFileUploader"] {
        background-color: #1a1d2d;
        border: 1px dashed #3a3f55;
        border-radius: 12px;
        padding: 20px;
    }
    
    /* Text Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1a1d2d !important;
        color: white !important;
        border: 1px solid #2d3246 !important;
        border-radius: 8px !important;
    }
    
    /* Primary Button (Deploy Validator) */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.8rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s;
    }
    
    div.stButton > button:first-child:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        border: none;
    }
    
    /* Metric Cards (Sidebar) */
    .metric-box {
        background-color: #1a1d2d;
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid #10b981; /* Green accent */
        color: #e0e0e0;
    }
    .metric-risk {
        border-left: 4px solid #f59e0b;
    }
    
    /* Divider */
    hr {
        border-color: #2d3246;
    }

</style>
""", unsafe_allow_html=True)

# --- Sidebar Layout ---
with st.sidebar:
    st.markdown("### ⚡ **ValidatorPro**")
    st.markdown("---")
    
    st.markdown("##### ⚙️ SYSTEM CONFIGURATION")
    max_workers = st.slider("Parallel Threads", min_value=1, max_value=100, value=50)
    
    # Status Card logic based on slider
    if max_workers <= 10:
        status_color = "#ef4444"
        status_text = "Slow Performance"
        status_desc = "Processing will be very slow."
        status_class = "metric-risk"
    elif max_workers <= 70:
        status_color = "#10b981"
        status_text = "Optimal Performance"
        status_desc = "Maximizes speed without errors."
        status_class = "metric-box"
    else:
        status_color = "#f59e0b"
        status_text = "High Risk Mode"
        status_desc = "May trigger rate limits."
        status_class = "metric-risk" # Re-use or custom

    st.markdown(f"""
    <div class="{status_class}" style="border-left-color: {status_color};">
        <div style="font-weight: 600; color: {status_color};">⚡ {status_text}</div>
        <div style="font-size: 0.85rem; color: #a1a3b5;">{status_desc}</div>
    </div>
    <br>
    
    <!-- Thread Performance Table -->
    <table style="width: 100%; border-collapse: collapse; color: #e0e0e0; font-size: 0.85rem;">
        <tr style="border: 1px solid #2d3246; background: #1a1d2d;">
            <th style="padding: 8px; text-align: left; border-right: 1px solid #2d3246;">Threads</th>
            <th style="padding: 8px; text-align: left;">Result</th>
        </tr>
        <tr style="border: 1px solid #2d3246;">
            <td style="padding: 8px; font-weight: 600; border-right: 1px solid #2d3246;">1–10</td>
            <td style="padding: 8px;">🐢 Too slow</td>
        </tr>
        <tr style="border: 1px solid #2d3246;">
            <td style="padding: 8px; font-weight: 600; border-right: 1px solid #2d3246;">20–40</td>
            <td style="padding: 8px;">⚖️ Stable + fast</td>
        </tr>
        <tr style="border: 1px solid #2d3246;">
            <td style="padding: 8px; font-weight: 600; border-right: 1px solid #2d3246;">50–70</td>
            <td style="padding: 8px;">🚀 Optimal</td>
        </tr>
        <tr style="border: 1px solid #2d3246;">
            <td style="padding: 8px; font-weight: 600; border-right: 1px solid #2d3246;">80–100</td>
            <td style="padding: 8px;">⚠️ Risky But Works</td>
        </tr>
    </table>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Email Settings in Expanders
    # Collapsed by default to keep clean
    with st.expander("📩 EMAIL NOTIFICATIONS", expanded=True):
        st.caption("Settings")
        smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
        smtp_port = st.number_input("SMTP Port", value=587)
        sender_email = st.text_input("Sender Email", value="evaluator2209@gmail.com").strip()
        sender_password = st.text_input("App Password", value="ooal rnxf ehdx irhq", type="password").strip()
        
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                t_success, t_msg = send_email_with_attachment(
                    sender_email, sender_password, sender_email, 
                    "Test Email", "<p>This is a test email from Project Evaluator.</p>", [], smtp_server, smtp_port
                )
                if t_success:
                    st.success("✅ Connection Successful!")
                else:
                    st.error(f"❌ Connection Failed: {t_msg}")

    # User Profile at Bottom (simulated)
    st.markdown("<br>"*5, unsafe_allow_html=True) # Spacer
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: #151725; border-radius: 8px;">
        <div style="width: 35px; height: 35px; background: #6366f1; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white;">SS</div>
        <div>
            <div style="font-size: 0.9rem; font-weight: 600;">Shubham Sharma</div>
            <div style="font-size: 0.7rem; color: #888;">Admin Workspace</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Hidden / Default Configs
    anti_scraping = True 

# --- Main Layout ---
col_main = st.container()

with col_main:
    st.markdown("# Certificate Validation")
    st.markdown("Automate the validation of Coursera certificates and LinkedIn submissions. Upload your dataset below to begin the verification queue.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Input Card Wrapper Start
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    
    st.markdown("### Input Data")
    
    # File Uploader & Sample
    st.markdown('<span style="color:#a1a3b5">Supported formats: .xlsx, .csv</span>', unsafe_allow_html=True)
    
    # 1. Sample Data (Full Width Expander)
    with st.expander("ℹ️ View Sample Input Format"):
        st.markdown("Your input file should look something like this:")
        sample_data = pd.DataFrame({
            'Student Name': ['John Doe', 'Jane Smith'],
            'Coursera Link': ['https://coursera.org/verify/XYZ123', 'https://coursera.org/verify/ABC456'],
            'LinkedIn Link': ['https://linkedin.com/posts/johndoe_certificate', 'https://linkedin.com/in/janesmith']
        })
        st.table(sample_data)
        
        # Download Sample Button
        sample_csv = sample_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download Sample CSV",
            sample_csv,
            "sample_input.csv",
            "text/csv",
            key='download-sample'
        )

    # 2. Main File Uploader
    uploaded_file = st.file_uploader("Upload Input File (Excel/CSV)", type=['xlsx', 'xls', 'csv'], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown('<div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: -10px;">👆 Drag and drop your file here</div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. Email & History (Side by Side)
    c_hist, c_recip = st.columns([1, 1])
    
    with c_hist:
        # Email History UI
        history = load_email_history()
        selected_hist = st.selectbox("Recent Inputs", ["(Select to auto-fill)"] + history)
    
    default_val = ""
    if selected_hist != "(Select to auto-fill)":
        default_val = selected_hist
    
    with c_recip:
        recipient_email = st.text_input("Recipient Email", value=default_val, placeholder="e.g., recipient@example.com")

st.markdown("</div>", unsafe_allow_html=True) # Close .input-card

# --- Action Bar (Deploy Check) ---
st.markdown("<br>", unsafe_allow_html=True)

# Logic for "Deploy" / "Start" buttons
# We need to hook this into the existing 'if uploaded_file...' logic below
if uploaded_file and recipient_email:
    # Calculate hash etc (preserve existing logic flow)
    # But UI button goes here
    pass  # We will handle button render inside the main block below to avoid scope issues

# Spacer
st.markdown("<br>", unsafe_allow_html=True)

if uploaded_file and recipient_email:

    # Reset session state if file changes
    # Use getvalue() to compute hash, then reset pointer for pandas
    file_bytes = uploaded_file.getvalue()
    file_hash = compute_file_hash(file_bytes)
    uploaded_file.seek(0)

    if 'current_file_hash' not in st.session_state or st.session_state['current_file_hash'] != file_hash:
        st.session_state['current_file_hash'] = file_hash
        
        # Try to load existing progress
        saved_results, is_resumed = load_progress(file_hash)
        
        if is_resumed:
           st.session_state['results_map'] = saved_results
           st.toast(f"🔄 Resumed progress! {len(saved_results)} records loaded from cache.", icon="📂")
        else:
           st.session_state['results_map'] = {}
           # If new file, ensure we don't have old cache lying around that might confuse logic later (though hash check prevents it)
           clear_progress()
           
        if 'df_fixed' in st.session_state:
            del st.session_state['df_fixed']

    try:
        # Load Data with Caching
        @st.cache_data
        def load_data(file_content, filename):
            if filename.endswith('.csv'):
                return pd.read_csv(BytesIO(file_content))
            else:
                return pd.read_excel(BytesIO(file_content))
        
        # Pass bytes to avoid stream position issues with caching
        uploaded_file.seek(0)
        df = load_data(uploaded_file.getvalue(), uploaded_file.name)
        
        from thefuzz import fuzz

        # --- Fuzzy Column Normalization ---
        # Robustly find coordinates
        targets = {
            'Student Name': ['Full Name of the Student','student name', 'full name', 'candidate name'],
            'Coursera Link': ['Coursera completion certificate link','coursera', 'certificate link'],
            'LinkedIn Link': ['LinkedIn Post Link','linkedin', 'post link']
        }
        
        new_columns = list(df.columns)
        
        for target, keywords in targets.items():
            best_score = 0
            best_col_idx = -1
            
            for idx, col in enumerate(df.columns):
                col_str = str(col).lower()
                
                # Exclusion
                if target == 'Student Name' and ('roll' in col_str or 'number' in col_str):
                    continue
                
                # Check against all keywords
                for kw in keywords:
                    score = fuzz.token_set_ratio(kw, col_str)
                    if score > best_score:
                        best_score = score
                        best_col_idx = idx
            
            # Threshold for accepting a match
            if best_score > 70 and best_col_idx != -1:
                col_name = df.columns[best_col_idx]
                # Avoid overwriting if already mapped to another higher priority target?
                # For now simple greedy.
                new_columns[best_col_idx] = target

        df.columns = new_columns
        # ----------------------------------

        # Save cleaned file explicitly for user
        try:
             outfile = "cleaned_input.xlsx"
             df.to_excel(outfile, index=False)
             st.success(f"✅ Auto-converted and saved normalized file to **{outfile}**")
        except Exception as e: 
             st.warning(f"Could not save cleaned file: {e}")

        st.success(f"Loaded {len(df)} records successfully!")
        
        # Validation Columns Check
        required_cols = ['Student Name', 'Coursera Link', 'LinkedIn Link']
        missing = [c for c in required_cols if c not in df.columns]
        
        if missing:
            st.error(f"⚠️ Auto-detection failed for: {missing}")
            
            with st.expander("🛠️ Manual Column Mapping (Fix Here)", expanded=True):
                st.write("Please select the correct columns from your file:")
                
                col_options = ["(Select Column)"] + list(df.columns)
                
                # Try to guess default index
                def get_idx(key):
                    return 0
                
                c1, c2, c3 = st.columns(3)
                map_student = c1.selectbox("Column for: Student Name", col_options)
                map_coursera = c2.selectbox("Column for: Coursera Link", col_options)
                map_linkedin = c3.selectbox("Column for: LinkedIn Link", col_options)
                
                if st.button("Apply Mapping & Proceed"):
                    rename_map = {}
                    if map_student != "(Select Column)": rename_map[map_student] = 'Student Name'
                    if map_coursera != "(Select Column)": rename_map[map_coursera] = 'Coursera Link'
                    if map_linkedin != "(Select Column)": rename_map[map_linkedin] = 'LinkedIn Link'
                    
                    if rename_map:
                        df.rename(columns=rename_map, inplace=True)
                        st.session_state['df_fixed'] = df
                        st.experimental_rerun()
                        
        # Check if we have a fixed dataframe in session state
        if 'df_fixed' in st.session_state:
             df = st.session_state['df_fixed']
             # Re-check missing
             missing = [c for c in required_cols if c not in df.columns]

        if missing:
             st.stop() # Stop here if still missing
             
        else:
            # --- State Management for Dynamic Parallelism ---
            # We use a persistent dictionary to store results: {row_index: result_dict}
            if 'results_map' not in st.session_state:
                st.session_state['results_map'] = {}
            
            if 'processing_active' not in st.session_state:
                st.session_state['processing_active'] = False
                
            # --- System Status & Deploy Action ---
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Status Indicator
            if st.session_state.get('processing_active'):
                 status_html = '<div style="color: #f59e0b; font-weight: 600; margin-bottom: 8px;">🟠 System Processing...</div>'
            else:
                 status_html = '<div style="color: #10b981; font-weight: 600; margin-bottom: 8px;">🟢 System Ready</div>'
            
            st.markdown(status_html, unsafe_allow_html=True)

            # Action Button
            if st.session_state.get('processing_active'):
                if st.button("⏸ Pause Validator", type="secondary", use_container_width=True):
                    st.session_state['processing_active'] = False
                    st.rerun()
            else:
                has_data = len(st.session_state.get('results_map', {})) > 0
                btn_label = "⚡ Resume Validator" if has_data else "⚡ Deploy Validator"
                
                if st.button(btn_label, type="primary", use_container_width=True):
                    st.session_state['processing_active'] = True
                    if not has_data:
                        st.session_state['results_map'] = {} # Reset only if fresh
                    st.rerun()

            # --- Main Processing Loop ---
            if st.session_state['processing_active']:
                
                # Progress Containers
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Metrics Placeholder
                col1, col2, col3 = st.columns(3)
                m1 = col1.empty()
                m2 = col2.empty()
                m3 = col3.empty()
                
                # Prepare Data
                rows = df.to_dict('records')
                total = len(rows)
                
                # Identify and Process in Micro-Batches to allow interruption
                while st.session_state['processing_active']:
                    # Re-calculate pending every iteration to check if we are done
                    pending_indices = [i for i in range(total) if i not in st.session_state['results_map']]
                    
                    if not pending_indices:
                        break
                        
                    # MICRO-BATCHING: Process a small chunk at a time.
                    # Batch size 1:1 with workers minimizes 'drain time' on interrupt
                    batch_size = max(max_workers, 10) 
                    current_batch_indices = pending_indices[:batch_size]
                    
                    batch_map = {i: rows[i] for i in current_batch_indices}
                    
                    status_text.text(f"Processing Batch... {total - len(pending_indices)}/{total} completed. (Threads: {max_workers})")
                    
                    # Run BATCH using current max_workers
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_idx = {executor.submit(process_single_row, row): idx for idx, row in batch_map.items()}
                        
                        for future in concurrent.futures.as_completed(future_to_idx):
                            original_idx = future_to_idx[future]
                            try:
                                res = future.result()
                                st.session_state['results_map'][original_idx] = res
                            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                                st.error(f"🚨 Network Connection Lost! Processing paused. ({e})")
                                st.warning("Please check your internet connection and click 'Resume Evaluation' when back online.")
                                st.session_state['processing_active'] = False
                                executor.shutdown(wait=False, cancel_futures=True)
                                break
                            except Exception as e:
                                err_res = rows[original_idx].copy()
                                err_res['Overall Status'] = f"Error: {e}"
                                st.session_state['results_map'][original_idx] = err_res
                                
                            # Update UI
                            curr_total = len(st.session_state['results_map'])
                            
                            # Incremental Save (Every 5 rows)
                            if curr_total % 5 == 0:
                                save_progress(st.session_state.get('current_file_hash'), st.session_state['results_map'])
                                
                            progress_bar.progress(curr_total / total)
                            status_text.text(f"Processing... {curr_total}/{total} (Threads: {max_workers})")
                            
                            # Metrics
                            all_res = st.session_state['results_map'].values()
                            v_coursera = sum(1 for r in all_res if r.get('Coursera Valid'))
                            v_linkedin = sum(1 for r in all_res if r.get('LinkedIn Valid'))
                            
                            m1.metric("Processed", f"{curr_total}/{total}")
                            m2.metric("Coursera Valid", f"{v_coursera}")
                            m3.metric("LinkedIn Valid", f"{v_linkedin}")
                            
                            if anti_scraping:
                                time.sleep(0.05)
                    
                    # If we broke out of inner loop due to error (processing_active set to False)
                    if not st.session_state['processing_active']:
                        break

                # --- Completion Check ---
                # Check again if done
                if len(st.session_state['results_map']) == total:
                    st.balloons()
                    status_text.success("✅ Processing Complete!")
                    st.session_state['processing_active'] = False # Stop the loop
                    clear_progress()
                    
                    # Final Assembly
                    final_results = [st.session_state['results_map'][i] for i in range(total)]
                    
                    # Result DataFrame
                    result_df = pd.DataFrame(final_results)
                    
                    # Remove 'Coursera Match Score' column if it exists
                    if 'Coursera Match Score' in result_df.columns:
                        result_df = result_df.drop(columns=['Coursera Match Score'])
                        
                    final_filename = "final_results.xlsx"
                    summary_filename = "student_summary.xlsx"
                    
                    # --- Generate Student Summary ---
                    summary_df = pd.DataFrame()
                    try:
                        # Group fields - try to find unique identifiers
                        group_cols = ['Student Name']
                        # Check if Roll Number-like columns exist to be more specific
                        roll_col = next((c for c in result_df.columns if 'roll' in c.lower() or 'number' in c.lower()), None)
                        if roll_col:
                            group_cols.append(roll_col)
                        
                        # Aggregation
                        summary_df = result_df.groupby(group_cols).agg(
                            Total_Coursera_Links=('Coursera Link', 'count'),
                            Valid_Coursera_Links=('Coursera Valid', lambda x: x.sum()),
                            Total_LinkedIn_Links=('LinkedIn Link', 'count'),
                            Valid_LinkedIn_Links=('LinkedIn Valid', lambda x: x.sum())
                        ).reset_index()
                        
                        # Optional: Add Email if available (take first)
                        email_col = next((c for c in result_df.columns if 'email' in c.lower()), None)
                        if email_col:
                            email_map = result_df.groupby(group_cols)[email_col].first().reset_index()
                            summary_df = pd.merge(summary_df, email_map, on=group_cols, how='left')

                            # --- Date Variance & Pattern Analysis ---
                        # Logic: Use 'Timestamp' if available for precise behavior tracking (Bulk vs Weekly).
                        # Fallback: Use extracted 'Coursera Date' / 'LinkedIn Date' if Timestamp missing.
                        
                        date_stats = []
                        from datetime import datetime, timedelta
                        
                        # Reference: Monday Jan 5, 2026 at 08:00 AM
                        start_date_ref = datetime(2026, 1, 5, 8, 0, 0)
                        
                        for name, group in result_df.groupby('Student Name'):
                            
                            # --- Unified Date Extraction Logic ---
                            # Iterate through each row to verify validity and extract the best available date.
                            # Priority: Timestamp > Extracted Date
                            
                            valid_dt_objs = [] 
                            
                            # Pre-convert columns to datetime objects for efficiency/robustness if they exist
                            # We use dayfirst=True for dates like DD-MM-YYYY
                            
                            # Helper to get date from row safely
                            def get_valid_date(val, is_timestamp=False):
                                try:
                                    if pd.isna(val) or val == '': return None
                                    # If it's already a datetime/timestamp object
                                    if isinstance(val, (pd.Timestamp, datetime)):
                                        return val
                                    # Parse string
                                    dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                                    if pd.isna(dt): return None
                                    return dt
                                except:
                                    return None

                            for idx, row in group.iterrows():
                                # STRICTLY use Extracted Dates (Column L / P logic)
                                # Ignored Timestamp for summary binning as per user request.

                                # 1. Process Coursera
                                if row.get('Coursera Valid'):
                                    c_date_val = row.get('Coursera Date')
                                    final_dt = get_valid_date(c_date_val)
                                    # Normalize extracted dates to noon (12:00 PM)
                                    if final_dt:
                                        final_dt = final_dt.replace(hour=12, minute=0, second=0)
                                        valid_dt_objs.append((final_dt, 'Coursera'))

                                # 2. Process LinkedIn
                                if row.get('LinkedIn Valid'):
                                    l_date_val = row.get('LinkedIn Date')
                                    final_dt = get_valid_date(l_date_val)
                                    # Normalize extracted dates to noon (12:00 PM)
                                    if final_dt:
                                        final_dt = final_dt.replace(hour=12, minute=0, second=0)
                                        valid_dt_objs.append((final_dt, 'LinkedIn'))
                            
                            # --- Scoring & Analysis ---
                            student_stat = {
                                'Student Name': name,
                                'Days Span': 0,
                                'Consistency Status': 'No Dates Found',
                                'Till Now Marks': 0
                            }
                            
                            # Filter only dates within first 12 weeks AND Calculate Scores
                            filtered_dts_only = []
                            week_counts_c = {}
                            week_counts_l = {}
                            week_headers = {} # Map eff_week_num -> col_name
                            
                            for dt, subtype in valid_dt_objs:
                                diff = dt - start_date_ref
                                if diff.total_seconds() < 0:
                                    raw_week_num = 1
                                else:
                                    raw_week_num = (diff.days // 7) + 1
                                
                                # ONLY allow up to Week 12
                                if 1 <= raw_week_num <= 12:
                                    filtered_dts_only.append(dt)
                                    
                                    # --- Merge Week 1 & 2 Logic ---
                                    if raw_week_num in [1, 2]:
                                        eff_week_num = 1.5
                                        # Special Header for W1+2
                                        range_str = "05 Jan - 19 Jan"
                                        col_name = "Week 1 & 2 (05 Jan - 19 Jan)"
                                    else:
                                        eff_week_num = raw_week_num
                                        # Normal Header (Mon-Mon)
                                        w_start = start_date_ref + timedelta(days=(raw_week_num - 1) * 7)
                                        w_end = w_start + timedelta(days=7) 
                                        range_str = f"{w_start.strftime('%d %b')} - {w_end.strftime('%d %b')}"
                                        col_name = f"Week {raw_week_num} ({range_str})"
                                    
                                    # Store Link
                                    week_headers[eff_week_num] = col_name

                                    if subtype == 'Coursera':
                                        week_counts_c[eff_week_num] = week_counts_c.get(eff_week_num, 0) + 1
                                    elif subtype == 'LinkedIn':
                                        week_counts_l[eff_week_num] = week_counts_l.get(eff_week_num, 0) + 1
                            
                            # --- Calculate "Till Now Marks" ---
                            current_now = datetime.now()
                            curr_diff = current_now - start_date_ref
                            if curr_diff.total_seconds() < 0:
                                max_raw_week = 1
                            else:
                                max_raw_week = (curr_diff.days // 7) + 1

                            max_raw_week = min(max_raw_week, 12) # Cap at 12
                            if max_raw_week < 1: max_raw_week = 1
                            
                            # Determine effective weeks to evaluate
                            weeks_to_eval = []
                            # If we are in or past week 1, we evaluate the "Week 1 & 2" block
                            # Since we merged them, we always check bucket 1.5 if max_raw_week >= 1
                            if max_raw_week >= 1:
                                weeks_to_eval.append(1.5)
                            
                            # Then add subsequent weeks if passed
                            for w in range(3, max_raw_week + 1):
                                weeks_to_eval.append(w)
                            
                            total_c_points = 0
                            total_l_points = 0
                            total_weeks_weight = 0
                            
                            for w in weeks_to_eval:
                                c_count = week_counts_c.get(w, 0)
                                l_count = week_counts_l.get(w, 0)
                                
                                if w == 1.5:
                                    # Merged Block: Target 4, Weight 2
                                    weight = 2.0
                                    target = 4.0
                                else:
                                    # Normal Week: Target 2, Weight 1
                                    weight = 1.0
                                    target = 2.0
                                
                                total_c_points += (min(c_count, target) / target) * weight
                                total_l_points += (min(l_count, target) / target) * weight
                                total_weeks_weight += weight
                            
                            # Normalize
                            if total_weeks_weight > 0:
                                final_c_score = (total_c_points / total_weeks_weight) * 4
                                final_l_score = (total_l_points / total_weeks_weight) * 4
                            else:
                                final_c_score = 0
                                final_l_score = 0
                            
                            final_marks = round(final_c_score + final_l_score, 2)

                            # --- Stats ---
                            if filtered_dts_only:
                                min_date = min(filtered_dts_only)
                                max_date = max(filtered_dts_only)
                                span_days = (max_date - min_date).days
                            else:
                                span_days = 0

                            # Consistency Status
                            total_links_filtered = len(filtered_dts_only)
                            status = "Incomplete Data"
                            if total_links_filtered >= 4:
                                if span_days <= 2:
                                    status = "⚠️ Bulk Submission (< 2 Days)"
                                elif span_days > 7: 
                                    status = "✅ Weekly Spread"
                                else:
                                    status = "⚖️ Moderate Pace"
                            elif total_links_filtered > 0:
                                 status = "Incomplete Data"
                            else:
                                 status = "No Valid Dates (in 12 weeks)"

                            student_stat.update({
                                'Days Span': span_days,
                                'Consistency Status': status,
                                'Till Now Marks': final_marks
                            })
                            
                            # Add week columns with formatted strings
                            for w, c_name in week_headers.items():
                                c = week_counts_c.get(w, 0)
                                l = week_counts_l.get(w, 0)
                                tot = c + l
                                fmt_val = f"{tot} = {c} + {l}"
                                student_stat[c_name] = fmt_val
                            
                            date_stats.append(student_stat)
                        
                        # Merge Date Stats
                        date_stats_df = pd.DataFrame(date_stats)
                        
                        # Fill NaN week counts with "0 = 0 + 0"
                        week_cols = [c for c in date_stats_df.columns if c.startswith('Week ')]
                        date_stats_df[week_cols] = date_stats_df[week_cols].fillna("0 = 0 + 0")
                        
                        # Sort columns properly
                        def sort_week_key(col_name):
                            try:
                                # Handle "Week 1 & 2"
                                if "Week 1 & 2" in col_name:
                                    return 1
                                num_part = col_name.split('Week ')[1].split(' (')[0]
                                return int(num_part)
                            except:
                                return 999
                        
                        sorted_week_cols = sorted(week_cols, key=sort_week_key)
                        
                        # Reorder date_stats_df
                        base_cols = [c for c in date_stats_df.columns if c not in week_cols]
                        date_stats_df = date_stats_df[base_cols + sorted_week_cols]
                        
                        summary_df = pd.merge(summary_df, date_stats_df, on='Student Name', how='left')

                    except Exception as e:
                        st.warning(f"Could not generate summary sheet: {e}")

                    # --- Auto-Save Independent Files ---
                    try:
                        # 1. Main Detailed Results
                        with pd.ExcelWriter(final_filename, engine='xlsxwriter') as writer:
                            result_df.to_excel(writer, index=False, sheet_name='Detailed Results')
                            # Auto-adjust columns
                            worksheet = writer.sheets['Detailed Results']
                            for i, col in enumerate(result_df.columns):
                                max_len = max(
                                    result_df[col].astype(str).map(len).max(),
                                    len(col)
                                ) + 2
                                worksheet.set_column(i, i, min(max_len, 50)) # Cap at 50 width
                        
                        # 2. Student Summary
                        if not summary_df.empty:
                            with pd.ExcelWriter(summary_filename, engine='xlsxwriter') as writer:
                                summary_df.to_excel(writer, index=False, sheet_name='Student Summary')
                                # Auto-adjust columns for Summary
                                worksheet = writer.sheets['Student Summary']
                                for i, col in enumerate(summary_df.columns):
                                    max_len = max(
                                        summary_df[col].astype(str).map(len).max(),
                                        len(col)
                                    ) + 2
                                    worksheet.set_column(i, i, min(max_len, 40))
                                
                        if hasattr(st, 'toast'):
                            st.toast(f"Saved results to project folder!", icon="💾")
                        else:
                            st.success(f"💾 Saved results to project folder!")
                    except Exception as e:
                        st.warning(f"Could not save local files: {e}")
                    
                    # --- Email Delivery (Multi-Attachment) ---
                    if sender_email and sender_password and recipient_email:
                        with st.spinner("📧 Sending result email..."):
                            email_subject = "Evaluation Completed – Your Result Files"
                            email_body = """
                            <p>Hello,</p>
                            <p>Congratulations! 🎉 You have successfully completed your task.</p>
                            <p>Please find attached:</p>
                            <ul>
                                <li><b>final_results.xlsx</b>: Detailed evaluation data.</li>
                                <li><b>student_summary.xlsx</b>: Aggregated student performance.</li>
                            </ul>
                            <br>
                            <p><i>Best regards,<br>Automated Project Evaluator</i></p>
                            """
                            
                            attachments = [final_filename]
                            if not summary_df.empty:
                                attachments.append(summary_filename)
                                
                            success, message = send_email_with_attachment(
                                sender_email, sender_password, recipient_email, 
                                email_subject, email_body, attachments, smtp_server, smtp_port
                            )
                            
                            if success:
                                save_email_history(recipient_email)
                                st.markdown(f"""
                                <div class="success-email">
                                    <h3>🚀 Email Sent Verification</h3>
                                    <p>The result files have been successfully emailed to <b>{recipient_email}</b>.</p>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.error(f"❌ Failed to send email: {message}")
                    elif not (sender_email and sender_password):
                        st.warning("⚠️ Email not sent: Please configure Sender Email & App Password in the sidebar.")
                    
                    # --- Downloads ---
                    c_d1, c_d2 = st.columns(2)
                    
                    # Download 1: Final Results
                    buffer = BytesIO()
                    engine = 'xlsxwriter'
                    try:
                        import xlsxwriter
                    except ImportError:
                        engine = 'openpyxl'
                    
                    with pd.ExcelWriter(buffer, engine=engine) as writer:
                        result_df.to_excel(writer, index=False, sheet_name='Detailed Results')
                        # Auto-adjust columns in Download buffer too
                        if engine == 'xlsxwriter':
                             worksheet = writer.sheets['Detailed Results']
                             for i, col in enumerate(result_df.columns):
                                max_len = max(result_df[col].astype(str).map(len).max(), len(col)) + 2
                                worksheet.set_column(i, i, min(max_len, 50))
                        
                    c_d1.download_button(
                        label="📥 Download Detailed Results",
                        data=buffer.getvalue(),
                        file_name="final_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Download 2: Summary
                    if not summary_df.empty:
                        buffer_sum = BytesIO()
                        with pd.ExcelWriter(buffer_sum, engine=engine) as writer:
                            summary_df.to_excel(writer, index=False, sheet_name='Student Summary')
                            # Auto-adjust columns in Download buffer too
                            if engine == 'xlsxwriter':
                                 worksheet = writer.sheets['Student Summary']
                                 for i, col in enumerate(summary_df.columns):
                                     max_len = max(summary_df[col].astype(str).map(len).max(), len(col)) + 2
                                     worksheet.set_column(i, i, min(max_len, 40))
                            
                        c_d2.download_button(
                            label="📊 Download Student Summary",
                            data=buffer_sum.getvalue(),
                            file_name="student_summary.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    with st.expander("🔍 View Results"):
                        st.dataframe(result_df)

    except Exception as e:
        st.error(f"Error during processing: {e}")
        # Show partial results if available
        if 'result_df' in locals():
             st.download_button("Download Partial Results", result_df.to_csv().encode('utf-8'), "partial_results.csv")
elif uploaded_file and not recipient_email:
    st.info("ℹ️ Please enter an email address to proceed with evaluation and delivery.")

# Footer
st.markdown("---")
st.caption("-BY SHUBHAM SHARMA")

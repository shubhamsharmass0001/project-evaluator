import streamlit as st
import pandas as pd
import time
import concurrent.futures
from io import BytesIO
from evaluator import process_single_row

# Page Config
st.set_page_config(
    page_title="Project Evaluator",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Premium" look
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: center;
    }
    .stProgress > div > div > div > div {
        background-color: #00FF00;
    }
</style>
""", unsafe_allow_html=True)

# Application Title
st.title("🎓 Automated Project Evaluator")
st.markdown("Upload your student submissions to validate Coursera certificates and LinkedIn posts instantly.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    max_workers = st.slider("Parallel Threads", min_value=1, max_value=20, value=5, help="Higher = Faster, but risk of rate limits.")
    anti_scraping = st.checkbox("Anti-Scraping Mode", value=True, help="Adds delays to avoid LinkedIn 429 errors.")
    st.info("ℹ️ **Anti-Scraping Mode** is recommended for LinkedIn validation.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload Input File (Excel/CSV)", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    try:
        # Load Data
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
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
            if st.button("🚀 Start Evaluation", type="primary"):
                
                # Progress Containers
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Metrics Placeholder
                col1, col2, col3 = st.columns(3)
                m1 = col1.empty()
                m2 = col2.empty()
                m3 = col3.empty()
                
                # Processing Logic
                results = []
                total = len(df)
                
                # Convert to list of dicts for processing
                rows = df.to_dict('records')
                
                # Execute
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    full_futures = {executor.submit(process_single_row, row): row for row in rows}
                    
                    completed = 0
                    valid_coursera = 0
                    valid_linkedin = 0
                    
                    for future in concurrent.futures.as_completed(full_futures):
                        res = future.result()
                        results.append(res)
                        completed += 1
                        
                        # Update Metrics
                        if res.get('Coursera Valid'): valid_coursera += 1
                        if res.get('LinkedIn Valid'): valid_linkedin += 1
                        
                        # Update UI (throttle updates slightly for performance)
                        if completed % 2 == 0 or completed == total:
                            pct = completed / total
                            progress_bar.progress(pct)
                            status_text.text(f"Processing... {completed}/{total}")
                            
                            m1.metric("Processed", f"{completed}/{total}")
                            m2.metric("Coursera Valid", f"{valid_coursera}")
                            m3.metric("LinkedIn Valid", f"{valid_linkedin}")
                            
                        # Anti-Scraping Delay (simulated here if needed, but evaluator handles it mostly)
                        if anti_scraping:
                            time.sleep(0.1) 

                # Completion
                st.balloons()
                status_text.success("✅ Processing Complete!")
                
                # Result DataFrame
                result_df = pd.DataFrame(results)
                
                # --- Auto-Save to Disk (for User convenience) ---
                try:
                    result_df.to_excel("final_results.xlsx", index=False)
                    if hasattr(st, 'toast'):
                        st.toast("Saved final_results.xlsx to project folder!", icon="💾")
                    else:
                        st.success("💾 Saved final_results.xlsx to project folder!")
                except Exception as e:
                    st.warning(f"Could not save local file: {e}")
                
                # Download Button
                buffer = BytesIO()
                # Default to xlsxwriter, fallback to openpyxl if needed
                engine = 'xlsxwriter'
                try:
                    import xlsxwriter
                except ImportError:
                    engine = 'openpyxl'

                with pd.ExcelWriter(buffer, engine=engine) as writer:
                    result_df.to_excel(writer, index=False, sheet_name='Results')
                    
                st.download_button(
                    label="📥 Download Final Results",
                    data=buffer.getvalue(),
                    file_name="final_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                with st.expander("🔍 View Results"):
                    st.dataframe(result_df)

    except Exception as e:
        st.error(f"Error during processing: {e}")
        # Show partial results if available
        if 'result_df' in locals():
             st.download_button("Download Partial Results", result_df.to_csv().encode('utf-8'), "partial_results.csv")

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit & Python")

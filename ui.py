import streamlit as st
import requests
import time
import json
import pandas as pd
import plotly.express as px
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="GitHub Critic",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define API URLs
API_BASE_URL = "https://github-critic-fastapi.onrender.com/api"
REPO_STRUCTURE_URL = f"{API_BASE_URL}/repositories/structure"
AUTO_ROAST_URL = f"{API_BASE_URL}/repositories/auto-roast"
DIRECTORY_EXPLORE_URL = f"{API_BASE_URL}/repositories/explore"
DIRECTORY_SIZES_URL = f"{API_BASE_URL}/repositories/directory-sizes"

# Display API settings at the top for debugging
with st.sidebar:
    st.write(f"API Base URL: {API_BASE_URL}")
    if st.checkbox("Debug Mode"):
        st.session_state.debug_mode = True
    else:
        st.session_state.debug_mode = False

# Add custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1rem 0;
    }
    .critique-box {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 20px;
        margin-top: 10px;
        border-left: 5px solid #6c757d;
        color: #212529;
    }
    .brutal {
        border-left: 5px solid #dc3545;
    }
    .constructive {
        border-left: 5px solid #28a745;
    }
    .educational {
        border-left: 5px solid #17a2b8;
    }
    .funny {
        border-left: 5px solid #ffc107;
    }
    .security {
        border-left: 5px solid #6f42c1;
    }
    .suggestion-box {
        background-color: #e9f7ef;
        border-radius: 5px;
        padding: 20px;
        margin-top: 10px;
        border-left: 5px solid #28a745;
    }
    .summary-box {
        background-color: #e2f0fb;
        border-radius: 5px;
        padding: 20px;
        margin-top: 10px;
        border-left: 5px solid #007bff;
    }
    .stFileUploader > div > button {
        width: 100%;
    }
    .log-entry {
        margin-bottom: 15px;
        padding: 10px;
        border-radius: 5px;
        background-color: #f8f9fa;
        border-left: 5px solid #6c757d;
    }
    .log-error {
        border-left: 5px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("GitHub Critic - powered by EdenAI")
st.markdown("Analyze GitHub repositories and get Claude's code critiques.")

# Initialize session state
if 'job_id' not in st.session_state:
    st.session_state.job_id = None
if 'repo_url' not in st.session_state:
    st.session_state.repo_url = ""
if 'repo_status' not in st.session_state:
    st.session_state.repo_status = None
if 'roast_status' not in st.session_state:
    st.session_state.roast_status = None
if 'roast_results' not in st.session_state:
    st.session_state.roast_results = None
if 'current_path' not in st.session_state:
    st.session_state.current_path = ""
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0
if 'directory_contents' not in st.session_state:
    st.session_state.directory_contents = None
if 'debug_mode' not in st.session_state:
    st.session_state.debug_mode = False
if 'request_logs' not in st.session_state:
    st.session_state.request_logs = []

# Function to log API requests and responses
def log_api_request(method, url, payload=None, response=None, error=None):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": method,
        "url": url,
        "payload": payload,
        "status_code": response.status_code if response else None,
        "response": response.json() if response and response.ok else None,
        "error": str(error) if error else None,
        "response_text": response.text if response else None
    }
    logger.info(f"API Request: {log_entry}")
    st.session_state.request_logs.append(log_entry)
    # Keep only last 20 logs
    if len(st.session_state.request_logs) > 20:
        st.session_state.request_logs = st.session_state.request_logs[-20:]

# Functions for API interaction
def analyze_repository(repo_url):
    """Start repository analysis and return job_id"""
    try:
        logger.info(f"Analyzing repository: {repo_url}")
        payload = {"repo_url": repo_url}
        
        response = requests.post(
            REPO_STRUCTURE_URL,
            json=payload,
            timeout=30
        )
        
        log_api_request("POST", REPO_STRUCTURE_URL, payload, response)
        
        # Check response status
        if response.ok:
            response_data = response.json()
            job_id = response_data.get("job_id")
            logger.info(f"Successfully created job with ID: {job_id}")
            return job_id
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error analyzing repository: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_api_request("POST", REPO_STRUCTURE_URL, payload, error=e)
        logger.error(f"Request error: {str(e)}")
        st.error(f"Error analyzing repository: {str(e)}")
        return None

def check_repo_status(job_id):
    """Check repository analysis status"""
    try:
        url = f"{API_BASE_URL}/repositories/structure/{job_id}"
        logger.info(f"Checking status for job: {job_id} at URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        log_api_request("GET", url, response=response)
        
        if response.ok:
            return response.json()
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            return {"status": "failed", "error": f"{response.status_code}: {response.text}"}
            
    except requests.exceptions.RequestException as e:
        log_api_request("GET", url, error=e)
        logger.error(f"Request error: {str(e)}")
        return {"status": "failed", "error": str(e)}

def explore_directory(job_id, path=""):
    """Get directory contents"""
    try:
        payload = {"job_id": job_id, "path": path}
        logger.info(f"Exploring directory: job_id={job_id}, path={path}")
        
        response = requests.post(
            DIRECTORY_EXPLORE_URL,
            json=payload,
            timeout=10
        )
        
        log_api_request("POST", DIRECTORY_EXPLORE_URL, payload, response)
        
        if response.ok:
            return response.json()
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error exploring directory: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_api_request("POST", DIRECTORY_EXPLORE_URL, payload, error=e)
        logger.error(f"Request error: {str(e)}")
        st.error(f"Error exploring directory: {str(e)}")
        return None

def get_directory_sizes(job_id, path=""):
    """Get directory sizes"""
    try:
        payload = {"job_id": job_id, "path": path}
        
        response = requests.post(
            DIRECTORY_SIZES_URL,
            json=payload,
            timeout=10
        )
        
        log_api_request("POST", DIRECTORY_SIZES_URL, payload, response)
        
        if response.ok:
            return response.json()
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error getting directory sizes: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_api_request("POST", DIRECTORY_SIZES_URL, payload, error=e)
        logger.error(f"Request error: {str(e)}")
        st.error(f"Error getting directory sizes: {str(e)}")
        return None

def auto_roast_repository(job_id, style="brutal", file_count=2, extensions=None, 
                         directories=None, description=None, suggestions="none"):
    """Auto-roast selected files from repository"""
    try:
        payload = {
            "job_id": job_id,
            "style": style,
            "file_count": file_count
        }
        
        # Add optional parameters if provided
        if extensions:
            payload["extensions"] = extensions
        if directories:
            payload["directories"] = directories
        if description:
            payload["description"] = description
        if suggestions:
            payload["suggestions"] = suggestions
            
        logger.info(f"Auto-roasting repository: {payload}")
        
        response = requests.post(
            AUTO_ROAST_URL,
            json=payload,
            timeout=300  # Longer timeout for LLM processing
        )
        
        log_api_request("POST", AUTO_ROAST_URL, payload, response)
        
        if response.ok:
            return response.json()
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error roasting repository: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_api_request("POST", AUTO_ROAST_URL, payload, error=e)
        logger.error(f"Request error: {str(e)}")
        st.error(f"Error roasting repository: {str(e)}")
        return None

def check_roast_results(job_id):
    """Check auto-roast results"""
    try:
        url = f"{API_BASE_URL}/repositories/auto-roast/{job_id}"
        
        response = requests.get(url, timeout=10)
        
        log_api_request("GET", url, response=response)
        
        if response.ok:
            return response.json()
        else:
            logger.error(f"Error response: {response.status_code} - {response.text}")
            st.error(f"Error checking roast results: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        log_api_request("GET", url, error=e)
        logger.error(f"Request error: {str(e)}")
        st.error(f"Error checking roast results: {str(e)}")
        return None

# Sidebar for repository input
with st.sidebar:
    st.header("Repository")
    repo_url = st.text_input("GitHub Repository URL", 
                            placeholder="https://github.com/username/repository")
    
    if st.button("Analyze Repository", use_container_width=True):
        if repo_url:
            with st.spinner("Analyzing repository... This may take a moment"):
                st.session_state.repo_url = repo_url
                
                # First attempt to create a job
                job_id = analyze_repository(repo_url)
                
                if job_id:
                    st.success(f"Analysis started! Job ID: {job_id}")
                    st.session_state.job_id = job_id
                    st.session_state.repo_status = "pending"
                    
                    # Wait a significant amount of time before checking status
                    # This gives the backend time to fully process the job
                    time.sleep(8)  # Increased from previous values
                    
                    # Retry mechanism for checking status with exponential backoff
                    retry_count = 0
                    max_retries = 4
                    success = False
                    
                    while retry_count < max_retries and not success:
                        try:
                            retry_count += 1
                            status_url = f"{API_BASE_URL}/repositories/structure/{job_id}"
                            
                            st.info(f"Checking job status (attempt {retry_count}/{max_retries})...")
                            
                            initial_status_response = requests.get(status_url, timeout=15)
                            
                            if initial_status_response.ok:
                                initial_status = initial_status_response.json()
                                st.session_state.repo_status = initial_status.get("status", "pending")
                                success = True
                                st.session_state.directory_contents = explore_directory(st.session_state.job_id)
                                st.success("Repository status check successful")
                                st.rerun()
                            else:
                                wait_time = 2 ** retry_count  # Exponential backoff
                                st.warning(f"Status check failed. Retrying in {wait_time} seconds...")
                                time.sleep(wait_time)
                        except Exception as e:
                            wait_time = 2 ** retry_count
                            st.warning(f"Error checking status: {str(e)}. Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                    
                    if not success:
                        st.error("Failed to verify job status after multiple attempts. Try clicking Analyze Repository again.")
                else:
                    st.error("Failed to start repository analysis. Check the logs for details.")
        else:
            st.warning("Please enter a GitHub repository URL")
    
    # Display repository status
    if st.session_state.job_id and st.session_state.repo_status:
        st.subheader("Repository Status")
        status_placeholder = st.empty()
        
        if st.session_state.repo_status != "completed":
            # Use the status_placeholder to show status updates
            polling_count = 0
            max_polling_attempts = 30  # Prevent infinite loops
            
            while (st.session_state.repo_status not in ["completed", "failed"] 
                  and polling_count < max_polling_attempts):
                
                polling_count += 1
                
                with status_placeholder:
                    st.info(f"Status: {st.session_state.repo_status} (Polling attempt: {polling_count})")
                    
                status_response = check_repo_status(st.session_state.job_id)
                
                if status_response:
                    st.session_state.repo_status = status_response.get("status")
                    
                    if st.session_state.debug_mode:
                        st.write("Status Response:")
                        st.json(status_response)
                    
                    if st.session_state.repo_status == "completed":
                        with status_placeholder:
                            st.success("Repository processed successfully!")
                        st.session_state.directory_contents = explore_directory(st.session_state.job_id)
                        st.rerun()
                    elif st.session_state.repo_status == "failed":
                        with status_placeholder:
                            st.error(f"Failed: {status_response.get('error', 'Unknown error')}")
                else:
                    with status_placeholder:
                        st.error("Failed to check repository status. See logs for details.")
                    break
                
                # Sleep for 2 seconds before next polling
                time.sleep(2)
                
            # If we've reached max polling attempts
            if polling_count >= max_polling_attempts and st.session_state.repo_status != "completed":
                with status_placeholder:
                    st.warning(f"Reached maximum polling attempts ({max_polling_attempts}). Status: {st.session_state.repo_status}")
                    if st.button("Retry Status Check"):
                        st.rerun()
        else:
            with status_placeholder:
                st.success("Repository processed successfully!")
    
    # Auto-Roast Configuration (only shown when repo is ready)
    if st.session_state.repo_status == "completed":
        st.subheader("Auto-Roast Configuration")
        
        style = st.selectbox(
            "Critique Style",
            options=["brutal", "constructive", "educational", "funny", "security"],
            format_func=lambda x: x.capitalize()
        )
        
        file_count = st.slider("Number of Files", min_value=1, max_value=5, value=2)
        
        suggestions = st.selectbox(
            "Improvement Suggestions",
            options=["none", "basic", "detailed"],
            format_func=lambda x: x.capitalize()
        )
        
        # Extension selection
        with st.expander("File Extensions"):
            py_files = st.checkbox("Python (.py)", value=True)
            js_files = st.checkbox("JavaScript (.js, .jsx)")
            ts_files = st.checkbox("TypeScript (.ts, .tsx)")
            java_files = st.checkbox("Java (.java)")
            other_ext = st.text_input("Other extensions (comma separated)", 
                                    placeholder="e.g. .rb,.go,.php")
            
            # Build extensions list
            extensions = []
            if py_files:
                extensions.append(".py")
            if js_files:
                extensions.extend([".js", ".jsx"])
            if ts_files:
                extensions.extend([".ts", ".tsx"])
            if java_files:
                extensions.append(".java")
            if other_ext:
                extensions.extend([ext.strip() for ext in other_ext.split(",") if ext.strip()])
        
        # Additional options
        description = st.text_area("Focus Description", 
                                placeholder="E.g., error handling, performance, security issues")
        
        if st.button("Roast Code!", use_container_width=True):
            with st.spinner("Roasting code... This may take a minute"):
                st.session_state.roast_status = "pending"
                roast_results = auto_roast_repository(
                    st.session_state.job_id,
                    style=style,
                    file_count=file_count,
                    extensions=extensions if extensions else None,
                    description=description if description else None,
                    suggestions=suggestions
                )
                
                if roast_results:
                    st.session_state.roast_results = roast_results
                    st.session_state.roast_status = "completed"
                    st.success("Code roasted successfully!")
                    st.session_state.active_tab = 2  # Switch to Results tab
                    st.rerun()
                else:
                    st.error("Failed to roast code. Check the logs for details.")

# Debug logs section
if st.session_state.debug_mode:
    st.header("Debug Information")
    st.write(f"Current Job ID: {st.session_state.job_id}")
    st.write(f"Repository Status: {st.session_state.repo_status}")
    
    # Display request logs
    st.subheader("API Request Logs")
    if st.session_state.request_logs:
        for log in reversed(st.session_state.request_logs):
            log_class = "log-entry"
            if log.get('error') or (log.get('status_code') and log.get('status_code') >= 400):
                log_class += " log-error"
                
            st.markdown(f"""
            <div class="{log_class}">
                <strong>{log['timestamp']}</strong> - {log['method']} {log['url']}<br/>
                Status Code: {log['status_code'] or 'N/A'}
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if log['payload']:
                    st.write("Request Payload:")
                    st.json(log['payload'])
                
            with col2:
                if log['response']:
                    st.write("Response:")
                    st.json(log['response'])
                elif log['response_text']:
                    st.write("Response Text:")
                    st.code(log['response_text'])
                    
            if log['error']:
                st.error(log['error'])
                
            st.markdown("---")
    else:
        st.write("No logs recorded yet")

# Main content area with tabs
tab1, tab2, tab3 = st.tabs(["Repository Info", "File Explorer", "Roast Results"])

with tab1:
    if st.session_state.repo_status == "completed":
        st.header(f"Repository: {st.session_state.repo_url.split('/')[-1]}")
        
        # Get directory sizes for visualization
        dir_sizes = get_directory_sizes(st.session_state.job_id)
        
        if dir_sizes and "directories" in dir_sizes:
            # Create two columns for stats and visualization
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Repository Statistics")
                # Total directories
                st.metric("Total Directories", dir_sizes.get("total_count", 0))
                
                # Total files
                total_files = sum(d.get("total_files", 0) for d in dir_sizes.get("directories", []))
                st.metric("Total Files", total_files)
                
                # Code files
                total_code = sum(d.get("code_files", 0) for d in dir_sizes.get("directories", []))
                st.metric("Code Files", total_code)
                
                # Largest directory
                if dir_sizes.get("directories"):
                    largest_dir = max(dir_sizes.get("directories", []), 
                                    key=lambda x: x.get("total_files", 0))
                    st.metric("Largest Directory", 
                            largest_dir.get("name"), 
                            f"{largest_dir.get('total_files', 0)} files")
            
            with col2:
                st.subheader("Directory Size Distribution")
                
                # Create DataFrame for visualization
                df = pd.DataFrame([
                    {
                        "Directory": d.get("name"),
                        "Total Files": d.get("total_files", 0),
                        "Code Files": d.get("code_files", 0),
                        "Other Files": d.get("total_files", 0) - d.get("code_files", 0),
                        "Subdirectories": d.get("subdirectories", 0)
                    }
                    for d in dir_sizes.get("directories", [])
                ])
                
                if not df.empty:
                    # Sort by total files
                    df = df.sort_values("Total Files", ascending=False).head(10)
                    
                    # Create bar chart
                    fig = px.bar(
                        df, 
                        x="Directory", 
                        y=["Code Files", "Other Files"],
                        title="Top 10 Directories by Size",
                        labels={"value": "Number of Files", "variable": "File Type"},
                        color_discrete_map={"Code Files": "#1f77b4", "Other Files": "#aec7e8"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Create a table view
                    st.dataframe(df, use_container_width=True)
        else:
            st.info("Directory statistics not available.")
    else:
        st.info("Enter a GitHub repository URL and click 'Analyze Repository' to get started.")

with tab2:
    if st.session_state.repo_status == "completed":
        st.header("File Explorer")
        
        # Breadcrumb navigation
        if st.session_state.current_path:
            path_parts = st.session_state.current_path.split('/')
            breadcrumb = " / ".join([
                f"[{part}](.)" if i == len(path_parts)-1 
                else f"[{part}](exec:set_path:{'/'.join(path_parts[:i+1])})"
                for i, part in enumerate(path_parts)
            ])
            breadcrumb = f"[root](exec:set_path:) / {breadcrumb}"
            
            # Add Back button when in a subdirectory
            parent_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ""
            if st.button("⬅️ Back to parent directory"):
                st.session_state.current_path = parent_path
                st.session_state.directory_contents = explore_directory(
                    st.session_state.job_id, 
                    parent_path
                )
                st.rerun()
        else:
            breadcrumb = "[root](.)"
            
        st.markdown(breadcrumb)
        
        # Get directory contents
        if st.session_state.directory_contents is None:
            st.session_state.directory_contents = explore_directory(
                st.session_state.job_id, 
                st.session_state.current_path
            )
        
        if st.session_state.directory_contents:
            contents = st.session_state.directory_contents
            
            # Display directories
            if contents.get("directories"):
                st.subheader("Directories")
                for directory in contents.get("directories", []):
                    dir_name = directory.get("name")
                    file_count = directory.get("file_count", 0)
                    path = directory.get("path")
                    
                    if st.button(f"📁 {dir_name} ({file_count} files)", key=f"dir_{path}"):
                        st.session_state.current_path = path
                        st.session_state.directory_contents = explore_directory(
                            st.session_state.job_id, 
                            path
                        )
                        st.rerun()
            
            # Display files
            if contents.get("files"):
                st.subheader("Files")
                # Group files by extension
                files_by_ext = {}
                for file in contents.get("files", []):
                    ext = file.get("extension", "").lower() or "other"
                    if ext not in files_by_ext:
                        files_by_ext[ext] = []
                    files_by_ext[ext].append(file)
                
                # Display files by extension group
                for ext, files in files_by_ext.items():
                    with st.expander(f"{ext} files ({len(files)})"):
                        for file in files:
                            file_name = file.get("name")
                            file_size = file.get("size", 0)
                            size_str = f"{file_size / 1024:.1f} KB" if file_size >= 1024 else f"{file_size} bytes"
                            st.text(f"📄 {file_name} ({size_str})")
            
            if not contents.get("directories") and not contents.get("files"):
                st.info("This directory is empty.")
        else:
            st.warning("Could not load directory contents.")
    else:
        st.info("Enter a GitHub repository URL and click 'Analyze Repository' to explore files.")

with tab3:
    if st.session_state.roast_status == "completed" and st.session_state.roast_results:
        st.header("Code Critique Results")
        
        results = st.session_state.roast_results
        style = results.get("parameters", {}).get("style", "brutal")
        
        # Display summary if available
        if "summary" in results:
            st.subheader("Repository-Wide Issues")
            st.markdown(f"""
            <div class="summary-box {style}" style="color: #333;">
                {results["summary"]}
            </div>
            """, unsafe_allow_html=True)
        
        # Display file critiques
        st.subheader("File Critiques")
        
        for file_data in results.get("roasted_files", []):
            if len(file_data) >= 2:  # Ensure we have at least the file path and critique
                file_path = file_data[0]
                critique = file_data[1]
                
                with st.expander(f"📄 {file_path}", expanded=True):
                    # Display the critique
                    st.markdown(f"""
                    <div class="critique-box {style}" style="color: #333;">
                        <h4>Critique ({style.capitalize()} Style)</h4>
                        {critique}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Display suggestions if available
                    if len(file_data) >= 3:
                        suggestions = file_data[2]
                        st.markdown(f"""
                        <div class="suggestion-box">
                            <h4>Improvement Suggestions</h4>
                            {suggestions}
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Configure and run Auto-Roast to see results here.")

# Handle breadcrumb navigation
if 'root' in st.session_state and st.session_state.current_path:
    st.session_state.current_path = ""
    st.session_state.directory_contents = explore_directory(
        st.session_state.job_id, 
        ""
    )
    st.rerun()

# Set the active tab based on session state
# This has to be at the end because streamlit doesn't support direct tab switching
if st.session_state.active_tab == 0:
    pass  # Already on Repository Info tab
elif st.session_state.active_tab == 1:
    # JavaScript to click the "File Explorer" tab
    js = f"""
    <script>
        var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
        tabs[1].click();
    </script>
    """
    st.components.v1.html(js, height=0)
elif st.session_state.active_tab == 2:
    # JavaScript to click the "Roast Results" tab
    js = f"""
    <script>
        var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
        tabs[2].click();
    </script>
    """
    st.components.v1.html(js, height=0)

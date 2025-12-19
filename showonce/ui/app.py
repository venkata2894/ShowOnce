"""
ShowOnce - Streamlit Web Interface

Run with: streamlit run showonce/ui/app.py
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json
import base64

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from showonce.config import get_config
from showonce.models.workflow import Workflow
from showonce.models.actions import ActionSequence, ActionType
from showonce.generate.runner import ScriptRunner
from showonce.capture.recorder import RecordingSession
import threading
import time


# Page configuration
st.set_page_config(
    page_title="ShowOnce",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .workflow-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .step-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        background: #f8f9fa;
    }
    .action-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .confidence-high { background: #28a745; color: white; }
    .confidence-medium { background: #ffc107; color: black; }
    .confidence-low { background: #dc3545; color: white; }
</style>
""", unsafe_allow_html=True)


def get_workflows():
    """Get all workflows from the workflows directory."""
    config = get_config()
    workflows = []
    
    workflows_dir = config.paths.workflows_dir
    if workflows_dir.exists():
        for path in workflows_dir.iterdir():
            if path.is_dir() and (path / "workflow.json").exists():
                try:
                    wf = Workflow.load(path)
                    workflows.append({
                        "name": wf.name,
                        "description": wf.description,
                        "steps": wf.step_count,
                        "analyzed": wf.analyzed,
                        "created": wf.metadata.created_at,
                        "path": path
                    })
                except Exception as e:
                    st.error(f"Error loading {path.name}: {e}")
    
    return workflows




def render_recording_section():
    """Render the live recording interface."""
    if "recording_active" not in st.session_state:
        st.session_state.recording_active = False
    
    if not st.session_state.recording_active:
        st.write("Start a live recording session. Use your hotkey or enable Automatic Mode.")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Recording Name", placeholder="e.g. quick_test", key="rec_name")
        with col2:
            desc = st.text_input("Description (Optional)", placeholder="What are you recording?", key="rec_desc")
        
        auto_mode = st.toggle("🚀 Automatic Mode: Capture on every click", value=True, help="Automatically capture a step whenever you click outside this window.")
            
        if st.button("🔴 Start Recording", type="primary", width="stretch"):
            rec_name = name or f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            start_live_recording(rec_name, desc, auto_capture=auto_mode)
            st.rerun()
    else:
        st.success(f"🎥 Recording Active: **{st.session_state.recording_name}**")
        
        # Live Stats and Manual Capture
        col_stats, col_preview = st.columns([1, 1])
        
        session = st.session_state.recording_session
        
        with col_stats:
            st.metric("Steps Captured", session.workflow.step_count)
            if session.auto_capture:
                st.info("⚡ Automatic Mode is ON. Clicks on other windows are being captured.")
            
            if st.button("📸 Manual Capture", width="stretch"):
                session.request_capture()
                time.sleep(0.5)
                st.rerun()
            
            if st.button("⏹️ Finish & Save", type="primary", width="stretch"):
                stop_live_recording()
                st.rerun()
            
            st.button("🔄 Refresh Preview", width="stretch")

        with col_preview:
            st.subheader("Live Preview")
            if session.last_screenshot:
                st.image(session.last_screenshot, caption="Last Captured Step", width="stretch")
            else:
                st.info("No steps captured yet. Use your hotkey or click elsewhere to capture.")

def start_live_recording(name, desc, auto_capture=False):
    """Start the recorder in a background thread."""
    session = RecordingSession(name, desc, no_prompt=True, auto_capture=auto_capture)
    st.session_state.recording_session = session
    st.session_state.recording_active = True
    st.session_state.recording_name = name
    
    # Start in background thread
    thread = threading.Thread(target=session.start, daemon=True)
    thread.start()
    st.session_state.recording_thread = thread

def stop_live_recording():
    """Stop the recording session."""
    if "recording_session" in st.session_state:
        session = st.session_state.recording_session
        session.stop()
        st.session_state.recording_active = False
        # Give it a second to save
        time.sleep(1)
        
        if session.workflow.step_count > 0:
            st.success(f"Workflow '{st.session_state.recording_name}' saved with {session.workflow.step_count} steps!")
        else:
            st.warning(f"No steps captured for '{st.session_state.recording_name}'. Process stopped.")
        
        # Cleanup session state
        del st.session_state.recording_session
        if "recording_thread" in st.session_state:
            del st.session_state.recording_thread

def render_dashboard(workflows):
    """Render the main dashboard."""
    st.markdown('<p class="main-header">📊 Dashboard</p>', unsafe_allow_html=True)
    
    # Create New Workflow Section
    with st.expander("➕ Create New Workflow", expanded=False):
        with st.form("new_workflow_form"):
            new_name = st.text_input("Workflow Name", placeholder="e.g. login_test")
            new_desc = st.text_area("Description", placeholder="Describe what this workflow does...")
            auto_cap = st.checkbox("Automatic Mode: Capture on every click", value=False, help="Automatically capture a step whenever you click outside this window.")
            submit_new = st.form_submit_button("Create Workflow")
            
            if submit_new:
                if not new_name:
                    st.error("Workflow name is required")
                else:
                    create_workflow_ui(new_name, new_desc)
    
    # 🔴 Live Recording Section
    with st.expander("🔴 Live Recording", expanded=st.session_state.get("recording_active", False)):
        render_recording_section()
    
    st.divider()
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(workflows)
    analyzed = sum(1 for w in workflows if w["analyzed"])
    total_steps = sum(w["steps"] for w in workflows)
    
    with col1:
        st.metric("Total Workflows", total)
    with col2:
        st.metric("Analyzed", analyzed)
    with col3:
        st.metric("Pending Analysis", total - analyzed)
    with col4:
        st.metric("Total Steps", total_steps)
    
    st.divider()
    
    # Workflow cards
    st.subheader("All Workflows")
    
    if not workflows:
        st.info("👋 Welcome! Start by creating a workflow above or recording one using the CLI:")
        st.code("python -m showonce.cli record --name my_workflow", language="bash")
        return
    
    # Display in grid
    cols = st.columns(3)
    for i, wf in enumerate(workflows):
        with cols[i % 3]:
            with st.container():
                status = "✅ Analyzed" if wf["analyzed"] else "⏳ Pending"
                st.markdown(f"""
                <div class="workflow-card">
                    <h4>{wf['name']}</h4>
                    <p>{wf['description'] or 'No description'}</p>
                    <p><strong>{wf['steps']}</strong> steps | {status}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"View Details", key=f"view_{wf['name']}"):
                    st.session_state.selected_workflow = wf['name']
                    st.rerun()

def create_workflow_ui(name, description):
    """Create a new workflow directory and JSON."""
    config = get_config()
    safe_name = "".join([c if c.isalnum() or c in "-_" else "_" for c in name])
    wf_path = config.paths.workflows_dir / safe_name
    
    if wf_path.exists():
        st.error(f"Workflow '{safe_name}' already exists")
        return
    
    try:
        wf_path.mkdir(parents=True, exist_ok=True)
        wf = Workflow(name=name, description=description)
        wf.path = wf_path
        wf.save(wf_path)
        st.success(f"Workflow '{name}' created successfully!")
        
        # Set session state to jump to this workflow
        st.session_state.selected_workflow = name
        st.session_state.page = "🔍 Workflow Viewer"
        st.rerun()
    except Exception as e:
        st.error(f"Failed to create workflow: {e}")

def render_workflow_viewer(workflow_name, workflows):
    """Render detailed workflow view."""
    st.markdown(f'<p class="main-header">🔍 Workflow: {workflow_name}</p>', unsafe_allow_html=True)
    
    # Find workflow
    workflow_info = next((w for w in workflows if w["name"] == workflow_name), None)
    if not workflow_info:
        st.error("Workflow not found")
        return
    
    # Load workflow
    try:
        workflow = Workflow.load(workflow_info["path"])
    except Exception as e:
        st.error(f"Error loading workflow: {e}")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📸 Steps & Upload", "🤖 Analysis", "⚡ Generated Code", "📝 Info"])
    
    with tab1:
        render_steps_tab(workflow)
    
    with tab2:
        render_analysis_tab(workflow, workflow_info)
        
    with tab3:
        render_generated_code_tab(workflow_name)
    
    with tab4:
        render_info_tab(workflow)

def render_steps_tab(workflow):
    """Render the steps tab with screenshots and upload functionality."""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"Captured Steps ({workflow.step_count})")
        if workflow.step_count == 0:
            st.info("No steps captured yet.")
        else:
            for step in workflow.steps:
                with st.expander(f"Step {step.step_number}: {step.description or 'No description'}", expanded=False):
                    s_col1, s_col2 = st.columns([3, 1])
                    with s_col1:
                        screenshot_data = step.get_screenshot_data()
                        if screenshot_data:
                            st.image(screenshot_data, width="stretch")
                        else:
                            st.warning("Screenshot not available")
                    with s_col2:
                        st.caption(f"Time: {step.timestamp.strftime('%H:%M:%S')}")
                        if step.metadata and step.metadata.window_title:
                            st.caption(f"App: {step.metadata.window_title[:20]}...")
    
    with col2:
        st.subheader("📤 Upload Screenshots")
        uploaded_files = st.file_uploader("Choose images...", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        
        if uploaded_files:
            if st.button("Add to Workflow"):
                with st.spinner("Processing uploads..."):
                    for uploaded_file in uploaded_files:
                        img_bytes = uploaded_file.read()
                        workflow.add_step(
                            description=uploaded_file.name,
                            screenshot_bytes=img_bytes
                        )
                    workflow.save(workflow.path)
                    st.success(f"Added {len(uploaded_files)} steps!")
                    st.rerun()

def render_generated_code_tab(workflow_name):
    """Show existing generated scripts for this workflow."""
    config = get_config()
    st.subheader("Generated Scripts")
    
    scripts = list(config.paths.output_dir.glob(f"{workflow_name}_*.py"))
    
    if not scripts:
        st.info("No scripts generated yet. Go to the 'Generate Code' page to create one.")
        if st.button("Go to Generator"):
            st.session_state.page = "⚡ Generate Code"
            st.rerun()
    else:
        for script_path in scripts:
            framework = script_path.stem.split('_')[-1]
            with st.expander(f"📜 {script_path.name} ({framework})"):
                with open(script_path, "r") as f:
                    code = f.read()
                st.code(code, language="python")
                st.download_button(
                    label="Download Script",
                    data=code,
                    file_name=script_path.name,
                    key=f"dl_{script_path.name}"
                )
                
                st.divider()
                render_script_runner(script_path)

def render_script_runner(script_path):
    """Render interface to run a script."""
    st.markdown("### 🚀 Run Automation")
    
    runner = ScriptRunner(script_path)
    info = runner.get_script_info()
    
    if "error" in info:
        st.error(f"Error parsing script info: {info['error']}")
        return
        
    params = {}
    if info.get("parameters"):
        st.write("This script requires parameters:")
        for param in info["parameters"]:
            params[param] = st.text_input(f"Value for `{param}`", key=f"param_{script_path.name}_{param}")
            
    col1, col2 = st.columns([1, 4])
    with col1:
        run_btn = st.button("▶️ Run", key=f"run_btn_{script_path.name}", type="primary")
    
    if run_btn:
        with st.status("Executing automation...", expanded=True) as status:
            st.write("Checking dependencies...")
            all_installed, missing = runner.check_dependencies()
            if not all_installed:
                st.error(f"Missing dependencies: {', '.join(missing)}")
                st.info("Run `pip install " + " ".join(missing) + "` in your terminal.")
                return
                
            st.write("Starting browser...")
            result = runner.run(params=params)
            
            if result["success"]:
                status.update(label="✅ Execution Successful!", state="complete")
                st.success("The automation finished successfully.")
            else:
                status.update(label="❌ Execution Failed", state="error")
                st.error(f"Exit code: {result['return_code']}")
            
            if result["output"]:
                with st.expander("Output Logs", expanded=True):
                    st.code(result["output"])
            
            if result["error"]:
                with st.expander("Error Logs", expanded=True):
                    st.code(result["error"])

def render_analysis_tab(workflow, workflow_info):
    """Render the analysis tab."""
    st.subheader("AI Analysis")
    
    if not workflow_info["analyzed"]:
        st.warning("This workflow has not been analyzed yet.")
        
        config = get_config()
        if not config.analyze.api_key:
            st.error("⚠️ ANTHROPIC_API_KEY not configured. Set it in the Settings page.")
        else:
            if st.button("🔍 Analyze Now", type="primary"):
                analyze_workflow_ui(workflow)
    else:
        st.success("✅ Workflow has been analyzed")
        
        if st.button("🔄 Re-analyze"):
            analyze_workflow_ui(workflow)
        
        # Display existing analysis if possible (simplified for now as we don't store action sequence separately yet)
        st.info("View inferred actions by running re-analysis or checking generated code.")

def analyze_workflow_ui(workflow):
    """Run analysis with progress UI."""
    from showonce.analyze import ActionInferenceEngine
    
    with st.spinner("Analyzing workflow with Claude Vision..."):
        try:
            engine = ActionInferenceEngine()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total):
                progress_bar.progress(current / total)
                status_text.text(f"Analyzing transition {current}/{total}...")
            
            action_sequence = engine.analyze_workflow(workflow, progress_callback=update_progress)
            
            progress_bar.progress(1.0)
            status_text.text("Analysis complete!")
            
            st.success(f"✅ Inferred {len(action_sequence.actions)} actions")
            
            for action in action_sequence.actions:
                confidence = int(action.confidence * 100)
                badge_color = "green" if confidence >= 80 else "orange" if confidence >= 50 else "red"
                
                with st.expander(f"Step {action.sequence}: {action.action_type.value} ({confidence}%)"):
                    st.write(f"**Description:** {action.description}")
                    if action.target:
                        st.write(f"**Target:** {action.target.description}")
                        if action.target.selectors:
                            st.code(action.target.get_primary_selector().value)
            
            workflow.analyzed = True
            workflow.save(workflow.path)
            
        except Exception as e:
            st.error(f"Analysis failed: {e}")

def render_info_tab(workflow):
    """Render workflow info tab."""
    st.subheader("Workflow Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Name:**", workflow.name)
        st.write("**Description:**", workflow.description or "N/A")
        st.write("**Analyzed:**", "Yes" if workflow.analyzed else "No")
    with col2:
        st.write("**Steps:**", workflow.step_count)
        if workflow.metadata:
            st.write("**Created:**", workflow.metadata.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            st.write("**Path:**", str(workflow.path))

def render_generate_page(workflow_name, workflows):
    """Render the code generation page."""
    st.markdown('<p class="main-header">⚡ Generate Code</p>', unsafe_allow_html=True)
    
    if not workflow_name:
        st.info("Select a workflow from the sidebar to generate code.")
        return
    
    workflow_info = next((w for w in workflows if w["name"] == workflow_name), None)
    if not workflow_info:
        st.error("Workflow not found")
        return
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        framework = st.selectbox("Automation Framework", ["playwright", "selenium", "pyautogui"])
    with col2:
        headless = st.checkbox("Headless Mode", value=False)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_btn = st.button("Generate Script", type="primary", width="stretch")
    
    if generate_btn:
        generate_code_ui(workflow_name, workflow_info, framework, headless)

def generate_code_ui(workflow_name, workflow_info, framework, headless):
    """Generate code and show results."""
    from showonce.generate import get_generator
    from showonce.analyze import ActionInferenceEngine
    
    try:
        workflow = Workflow.load(workflow_info["path"])
        
        with st.status(f"Generating {framework} code...") as status:
            st.write("Analyzing transitions...")
            engine = ActionInferenceEngine()
            action_sequence = engine.analyze_workflow(workflow)
            
            st.write("Building script...")
            generator = get_generator(framework, headless=headless)
            code = generator.generate(action_sequence)
            
            status.update(label="Generation Complete!", state="complete")
        
        st.subheader(f"Generated Code ({framework})")
        st.code(code, language="python")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("Download Python Script", code, file_name=f"{workflow_name}_{framework}.py")
        with col2:
            config = get_config()
            output_path = config.paths.output_dir / f"{workflow_name}_{framework}.py"
            generator.save(code, output_path)
            st.success(f"Saved to {output_path}")
            
    except Exception as e:
        st.error(f"Failed to generate code: {e}")

def render_settings_page():
    """Render the settings page."""
    st.markdown('<p class="main-header">⚙️ Settings</p>', unsafe_allow_html=True)
    
    config = get_config()
    
    st.subheader("Anthropic API Key")
    current_key = config.analyze.api_key
    if current_key:
        st.success(f"Key configured: {current_key[:6]}...{current_key[-4:]}")
    else:
        st.error("API Key not set! AI analysis will not work.")
    
    new_key = st.text_input("Update API Key", type="password")
    if st.button("Save Key"):
        # This is a bit tricky since config is loaded from env/files.
        # We'll suggest updating the .env file.
        st.info("To save the key permanently, update your `.env` file.")
        if new_key:
            st.session_state.temp_api_key = new_key
            st.success("Key applied for this session!")
    
    st.divider()
    st.subheader("System Paths")
    st.write("**Workflows:**", str(config.paths.workflows_dir))
    st.write("**Generated Scripts:**", str(config.paths.output_dir))
    
    if st.button("Open Config Directory"):
        import os
        os.startfile(config.paths.base_dir)

def main():
    """Main application entry point."""
    if "selected_workflow" not in st.session_state:
        st.session_state.selected_workflow = None
    if "page" not in st.session_state:
        st.session_state.page = "📊 Dashboard"
    
    # Sidebar
    with st.sidebar:
        st.title("🎯 ShowOnce")
        st.caption("AI-Powered Automation Learning")
        st.divider()
        
        page = st.radio("Navigation", ["📊 Dashboard", "🔍 Workflow Viewer", "⚡ Generate Code", "⚙️ Settings"], key="nav_radio")
        st.session_state.page = page
        
        st.divider()
        workflows = get_workflows()
        if workflows:
            st.subheader("Recent Workflows")
            for wf in workflows[:5]:
                if st.button(wf["name"], key=f"sb_{wf['name']}", width="stretch"):
                    st.session_state.selected_workflow = wf["name"]
                    st.session_state.page = "🔍 Workflow Viewer"
                    st.rerun()
    
    # Content
    if st.session_state.page == "📊 Dashboard":
        render_dashboard(workflows)
    elif st.session_state.page == "🔍 Workflow Viewer":
        if st.session_state.selected_workflow:
            render_workflow_viewer(st.session_state.selected_workflow, workflows)
        else:
            st.info("Select a workflow from the dashboard or sidebar to view details.")
    elif st.session_state.page == "⚡ Generate Code":
        render_generate_page(st.session_state.selected_workflow, workflows)
    elif st.session_state.page == "⚙️ Settings":
        render_settings_page()

if __name__ == "__main__":
    main()

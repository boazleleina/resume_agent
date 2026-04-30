import streamlit as st
from api import stream_analysis_sync

st.set_page_config(page_title="Resume Agent", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

* {
    font-family: 'Inter', sans-serif;
}

/* ── Streamlit shell overrides ── */
header { visibility: hidden !important; }
#MainMenu { visibility: hidden !important; }

.stApp {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
    color: #e8e9f3;
}
.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Header ── */
.header {
    padding: 30px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(255, 255, 255, 0.02);
    backdrop-filter: blur(10px);
    display: flex;
    flex-direction: column;
    align-items: center;
}

.logo-row {
    display: flex;
    align-items: center;
    gap: 14px;
}

.logo {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, #64ffda, #7c4dff);
    color: #0f0f1a;
    display: grid;
    place-items: center;
    font-size: 23px;
    font-weight: 800;
}

.title {
    font-size: 30px;
    font-weight: 800;
    color: #e8e9f3;
}

.subtitle {
    margin-top: 8px;
    color: #a0a0b0;
    font-size: 16px;
    text-align: center;
}

/* ── Main Layout ── */
.main {
    max-width: 1000px;
    margin: 0 auto;
    padding: 48px 20px 60px;
}

h2 {
    font-size: 26px !important;
    color: #e8e9f3 !important;
    font-weight: 800 !important;
    margin-bottom: 6px !important;
}

.label-text {
    color: #a0a0b0;
    font-size: 15px;
    margin-bottom: 24px;
}

/* ── File Uploader Styling ── */
[data-testid="stFileUploader"] > section {
    height: 256px !important;
    border: 2px dashed rgba(100, 255, 218, 0.3) !important;
    background: rgba(100, 255, 218, 0.02) !important;
    border-radius: 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
}
[data-testid="stFileUploader"] > section:hover {
    border-color: #64ffda !important;
    background: rgba(100, 255, 218, 0.05) !important;
}

/* ── Radio Toggle (Tabs) ── */
div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border-radius: 11px !important;
    padding: 4px !important;
    margin-bottom: 23px !important;
}
div[role="radiogroup"] > label {
    flex: 1 !important;
    text-align: center !important;
    padding: 11px !important;
    font-weight: 600 !important;
    color: #a0a0b0 !important;
    background: transparent !important;
    border-radius: 9px !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}
div[role="radiogroup"] > label[aria-checked="true"],
div[role="radiogroup"] > label[data-checked="true"] {
    background: rgba(124, 77, 255, 0.1) !important;
    color: #64ffda !important;
    border: 1px solid rgba(100, 255, 218, 0.3) !important;
}
div[role="radiogroup"] > label > div:first-child {
    display: none !important;
}
div[role="radiogroup"] > label p {
    margin: 0 !important;
    white-space: nowrap !important;
}

/* ── Text Area ── */
.stTextArea > div > div > textarea,
.stTextInput > div > div > input {
    height: 256px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #e8e9f3 !important;
    background: rgba(0, 0, 0, 0.2) !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.9rem !important;
    padding: 1rem !important;
}
.stTextInput > div > div > input {
    height: 60px !important;
}
.stTextArea > div > div > textarea:focus,
.stTextInput > div > div > input:focus {
    border-color: #64ffda !important;
    box-shadow: 0 0 0 1px #64ffda !important;
}

.counter-row {
    display: flex;
    justify-content: space-between;
    color: #a0a0b0;
    font-size: 14px;
    margin-top: 4px;
}

.orange {
    color: #ff9800;
}

/* ── Buttons ── */
.analyze-wrap {
    display: flex;
    justify-content: center;
    margin-top: 46px;
}
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #64ffda 0%, #7c4dff 100%) !important;
    color: #0f0f1a !important;
    border-radius: 10px !important;
    padding: 14px 44px !important;
    font-weight: 800 !important;
    border: none !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="baseButton-primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(100, 255, 218, 0.3) !important;
}
[data-testid="baseButton-primary"]:focus {
    outline: none !important;
}

/* ── Feature Cards / Tip Boxes ── */
.tip {
    margin-top: 24px;
    padding: 18px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    color: #a0a0b0;
    font-size: 14px;
}
.tip b {
    color: #64ffda;
}

.feature-card {
    height: 100%;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 25px;
}
.feature-icon {
    width: 48px;
    height: 48px;
    border-radius: 13px;
    background: rgba(100, 255, 218, 0.1);
    color: #64ffda;
    display: grid;
    place-items: center;
    font-size: 25px;
    margin-bottom: 15px;
}
.feature-title {
    font-weight: 800;
    font-size: 18px;
    color: #e8e9f3;
    margin-bottom: 8px;
}
.feature-desc {
    color: #a0a0b0;
    font-size: 14px;
    line-height: 1.5;
}

/* ── File Success Box ── */
.file-success {
    background: rgba(76, 175, 80, 0.1);
    border: 1px solid rgba(76, 175, 80, 0.3);
    border-radius: 16px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-top: 10px;
}

/* ── Results & Loading UI ── */
.loading-wrap { max-width: 700px; margin: 6rem auto 0; padding: 3rem 2rem; text-align: center; }
.loading-title { font-size: 2.5rem; font-weight: 600; color: #64ffda; margin-bottom: 0.5rem; }
.dots-row { display: flex; justify-content: center; gap: 0.6rem; margin-top: 1.5rem; }
@keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #64ffda; animation: pulse-dot 1.4s ease-in-out infinite; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

.match-score-large { text-align: center; margin-bottom: 2rem; margin-top: 2rem; }
.score-number { font-family: 'Space Mono', monospace; font-size: 4rem; font-weight: 700; color: #64ffda; display: block; }
.score-label { font-size: 1.2rem; color: #a0a0b0; text-transform: uppercase; letter-spacing: 2px; }

.results-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 2rem; margin-top: 2rem; }
.card { background: rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.1); }
.card-title { font-size: 1.4rem; font-weight: 600; color: #64ffda; margin-bottom: 1rem; }
.angle-box { background: rgba(124, 77, 255, 0.1); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #64ffda; }
.skill-tag { padding: 0.3rem 0.8rem; border-radius: 6px; font-size: 0.8rem; font-family: 'Space Mono', monospace; border: 1px solid rgba(100, 255, 218, 0.3); }
.skill-matched { background: rgba(76, 175, 80, 0.2); border-color: #4caf50; color: #4caf50; }
.skill-missing { background: rgba(244, 67, 54, 0.2); border-color: #f44336; color: #f44336; }
.skills-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }
.edit-card { background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 1rem; margin: 1rem 0; border: 1px solid rgba(255, 255, 255, 0.1); }
.traceability-tag { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px; font-size: 0.7rem; font-family: 'Space Mono', monospace; }
.trace-supported { background: rgba(76, 175, 80, 0.2); color: #4caf50; }
.trace-missing { background: rgba(255, 152, 0, 0.2); color: #ff9800; }
.trace-rephrase { background: rgba(100, 255, 218, 0.2); color: #64ffda; }
</style>
""", unsafe_allow_html=True)


# ── Views ──────────────────────────────────────────────

def render_input_view():
    st.markdown("""
    <div class="header">
        <div class="logo-row">
            <div class="logo">✧</div>
            <div class="title">Resume Agent</div>
        </div>
        <div class="subtitle">Analyze your resume against job descriptions with AI-powered insights</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main">', unsafe_allow_html=True)

    if "jd_input_mode" not in st.session_state:
        st.session_state.jd_input_mode = "Paste Text"
    if "jd_text_value" not in st.session_state:
        st.session_state.jd_text_value = ""

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("<h2>Your Resume</h2>", unsafe_allow_html=True)
        st.markdown('<div class="label-text">Upload your resume in PDF format</div>', unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Upload", type=["pdf", "docx"], label_visibility="collapsed")
        
        file_valid = False
        if uploaded_file:
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File is too large. Maximum size is 5MB.")
            else:
                file_valid = True
                st.markdown(f"""
                <div class="file-success">
                    <div class="logo" style="background: rgba(76, 175, 80, 0.2); color: #4caf50;">📄</div>
                    <div>
                        <div style="font-weight: 700; color: #e8e9f3;">{uploaded_file.name}</div>
                        <div style="color: #a0a0b0; font-size: 14px;">{uploaded_file.size / 1024:.1f} KB</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
        <div class="tip"><b>Tip:</b> Use a well-formatted resume for better analysis results</div>
        """, unsafe_allow_html=True)

    with right:
        st.markdown("<h2>Job Description</h2>", unsafe_allow_html=True)
        st.markdown('<div class="label-text">Paste the job description or provide a link</div>', unsafe_allow_html=True)

        mode = st.radio("Mode", ["Paste Text", "Paste Link"], horizontal=True, label_visibility="collapsed", key="jd_input_mode")

        if mode == "Paste Text":
            jd_input = st.text_area(
                "Job Description",
                value=st.session_state.jd_text_value,
                placeholder="Paste the job description here... Include the role, responsibilities, required skills, and qualifications.",
                label_visibility="collapsed"
            )
            st.session_state.jd_text_value = jd_input
            
            char_count = len(jd_input)
            st.markdown(f"""
            <div class="counter-row">
                <span>{char_count} characters</span>
                {f'<span class="orange">Add more details for better analysis</span>' if 0 < char_count < 100 else ''}
            </div>
            """, unsafe_allow_html=True)
        else:
            jd_input = st.text_input(
                "Job Link",
                value=st.session_state.jd_text_value,
                placeholder="Paste the job posting link (LinkedIn, Indeed, etc.)",
                label_visibility="collapsed"
            )
            st.session_state.jd_text_value = jd_input

        st.markdown("""
        <div class="tip"><b>Pro tip:</b> The more detailed the job description, the more accurate the analysis</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="analyze-wrap"></div>', unsafe_allow_html=True)
    is_ready = file_valid and jd_input.strip() != ""
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
    with col_btn2:
        if st.button("✧  Analyze Resume", type="primary", disabled=not is_ready, use_container_width=True):
            st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.uploaded_file_type = uploaded_file.type
            st.session_state.jd_input = jd_input
            st.session_state.app_state = "analyzing"
            st.rerun()

    st.markdown('<div style="margin-top: 64px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">▣</div>
            <div class="feature-title">Resume Parsing</div>
            <div class="feature-desc">AI extracts skills and quantifiable metrics from your resume with strict fidelity.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">✣</div>
            <div class="feature-title">Smart Matching</div>
            <div class="feature-desc">Mathematical insights on how your exact tech stack matches the job.</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">↗</div>
            <div class="feature-title">Actionable Feedback</div>
            <div class="feature-desc">Traceability-backed recommendations to tailor your resume and close gaps.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_loading_view():
    loading_html = (
        '<div class="main">'
        '<div class="loading-wrap">'
        '<div class="loading-title">Agent is Working...</div>'
        '<p class="loading-subtitle" style="color: #a0a0b0;">Running AI analysis pipeline</p>'
        '<div class="dots-row">'
        '<div class="dot"></div>'
        '<div class="dot"></div>'
        '<div class="dot"></div>'
        '</div>'
        '</div>'
        '</div>'
    )
    st.markdown(loading_html, unsafe_allow_html=True)

    progress_bar = st.progress(10)
    status_text = st.empty()
    status_text.markdown("**🔄 Breaking down your resume...**")

    try:
        resume_data = None
        match_data = None
        grading_data = None

        for event_obj in stream_analysis_sync(
            st.session_state.uploaded_file_bytes,
            st.session_state.uploaded_file_name,
            st.session_state.uploaded_file_type,
            st.session_state.jd_input
        ):
            event = event_obj["event"]
            data = event_obj["data"]

            if event == "resume":
                status_text.markdown("**🔄 Extracting job requirements...**")
                progress_bar.progress(40)
                resume_data = data

            elif event == "jd":
                status_text.markdown("**🔄 Crunching the numbers...**")
                progress_bar.progress(60)

            elif event == "skill_match":
                status_text.markdown("**🔄 Synthesizing AI feedback (this takes ~30–60s)...**")
                progress_bar.progress(75)
                match_data = data

            elif event == "grading":
                status_text.markdown("**✅ Analysis Complete!**")
                progress_bar.progress(100)
                grading_data = data

            elif event == "done":
                break

        st.session_state.resume_data = resume_data
        st.session_state.match_data = match_data
        st.session_state.grading_data = grading_data
        st.session_state.app_state = "results"
        st.rerun()

    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        if st.button("Try Again"):
            st.session_state.app_state = "input"
            st.rerun()


def render_results_view():
    resume_data  = st.session_state.resume_data  or {}
    match_data   = st.session_state.match_data   or {}
    grading_data = st.session_state.grading_data or {}

    match_score = grading_data.get("match_score", 0)
    angle       = grading_data.get("strongest_angle", "No angle generated.")
    
    gaps_html = "".join(f'<div style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);"><strong>• {g}</strong></div>' for g in grading_data.get("honest_gaps", []))
    matched_html = "".join(f'<span class="skill-tag skill-matched">{s}</span>' for s in match_data.get("matched", []))
    missing_skills = match_data.get("missing_tech", []) + match_data.get("missing_required", [])
    missing_html = "".join(f'<span class="skill-tag skill-missing">{s}</span>' for s in missing_skills)

    edits_html = ""
    for i, edit in enumerate(grading_data.get("top_3_edits", []), 1):
        trace = edit.get("traceability", "")
        trace_class = "trace-supported"
        if "missing" in trace: trace_class = "trace-missing"
        elif "rephrase" in trace: trace_class = "trace-rephrase"
        edits_html += f'<div class="edit-card"><div style="color: #64ffda; font-size: 0.8rem; margin-bottom: 0.5rem;">EDIT {i} • {edit.get("section", "GENERAL").upper()} SECTION</div><div style="margin-bottom: 0.8rem;">{edit.get("suggestion", "")}</div><span class="traceability-tag {trace_class}">{trace}</span></div>'

    html = f"""
    <div class="header">
        <div class="title">Analysis Complete</div>
        <div class="subtitle">AI-Powered Resume Optimization Results</div>
    </div>
    <div class="main">
        <div class="match-score-large">
            <span class="score-number">{match_score}%</span>
            <span class="score-label">Match Score</span>
        </div>

        <div class="results-grid">
            <div class="card">
                <h3 class="card-title">🎯 Your Strongest Angle</h3>
                <div class="angle-box">{angle}</div>
            </div>

            <div class="card">
                <h3 class="card-title">📊 Skills Analysis</h3>
                <div style="margin: 1rem 0;">
                    <h4 style="color:#4caf50;margin-bottom:0.5rem;">✅ Matched Skills</h4>
                    <div class="skills-grid">{matched_html}</div>
                </div>
                <div style="margin: 1rem 0;">
                    <h4 style="color:#f44336;margin-bottom:0.5rem;">❌ Missing Skills</h4>
                    <div class="skills-grid">{missing_html}</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title">⚠️ Areas for Improvement</h3>
                <div>{gaps_html}</div>
            </div>
        </div>

        <div class="card" style="margin-top:2rem;">
            <h3 class="card-title">📝 Top 3 Recommended Edits</h3>
            {edits_html}
        </div>
    </div>
    """
    st.markdown("\n".join(l for l in html.split("\n") if l.strip()), unsafe_allow_html=True)
    
    st.markdown('<div class="main" style="padding-top:0;">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⬅️ Analyze Another Resume", type="primary", use_container_width=True):
            st.session_state.app_state = "input"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ── Router ─────────────────────────────────────────────

def main():
    if "app_state" not in st.session_state:
        st.session_state.app_state = "input"

    state = st.session_state.app_state
    if state == "input":
        render_input_view()
    elif state == "analyzing":
        render_loading_view()
    elif state == "results":
        render_results_view()

if __name__ == "__main__":
    main()

import streamlit as st
from api import stream_analysis_sync

st.set_page_config(
    page_title="Resume Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600&family=Space+Mono:wght@400;700&display=swap');

    /* ── Streamlit shell overrides ── */
    .stApp {
        background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        color: #e8e9f3;
        font-family: 'Crimson Pro', serif;
    }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    [data-testid="stAppViewContainer"] > section > div {
        padding: 0 !important;
    }
    .stDeployButton { display: none; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* ── Layout shell ── */
    .page-wrap {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
        box-sizing: border-box;
        font-family: 'Crimson Pro', serif;
        color: #e8e9f3;
    }

    /* ── Header ── */
    .page-header {
        text-align: center;
        padding: 3rem 0;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }

    /* ── Shine animation ── */
    @keyframes titleShine {
        0%   { background-position: 0%   center; }
        50%  { background-position: 100% center; }
        100% { background-position: 0%   center; }
    }
    .main-title {
        font-family: 'Crimson Pro', serif;
        font-size: 3.5rem;
        font-weight: 600;
        background: linear-gradient(135deg, #64ffda 0%, #ffffff 40%, #7c4dff 70%, #64ffda 100%);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleShine 5s ease infinite;
        margin-bottom: 0.5rem;
        display: block;
    }
    .subtitle {
        font-family: 'Space Mono', monospace;
        font-size: 1.1rem;
        color: #a0a0b0;
        letter-spacing: 0.5px;
    }

    /* ── Score ── */
    .match-score-large {
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-number {
        font-family: 'Space Mono', monospace;
        font-size: 4rem;
        font-weight: 700;
        color: #64ffda;
        display: block;
    }
    .score-label {
        font-size: 1.2rem;
        color: #a0a0b0;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* ── Results grid ── */
    .results-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
        gap: 2rem;
        margin-top: 2rem;
    }

    /* ── Cards ── */
    .card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(5px);
    }
    .card-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #64ffda;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── Angle box ── */
    .angle-box {
        background: linear-gradient(135deg, rgba(100, 255, 218, 0.1), rgba(124, 77, 255, 0.1));
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #64ffda;
        margin: 1rem 0;
    }
    .angle-text {
        font-size: 1.1rem;
        line-height: 1.6;
        font-style: italic;
    }

    /* ── Metrics ── */
    .metrics-row {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
        text-align: center;
    }
    .metric { flex: 1; }
    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #64ffda;
        display: block;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #a0a0b0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* ── Skill tags ── */
    .skills-section { margin: 1rem 0; }
    .skills-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0;
    }
    .skill-tag {
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-family: 'Space Mono', monospace;
        border: 1px solid rgba(100, 255, 218, 0.3);
    }
    .skill-matched {
        background: rgba(76, 175, 80, 0.2);
        border-color: #4caf50;
        color: #4caf50;
    }
    .skill-missing {
        background: rgba(244, 67, 54, 0.2);
        border-color: #f44336;
        color: #f44336;
    }

    /* ── Edit cards ── */
    .edit-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: background 0.3s ease, transform 0.3s ease;
    }
    .edit-card:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateY(-2px);
    }
    .edit-number {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        color: #64ffda;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    .edit-section {
        font-family: 'Space Mono', monospace;
        font-size: 0.8rem;
        color: #7c4dff;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    .edit-suggestion {
        line-height: 1.5;
        margin-bottom: 0.8rem;
    }
    .traceability-tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.7rem;
        font-family: 'Space Mono', monospace;
    }
    .trace-supported { background: rgba(76, 175, 80, 0.2);  color: #4caf50; }
    .trace-missing   { background: rgba(255, 152, 0, 0.2);  color: #ff9800; }
    .trace-rephrase  { background: rgba(100, 255, 218, 0.2); color: #64ffda; }

    /* ── Gaps / resume info ── */
    .gaps-list { margin: 1rem 0; }
    .gap-item {
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .gap-item:last-child { border-bottom: none; }
    .resume-info {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }
    .info-section h4 {
        color: #64ffda;
        margin-bottom: 0.5rem;
        font-size: 1rem;
    }
    .info-section ul { list-style: none; padding: 0; }
    .info-section li { padding: 0.2rem 0; color: #e8e9f3; }

    /* ── Loading screen ── */
    .loading-wrap {
        max-width: 700px;
        margin: 6rem auto 0;
        padding: 3rem 2rem;
        text-align: center;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    .loading-title {
        font-family: 'Crimson Pro', serif;
        font-size: 2.5rem;
        font-weight: 600;
        background: linear-gradient(135deg, #64ffda 0%, #ffffff 40%, #7c4dff 70%, #64ffda 100%);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: titleShine 5s ease infinite;
        margin-bottom: 0.5rem;
    }
    .loading-subtitle {
        font-family: 'Space Mono', monospace;
        font-size: 0.9rem;
        color: #a0a0b0;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
    }

    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.4; transform: scale(0.8); }
    }
    .dots-row {
        display: flex;
        justify-content: center;
        gap: 0.6rem;
        margin-top: 1.5rem;
    }
    .dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        background: #64ffda;
        animation: pulse-dot 1.4s ease-in-out infinite;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }

    /* ── Footer ── */
    .page-footer {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 12px;
    }
    .page-footer p {
        color: #a0a0b0;
        font-family: 'Space Mono', monospace;
        font-size: 0.85rem;
    }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .page-wrap { padding: 1rem; }
        .main-title { font-size: 2.5rem; }
        .results-grid { grid-template-columns: 1fr; }
        .metrics-row { flex-direction: column; gap: 1rem; }
    }
</style>
""", unsafe_allow_html=True)


# ── Views ──────────────────────────────────────────────

def render_input_view():
    st.markdown(
        '<div class="page-wrap">'
        '<div class="page-header">'
        '<span class="main-title">Resume Agent</span>'
        '<p class="subtitle">AI-Powered Resume Optimization &amp; Job Matching</p>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<h3 style="font-family:\'Crimson Pro\',serif;font-size:1.4rem;color:#64ffda;margin-bottom:1rem;">📄 Resume Upload</h3>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Select your resume (PDF or DOCX)", type=["pdf", "docx"])

    with col2:
        st.markdown('<h3 style="font-family:\'Crimson Pro\',serif;font-size:1.4rem;color:#64ffda;margin-bottom:1rem;">🔗 Job Description</h3>', unsafe_allow_html=True)
        jd_input = st.text_area("Job description text or URL", height=150, placeholder="Paste the URL or the full job description text here...")

    if st.button("🚀 Analyze Resume", type="primary", use_container_width=True):
        if uploaded_file and jd_input:
            st.session_state.uploaded_file_bytes = uploaded_file.getvalue()
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.uploaded_file_type = uploaded_file.type
            st.session_state.jd_input = jd_input
            st.session_state.app_state = "analyzing"
            st.rerun()
        else:
            st.warning("Please upload a resume and provide a job description before analyzing.")


def render_loading_view():
    loading_html = (
        '<div class="page-wrap">'
        '<div class="loading-wrap">'
        '<div class="loading-title">Agent is Working...</div>'
        '<p class="loading-subtitle">Running AI analysis pipeline</p>'
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

    # ── Parse grading
    match_score = grading_data.get("match_score", 0)
    angle       = grading_data.get("strongest_angle", "No angle generated.")
    gaps_html   = "".join(
        f'<div class="gap-item"><strong>• {g}</strong></div>'
        for g in grading_data.get("honest_gaps", [])
    )

    # ── Parse match
    tech_match    = match_data.get("tech_match_pct", 0)
    matched_html  = "".join(f'<span class="skill-tag skill-matched">{s}</span>' for s in match_data.get("matched", []))
    missing_skills = match_data.get("missing_tech", []) + match_data.get("missing_required", [])
    missing_html  = "".join(f'<span class="skill-tag skill-missing">{s}</span>' for s in missing_skills)

    # ── Parse resume
    contact  = resume_data.get("contact", {})
    name     = contact.get("name", "N/A")
    email    = contact.get("email", "N/A")
    links    = ", ".join(contact.get("links", []))
    exp_html = "".join(
        f"<li>{e.get('title')} at {e.get('company')}</li>"
        for e in resume_data.get("experience", [])
    )
    metrics_html = "".join(
        f'<span class="skill-tag skill-matched">{m}</span>'
        for m in resume_data.get("metrics_found", [])[:6]
    )

    # ── Parse edits
    edits_html = ""
    for i, edit in enumerate(grading_data.get("top_3_edits", []), 1):
        trace = edit.get("traceability", "")
        trace_class = "trace-supported"
        if "missing" in trace:
            trace_class = "trace-missing"
        elif "rephrase" in trace or "already present" in trace:
            trace_class = "trace-rephrase"
        edits_html += (
            f'<div class="edit-card">'
            f'<div class="edit-number">Edit {i}</div>'
            f'<div class="edit-section">{edit.get("section", "General").upper()} SECTION</div>'
            f'<div class="edit-suggestion">{edit.get("suggestion", "")}</div>'
            f'<span class="traceability-tag {trace_class}">{trace}</span>'
            f'</div>'
        )

    html = f"""
<div class="page-wrap">
    <div class="page-header">
        <span class="main-title">Resume Analysis Complete</span>
        <p class="subtitle">AI-Powered Resume Optimization Results</p>
    </div>

    <div class="match-score-large">
        <span class="score-number">{match_score}%</span>
        <span class="score-label">Match Score</span>
    </div>

    <div class="results-grid">
        <div class="card">
            <h3 class="card-title">🎯 Your Strongest Angle</h3>
            <div class="angle-box">
                <p class="angle-text">"{angle}"</p>
            </div>
        </div>

        <div class="card">
            <h3 class="card-title">📊 Skills Analysis</h3>
            <div class="metrics-row">
                <div class="metric">
                    <span class="metric-value">{tech_match}%</span>
                    <span class="metric-label">Tech Stack</span>
                </div>
            </div>
            <div class="skills-section">
                <h4 style="color:#4caf50;margin-bottom:0.5rem;">✅ Matched Skills</h4>
                <div class="skills-grid">{matched_html}</div>
            </div>
            <div class="skills-section">
                <h4 style="color:#f44336;margin-bottom:0.5rem;">❌ Missing Skills</h4>
                <div class="skills-grid">{missing_html}</div>
            </div>
        </div>

        <div class="card">
            <h3 class="card-title">📋 Resume Overview</h3>
            <div class="resume-info">
                <div class="info-section">
                    <h4>Contact</h4>
                    <ul>
                        <li><strong>Name:</strong> {name}</li>
                        <li><strong>Email:</strong> {email}</li>
                        <li><strong>Links:</strong> {links}</li>
                    </ul>
                </div>
                <div class="info-section">
                    <h4>Experience</h4>
                    <ul>{exp_html}</ul>
                </div>
                <div class="info-section">
                    <h4>Key Metrics</h4>
                    <div class="skills-grid">{metrics_html}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h3 class="card-title">⚠️ Areas for Improvement</h3>
            <div class="gaps-list">{gaps_html}</div>
        </div>
    </div>

    <div class="card" style="margin-top:2rem;">
        <h3 class="card-title">📝 Top 3 Recommended Edits</h3>
        {edits_html}
    </div>

    <div class="page-footer">
        <p>Analysis complete &bull; Resume Agent v2.0 &bull; Built with ❤️ and local LLMs</p>
    </div>
</div>
"""
    # Strip blank lines — blank line + 4-space indent triggers CommonMark code blocks
    st.markdown("\n".join(l for l in html.split("\n") if l.strip()), unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⬅️ Analyze Another Resume", type="primary", use_container_width=True):
            st.session_state.app_state = "input"
            st.rerun()


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

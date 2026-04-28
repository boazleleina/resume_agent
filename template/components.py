import streamlit as st

def render_scorecard(skill_match: dict):
    overall = skill_match.get("overall_match_pct", 0)
    required = skill_match.get("required_match_pct", 0)
    
    matched = skill_match.get("matched", [])
    missing = skill_match.get("missing_required", []) + skill_match.get("missing_tech", [])
    
    # Generate HTML for chips
    matched_html = "".join([f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 mr-2 mb-2">{s}</span>' for s in matched])
    missing_html = "".join([f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 mr-2 mb-2">{s}</span>' for s in missing])
    
    html = f"""
    <div class="bg-white shadow sm:rounded-lg mb-6 border border-gray-200">
        <div class="px-4 py-5 sm:px-6 bg-gray-50 flex justify-between items-center border-b border-gray-200">
            <h3 class="text-lg leading-6 font-medium text-gray-900">Skill Match Scorecard</h3>
            <div class="text-2xl font-bold text-indigo-600">{overall}%</div>
        </div>
        <div class="px-4 py-5 sm:p-0">
            <dl class="sm:divide-y sm:divide-gray-200">
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                    <dt class="text-sm font-medium text-gray-500">Required Skills Match</dt>
                    <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{required}%</dd>
                </div>
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                    <dt class="text-sm font-medium text-gray-500">Matched Skills</dt>
                    <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2 flex flex-wrap">{matched_html}</dd>
                </div>
                <div class="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                    <dt class="text-sm font-medium text-gray-500">Missing Skills</dt>
                    <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2 flex flex-wrap">{missing_html}</dd>
                </div>
            </dl>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_grading(grading: dict):
    score = grading.get("match_score", 0)
    angle = grading.get("strongest_angle", "")
    gaps = grading.get("honest_gaps", [])
    edits = grading.get("top_3_edits", [])
    
    gaps_html = "".join([f'<li class="text-sm text-gray-700 ml-4">{g}</li>' for g in gaps])
    
    edits_html = ""
    for idx, edit in enumerate(edits):
        section = edit.get("section", "general").title()
        sug = edit.get("suggestion", "")
        trace = edit.get("traceability", "")
        
        # Color coding the traceability tags
        trace_color = "bg-blue-100 text-blue-800"
        if "missing" in trace:
            trace_color = "bg-yellow-100 text-yellow-800"
        elif "already present" in trace:
            trace_color = "bg-purple-100 text-purple-800"
            
        edits_html += f"""
        <div class="bg-gray-50 rounded p-4 mb-4 border border-gray-200">
            <div class="flex justify-between items-start mb-2">
                <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">{section}</span>
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {trace_color}">{trace}</span>
            </div>
            <p class="text-gray-800 text-sm">{sug}</p>
        </div>
        """
        
    html = f"""
    <div class="bg-white shadow sm:rounded-lg mb-6 border border-gray-200">
        <div class="px-4 py-5 sm:px-6 bg-indigo-50 border-b border-indigo-100 flex justify-between items-center">
            <h3 class="text-lg leading-6 font-bold text-indigo-900">AI Grading & Recommendations</h3>
            <div class="text-2xl font-bold text-indigo-600">{score}/100</div>
        </div>
        <div class="px-4 py-5 sm:p-6">
            <h4 class="text-md font-semibold text-gray-900 mb-2">Strongest Angle</h4>
            <p class="text-sm text-gray-700 mb-6">{angle}</p>
            
            <h4 class="text-md font-semibold text-gray-900 mb-2">Identified Gaps</h4>
            <ul class="list-disc pl-5 mb-6">{gaps_html}</ul>
            
            <h4 class="text-md font-semibold text-gray-900 mb-3">Top 3 Recommended Edits</h4>
            {edits_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

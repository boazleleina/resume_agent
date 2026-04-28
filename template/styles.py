import streamlit as st

def inject_tailwind():
    """
    Injects Tailwind CSS via CDN and adds custom animations.
    """
    st.markdown("""
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <style>
            /* Clean up default Streamlit padding */
            .block-container {
                padding-top: 2rem;
                max-width: 64rem;
            }
            /* Remove header background */
            .stApp header {
                background-color: transparent;
            }
            /* Custom loading pulse animation */
            .pulse-text {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: .5; }
            }
        </style>
    """, unsafe_allow_html=True)

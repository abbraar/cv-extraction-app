# streamlit_app.py
import os
import json
import tempfile

import streamlit as st
from dotenv import load_dotenv

from cv_extractor import (
    read_cv_text,
    extract_with_gemini,
    normalize_parsed,
    write_ats_docx,
    heuristic_projects_from_text,  # fallback to mine projects if empty
)

# ----------------------------
# Environment / API key setup
# ----------------------------
# Load local .env (for development)
load_dotenv()

# Prefer Streamlit Secrets on cloud; fallback to .env locally
gem_key = (
    st.secrets.get("GEMINI_API_KEY")
    or st.secrets.get("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

# Make the key available for any SDK that expects either name
if gem_key:
    os.environ["GEMINI_API_KEY"] = gem_key
    os.environ["GOOGLE_API_KEY"] = gem_key

api_key_present = bool(gem_key)

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="CV → ATS Extractor", page_icon="📝", layout="centered")
st.title("CV → ATS Extractor (Gemini 2.5 Flash)")
st.caption("Upload a PDF or DOCX CV. We’ll extract clean fields and generate an ATS-friendly Word file.")

with st.expander("Environment status", expanded=not api_key_present):
    st.write("**GEMINI_API_KEY**:", "✅ Found" if api_key_present else "❌ Missing")
    if not api_key_present:
        st.info("Add `GEMINI_API_KEY=...` to your `.env` (local) **or** set it in Streamlit **Secrets** (cloud).")

uploaded = st.file_uploader("Upload CV (.pdf or .docx)", type=["pdf", "docx"])

if uploaded:
    if not api_key_present:
        st.error("GEMINI_API_KEY is not set. Please configure it and refresh.")
        st.stop()

    st.info("Processing… please wait.", icon="⏳")

    # Save upload to a temp file with the correct suffix
    suffix = ".pdf" if (uploaded.type == "application/pdf" or uploaded.name.lower().endswith(".pdf")) else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_in:
        tmp_in.write(uploaded.read())
        tmp_in.flush()
        cv_path = tmp_in.name

    try:
        # 1) Extract plain text from the CV
        text = read_cv_text(cv_path)

        # 2) Call Gemini to parse structured fields
        data = extract_with_gemini(text)

        # 3) Normalize schema / shapes
        data = normalize_parsed(data)

        # 4) Fallback: mine Projects from text if the model returned none
        if not data.get("projects"):
            mined = heuristic_projects_from_text(text, max_items=5)
            if mined:
                data["projects"] = mined

        # 5) Build downloads (JSON + ATS .docx)
        json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_out:
            write_ats_docx(data, tmp_out.name)
            tmp_out.flush()
            with open(tmp_out.name, "rb") as f:
                docx_bytes = f.read()

        st.success("Done! Download your files below.", icon="✅")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Download JSON",
                data=json_bytes,
                file_name="cv_parsed.json",
                mime="application/json",
            )
        with col2:
            st.download_button(
                "⬇️ Download ATS .docx",
                data=docx_bytes,
                file_name="cv_parsed_ats.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        st.subheader("Preview (JSON)")
        st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    except Exception as e:
        st.error(f"Error: {e}")

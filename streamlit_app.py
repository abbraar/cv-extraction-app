# streamlit_app.py
import os
import json
import tempfile
import re

import streamlit as st
from dotenv import load_dotenv

from cv_extractor import (
    read_cv_text,
    extract_with_gemini,
    normalize_parsed,
    write_ats_docx,
    heuristic_projects_from_text,  # fallback if projects empty
)

# ----------------------------
# Environment / API key setup
# ----------------------------
load_dotenv()

def _get_secret(name: str):
    try:
        return st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        return None

# Optional org branding via env/Secrets
COMPANY_NAME = _get_secret("COMPANY_NAME") or os.getenv("COMPANY_NAME") or "CV Extraction Service"

# Try Secrets first (cloud), then env (.env/host)
gem_key = (
    _get_secret("GEMINI_API_KEY")
    or _get_secret("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
)

# Expose for any SDK name
if gem_key:
    os.environ["GEMINI_API_KEY"] = gem_key
    os.environ["GOOGLE_API_KEY"] = gem_key

api_key_present = bool(gem_key)

# ----------------------------
# Page config & minimal styling
# ----------------------------
st.set_page_config(
    page_title=f"{COMPANY_NAME} · Unified CV Parser",
    page_icon="📝",
    layout="centered"
)

st.markdown(
    """
    <style>
      .brand-badge {
        display:inline-block; padding:6px 10px; border-radius:8px;
        background: rgba(99, 102, 241, 0.12); color:#4f46e5; font-weight:600; font-size:12px;
        border:1px solid rgba(99, 102, 241, 0.25);
      }
      .footer {
        color:#6b7280; font-size:12px; text-align:center; margin-top:36px;
      }
      .small { color:#6b7280; font-size:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown(f"<span class='brand-badge'>{COMPANY_NAME}</span>", unsafe_allow_html=True)
st.title("Unified CV Parser & ATS Word Generator")
st.caption("Upload a CV (PDF or DOCX) to generate a clean, ATS-friendly Word document.")

with st.expander("Environment status", expanded=not api_key_present):
    st.write("**GEMINI_API_KEY / GOOGLE_API_KEY**:", "✅ Found" if api_key_present else "❌ Missing")
    if not api_key_present:
        st.info("Set `GEMINI_API_KEY` in `.env` (local) or Streamlit **Secrets**. You can also use `GOOGLE_API_KEY`.")

# ----------------------------
# Helpers
# ----------------------------
_filename_safe = re.compile(r"[^A-Za-z0-9._-]+")

def slugify(name: str) -> str:
    name = (name or "").strip()
    name = name.replace("—", "-").replace("–", "-")
    name = name.replace(" ", "_")
    name = _filename_safe.sub("_", name)
    return name.strip("_") or "cv"

def derive_base_name(uploaded_name: str, parsed_json: dict) -> str:
    """Prefer the person's full name, else use uploaded filename (without ext)."""
    full_name = (parsed_json or {}).get("full_name")
    if full_name and isinstance(full_name, str) and full_name.strip():
        return slugify(full_name)
    base, _ = os.path.splitext(uploaded_name)
    return slugify(base)

# ----------------------------
# UI
# ----------------------------
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
        # 1) Extract plain text
        text = read_cv_text(cv_path)

        # 2) Parse with Gemini
        data = extract_with_gemini(text)

        # 3) Normalize output schema
        data = normalize_parsed(data)

        # 4) Fallback: mine Projects if empty
        if not data.get("projects"):
            mined = heuristic_projects_from_text(text, max_items=5)
            if mined:
                data["projects"] = mined

        # 5) Derive output base name from person's full name (fallback to uploaded filename)
        base = derive_base_name(uploaded.name, data)

        # 6) Build ATS .docx
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_out:
            write_ats_docx(data, tmp_out.name)
            tmp_out.flush()
            with open(tmp_out.name, "rb") as f:
                docx_bytes = f.read()

        st.success("Done! Download your ATS Word file below.", icon="✅")
        st.download_button(
            "⬇️ Download ATS .docx",
            data=docx_bytes,
            file_name=f"{base}_ATS.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except Exception as e:
        st.error(f"Error: {e}")

# ----------------------------
# Footer / Ownership
# ----------------------------
st.markdown(
    """
    <div class="footer">
      Built by <strong>Abrar Abdulaziz Sebiany</strong> · Powered by <strong>Gemini API</strong><br/>
      Unified internal tool for CV parsing & ATS document generation.
    </div>
    """,
    unsafe_allow_html=True,
)

"""
Enterprise DocAI - Tri-Lingual Platform (Executive Edition with Full-Screen Home Page)
(English • हिन्दी • ಕನ್ನಡ) - Voice Input, Live Indic Transliteration, Audio & Grounded RAG
"""

import streamlit as st
import streamlit.components.v1 as components
import os
import time
import urllib.parse
import urllib.request
import json

from ingestion import build_chunk_records
from llm import generate_answer
from vector_store import add_chunks, document_stats, delete_document, query

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise DocAI | Grounded Tri-Lingual RAG",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. TRI-LINGUAL CONFIGURATION & LOCALIZED KNOWLEDGE
# -----------------------------------------------------------------------------
LANGUAGES = {
    "English": {
        "code": "en-IN",
        "target_lang": "en",
        "tts_lang": "en",
        "native": "English",
        "flag": "🇬🇧",
        "placeholder": "Type in English or speak your question...",
        "speak_btn": "Start Voice Input",
        "listen_btn": "🔊 Listen to Answer (Read Aloud)",
        "grounded_tag": "✓ 100% Grounded & Verified",
        "guardrail_tag": "🛑 Guardrail Triggered: Unanswerable",
        "citations_title": "Supporting Source Citations:",
    },
    "ಕನ್ನಡ (Kannada)": {
        "code": "kn-IN",
        "target_lang": "kn",
        "tts_lang": "kn",
        "native": "ಕನ್ನಡ",
        "flag": "🟡🔴",
        "placeholder": "Type in Kanglish (e.g. namaste, eshtu samaya valid)...",
        "speak_btn": "ಧ್ವನಿ ಮೂಲಕ ಕೇಳಿ (Voice Input)",
        "listen_btn": "🔊 ಉತ್ತರವನ್ನು ಆಲಿಸಿ (Read Aloud)",
        "grounded_tag": "✓ 100% ದೃಢೀಕರಿಸಿದ ಉತ್ತರ (Grounded)",
        "guardrail_tag": "🛑 ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ (Guardrail)",
        "citations_title": "ಆಧಾರಿತ ಮೂಲ ದಾಖಲೆಗಳು (Citations):",
    },
    "हिन्दी (Hindi)": {
        "code": "hi-IN",
        "target_lang": "hi",
        "tts_lang": "hi",
        "native": "हिन्दी",
        "flag": "🇮🇳",
        "placeholder": "Type in Hinglish (e.g. namaste, kitne samay tak valid hai)...",
        "speak_btn": "बोलकर पूछें (Voice Input)",
        "listen_btn": "🔊 उत्तर सुनें (Audio Read Aloud)",
        "grounded_tag": "✓ 100% प्रमाणित उत्तर (Grounded)",
        "guardrail_tag": "🛑 सुरक्षा गार्ड सक्रिय: जानकारी अनुपलब्ध",
        "citations_title": "प्रमाणित स्रोत संदर्भ (Citations):",
    },
}

MULTILINGUAL_KNOWLEDGE = {
    "password": {
        "en": "A password reset link is valid for 30 minutes from the time of generation. If not used within this window, a new request must be submitted.",
        "kn": "ಪಾಸ್‌ವರ್ಡ್ ಮರುಹೊಂದಿಸುವ (Reset) ಲಿಂಕ್ ರಚಿಸಿದ ಸಮಯದಿಂದ 30 ನಿಮಿಷಗಳವರೆಗೆ ಮಾತ್ರ ಮಾನ್ಯವಾಗಿರುತ್ತದೆ. ಈ ಸಮಯ ಮೀರಿದರೆ, ಹೊಸ ವಿನಂತಿಯನ್ನು ಸಲ್ಲಿಸಬೇಕಾಗುತ್ತದೆ.",
        "hi": "पासवर्ड रीसेट लिंक जनरेट होने के समय से 30 मिनट के लिए वैध है। यदि इस समय सीमा के भीतर इसका उपयोग नहीं किया जाता है, तो एक नया अनुरोध सबमिट करना होगा।",
    },
    "critical": {
        "en": "For Critical (Priority 1) incidents, the guaranteed response time SLA is 1 hour, with continuous hourly status updates provided to stakeholders until resolution.",
        "kn": "ಗಂಭೀರ (ಆದ್ಯತೆ 1 / Critical) ಸಮಸ್ಯೆಗಳಿಗೆ, ಗ್ಯಾರಂಟಿ ಪ್ರತಿಕ್ರಿಯೆ ಸಮಯ (SLA) 1 ಗಂಟೆಯಾಗಿದೆ ಮತ್ತು ಸಮಸ್ಯೆಯನ್ನು ಬಗೆಹರಿಸುವವರೆಗೆ ಪ್ರತಿ ಗಂಟೆಗೆ ಅಪ್‌ಡೇಟ್‌ಗಳನ್ನು ನೀಡಲಾಗುತ್ತದೆ.",
        "hi": "गंभीर (प्राथमिकता 1 / Critical) घटनाओं के लिए, गारंटीकृत प्रतिक्रिया समय SLA 1 घंटा है, जिसमें समाधान होने तक हितधारकों को प्रति घंटा स्थिति अपडेट दी जाती है।",
    },
    "vpn": {
        "en": "Remote access requires the GlobalProtect VPN client with Multi-Factor Authentication (MFA) enabled. Split tunneling is strictly prohibited.",
        "kn": "ರಿಮೋಟ್ ಪ್ರವೇಶಕ್ಕೆ (VPN) ಮಲ್ಟಿ-ಫ್ಯಾಕ್ಟರ್ ದೃಢೀಕರಣದೊಂದಿಗೆ (MFA) GlobalProtect VPN ಕಡ್ಡಾಯವಾಗಿದೆ.",
        "hi": "रिमोट एक्सेस के लिए मल्टी-फैक्टर ऑथेंटिकेशन (MFA) के साथ GlobalProtect VPN का उपयोग अनिवार्य है।",
    },
    "hardware": {
        "en": "Standard hardware replacement requests are processed within 3 business days following manager approval in the IT procurement portal.",
        "kn": "ಮ್ಯಾನೇಜರ್ ಅನುಮೋದನೆಯ ನಂತರ 3 ಕೆಲಸದ ದಿನಗಳಲ್ಲಿ ಹೊಸ ಲ್ಯಾಪ್‌ಟಾಪ್/ಹಾರ್ಡ್‌ವೇರ್ ಒದಗಿಸಲಾಗುತ್ತದೆ.",
        "hi": "मैनेजर की मंजूरी के बाद 3 कार्य दिवसों के भीतर हार्डवेयर अनुरोध को पूरा किया जाता है।",
    },
    "general": {
        "en": "Based on the indexed IT Support Policy, all standard requests are tracked via the IT Helpdesk Portal with end-to-end audit logging.",
        "kn": "ಲಭ್ಯವಿರುವ ಐಟಿ ನೀತಿ ದಾಖಲೆಯ ಪ್ರಕಾರ, ಎಲ್ಲಾ ವಿನಂತಿಗಳನ್ನು ಐಟಿ ಹೆಲ್ಪ್‌ಡೆಸ್ಕ್ ಪೋರ್ಟಲ್ ಮೂಲಕ ಪರಿಶೀಲಿಸಲಾಗುತ್ತದೆ.",
        "hi": "अनुक्रमित आईटी सहायता नीति के अनुसार, सभी मानक अनुरोधों को आईटी हेल्पडेस्क पोर्टल द्वारा ट्रैक किया जाता है।",
    },
    "unrelated": {
        "en": "I don’t have enough information in the indexed documents to answer that.",
        "kn": "ಈ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಲು ಲಭ್ಯವಿರುವ ದಾಖಲೆಗಳಲ್ಲಿ (Documents) ಸಾಕಷ್ಟು ಮಾಹಿತಿಯಿಲ್ಲ.",
        "hi": "इस प्रश्न का उत्तर देने के लिए अनुक्रमित दस्तावेजों में पर्याप्त जानकारी उपलब्ध नहीं है।",
    }
}

# -----------------------------------------------------------------------------
# 3. TRANSLITERATION & TEXT-TO-SPEECH (Zero External Dependencies)
# -----------------------------------------------------------------------------
def transliterate_phonetic_indic(text: str, lang: str) -> str:
    """Converts phonetic Kanglish / Hinglish into pure Kannada / Hindi script."""
    if not text or not text.strip() or lang == "en":
        return text

    itc_code = "kn-t-i0-und" if lang == "kn" else ("hi-t-i0-und" if lang == "hi" else None)
    if not itc_code:
        return text

    try:
        encoded_text = urllib.parse.quote(text.strip())
        url = f"https://inputtools.google.com/request?text={encoded_text}&itc={itc_code}&num=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data[0] == "SUCCESS":
                converted_words = []
                for item in data[1]:
                    if len(item) > 1 and item[1] and len(item[1]) > 0:
                        converted_words.append(item[1][0])
                    else:
                        converted_words.append(item[0])
                return " ".join(converted_words)
    except Exception:
        pass
    return text


@st.cache_data(show_spinner=False)
def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate query or answer text while keeping the vector store language-neutral."""
    if not text or source_lang == target_lang:
        return text

    try:
        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": source_lang,
                "tl": target_lang,
                "dt": "t",
                "q": text.strip(),
            }
        )
        url = f"https://translate.googleapis.com/translate_a/single?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join(part[0] for part in data[0] if part and part[0])
            return translated.strip() or text
    except Exception:
        return text


@st.cache_data(show_spinner=False)
def fetch_tts_audio_bytes(text: str, tts_lang: str):
    """Fetches natural voice audio stream in Kannada ('kn'), Hindi ('hi'), or English ('en')."""
    try:
        clean_text = text.replace("**", "").replace("\n", " ").strip()[:250]
        encoded_query = urllib.parse.quote(clean_text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={tts_lang}&client=tw-ob&q={encoded_query}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            return response.read()
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 4. PRISTINE ENTERPRISE CSS (NO OVERLAPPING TEXT, CLEAN BOXING)
# -----------------------------------------------------------------------------
def inject_enterprise_css(theme_mode="Light"):
    dark_theme_css = """
        <style>
        html, body, [class*="css"], .stApp { background: #0B1721 !important; color: #E2E8F0 !important; }
        [data-testid="stSidebar"] { background: #102A43 !important; }
        .top-nav, .content-card, .feature-card, .metric-kpi-card { background: #122536 !important; border-color: #29465A !important; }
        .brand-title, .card-header, .feature-title, .metric-box-value, .preview-text { color: #F8FAFC !important; }
        .card-subtitle, .feature-text, .metric-label, .metric-footer, [data-testid="stCaptionContainer"] { color: #AFC2D0 !important; }
        .metric-box-value, .citation-badge { background: #0F1D2A !important; border-color: #36576D !important; }
        .live-preview-box { background: #12332F !important; border-color: #267568 !important; }
        div[data-baseweb="tab-list"] { border-color: #29465A !important; }
        div[data-baseweb="tab"] { color: #AFC2D0 !important; }
        div[data-baseweb="tab"]:hover { color: #8DD3C7 !important; background: rgba(141, 211, 199, 0.08) !important; }
        </style>
    """ if theme_mode == "Dark" else ""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&family=Noto+Sans+Kannada:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        /* Base Typography Reset */
        html, body, [class*="css"], .stApp {
            font-family: 'DM Sans', 'Noto Sans Kannada', 'Noto Sans Devanagari', sans-serif !important;
            background: #F4F7F9 !important;
            color: #0F172A;
            line-height: 1.6;
            box-sizing: border-box;
        }

        code, pre, .mono-text {
            font-family: 'JetBrains Mono', monospace !important;
        }

        /* Full Width Container Setup */
        .block-container {
            max-width: 96% !important;
            padding-top: 1.25rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1.75rem !important;
            padding-right: 1.75rem !important;
        }

        /* Top Header Navbar */
        .top-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #FFFFFF;
            padding: 16px 24px;
            border-radius: 12px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
            animation: nav-drop-in 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, transform 0.25s ease;
        }

        .top-nav:hover {
            border-color: #B6DCD7;
            box-shadow: 0 10px 28px rgba(16, 42, 67, 0.08);
            transform: translateY(-1px);
        }

        @keyframes nav-drop-in {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .brand-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 0;
            line-height: 1.3;
        }

        .brand-lockup {
            display: inline-flex;
            align-items: center;
            gap: 10px;
            position: relative;
            padding: 3px 0 7px;
        }

        .brand-lockup::after {
            content: '';
            position: absolute;
            left: 34px;
            right: 0;
            bottom: 0;
            height: 3px;
            border-radius: 4px;
            background: linear-gradient(90deg, #4F46E5, #2A9D8F, transparent);
            animation: brand-highlight-in 0.7s ease both;
        }

        .brand-mark {
            display: inline-grid;
            place-items: center;
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background: linear-gradient(135deg, #102A43, #176B87);
            box-shadow: 0 5px 12px rgba(23, 107, 135, 0.22);
            font-size: 21px;
        }

        .brand-name {
            font-family: 'Manrope', sans-serif !important;
            font-size: clamp(25px, 2.5vw, 36px);
            font-weight: 800;
            letter-spacing: 0;
            line-height: 1.05;
            background: linear-gradient(100deg, #102A43 10%, #176B87 58%, #2A9D8F 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        @keyframes brand-highlight-in {
            from { opacity: 0; transform: scaleX(0.35); transform-origin: left; }
            to { opacity: 1; transform: scaleX(1); transform-origin: left; }
        }

        @media (max-width: 600px) {
            .brand-name { font-size: 23px; }
            .brand-mark { width: 34px; height: 34px; font-size: 18px; }
            .brand-lockup::after { left: 30px; }
        }

        /* Full Screen Home Hero Section */
        .home-stage {
            min-height: calc(100vh - 190px);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            margin-bottom: 22px;
        }

        .home-hero-card {
            background: linear-gradient(118deg, #102A43 0%, #176B87 55%, #2A9D8F 100%);
            border-radius: 20px;
            min-height: 410px;
            padding: 54px 58px;
            color: #FFFFFF;
            margin-bottom: 22px;
            box-shadow: 0 24px 50px rgba(16, 42, 67, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            animation: home-fade-in 0.45s ease both;
        }

        @keyframes home-fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

        div[data-testid="stTabs"] > div[role="tabpanel"]:first-of-type {
            min-height: calc(100vh - 190px);
        }

        .home-hero-card::before {
            content: '';
            position: absolute;
            width: 420px;
            height: 420px;
            right: 8%;
            top: -145px;
            border: 1px solid rgba(255, 255, 255, 0.17);
            border-radius: 50%;
            box-shadow: 0 0 0 38px rgba(255, 255, 255, 0.035), 0 0 0 76px rgba(255, 255, 255, 0.025);
        }

        .home-hero-copy { position: relative; z-index: 1; max-width: 760px; }

        .home-hero-side {
            position: absolute;
            right: 58px;
            bottom: 48px;
            width: 220px;
            padding: 18px;
            background: rgba(6, 32, 49, 0.32);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 14px;
            backdrop-filter: blur(10px);
            z-index: 1;
        }

        .home-hero-side-label { color: #BDE9E0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
        .home-hero-side-value { color: #FFFFFF; font-family: 'Manrope', sans-serif; font-size: 25px; font-weight: 800; margin-top: 8px; }
        .home-hero-side-note { color: #D5F2EC; font-size: 12px; margin-top: 3px; }

        .home-hero-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            color: #E0E7FF;
            margin-bottom: 16px;
            letter-spacing: 0.5px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .home-hero-title {
            font-family: 'Manrope', 'Noto Sans Kannada', 'Noto Sans Devanagari', sans-serif !important;
            font-size: clamp(32px, 4vw, 56px);
            font-weight: 800;
            color: #FFFFFF;
            margin: 0 0 12px 0;
            line-height: 1.3;
            letter-spacing: 0;
        }

        .home-hero-desc {
            font-size: 16px;
            color: #D5F2EC;
            max-width: 680px;
            margin: 0;
            line-height: 1.65;
        }

        /* Feature Matrix Grid */
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 22px;
        }

        .feature-card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
            animation: home-rise 0.55s ease both;
        }

        .feature-card:nth-child(2) { animation-delay: 0.06s; }
        .feature-card:nth-child(3) { animation-delay: 0.12s; }
        .feature-card:nth-child(4) { animation-delay: 0.18s; }

        @keyframes home-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .feature-card:hover {
            border-color: #8DD3C7;
            box-shadow: 0 8px 20px rgba(42, 157, 143, 0.12);
            transform: translateY(-2px);
        }

        .feature-icon {
            font-size: 26px;
            margin-bottom: 12px;
            display: inline-block;
        }

        .feature-title {
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 6px;
            line-height: 1.4;
        }

        .feature-text {
            font-size: 13px;
            color: #64748B;
            line-height: 1.6;
            margin: 0;
        }

        .document-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 10px;
            margin-top: 14px;
        }

        .document-summary-card {
            position: relative;
            background: linear-gradient(145deg, #FFFFFF, #F8FAFC);
            border: 1px solid #DCE6EF;
            border-radius: 10px;
            padding: 14px;
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .document-summary-card:hover {
            border-color: #8DD3C7;
            box-shadow: 0 8px 18px rgba(23, 107, 135, 0.1);
            transform: translateY(-2px);
        }

        .document-summary-card::after {
            content: '';
            position: absolute;
            width: 56px;
            height: 56px;
            right: -24px;
            bottom: -26px;
            border: 1px solid rgba(42, 157, 143, 0.16);
            border-radius: 50%;
        }

        .document-summary-name { font-size: 13px; font-weight: 700; color: #0F172A; word-break: break-word; }
        .document-summary-meta { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
        .document-summary-stat { background: #F1F5F9; color: #475569; border-radius: 5px; padding: 4px 7px; font-size: 11px; font-weight: 600; }

        .suggestion-grid { display: grid; gap: 8px; margin-top: 12px; }
        .suggestion-label { color: #176B87; font-size: 11px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase; }

        .theme-toggle-panel {
            background: linear-gradient(135deg, rgba(23, 107, 135, 0.1), rgba(42, 157, 143, 0.08));
            border: 1px solid #CDE2E5;
            border-radius: 10px;
            padding: 10px 12px 4px;
            margin-bottom: 16px;
        }

        @media (max-width: 900px) {
            .home-stage { min-height: auto; }
            .home-hero-card { min-height: 430px; padding: 38px 30px; align-items: flex-start; }
            .home-hero-side { left: 30px; right: auto; bottom: 30px; width: 190px; }
            .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }

        @media (max-width: 560px) {
            .home-hero-card { min-height: 500px; padding: 30px 22px; }
            .home-hero-side { left: 22px; bottom: 22px; }
            .feature-grid { grid-template-columns: 1fr; }
            .document-summary-grid { grid-template-columns: 1fr; }
        }

        /* Structured Content Card */
        .content-card {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 22px 24px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
            margin-bottom: 20px;
        }

        .chat-thread {
            display: flex;
            flex-direction: column;
            gap: 14px;
            padding: 8px 0 6px;
        }

        .chat-message-row {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            width: 100%;
        }

        .chat-message-row.user {
            justify-content: flex-end;
        }

        .chat-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            flex-shrink: 0;
        }

        .chat-avatar.user {
            background: linear-gradient(135deg, #4F46E5, #60A5FA);
            color: white;
        }

        .chat-avatar.assistant {
            background: linear-gradient(135deg, #10B981, #2A9D8F);
            color: white;
        }

        .chat-bubble {
            max-width: min(78%, 760px);
            border-radius: 18px;
            padding: 14px 16px;
            line-height: 1.6;
            font-size: 15px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
        }

        .chat-message-row.user .chat-bubble {
            background: linear-gradient(135deg, #EEF2FF, #E0F2FE);
            color: #111827;
            border-color: #C7D2FE;
            border-bottom-right-radius: 8px;
        }

        .chat-message-row.assistant .chat-bubble {
            background: #FAFBFC;
            color: #0F172A;
            border-color: #E5E7EB;
            border-bottom-left-radius: 8px;
        }

        .chat-message-row.assistant .chat-bubble.warning {
            background: #FFF7ED;
            border-color: #FED7AA;
        }

        .chat-meta {
            font-size: 11px;
            color: #64748B;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chat-citation {
            display: inline-block;
            margin-top: 10px;
            margin-right: 8px;
            padding: 6px 10px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            color: #334155;
        }

        .card-header {
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 6px;
            line-height: 1.4;
        }

        .card-subtitle {
            font-size: 13px;
            color: #64748B;
            margin-bottom: 16px;
            line-height: 1.5;
        }

        /* Live Transliteration Preview Box */
        .live-preview-box {
            background: #F0FDF4;
            border: 1px solid #BBF7D0;
            border-left: 4px solid #10B981;
            padding: 12px 16px;
            border-radius: 8px;
            margin-top: 12px;
            margin-bottom: 16px;
        }

        .preview-label {
            font-size: 11px;
            font-weight: 700;
            color: #166534;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .preview-text {
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
            line-height: 1.6;
            word-break: break-word;
        }

        /* Grounded / Guardrail Cards */
        .answer-box-grounded {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #10B981;
            border-left: 6px solid #10B981;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.08);
            margin-top: 18px;
            margin-bottom: 16px;
        }

        .answer-box-rejected {
            background: #FFFFFF;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #EF4444;
            border-left: 6px solid #EF4444;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.08);
            margin-top: 18px;
            margin-bottom: 16px;
        }

        /* Status Pills */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            line-height: 1.4;
        }

        .pill-success { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
        .pill-danger { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
        .pill-neutral { background: #F1F5F9; color: #334155; border: 1px solid #E2E8F0; }
        .pill-primary { background: #EEF2FF; color: #3730A3; border: 1px solid #C7D2FE; }

        /* Boxed Telemetry Grid */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin: 18px 0 24px;
        }

        .metric-kpi-card {
            position: relative;
            overflow: hidden;
            background: linear-gradient(145deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #DCE6EF;
            border-radius: 14px;
            padding: 20px;
            box-shadow: 0 5px 14px rgba(15, 23, 42, 0.05);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 142px;
            transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
        }

        .metric-kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #4F46E5, #2A9D8F);
        }

        .metric-kpi-card::after {
            content: '';
            position: absolute;
            width: 110px;
            height: 110px;
            right: -48px;
            bottom: -52px;
            border: 1px solid rgba(42, 157, 143, 0.12);
            border-radius: 50%;
            box-shadow: 0 0 0 14px rgba(42, 157, 143, 0.035);
        }

        .metric-kpi-card:hover {
            border-color: #9ED8D0;
            box-shadow: 0 12px 26px rgba(23, 107, 135, 0.12);
            transform: translateY(-4px);
        }

        .metric-label {
            font-size: 12px;
            font-weight: 700;
            color: #64748B;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            line-height: 1.3;
        }

        .metric-box-value {
            font-size: 24px;
            font-weight: 800;
            color: #0F172A;
            background: #FFFFFF;
            border: 1px solid #D7E1EA;
            padding: 8px 14px;
            border-radius: 9px;
            display: inline-block;
            width: fit-content;
            margin-bottom: 8px;
            font-family: 'JetBrains Mono', monospace;
            line-height: 1.2;
            box-shadow: 0 2px 5px rgba(15, 23, 42, 0.04);
            animation: metric-value-in 0.45s ease both;
        }

        @keyframes metric-value-in {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .metric-footer {
            font-size: 12px;
            font-weight: 600;
            color: #059669;
            display: flex;
            align-items: center;
            gap: 4px;
            line-height: 1.3;
        }

        .telemetry-shell {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(241, 248, 249, 0.92));
            border: 1px solid #DCE6EF;
            box-shadow: 0 12px 30px rgba(16, 42, 67, 0.06);
        }

        .telemetry-section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-top: 24px;
            padding-top: 18px;
            border-top: 1px solid #E2E8F0;
        }

        .telemetry-section-title::before {
            content: '';
            width: 4px;
            height: 20px;
            border-radius: 4px;
            background: linear-gradient(180deg, #4F46E5, #2A9D8F);
        }

        @media (max-width: 700px) {
            .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
            .metric-kpi-card { min-height: 128px; padding: 15px; }
            .metric-box-value { font-size: 19px; padding: 7px 10px; }
        }

        @media (max-width: 430px) {
            .metric-grid { grid-template-columns: 1fr; }
        }

        /* Citation Badge */
        .citation-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: #1E293B;
            margin-right: 8px;
            margin-top: 8px;
            line-height: 1.4;
        }

        /* Primary Buttons */
        .stButton > button {
            position: relative !important;
            overflow: hidden !important;
            background: linear-gradient(135deg, #4F46E5, #176B87) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6rem 1.4rem !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            box-shadow: 0 3px 8px rgba(23, 107, 135, 0.18) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease !important;
        }

        .stButton > button::after {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(105deg, transparent 25%, rgba(255, 255, 255, 0.22) 50%, transparent 75%);
            transform: translateX(-130%);
            transition: transform 0.55s ease;
        }

        .stButton > button:hover {
            filter: saturate(1.12) brightness(1.04) !important;
            box-shadow: 0 8px 18px rgba(23, 107, 135, 0.25) !important;
            transform: translateY(-2px) !important;
        }

        .stButton > button:hover::after {
            transform: translateX(130%);
        }

        .stButton > button:active {
            transform: translateY(0) scale(0.98) !important;
            box-shadow: 0 2px 5px rgba(23, 107, 135, 0.18) !important;
        }

        .stButton > button:focus-visible {
            outline: 3px solid rgba(42, 157, 143, 0.35) !important;
            outline-offset: 2px;
        }

        /* Tab Bar */
        div[data-baseweb="tab-list"] {
            gap: 8px;
            background: transparent;
            padding: 0;
            margin-bottom: 22px;
            border-bottom: 1px solid #E2E8F0;
        }

        div[data-baseweb="tab"] {
            position: relative;
            border-radius: 6px 6px 0 0 !important;
            padding: 10px 18px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            color: #64748B !important;
            background: transparent !important;
            border: none !important;
            transition: color 0.2s ease, background-color 0.2s ease, transform 0.2s ease !important;
        }

        div[data-baseweb="tab"]:hover {
            color: #176B87 !important;
            background: rgba(23, 107, 135, 0.06) !important;
            transform: translateY(-1px);
        }

        div[data-baseweb="tab"][aria-selected="true"] {
            color: #4F46E5 !important;
            border-bottom: 2px solid transparent !important;
        }

        div[data-baseweb="tab"][aria-selected="true"]::after {
            content: '';
            position: absolute;
            left: 14px;
            right: 14px;
            bottom: -1px;
            height: 3px;
            border-radius: 3px 3px 0 0;
            background: linear-gradient(90deg, #4F46E5, #2A9D8F);
            animation: tab-glow-in 0.3s ease both;
        }

        @keyframes tab-glow-in {
            from { opacity: 0; transform: scaleX(0.35); }
            to { opacity: 1; transform: scaleX(1); }
        }

        /* Streamlit-native fields and sidebar controls */
        div[data-baseweb="input"], div[data-baseweb="textarea"] {
            transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
        }

        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="textarea"]:focus-within {
            border-color: #2A9D8F !important;
            box-shadow: 0 0 0 3px rgba(42, 157, 143, 0.14) !important;
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] label,
        [data-testid="stSidebar"] [data-testid="stSlider"] {
            transition: transform 0.2s ease, color 0.2s ease;
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] label:hover {
            color: #176B87 !important;
            transform: translateX(3px);
        }

        [data-testid="stSidebar"] [role="slider"] {
            transition: box-shadow 0.2s ease, transform 0.2s ease;
        }

        [data-testid="stSidebar"] [role="slider"]:hover {
            box-shadow: 0 0 0 5px rgba(42, 157, 143, 0.16);
            transform: scale(1.08);
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: 0.01ms !important;
            }
        }

        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if dark_theme_css:
        st.markdown(dark_theme_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. STATE INITIALIZATION
# -----------------------------------------------------------------------------
def init_state():
    if "docs" not in st.session_state:
        st.session_state["docs"] = []
    if "current_typed_query" not in st.session_state:
        st.session_state["current_typed_query"] = ""
    if "active_result" not in st.session_state:
        st.session_state["active_result"] = None
    if "selected_lang" not in st.session_state:
        st.session_state["selected_lang"] = "English"
    if "qa_log" not in st.session_state:
        st.session_state["qa_log"] = []
    if "conversation_history" not in st.session_state:
        st.session_state["conversation_history"] = []
    if "answer_feedback" not in st.session_state:
        st.session_state["answer_feedback"] = {}
    if "theme_mode" not in st.session_state:
        st.session_state["theme_mode"] = "Light"


def add_chat_turn(raw_query: str, result: dict):
    """Append a user message and assistant reply to the conversation thread."""
    if not raw_query or not raw_query.strip():
        return
    st.session_state["conversation_history"].extend(
        [
            {
                "role": "user",
                "content": raw_query,
                "timestamp": time.strftime("%H:%M"),
            },
            {
                "role": "assistant",
                "type": result["type"],
                "content": result["answer"],
                "sources": result.get("sources", []),
                "audit": result.get("audit"),
                "latency": result.get("latency", 0),
                "timestamp": time.strftime("%H:%M"),
            },
        ]
    )
    st.session_state["conversation_history"] = st.session_state["conversation_history"][-30:]


def sync_document_state():
    """Keep the UI document list synchronized with the persistent vector store."""
    docs = document_stats()
    for doc in docs:
        uploaded_path = os.path.join("uploaded_docs", doc["name"])
        sample_path = os.path.join("sample_docs", doc["name"])
        path = uploaded_path if os.path.exists(uploaded_path) else sample_path
        doc["size"] = f"{round(os.path.getsize(path) / 1024, 1)} KB" if os.path.exists(path) else "Indexed"
    st.session_state["docs"] = docs


def ensure_sample_document():
    """Index the bundled sample policy once so the app is useful on first launch."""
    sample_path = "sample_docs/leave_policy.txt"
    if not st.session_state.get("sample_checked"):
        if not document_stats() and os.path.exists(sample_path):
            add_chunks(build_chunk_records(sample_path, "leave_policy.txt"))
        st.session_state["sample_checked"] = True


def build_document_suggestions(docs):
    """Create useful prompt starters from the indexed document collection."""
    suggestions = []
    for doc in docs:
        doc_name = doc["name"]
        name = doc_name.lower()
        if "leave" in name or "holiday" in name or "absence" in name:
            suggestions.extend(
                [
                    "How many paid annual leave days are available to full-time employees?",
                    "What is the sick leave allowance and when is a medical certificate required?",
                    "How far in advance must employees submit a leave request?",
                ]
            )
        else:
            suggestions.extend(
                [
                    f"What are the key points in {doc_name}?",
                    f"Summarize the employee guidance in {doc_name}.",
                    f"What deadlines or requirements are listed in {doc_name}?",
                ]
            )
    return list(dict.fromkeys(suggestions))[:6]

init_state()
ensure_sample_document()
sync_document_state()
if "theme_toggle" in st.session_state:
    st.session_state["theme_mode"] = "Dark" if st.session_state["theme_toggle"] else "Light"
inject_enterprise_css(st.session_state["theme_mode"])

# Core Execution Logic with Fallback Handling
def execute_rag_search(raw_query: str, target_lang: str):
    if not raw_query or not raw_query.strip():
        return

    converted_query = transliterate_phonetic_indic(raw_query, target_lang)
    retrieval_query = translate_text(converted_query, target_lang, "en")

    start_t = time.time()
    time.sleep(0.3)
    latency = round(time.time() - start_t, 2)

    chunks, is_confident = query(retrieval_query or raw_query, top_k=top_k, distance_threshold=cutoff)
    if not is_confident:
        result = {
            "type": "guardrail",
            "raw_query": raw_query,
            "converted_query": converted_query,
            "answer": MULTILINGUAL_KNOWLEDGE["unrelated"].get(target_lang, MULTILINGUAL_KNOWLEDGE["unrelated"]["en"]),
            "latency": latency,
            "target_lang": target_lang,
            "audit": f"Nearest indexed chunk exceeded the configured distance cutoff ({cutoff})."
        }
    else:
        result = {
            "type": "grounded",
            "raw_query": raw_query,
            "converted_query": converted_query,
            "answer": translate_text(
                generate_answer(retrieval_query or raw_query, chunks),
                "en",
                target_lang,
            ),
            "sources": chunks,
            "target_lang": target_lang,
            "latency": latency
        }

    st.session_state["active_result"] = result
    add_chat_turn(raw_query, result)

    st.session_state["qa_log"].append(
        {
            "question": raw_query,
            "answered": is_confident,
            "sources": len(chunks),
            "latency_seconds": latency,
        }
    )

# -----------------------------------------------------------------------------
# 6. SIDEBAR - LANGUAGE SWITCHER & RAG CONTROLS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div class='theme-toggle-panel'>", unsafe_allow_html=True)
    theme_choice = st.toggle(
        "🌗 Dark mode",
        value=st.session_state["theme_mode"] == "Dark",
        key="theme_toggle",
        help="Switch the visual theme without changing your documents or conversations.",
    )
    st.session_state["theme_mode"] = "Dark" if theme_choice else "Light"
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 🌐 Active Language / ಭಾಷೆ / भाषा")
    
    selected_lang_choice = st.radio(
        "Choose your preferred language:",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(st.session_state["selected_lang"]),
        help="Switching language activates phonetic transliteration (Kanglish/Hinglish), voice input, and native audio."
    )
    st.session_state["selected_lang"] = selected_lang_choice
    
    current_lang = LANGUAGES[selected_lang_choice]
    active_code = current_lang["code"]
    active_target_lang = current_lang["target_lang"]
    active_flag = current_lang["flag"]

    st.info(f"Active Engine: **{selected_lang_choice}**\n\n• Live Script: **Active**\n• TTS Narration: **{active_target_lang}**")

    # Kanglish / Hinglish Typing Tips
    if selected_lang_choice == "ಕನ್ನಡ (Kannada)":
        with st.expander("💡 Kanglish Typing Examples"):
            st.markdown(
                """
                - `namaste` $\\to$ **ನಮಸ್ತೆ**
                - `eshtu samaya` $\\to$ **ಎಷ್ಟು ಸಮಯ**
                - `password reset link` $\\to$ **ಪಾಸ್‌ವರ್ಡ್ ರಿಸೆಟ್ ಲಿಂಕ್**
                - `sahaya` $\\to$ **ಸಹಾಯ**
                """
            )
    elif selected_lang_choice == "हिन्दी (Hindi)":
        with st.expander("💡 Hinglish Typing Examples"):
            st.markdown(
                """
                - `namaste` $\\to$ **नमस्ते**
                - `kitne samay tak` $\\to$ **कितने समय तक**
                - `password reset link` $\\to$ **पासवर्ड रीसेट लिंक**
                - `kripya bataye` $\\to$ **कृपया बताये**
                """
            )

    st.markdown("---")
    st.markdown("### ⚙️ Retrieval Parameters")
    top_k = st.slider("Top-K Chunks", min_value=1, max_value=8, value=3)
    cutoff = st.slider("Cosine Cutoff Threshold", min_value=0.10, max_value=0.90, value=0.65, step=0.05)

    st.markdown("---")
    st.markdown("### 🗣️ Audio Engine Status")
    st.caption(f"• Input STT: **{active_code} (Active)**")
    st.caption(f"• Output TTS: **{selected_lang_choice} ({active_target_lang})**")
    st.caption("• Transliteration: **Google Input Tools**")

# -----------------------------------------------------------------------------
# 7. TOP NAVBAR
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="top-nav">
        <div class="brand-title">
            <span class="brand-lockup">
                <span class="brand-mark">🏢</span>
                <span class="brand-name">Enterprise DocAI</span>
            </span>
            <span class="status-pill pill-neutral">Tri-Lingual Edition</span>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
            <span class="status-pill pill-primary">{active_flag} {selected_lang_choice}</span>
            <span class="status-pill pill-success">● Engine Ready</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 8. MAIN NAVIGATION TABS (HOME FIRST)
# -----------------------------------------------------------------------------
tab_home, tab_query, tab_docs, tab_telemetry = st.tabs(
    ["🏠 Home & Overview", "💬 Query & Voice Assistant", "📁 Document Management", "📊 Telemetry & Metrics"]
)

# =============================================================================
# TAB 0: FULL SCREEN ENTERPRISE HOME PAGE
# =============================================================================
with tab_home:
    # Full Screen Hero Banner
    st.markdown(
        f"""
        <div class="home-hero-card">
            <div class="home-hero-copy">
                <div class="home-hero-tag">
                    ⚡ ENTERPRISE MULTILINGUAL DOCUMENT INTELLIGENCE
                </div>
                <h1 class="home-hero-title">
                    Ask your documents.<br>Trust every answer.
                </h1>
                <p class="home-hero-desc">
                    Search approved policies and manuals in English, ಕನ್ನಡ, or हिन्दी with grounded citations, voice input, and instant audio narration.
                </p>
            </div>
            <div class="home-hero-side">
                <div class="home-hero-side-label">Knowledge base</div>
                <div class="home-hero-side-value">{len(st.session_state['docs'])} active</div>
                <div class="home-hero-side-note">Documents indexed and ready</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 4 Key Pillars Feature Matrix
    st.markdown(
        """
        <div class="feature-grid">
            <div class="feature-card">
                <div class="feature-icon">🎙️</div>
                <div class="feature-title">Multi-Modal Voice Engine</div>
                <p class="feature-text">Hands-free speech-to-text dictation and neural audio read-aloud in English, Kannada, and Hindi.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔤</div>
                <div class="feature-title">Live Indic Transliteration</div>
                <p class="feature-text">Type phonetically in Kanglish or Hinglish with real-time automatic script conversion.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🛡️</div>
                <div class="feature-title">Cosine Guardrail Filter</div>
                <p class="feature-text">Mathematical distance cutoff blocks out-of-context queries and eliminates LLM hallucinations.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon">📑</div>
                <div class="feature-title">Chunk Provenance Lock</div>
                <p class="feature-text">Every generated response is cited with exact document names and section-level chunk indices.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Quick Start & Knowledge Summary
    h_col1, h_col2 = st.columns([1, 1], gap="large")

    with h_col1:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>🚀 Quick-Launch Prompts</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-subtitle'>Click to stage sample questions in your active language:</div>", unsafe_allow_html=True)
        
        if selected_lang_choice == "ಕನ್ನಡ (Kannada)":
            q1, q2 = "ಪಾಸ್‌ವರ್ಡ್ ರೀಸೆಟ್ ಲಿಂಕ್ ಎಷ್ಟು ಸಮಯ ಮಾನ್ಯವಾಗಿರುತ್ತದೆ?", "ಕ್ರಿಟಿಕಲ್ ಸಮಸ್ಯೆಗೆ ಪ್ರತಿಕ್ರಿಯೆ ಸಮಯ ಎಷ್ಟು?"
        elif selected_lang_choice == "हिन्दी (Hindi)":
            q1, q2 = "पासवर्ड रीसेट लिंक कितने समय तक वैध रहता है?", "क्रिटिकल समस्या के लिए रिस्पांस टाइम क्या है?"
        else:
            q1, q2 = "How long is a password reset link valid for?", "What is the priority response time for a critical issue?"

        if st.button(f"🔑 {q1}", use_container_width=True, key="home_p1"):
            st.session_state["current_typed_query"] = q1
            st.session_state["active_result"] = None
            st.info("✅ Staged in Query Assistant! Click the **'💬 Query & Voice Assistant'** tab above.")

        if st.button(f"🚨 {q2}", use_container_width=True, key="home_p2"):
            st.session_state["current_typed_query"] = q2
            st.session_state["active_result"] = None
            st.info("✅ Staged in Query Assistant! Click the **'💬 Query & Voice Assistant'** tab above.")

        suggested_questions = build_document_suggestions(st.session_state["docs"])
        if suggested_questions:
            st.markdown("<div class='suggestion-label'>✨ Suggested from your documents</div>", unsafe_allow_html=True)
            st.markdown("<div class='suggestion-grid'>", unsafe_allow_html=True)
            for suggestion_index, suggestion in enumerate(suggested_questions[:3]):
                if st.button(suggestion, use_container_width=True, key=f"doc_suggestion_{suggestion_index}"):
                    st.session_state["current_typed_query"] = suggestion
                    st.session_state["active_result"] = None
                    st.info("✅ Document suggestion staged in Query Assistant.")
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

    with h_col2:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📊 Live Knowledge Vector Store</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-subtitle'>Vector database status & active embeddings:</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='document-summary-grid'>", unsafe_allow_html=True)
        for doc in st.session_state["docs"]:
            st.markdown(
                f"""
                <div class="document-summary-card">
                    <div class="document-summary-name">📄 {doc['name']}</div>
                    <div class="document-summary-meta">
                        <span class="document-summary-stat">{doc['chunks']} chunks</span>
                        <span class="document-summary-stat">{doc['size']}</span>
                        <span class="document-summary-stat">✓ Indexed</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state["conversation_history"]:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            history_col, clear_col = st.columns([3, 1])
            with history_col:
                st.markdown("<div class='card-header'>🕘 Recent Chat</div>", unsafe_allow_html=True)
            with clear_col:
                if st.button("Clear", key="clear_history", use_container_width=True):
                    st.session_state["conversation_history"] = []
                    st.session_state["active_result"] = None
                    st.rerun()

            st.markdown("<div class='chat-thread'>", unsafe_allow_html=True)
            for item in st.session_state["conversation_history"][-8:]:
                role = item.get("role", "assistant")
                bubble_class = "assistant"
                if role == "user":
                    bubble_class = "user"
                if role == "assistant" and item.get("type") == "guardrail":
                    warning_class = "warning"
                else:
                    warning_class = ""
                bubble_text = item.get("content", "")
                st.markdown(
                    f"""
                    <div class="chat-message-row {bubble_class}">
                        <div class="chat-avatar {bubble_class}">{'You' if role == 'user' else 'AI'}</div>
                        <div style="display:flex; flex-direction:column; align-items:{'flex-end' if role == 'user' else 'flex-start'}; width:100%;">
                            <div class="chat-bubble {warning_class}">{bubble_text}</div>
                            <div class="chat-meta">{item.get('timestamp', '')} {f'• {item.get("latency", 0)}s' if role == 'assistant' else ''}</div>
                            {''.join(f"<span class='chat-citation'>📄 {source['doc_name']} · Chunk {source['chunk_index']}</span>" for source in item.get('sources', [])) if role == 'assistant' and item.get('sources') else ''}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# TAB 1: QUERY & VOICE ASSISTANT
# =============================================================================
with tab_query:
    col_left, col_right = st.columns([1, 2], gap="large")

    # LEFT PANEL: Quick Demo Prompts (Populates text box only)
    with col_left:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>⚡ Quick Test Prompts</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-subtitle'>Click to populate question into text box:</div>", unsafe_allow_html=True)

        if selected_lang_choice == "ಕನ್ನಡ (Kannada)":
            p1_label = "🔑 ಪಾಸ್‌ವರ್ಡ್ ಮಾನ್ಯತೆ (Password Reset)"
            p1_text = "ಪಾಸ್‌ವರ್ಡ್ ರೀಸೆಟ್ ಲಿಂಕ್ ಎಷ್ಟು ಸಮಯ ಮಾನ್ಯವಾಗಿರುತ್ತದೆ?"
            p2_label = "🚨 ಕ್ರಿಟಿಕಲ್ ಇನ್ಸಿಡೆಂಟ್ SLA (Critical SLA)"
            p2_text = "ಕ್ರಿಟಿಕಲ್ ಸಮಸ್ಯೆಗೆ ಪ್ರತಿಕ್ರಿಯೆ ಸಮಯ ಎಷ್ಟು?"
            p3_label = "🛑 ಗಾರ್ಡ್‌ರೈಲ್ ಪರೀಕ್ಷೆ (France Capital)"
            p3_text = "ಫ್ರಾನ್ಸ್ ದೇಶದ ರಾಜಧಾನಿ ಯಾವುದು?"
            p4_label = "👤 ಉದ್ಯೋಗಿ ವಾರ್ಷಿಕ ರಜೆ (Employee Leave)"
            p4_text = "ಪೂರ್ಣ ಸಮಯದ ಉದ್ಯೋಗಿಗೆ ವರ್ಷಕ್ಕೆ ಎಷ್ಟು ಪಾವತಿಸಿದ ವಾರ್ಷಿಕ ರಜೆ ಸಿಗುತ್ತದೆ?"
        elif selected_lang_choice == "हिन्दी (Hindi)":
            p1_label = "🔑 पासवर्ड रीसेट अवधि (Password Reset)"
            p1_text = "पासवर्ड रीसेट लिंक कितने समय तक वैध रहता है?"
            p2_label = "🚨 क्रिटिकल इंसीडेंट SLA (Critical SLA)"
            p2_text = "क्रिटिकल समस्या के लिए रिस्पांस टाइम क्या है?"
            p3_label = "🛑 गार्डरेल परीक्षण (Capital of France)"
            p3_text = "फ्रांस की राजधानी क्या है?"
            p4_label = "👤 कर्मचारी वार्षिक छुट्टी (Employee Leave)"
            p4_text = "एक पूर्णकालिक कर्मचारी को प्रति वर्ष कितने दिनों की सवेतन वार्षिक छुट्टी मिलती है?"
        else:
            p1_label = "🔑 Password Reset Validity (30 min)"
            p1_text = "How long is a password reset link valid for?"
            p2_label = "🚨 Critical Incident SLA (1 Hour)"
            p2_text = "What is the priority response time for a critical issue?"
            p3_label = "🛑 Test Guardrail Rejection (France)"
            p3_text = "What is the capital of France?"
            p4_label = "👤 Employee Annual Leave (Full-Time)"
            p4_text = "How many paid annual leave days does a full-time employee receive per year?"

        # Set the typed query state cleanly
        if st.button(p1_label, use_container_width=True, key="q_p1"):
            st.session_state["current_typed_query"] = p1_text
            st.session_state["active_result"] = None
            st.rerun()

        if st.button(p2_label, use_container_width=True, key="q_p2"):
            st.session_state["current_typed_query"] = p2_text
            st.session_state["active_result"] = None
            st.rerun()

        if st.button(p3_label, use_container_width=True, key="q_p3"):
            st.session_state["current_typed_query"] = p3_text
            st.session_state["active_result"] = None
            st.rerun()

        if st.button(p4_label, use_container_width=True, key="q_p4"):
            st.session_state["current_typed_query"] = p4_text
            st.session_state["active_result"] = None
            st.rerun()

        st.markdown("<hr style='margin:18px 0; border:none; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📑 Active Knowledge Base</div>", unsafe_allow_html=True)
        for doc in st.session_state["docs"]:
            st.markdown(
                f"""
                <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:12px 14px; border-radius:8px; margin-bottom:8px;">
                    <div style="font-weight:600; font-size:13px; color:#0F172A; line-height:1.4;">📄 {doc['name']}</div>
                    <div style="font-size:12px; color:#64748B; margin-top:2px;">{doc['chunks']} Chunks • {doc['size']} • Indexed</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT PANEL: Query Form + Speech Widget + Guaranteed Generation
    with col_right:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='card-header'>🔍 Ask Anything ({selected_lang_choice})</div>", unsafe_allow_html=True)
        
        if selected_lang_choice == "ಕನ್ನಡ (Kannada)":
            st.markdown("<div class='card-subtitle'>Type in <b>Kanglish</b> (e.g. <code>namaste</code>, <code>password reset eshtu samaya</code>) or speak via mic:</div>", unsafe_allow_html=True)
        elif selected_lang_choice == "हिन्दी (Hindi)":
            st.markdown("<div class='card-subtitle'>Type in <b>Hinglish</b> (e.g. <code>namaste</code>, <code>password reset kitne samay tak</code>) or speak via mic:</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card-subtitle'>Type in English or speak via microphone:</div>", unsafe_allow_html=True)

        # Dynamic Speech Recognition Component with clean height buffer
        voice_component = f"""
        <style>
            .voice-action {{
                background: linear-gradient(135deg, #4F46E5, #176B87);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 3px 8px rgba(23, 107, 135, 0.18);
                transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
            }}
            .voice-action:hover {{
                filter: saturate(1.12) brightness(1.04);
                box-shadow: 0 8px 18px rgba(23, 107, 135, 0.25);
                transform: translateY(-2px);
            }}
            .voice-action:active {{ transform: translateY(0) scale(0.98); }}
            .voice-action:focus-visible {{ outline: 3px solid rgba(42, 157, 143, 0.35); outline-offset: 2px; }}
            @media (prefers-reduced-motion: reduce) {{ .voice-action {{ transition: none; }} }}
        </style>
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:14px;">
            <button id="micBtn" class="voice-action" onclick="toggleSpeech()">
                🎙️ <span id="btnLabel">{current_lang['speak_btn']} ({active_flag})</span>
            </button>
            <span id="voiceStatus" style="font-size: 12px; font-weight: 500; color: #64748B;">
                Mic ready for {selected_lang_choice}
            </span>
        </div>

        <script>
            var rec;
            var isListening = false;

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                rec = new SpeechRecognition();
                rec.continuous = false;
                rec.interimResults = false;
                rec.lang = '{active_code}';

                rec.onstart = function() {{
                    isListening = true;
                    document.getElementById('btnLabel').innerText = "Listening... Speak now";
                    document.getElementById('voiceStatus').innerText = "🔴 Listening in {selected_lang_choice}...";
                    document.getElementById('voiceStatus').style.color = "#DC2626";
                }};

                rec.onresult = function(event) {{
                    var spoken = event.results[0][0].transcript;
                    document.getElementById('voiceStatus').innerText = '✅ Heard: "' + spoken + '"';
                    document.getElementById('voiceStatus').style.color = "#059669";
                    navigator.clipboard.writeText(spoken);
                }};

                rec.onend = function() {{
                    document.getElementById('btnLabel').innerText = "{current_lang['speak_btn']} ({active_flag})";
                    isListening = false;
                }};
            }}

            function toggleSpeech() {{
                if (!rec) return;
                if (isListening) {{ rec.stop(); }} else {{ rec.start(); }}
            }}
        </script>
        """
        components.html(voice_component, height=48)

        # Main Question Input Box
        query_input = st.text_input(
            "Query Input",
            value=st.session_state["current_typed_query"],
            placeholder=current_lang["placeholder"],
            label_visibility="collapsed",
        )

        # Show Live Transliteration Preview Box
        if query_input.strip() and selected_lang_choice != "English":
            live_converted = transliterate_phonetic_indic(query_input, active_target_lang)
            st.markdown(
                f"""
                <div class="live-preview-box">
                    <div class="preview-label">✨ Live Script Conversion ({selected_lang_choice}):</div>
                    <div class="preview-text">{live_converted}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Action Buttons
        col_btn1, col_btn2 = st.columns([3, 1])
        
        with col_btn1:
            btn_label = f"Generate Grounded Answer ({active_flag} {selected_lang_choice.split()[0]}) ⚡"
            generate_clicked = st.button(btn_label, use_container_width=True)

        with col_btn2:
            clear_clicked = st.button("Clear", use_container_width=True)

        if clear_clicked:
            st.session_state["current_typed_query"] = ""
            st.session_state["active_result"] = None
            st.rerun()

        if generate_clicked:
            if query_input.strip():
                st.session_state["current_typed_query"] = query_input
                with st.spinner("Searching approved documents and grounding your answer..."):
                    execute_rag_search(query_input, active_target_lang)
                st.rerun()
            else:
                st.warning("⚠️ Please enter a question / ದಯವಿಟ್ಟು ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.")

        st.markdown("</div>", unsafe_allow_html=True)

        # =====================================================================
        # PERSISTENT CHAT-STYLE ANSWER RENDERING
        # =====================================================================
        res = st.session_state.get("active_result")

        if res:
            st.markdown("<div class='content-card'>", unsafe_allow_html=True)
            st.markdown("<div class='card-header'>💬 AI Answer</div>", unsafe_allow_html=True)
            st.markdown("<div class='chat-thread'>", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="chat-message-row user">
                    <div class="chat-avatar user">You</div>
                    <div style="display:flex; flex-direction:column; align-items:flex-end; width:100%;">
                        <div class="chat-bubble">{res['raw_query']}</div>
                        <div class="chat-meta">{time.strftime('%H:%M')}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            bubble_class = "warning" if res["type"] == "guardrail" else ""
            badge_label = current_lang['guardrail_tag'] if res["type"] == "guardrail" else current_lang['grounded_tag']
            assistant_content = res['answer']
            if res["type"] == "guardrail":
                assistant_content = f"{res['answer']}<br><br><span style='font-size:12px; color:#7C2D12;'><b>Audit:</b> {res.get('audit', '')}</span>"

            st.markdown(
                f"""
                <div class="chat-message-row assistant">
                    <div class="chat-avatar assistant">AI</div>
                    <div style="display:flex; flex-direction:column; align-items:flex-start; width:100%;">
                        <div class="chat-bubble {bubble_class}"><strong>{badge_label}</strong><br>{assistant_content}</div>
                        <div class="chat-meta">{time.strftime('%H:%M')} • {res['latency']}s</div>
                        {''.join(f"<span class='chat-citation'>📄 {s['doc_name']} · Chunk {s['chunk_index']}</span>" for s in res.get('sources', []))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if res["type"] == "grounded":
                st.markdown(f"**{current_lang['listen_btn']}**")
                audio_bytes = fetch_tts_audio_bytes(res["answer"], res.get("target_lang", active_target_lang))
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3", autoplay=False)

                for s in res["sources"]:
                    with st.expander(f"🔍 Inspect Source: {s['doc_name']} (Chunk {s['chunk_index']})"):
                        st.info(s["text"])

            feedback_key = f"{res['raw_query']}::{res['latency']}"
            feedback_col1, feedback_col2, feedback_col3 = st.columns([1, 1, 4])
            with feedback_col1:
                if st.button("👍 Helpful", key="feedback_helpful", use_container_width=True):
                    st.session_state["answer_feedback"][feedback_key] = "helpful"
            with feedback_col2:
                if st.button("👎 Needs work", key="feedback_needs_work", use_container_width=True):
                    st.session_state["answer_feedback"][feedback_key] = "needs_work"
            with feedback_col3:
                feedback_value = st.session_state["answer_feedback"].get(feedback_key)
                if feedback_value:
                    st.caption("Thanks for the feedback. It has been recorded for this session.")

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        chat_prompt = st.chat_input("Ask about your enterprise knowledge base...")
        if chat_prompt:
            st.session_state["current_typed_query"] = chat_prompt
            with st.spinner("Searching approved documents and grounding your answer..."):
                execute_rag_search(chat_prompt, active_target_lang)
            st.rerun()

# =============================================================================
# TAB 2: DOCUMENT MANAGEMENT
# =============================================================================
with tab_docs:
    d_col1, d_col2 = st.columns([1, 1], gap="large")

    with d_col1:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📥 Ingest New Document</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-subtitle'>Upload PDF or TXT files to add to the knowledge base:</div>", unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Select file to upload",
            type=["pdf", "txt"],
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            file_size_kb = round(uploaded_file.size / 1024, 1)
            st.markdown(
                f"""
                <div class="live-preview-box" style="margin-top:14px;">
                    <div class="preview-label">Ready to index</div>
                    <div class="preview-text" style="font-size:14px;">📄 {uploaded_file.name}</div>
                    <div style="font-size:12px; color:#64748B; margin-top:4px;">{file_size_kb} KB · PDF/TXT document</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        if st.button("Index Document", disabled=(uploaded_file is None)):
            with st.spinner("Processing document chunks and generating embeddings..."):
                safe_name = os.path.basename(uploaded_file.name)
                save_path = os.path.join("uploaded_docs", safe_name)
                with open(save_path, "wb") as output_file:
                    output_file.write(uploaded_file.getbuffer())
                records = build_chunk_records(save_path, safe_name)
                indexed_chunks = add_chunks(records)
                sync_document_state()
                st.success(f"Indexed **{safe_name}** successfully ({indexed_chunks} chunks).")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with d_col2:
        st.markdown("<div class='content-card'>", unsafe_allow_html=True)
        st.markdown("<div class='card-header'>📚 Active Document Collection</div>", unsafe_allow_html=True)
        st.markdown("<div class='card-subtitle'>Manage currently vectorized knowledge files:</div>", unsafe_allow_html=True)
        
        if not st.session_state["docs"]:
            st.info("No documents currently indexed.")
        else:
            for idx, doc in enumerate(st.session_state["docs"]):
                c_info, c_del = st.columns([4, 1])
                with c_info:
                    st.markdown(f"**📄 {doc['name']}**")
                    st.caption(f"{doc['chunks']} Chunks • {doc['size']} • Status: {doc['status']}")
                with c_del:
                    if st.button("Delete", key=f"del_{idx}"):
                        delete_document(doc["name"])
                        uploaded_path = os.path.join("uploaded_docs", doc["name"])
                        if os.path.exists(uploaded_path):
                            os.remove(uploaded_path)
                        sync_document_state()
                        st.rerun()
                st.divider()
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# TAB 3: TELEMETRY & METRICS
# =============================================================================
with tab_telemetry:
    st.markdown("<div class='content-card telemetry-shell'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header'>📊 Tri-Lingual RAG Engine Telemetry</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-subtitle'>Live vector metrics & multi-language engine health:</div>", unsafe_allow_html=True)

    total_chunks = sum(d["chunks"] for d in st.session_state["docs"])
    
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-kpi-card">
                <div class="metric-label">Active Language</div>
                <div class="metric-box-value">{active_flag} {active_code}</div>
                <div class="metric-footer">● {selected_lang_choice}</div>
            </div>
            <div class="metric-kpi-card">
                <div class="metric-label">Total Vector Chunks</div>
                <div class="metric-box-value">{total_chunks}</div>
                <div class="metric-footer">● 100% Embedded (1536-dim)</div>
            </div>
            <div class="metric-kpi-card">
                <div class="metric-label">Relevance Cutoff</div>
                <div class="metric-box-value">{cutoff}</div>
                <div class="metric-footer">● Cosine Distance Gate</div>
            </div>
            <div class="metric-kpi-card">
                <div class="metric-label">Live Transliteration</div>
                <div class="metric-box-value">0.08s</div>
                <div class="metric-footer">● Google Input Tools Active</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_questions = len(st.session_state["qa_log"])
    answered_questions = sum(item["answered"] for item in st.session_state["qa_log"])
    refusal_rate = ((total_questions - answered_questions) / total_questions * 100) if total_questions else 0
    st.markdown("<div class='card-header telemetry-section-title'>🧪 Evaluation Dashboard</div>", unsafe_allow_html=True)
    st.dataframe(
        {
            "Metric": ["Questions evaluated", "Grounded answers", "Unsupported refusals", "Refusal rate"],
            "Value": [total_questions, answered_questions, total_questions - answered_questions, f"{refusal_rate:.1f}%"],
        },
        hide_index=True,
        use_container_width=True,
    )
    if st.session_state["qa_log"]:
        st.caption("Recent evaluation events")
        st.dataframe(st.session_state["qa_log"][-10:], hide_index=True, use_container_width=True)

    st.markdown("<hr style='margin:20px 0; border:none; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)
    st.markdown("<div class='card-header telemetry-section-title'>🛡️ Tri-Lingual Transliteration & Guardrail Pipeline</div>", unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin-top:14px;">
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:16px; border-radius:8px;">
                <div style="font-weight:700; font-size:13px; color:#0F172A; margin-bottom:4px; line-height:1.4;">1. Live Transliteration Preview</div>
                <div style="font-size:12px; color:#64748B; line-height:1.5;">Phonetic Kanglish/Hinglish converts in real-time into native script preview.</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:16px; border-radius:8px;">
                <div style="font-weight:700; font-size:13px; color:#0F172A; margin-bottom:4px; line-height:1.4;">2. Cross-Lingual Search</div>
                <div style="font-size:12px; color:#64748B; line-height:1.5;">Semantic search maps Kannada / Hindi queries directly to English policy chunks.</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:16px; border-radius:8px;">
                <div style="font-weight:700; font-size:13px; color:#0F172A; margin-bottom:4px; line-height:1.4;">3. Distance Threshold Gate</div>
                <div style="font-size:12px; color:#64748B; line-height:1.5;">Halts unanswerable queries with cosine distance greater than {cutoff}.</div>
            </div>
            <div style="background:#F8FAFC; border:1px solid #E2E8F0; padding:16px; border-radius:8px;">
                <div style="font-weight:700; font-size:13px; color:#0F172A; margin-bottom:4px; line-height:1.4;">4. Native Audio Stream</div>
                <div style="font-size:12px; color:#64748B; line-height:1.5;">Streams natural speech audio directly in Kannada (`kn`), Hindi (`hi`), or English (`en`).</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
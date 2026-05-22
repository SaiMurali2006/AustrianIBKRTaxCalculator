"""FinTech Streamlit styling for the Austrian tax dashboard."""

FINTECH_CSS = """
<style>
:root {
    --bg: #0E1117;
    --panel: #151A23;
    --panel-soft: #1B2230;
    --text: #F4F7FB;
    --muted: #8B98A9;
    --blue: #00D4FF;
    --purple: #BB86FC;
    --green: #00FF88;
    --gold: #FFD700;
    --red: #FF4D6D;
}

.stApp {
    background:
        radial-gradient(circle at 15% 12%, rgba(0, 212, 255, 0.10), transparent 26%),
        radial-gradient(circle at 88% 8%, rgba(187, 134, 252, 0.11), transparent 24%),
        var(--bg);
    color: var(--text);
}

section[data-testid="stSidebar"] {
    background: #0A0D12;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    letter-spacing: 0;
    color: var(--text);
}

.tax-hero {
    padding: 26px 28px;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(21,26,35,0.96), rgba(13,17,23,0.94));
    box-shadow: 0 16px 42px rgba(0,0,0,0.42);
    margin-bottom: 22px;
}

.tax-hero .eyebrow {
    color: var(--blue);
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.tax-hero .title {
    font-size: 2.2rem;
    line-height: 1.1;
    font-weight: 800;
    margin: 6px 0 8px;
}

.tax-hero .subtitle {
    color: var(--muted);
    max-width: 860px;
    font-size: 0.98rem;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
    margin: 14px 0 22px;
}

.tax-card {
    min-height: 142px;
    padding: 17px 17px 15px;
    border-radius: 8px;
    background: rgba(21, 26, 35, 0.92);
    border: 1px solid rgba(255,255,255,0.09);
    box-shadow: 0 12px 30px rgba(0,0,0,0.30);
}

.tax-card.blue { border-color: rgba(0, 212, 255, 0.50); box-shadow: 0 0 22px rgba(0, 212, 255, 0.10); }
.tax-card.purple { border-color: rgba(187, 134, 252, 0.50); box-shadow: 0 0 22px rgba(187, 134, 252, 0.10); }
.tax-card.green { border-color: rgba(0, 255, 136, 0.45); box-shadow: 0 0 22px rgba(0, 255, 136, 0.09); }
.tax-card.gold { border-color: rgba(255, 215, 0, 0.50); box-shadow: 0 0 22px rgba(255, 215, 0, 0.09); }
.tax-card.red { border-color: rgba(255, 77, 109, 0.48); box-shadow: 0 0 22px rgba(255, 77, 109, 0.09); }

.tax-card .field {
    color: var(--muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
}

.tax-card .value {
    color: var(--text);
    font-size: 1.72rem;
    line-height: 1.18;
    font-weight: 800;
    margin-top: 12px;
    overflow-wrap: anywhere;
}

.tax-card .label {
    color: var(--muted);
    font-size: 0.86rem;
    margin-top: 8px;
}

.status-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 4px 0 18px;
}

.status-pill {
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 0.82rem;
    color: var(--text);
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
}

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    overflow: hidden;
}

.stDownloadButton button, .stButton button {
    border-radius: 8px;
    border: 1px solid rgba(0, 212, 255, 0.45);
    background: rgba(0, 212, 255, 0.10);
    color: var(--text);
    font-weight: 700;
}

.stDownloadButton button:hover, .stButton button:hover {
    border-color: var(--blue);
    color: var(--blue);
}
</style>
"""


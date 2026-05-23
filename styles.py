"""Animated dark FinTech theme — compact layout for the Austrian KeSt dashboard."""

FINTECH_CSS = """
<style>
/* ─── Design Tokens ───────────────────────────────────────────────── */
:root {
    --bg:         #0E1117;
    --panel:      #151A23;
    --panel-soft: #1B2230;
    --text:       #F4F7FB;
    --muted:      #8B98A9;
    --blue:       #00D4FF;
    --purple:     #BB86FC;
    --green:      #00FF88;
    --gold:       #FFD700;
    --red:        #FF4D6D;
}

/* ─── Keyframes ───────────────────────────────────────────────────── */

@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0);    }
}
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateX(-16px); }
    to   { opacity: 1; transform: translateX(0);     }
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to   { opacity: 1; transform: scale(1);    }
}
@keyframes popIn {
    0%   { opacity: 0; transform: scale(0.78); }
    65%  {             transform: scale(1.06); }
    100% { opacity: 1; transform: scale(1);    }
}
@keyframes shimmer {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(220%);  }
}
@keyframes pulseGlowRed {
    0%, 100% { box-shadow: 0 0 16px rgba(255, 77, 109, 0.10); }
    50%       { box-shadow: 0 0 44px rgba(255, 77, 109, 0.42); }
}
@keyframes countIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0);   }
}
@keyframes heroPulse {
    0%, 100% { opacity: 0.45; transform: scale(1);    }
    50%       { opacity: 0.72; transform: scale(1.05); }
}
@keyframes dotPulse {
    0%, 100% { transform: scale(1);   box-shadow: 0 0 3px currentColor; }
    50%       { transform: scale(1.5); box-shadow: 0 0 9px currentColor; }
}
@keyframes tooltipIn {
    from { opacity: 0; transform: translateX(-50%) translateY(4px); }
    to   { opacity: 1; transform: translateX(-50%) translateY(0);   }
}

/* ─── Base ────────────────────────────────────────────────────────── */

.stApp {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(0,212,255,0.10), transparent 28%),
        radial-gradient(ellipse at 88% 8%,  rgba(187,134,252,0.11), transparent 26%),
        radial-gradient(ellipse at 50% 90%, rgba(0,255,136,0.04), transparent 30%),
        var(--bg);
    color: var(--text);
}

.block-container {
    padding-top: 0.9rem !important;
    padding-bottom: 1.5rem !important;
    max-width: 100% !important;
}

h1 { margin: 0 0 0.5rem  !important; }
h2 { margin: 0 0 0.3rem  !important; font-size: 1.05rem !important; animation: fadeSlideIn 0.4s ease-out both; }
h3 { margin: 0 0 0.25rem !important; font-size: 0.95rem !important; animation: fadeSlideIn 0.4s ease-out both; }

::-webkit-scrollbar             { width: 4px; height: 4px; }
::-webkit-scrollbar-track       { background: transparent; }
::-webkit-scrollbar-thumb       { background: rgba(255,255,255,0.12); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }

/* ─── Sidebar ─────────────────────────────────────────────────────── */

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090C10 0%, #0A0D14 100%);
    border-right: 1px solid rgba(255,255,255,0.07);
}
section[data-testid="stSidebar"] > div:first-child {
    animation: fadeSlideIn 0.4s cubic-bezier(0.22,1,0.36,1) both;
}
section[data-testid="stSidebar"] label {
    color: var(--muted) !important;
    font-size: 0.74rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700 !important;
}

/* ─── Hero ────────────────────────────────────────────────────────── */

.tax-hero {
    padding: 14px 18px 13px;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(21,26,35,0.97), rgba(11,14,20,0.95));
    box-shadow: 0 12px 36px rgba(0,0,0,0.42);
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
    animation: scaleIn 0.45s cubic-bezier(0.22,1,0.36,1) both;
}
.tax-hero::before {
    content: "";
    position: absolute;
    top: -50px; left: -50px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,212,255,0.07), transparent 70%);
    animation: heroPulse 5s ease-in-out infinite;
    pointer-events: none;
}
.tax-hero::after {
    content: "";
    position: absolute;
    inset: 0; width: 50%;
    background: linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.04) 50%, transparent 70%);
    animation: shimmer 5s ease-in-out infinite;
    pointer-events: none;
}
.tax-hero .eyebrow {
    color: var(--blue);
    font-size: 0.70rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.10em;
    animation: fadeSlideIn 0.45s ease-out 0.08s both;
}
.tax-hero .title {
    font-size: 1.65rem; line-height: 1.12; font-weight: 800;
    margin: 4px 0 5px;
    animation: fadeSlideUp 0.45s ease-out 0.13s both;
}
.tax-hero .subtitle {
    color: var(--muted); max-width: 860px;
    font-size: 0.83rem; line-height: 1.45;
    animation: fadeSlideUp 0.45s ease-out 0.19s both;
}

/* Prevent Streamlit wrapper divs from clipping overflowing tooltips */
div[data-testid="stMarkdownContainer"],
div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    overflow: visible !important;
}

/* ─── Metric Grid — always 3 columns ─────────────────────────────── */

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 8px 0 10px;
    overflow: visible;
}

/* ─── Card Wrapper — carries the tooltip ─────────────────────────── */

.card-wrap {
    position: relative;
    /* z-index:1 ensures each wrap participates in the same stacking order.
       On hover we raise to 10 so the active card's stacking context sits above
       all siblings — otherwise adjacent cards (painted later in DOM order) would
       cover the ::after tooltip even at z-index:9999. */
    z-index: 1;
    animation: fadeSlideUp 0.50s cubic-bezier(0.22,1,0.36,1) both;
}
.card-wrap:nth-child(1) { animation-delay: 0.07s; }
.card-wrap:nth-child(2) { animation-delay: 0.13s; }
.card-wrap:nth-child(3) { animation-delay: 0.19s; }
.card-wrap:nth-child(4) { animation-delay: 0.25s; }
.card-wrap:nth-child(5) { animation-delay: 0.31s; }
.card-wrap:nth-child(6) { animation-delay: 0.37s; }

.card-wrap:hover { z-index: 10; }

/* CSS Tooltip — appears ABOVE the card so it is never covered by rows below */
.card-wrap[data-tip]::after {
    content: attr(data-tip);
    position: absolute;
    bottom: calc(100% + 9px);
    top: auto;
    left: 50%;
    transform: translateX(-50%) translateY(6px);
    width: 240px;
    background: rgba(9,12,16,0.97);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 0.75rem;
    line-height: 1.5;
    color: var(--muted);
    text-align: left;
    white-space: normal;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.18s ease, transform 0.18s ease;
    z-index: 9999;
    box-shadow: 0 10px 32px rgba(0,0,0,0.65);
}
.card-wrap[data-tip]:hover::after {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
}

/* ─── Tax Cards ───────────────────────────────────────────────────── */

.tax-card {
    min-height: 108px;
    padding: 11px 13px 10px;
    border-radius: 9px;
    background: rgba(19,24,33,0.94);
    border: 1px solid rgba(255,255,255,0.09);
    box-shadow: 0 8px 22px rgba(0,0,0,0.28);
    position: relative;
    overflow: hidden;
    cursor: default;
    height: 100%;
    transition: transform 0.22s cubic-bezier(0.22,1,0.36,1), box-shadow 0.22s ease;
}
.card-wrap:hover .tax-card { transform: translateY(-4px) scale(1.014); }

/* shimmer on hover */
.tax-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; width: 55%; height: 100%;
    background: linear-gradient(110deg, transparent 35%, rgba(255,255,255,0.055) 50%, transparent 65%);
    transform: translateX(-100%);
}
.card-wrap:hover .tax-card::before { animation: shimmer 0.55s ease forwards; }

/* colour variants */
.tax-card.blue   { border-color: rgba(0,212,255,0.45);   box-shadow: 0 0 18px rgba(0,212,255,0.09); }
.tax-card.purple { border-color: rgba(187,134,252,0.45); box-shadow: 0 0 18px rgba(187,134,252,0.09); }
.tax-card.green  { border-color: rgba(0,255,136,0.40);   box-shadow: 0 0 18px rgba(0,255,136,0.08); }
.tax-card.gold   { border-color: rgba(255,215,0,0.45);   box-shadow: 0 0 18px rgba(255,215,0,0.08); }

.card-wrap:hover .tax-card.blue   { box-shadow: 0 8px 32px rgba(0,212,255,0.24); }
.card-wrap:hover .tax-card.purple { box-shadow: 0 8px 32px rgba(187,134,252,0.24); }
.card-wrap:hover .tax-card.green  { box-shadow: 0 8px 32px rgba(0,255,136,0.22); }
.card-wrap:hover .tax-card.gold   { box-shadow: 0 8px 32px rgba(255,215,0,0.22); }

/* Red: persistent pulse — animation applied directly since nth-child stagger is on .card-wrap */
.tax-card.red {
    border-color: rgba(255,77,109,0.48);
    animation: pulseGlowRed 3.4s ease-in-out 0.9s infinite;
}
.card-wrap:hover .tax-card.red { box-shadow: 0 8px 36px rgba(255,77,109,0.34); }

/* Field label with animated colour dot */
.tax-card .field {
    color: var(--muted);
    font-size: 0.70rem; text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 700;
    display: flex; align-items: center; gap: 6px;
}
.tax-card .field::before {
    content: "";
    display: inline-block; width: 6px; height: 6px;
    border-radius: 50%; flex-shrink: 0;
    animation: dotPulse 2.8s ease-in-out infinite;
}
.tax-card.blue   .field::before { background: var(--blue);   color: var(--blue);   animation-delay: 0.0s; }
.tax-card.purple .field::before { background: var(--purple); color: var(--purple); animation-delay: 0.4s; }
.tax-card.green  .field::before { background: var(--green);  color: var(--green);  animation-delay: 0.8s; }
.tax-card.gold   .field::before { background: var(--gold);   color: var(--gold);   animation-delay: 1.2s; }
.tax-card.red    .field::before { background: var(--red);    color: var(--red);    animation-delay: 1.6s; }

.tax-card .value {
    color: var(--text);
    font-size: 1.34rem; line-height: 1.15; font-weight: 800;
    margin-top: 8px; overflow-wrap: anywhere;
    animation: countIn 0.45s ease-out 0.45s both;
}
.tax-card .label {
    color: var(--muted);
    font-size: 0.76rem; margin-top: 4px; line-height: 1.3;
}

/* ─── Status Strip ────────────────────────────────────────────────── */

.status-strip {
    display: flex; flex-wrap: wrap;
    gap: 7px; margin: 0 0 10px;
}
.status-pill {
    border-radius: 999px; padding: 4px 11px;
    font-size: 0.75rem; font-weight: 600; color: var(--text);
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    animation: popIn 0.4s cubic-bezier(0.22,1,0.36,1) both;
    transition: background 0.16s, border-color 0.16s, transform 0.14s;
    cursor: help;
}
.status-pill:nth-child(1) { animation-delay: 0.40s; }
.status-pill:nth-child(2) { animation-delay: 0.47s; }
.status-pill:nth-child(3) { animation-delay: 0.54s; }
.status-pill:nth-child(4) { animation-delay: 0.61s; }
.status-pill:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.22);
    transform: translateY(-1px);
}

/* ─── Section Divider ─────────────────────────────────────────────── */

.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.09) 25%, rgba(255,255,255,0.09) 75%, transparent);
    margin: 10px 0;
    animation: fadeSlideIn 0.4s ease-out 0.5s both;
}

/* ─── Native Metrics (breakdown expander) ─────────────────────────── */

div[data-testid="stMetric"] {
    background: rgba(21,26,35,0.70);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 10px 13px;
    animation: fadeSlideUp 0.4s ease-out both;
    transition: background 0.18s;
}
div[data-testid="stMetric"]:hover { background: rgba(21,26,35,0.90); }
div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700 !important;
}
div[data-testid="stMetricValue"] > div {
    color: var(--text) !important;
    font-size: 1.15rem !important; font-weight: 800 !important;
}

/* ─── Data Tables ─────────────────────────────────────────────────── */

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px; overflow: hidden;
    animation: fadeSlideUp 0.4s ease-out 0.2s both;
}

/* ─── Expander ────────────────────────────────────────────────────── */

div[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 9px !important;
    background: rgba(21,26,35,0.55) !important;
    animation: fadeSlideUp 0.4s ease-out 0.3s both;
}

/* ─── Alerts ──────────────────────────────────────────────────────── */

div[data-testid="stAlert"] {
    border-radius: 8px;
    animation: fadeSlideUp 0.35s ease-out 0.1s both;
}

/* ─── Buttons ─────────────────────────────────────────────────────── */

.stDownloadButton button, .stButton button {
    border-radius: 7px;
    border: 1px solid rgba(0,212,255,0.38);
    background: rgba(0,212,255,0.08);
    color: var(--text); font-weight: 700; font-size: 0.84rem;
    transition: background 0.18s, border-color 0.18s, box-shadow 0.18s, transform 0.14s;
}
.stDownloadButton button:hover, .stButton button:hover {
    border-color: var(--blue); color: var(--blue);
    background: rgba(0,212,255,0.12);
    box-shadow: 0 0 18px rgba(0,212,255,0.20);
    transform: translateY(-1px);
}
.stDownloadButton button:active, .stButton button:active { transform: translateY(0); }

/* ─── Spinner ─────────────────────────────────────────────────────── */

div[data-testid="stSpinner"] { animation: fadeSlideUp 0.3s ease-out both; }

/* ─── Performance View ────────────────────────────────────────────── */

.perf-section-label {
    color: var(--muted);
    font-size: 0.70rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.09em;
    margin: 10px 0 4px;
    animation: fadeSlideIn 0.4s ease-out both;
}

/* ─── Footer ──────────────────────────────────────────────────────── */

.kest-footer {
    margin-top: 24px; padding-top: 12px;
    border-top: 1px solid rgba(255,255,255,0.07);
    color: var(--muted); font-size: 0.74rem; text-align: center;
    animation: fadeSlideUp 0.4s ease-out 0.6s both;
}
</style>
"""

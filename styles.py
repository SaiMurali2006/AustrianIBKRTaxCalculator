"""Animated dark FinTech theme for the Austrian KeSt dashboard."""

FINTECH_CSS = """
<style>
/* ─── Design Tokens ───────────────────────────────────────────────── */
:root {
    --bg:          #0E1117;
    --panel:       #151A23;
    --panel-soft:  #1B2230;
    --text:        #F4F7FB;
    --muted:       #8B98A9;
    --blue:        #00D4FF;
    --purple:      #BB86FC;
    --green:       #00FF88;
    --gold:        #FFD700;
    --red:         #FF4D6D;
}

/* ─── Keyframes ───────────────────────────────────────────────────── */

@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0);    }
}

@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateX(-18px); }
    to   { opacity: 1; transform: translateX(0);     }
}

@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.94); }
    to   { opacity: 1; transform: scale(1);    }
}

@keyframes popIn {
    0%   { opacity: 0; transform: scale(0.75); }
    65%  {             transform: scale(1.07); }
    100% { opacity: 1; transform: scale(1);    }
}

@keyframes shimmer {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(200%);  }
}

@keyframes pulseGlowRed {
    0%, 100% { box-shadow: 0 0 20px rgba(255, 77,  109, 0.10), inset 0 0 0 rgba(255,77,109,0); }
    50%       { box-shadow: 0 0 50px rgba(255, 77,  109, 0.40), inset 0 0 20px rgba(255,77,109,0.03); }
}

@keyframes pulseGlowBlue {
    0%, 100% { box-shadow: 0 0 22px rgba(0, 212, 255, 0.08); }
    50%       { box-shadow: 0 0 44px rgba(0, 212, 255, 0.28); }
}

@keyframes countIn {
    from { opacity: 0; transform: translateY(8px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0)   scale(1);    }
}

@keyframes heroPulse {
    0%, 100% { opacity: 0.55; transform: scale(1);    }
    50%       { opacity: 0.80; transform: scale(1.04); }
}

@keyframes borderGlow {
    0%, 100% { opacity: 0.45; }
    50%       { opacity: 0.90; }
}

@keyframes dotPulse {
    0%, 100% { transform: scale(1);    opacity: 1;    box-shadow: 0 0 5px currentColor; }
    50%       { transform: scale(1.45); opacity: 0.75; box-shadow: 0 0 12px currentColor; }
}

@keyframes spinnerDash {
    0%   { stroke-dasharray: 1, 150; stroke-dashoffset: 0;   }
    50%  { stroke-dasharray: 90, 150; stroke-dashoffset: -35; }
    100% { stroke-dasharray: 90, 150; stroke-dashoffset: -124;}
}

/* ─── Base ────────────────────────────────────────────────────────── */

.stApp {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(0, 212, 255, 0.11), transparent 28%),
        radial-gradient(ellipse at 88% 8%,  rgba(187, 134, 252, 0.12), transparent 26%),
        radial-gradient(ellipse at 50% 90%, rgba(0, 255, 136, 0.05), transparent 30%),
        var(--bg);
    color: var(--text);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 { letter-spacing: 0; color: var(--text); }

h2, h3 { animation: fadeSlideIn 0.4s ease-out both; }

/* Scrollbars */
::-webkit-scrollbar             { width: 5px; height: 5px; }
::-webkit-scrollbar-track       { background: transparent; }
::-webkit-scrollbar-thumb       { background: rgba(255,255,255,0.13); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.24); }

/* ─── Sidebar ─────────────────────────────────────────────────────── */

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #090C10 0%, #0A0D14 100%);
    border-right: 1px solid rgba(255,255,255,0.07);
}

section[data-testid="stSidebar"] > div:first-child {
    animation: fadeSlideIn 0.45s cubic-bezier(0.22,1,0.36,1) both;
}

section[data-testid="stSidebar"] label {
    color: var(--muted) !important;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700 !important;
}

/* ─── Hero ────────────────────────────────────────────────────────── */

.tax-hero {
    padding: 28px 30px 26px;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
    background: linear-gradient(135deg, rgba(21,26,35,0.97), rgba(11,14,20,0.95));
    box-shadow: 0 20px 56px rgba(0,0,0,0.48);
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
    animation: scaleIn 0.5s cubic-bezier(0.22,1,0.36,1) both;
}

/* Ambient glow orb behind hero */
.tax-hero::before {
    content: "";
    position: absolute;
    top: -60px; left: -60px;
    width: 260px; height: 260px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(0,212,255,0.08), transparent 70%);
    animation: heroPulse 5s ease-in-out infinite;
    pointer-events: none;
}

/* Shimmer sweep across hero */
.tax-hero::after {
    content: "";
    position: absolute;
    inset: 0;
    width: 50%;
    background: linear-gradient(
        105deg,
        transparent 30%,
        rgba(255,255,255,0.045) 50%,
        transparent 70%
    );
    animation: shimmer 5s ease-in-out infinite;
    pointer-events: none;
}

.tax-hero .eyebrow {
    color: var(--blue);
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    animation: fadeSlideIn 0.5s ease-out 0.10s both;
}

.tax-hero .title {
    font-size: 2.2rem;
    line-height: 1.1;
    font-weight: 800;
    margin: 7px 0 10px;
    animation: fadeSlideUp 0.5s ease-out 0.16s both;
}

.tax-hero .subtitle {
    color: var(--muted);
    max-width: 860px;
    font-size: 0.97rem;
    line-height: 1.55;
    animation: fadeSlideUp 0.5s ease-out 0.23s both;
}

/* ─── Metric Grid ─────────────────────────────────────────────────── */

.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 14px;
    margin: 14px 0 20px;
}

/* ─── Tax Cards ───────────────────────────────────────────────────── */

.tax-card {
    min-height: 150px;
    padding: 18px 18px 16px;
    border-radius: 11px;
    background: rgba(19, 24, 33, 0.94);
    border: 1px solid rgba(255,255,255,0.09);
    box-shadow: 0 10px 28px rgba(0,0,0,0.30);
    position: relative;
    overflow: hidden;
    cursor: default;
    transition: transform 0.24s cubic-bezier(0.22,1,0.36,1),
                box-shadow  0.24s ease;
    animation: fadeSlideUp 0.55s cubic-bezier(0.22,1,0.36,1) both;
}

/* staggered entrance */
.tax-card:nth-child(1) { animation-delay: 0.08s; }
.tax-card:nth-child(2) { animation-delay: 0.15s; }
.tax-card:nth-child(3) { animation-delay: 0.22s; }
.tax-card:nth-child(4) { animation-delay: 0.29s; }
.tax-card:nth-child(5) { animation-delay: 0.36s; }
.tax-card:nth-child(6) { animation-delay: 0.43s; }

/* hover lift */
.tax-card:hover { transform: translateY(-6px) scale(1.016); }

/* shimmer sweep on hover */
.tax-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 55%; height: 100%;
    background: linear-gradient(
        110deg,
        transparent 35%,
        rgba(255,255,255,0.06) 50%,
        transparent 65%
    );
    transform: translateX(-100%);
}
.tax-card:hover::before { animation: shimmer 0.6s ease forwards; }

/* color variants with animated border glow */
.tax-card.blue {
    border-color: rgba(0, 212, 255, 0.45);
    box-shadow: 0 0 22px rgba(0, 212, 255, 0.09);
}
.tax-card.blue:hover   { box-shadow: 0 10px 40px rgba(0, 212, 255, 0.26); }

.tax-card.purple {
    border-color: rgba(187, 134, 252, 0.45);
    box-shadow: 0 0 22px rgba(187, 134, 252, 0.09);
}
.tax-card.purple:hover { box-shadow: 0 10px 40px rgba(187, 134, 252, 0.26); }

.tax-card.green {
    border-color: rgba(0, 255, 136, 0.40);
    box-shadow: 0 0 22px rgba(0, 255, 136, 0.08);
}
.tax-card.green:hover  { box-shadow: 0 10px 40px rgba(0, 255, 136, 0.22); }

.tax-card.gold {
    border-color: rgba(255, 215, 0, 0.45);
    box-shadow: 0 0 22px rgba(255, 215, 0, 0.08);
}
.tax-card.gold:hover   { box-shadow: 0 10px 40px rgba(255, 215, 0, 0.22); }

/* Red card: persistent pulse glow */
.tax-card.red {
    border-color: rgba(255, 77, 109, 0.48);
    animation: fadeSlideUp 0.55s cubic-bezier(0.22,1,0.36,1) 0.43s both,
               pulseGlowRed 3.4s ease-in-out 1.0s infinite;
}
.tax-card.red:hover    { box-shadow: 0 10px 44px rgba(255, 77, 109, 0.36); }

/* Field label row with animated colour dot */
.tax-card .field {
    color: var(--muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 7px;
}

.tax-card .field::before {
    content: "";
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    animation: dotPulse 2.8s ease-in-out infinite;
}
.tax-card.blue   .field::before { background: var(--blue);   color: var(--blue);   animation-delay: 0.0s; }
.tax-card.purple .field::before { background: var(--purple); color: var(--purple); animation-delay: 0.4s; }
.tax-card.green  .field::before { background: var(--green);  color: var(--green);  animation-delay: 0.8s; }
.tax-card.gold   .field::before { background: var(--gold);   color: var(--gold);   animation-delay: 1.2s; }
.tax-card.red    .field::before { background: var(--red);    color: var(--red);    animation-delay: 1.6s; }

.tax-card .value {
    color: var(--text);
    font-size: 1.70rem;
    line-height: 1.18;
    font-weight: 800;
    margin-top: 14px;
    overflow-wrap: anywhere;
    animation: countIn 0.5s ease-out 0.5s both;
}

.tax-card .label {
    color: var(--muted);
    font-size: 0.83rem;
    margin-top: 8px;
    line-height: 1.35;
}

/* ─── Status Strip ────────────────────────────────────────────────── */

.status-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 2px 0 20px;
}

.status-pill {
    border-radius: 999px;
    padding: 7px 14px;
    font-size: 0.81rem;
    font-weight: 600;
    color: var(--text);
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
    animation: popIn 0.45s cubic-bezier(0.22,1,0.36,1) both;
    transition: background 0.18s, border-color 0.18s, transform 0.15s;
}
.status-pill:nth-child(1) { animation-delay: 0.44s; }
.status-pill:nth-child(2) { animation-delay: 0.52s; }
.status-pill:nth-child(3) { animation-delay: 0.60s; }
.status-pill:nth-child(4) { animation-delay: 0.68s; }
.status-pill:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.22);
    transform: translateY(-2px);
}

/* ─── Section Divider ─────────────────────────────────────────────── */

.section-divider {
    height: 1px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255,255,255,0.10) 25%,
        rgba(255,255,255,0.10) 75%,
        transparent 100%
    );
    margin: 20px 0;
    animation: fadeSlideIn 0.5s ease-out 0.55s both;
}

/* ─── Native Metrics (breakdown expander) ─────────────────────────── */

div[data-testid="stMetric"] {
    background: rgba(21,26,35,0.70);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px;
    padding: 14px 16px;
    animation: fadeSlideUp 0.4s ease-out both;
    transition: background 0.2s;
}
div[data-testid="stMetric"]:hover {
    background: rgba(21,26,35,0.90);
}
div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 0.76rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700 !important;
}
div[data-testid="stMetricValue"] > div {
    color: var(--text) !important;
    font-size: 1.28rem !important;
    font-weight: 800 !important;
}

/* ─── Data Tables ─────────────────────────────────────────────────── */

div[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    overflow: hidden;
    animation: fadeSlideUp 0.45s ease-out 0.2s both;
}

/* ─── Expander ────────────────────────────────────────────────────── */

div[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    background: rgba(21,26,35,0.60) !important;
    animation: fadeSlideUp 0.4s ease-out 0.3s both;
}

/* ─── Alerts ──────────────────────────────────────────────────────── */

div[data-testid="stAlert"] {
    border-radius: 9px;
    animation: fadeSlideUp 0.4s ease-out 0.1s both;
}

/* ─── Buttons ─────────────────────────────────────────────────────── */

.stDownloadButton button,
.stButton button {
    border-radius: 8px;
    border: 1px solid rgba(0, 212, 255, 0.40);
    background: rgba(0, 212, 255, 0.08);
    color: var(--text);
    font-weight: 700;
    transition: background 0.2s, border-color 0.2s, box-shadow 0.2s, transform 0.15s;
}
.stDownloadButton button:hover,
.stButton button:hover {
    border-color: var(--blue);
    color: var(--blue);
    background: rgba(0, 212, 255, 0.13);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.22);
    transform: translateY(-2px);
}
.stDownloadButton button:active,
.stButton button:active { transform: translateY(0); }

/* ─── Spinner ─────────────────────────────────────────────────────── */

div[data-testid="stSpinner"] {
    animation: fadeSlideUp 0.3s ease-out both;
}

/* ─── Footer ──────────────────────────────────────────────────────── */

.kest-footer {
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid rgba(255,255,255,0.07);
    color: var(--muted);
    font-size: 0.78rem;
    text-align: center;
    animation: fadeSlideUp 0.4s ease-out 0.6s both;
}
</style>
"""

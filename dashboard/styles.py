"""Visual system for the ResolveOps Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

CSS = r"""
<style>
    :root {
        --ops-bg: #06101d;
        --ops-panel: #0b1828;
        --ops-panel-2: #0f2034;
        --ops-line: #20334a;
        --ops-text: #edf5ff;
        --ops-muted: #8ea4bc;
        --ops-cyan: #51d7ff;
        --ops-green: #43e6a0;
        --ops-amber: #ffcb6b;
        --ops-red: #ff6b7a;
        --ops-purple: #a78bfa;
    }

    .stApp {
        background:
            radial-gradient(circle at 88% -10%, rgba(41, 151, 199, .15), transparent 30rem),
            radial-gradient(circle at -5% 45%, rgba(89, 71, 185, .08), transparent 28rem),
            var(--ops-bg);
        color: var(--ops-text);
    }
    [data-testid="stHeader"] { background: rgba(6, 16, 29, .75); }
    [data-testid="stSidebar"] {
        background: #081421;
        border-right: 1px solid var(--ops-line);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #b8c8d9;
    }
    #MainMenu, footer { visibility: hidden; }
    .block-container { max-width: 1500px; padding-top: 2.2rem; padding-bottom: 4rem; }

    h1, h2, h3 { color: var(--ops-text) !important; letter-spacing: -.02em; }
    p, li { color: #c7d5e4; }
    hr { border-color: var(--ops-line) !important; }

    .ops-kicker {
        color: var(--ops-cyan);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: .45rem;
    }
    .ops-title {
        color: #f7fbff;
        font-size: clamp(2.1rem, 4vw, 3.35rem);
        font-weight: 760;
        letter-spacing: -.055em;
        line-height: .98;
        margin-bottom: .8rem;
    }
    .ops-subtitle { color: var(--ops-muted); font-size: 1rem; max-width: 720px; }
    .ops-wordmark {
        font-size: 1.12rem;
        color: #f5faff;
        font-weight: 850;
        letter-spacing: .08em;
        margin: .25rem 0 1.3rem;
    }
    .ops-wordmark span { color: var(--ops-cyan); }

    .ops-badge {
        display: inline-flex;
        align-items: center;
        gap: .32rem;
        padding: .25rem .55rem;
        border: 1px solid var(--ops-line);
        border-radius: 999px;
        background: rgba(18, 37, 58, .7);
        color: #bdd0e3;
        font-size: .68rem;
        font-weight: 750;
        letter-spacing: .07em;
        text-transform: uppercase;
        white-space: nowrap;
    }
    .ops-badge.success { color: var(--ops-green); border-color: rgba(67,230,160,.33); background: rgba(67,230,160,.07); }
    .ops-badge.warning { color: var(--ops-amber); border-color: rgba(255,203,107,.35); background: rgba(255,203,107,.07); }
    .ops-badge.danger { color: var(--ops-red); border-color: rgba(255,107,122,.35); background: rgba(255,107,122,.07); }
    .ops-badge.info { color: var(--ops-cyan); border-color: rgba(81,215,255,.35); background: rgba(81,215,255,.07); }
    .ops-badge.purple { color: #c4b5fd; border-color: rgba(167,139,250,.35); background: rgba(167,139,250,.07); }
    .ops-dot { width: .42rem; height: .42rem; border-radius: 50%; background: currentColor; box-shadow: 0 0 12px currentColor; }

    .ops-section-heading {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin: 1.6rem 0 .75rem;
    }
    .ops-section-heading h2 { font-size: 1.22rem; margin: 0; }
    .ops-section-heading p { color: var(--ops-muted); font-size: .8rem; margin: .25rem 0 0; }

    .ops-panel {
        background: linear-gradient(145deg, rgba(15,32,52,.94), rgba(9,23,38,.97));
        border: 1px solid var(--ops-line);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 13px 30px rgba(0,0,0,.16);
    }
    .ops-panel.accent { border-top: 2px solid var(--ops-cyan); }
    .ops-label {
        color: var(--ops-muted);
        font-size: .68rem;
        font-weight: 750;
        letter-spacing: .1em;
        text-transform: uppercase;
    }
    .ops-value { color: #f6faff; font-size: 1.65rem; font-weight: 760; margin-top: .22rem; }
    .ops-copy { color: #c7d5e4; line-height: 1.55; font-size: .9rem; }
    .ops-muted { color: var(--ops-muted); font-size: .78rem; }
    .evidence-detail { color: #c7d5e4; line-height: 1.5; font-size: .84rem; white-space: pre-wrap; overflow-wrap: anywhere; }

    .scenario-icon {
        display: grid; place-items: center; width: 2.15rem; height: 2.15rem;
        color: var(--ops-cyan); background: rgba(81,215,255,.08);
        border: 1px solid rgba(81,215,255,.22); border-radius: 9px;
        font-size: 1rem; margin-bottom: .65rem;
    }
    .scenario-title { color: #f4f9ff; font-size: .96rem; font-weight: 720; min-height: 2.5rem; }
    .scenario-detail { color: var(--ops-muted); font-size: .78rem; min-height: 3.7rem; line-height: 1.45; }

    .incident-title { color: #f6faff; font-weight: 720; font-size: 1.25rem; margin: .3rem 0; }
    .incident-id { color: var(--ops-cyan); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .78rem; }
    .cause-box {
        border-left: 3px solid var(--ops-cyan);
        padding: .75rem .95rem;
        background: rgba(81,215,255,.045);
        border-radius: 0 10px 10px 0;
        margin: .5rem 0 .9rem;
    }
    .cause-box .cause { color: #f1f7fd; font-size: 1rem; font-weight: 650; }
    .cause-box .summary { color: #a9bbce; font-size: .83rem; margin-top: .4rem; line-height: 1.5; }

    .timeline {
        margin-left: .45rem;
        border-left: 1px solid #29405a;
        padding-left: 1.15rem;
    }
    .timeline-item { position: relative; padding: .15rem 0 1.25rem; }
    .timeline-item::before {
        content: ""; position: absolute; left: -1.47rem; top: .35rem;
        width: .55rem; height: .55rem; border-radius: 50%;
        background: var(--ops-cyan); border: 3px solid var(--ops-bg);
        box-shadow: 0 0 10px rgba(81,215,255,.6);
    }
    .timeline-time { color: #7189a2; font-size: .68rem; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
    .timeline-message { color: #dce8f4; font-size: .86rem; margin-top: .2rem; }
    .timeline-actor { color: var(--ops-muted); font-size: .7rem; margin-top: .18rem; }

    .empty-state {
        text-align: center; padding: 2.25rem 1.25rem; border: 1px dashed #2a4058;
        border-radius: 14px; background: rgba(11,24,40,.55);
    }
    .empty-state .icon { font-size: 1.65rem; color: var(--ops-cyan); }
    .empty-state .title { color: #edf5ff; font-size: .95rem; font-weight: 700; margin: .6rem 0 .25rem; }
    .empty-state .copy { color: var(--ops-muted); font-size: .8rem; max-width: 460px; margin: auto; }

    .offline-state {
        border: 1px solid rgba(255,107,122,.32); background: rgba(255,107,122,.055);
        border-radius: 12px; padding: .85rem 1rem; color: #ffd5da; font-size: .84rem;
    }
    .simulation-note {
        border: 1px solid rgba(255,203,107,.24); background: rgba(255,203,107,.045);
        border-radius: 10px; color: #d6c49d; padding: .65rem .8rem; font-size: .72rem;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(15,32,52,.9), rgba(9,23,38,.95));
        border: 1px solid var(--ops-line); border-radius: 13px; padding: .8rem 1rem;
    }
    div[data-testid="stMetricLabel"] { color: var(--ops-muted); }
    div[data-testid="stMetricValue"] { color: #f4f9ff; letter-spacing: -.035em; }

    .stButton > button, .stDownloadButton > button {
        border-radius: 8px; border: 1px solid #2c4762; background: #10243a;
        color: #e9f5ff; font-weight: 650; min-height: 2.35rem;
        transition: all .15s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        color: #fff; border-color: var(--ops-cyan); box-shadow: 0 0 0 1px rgba(81,215,255,.1);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(120deg, #1a8ead, #176a8e);
        border-color: #46ccec; color: white;
    }
    [data-testid="stExpander"] { border-color: var(--ops-line) !important; background: rgba(11,24,40,.6); }
    [data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
        background: #0c1b2c !important; border-color: #29415b !important;
    }
    div[data-testid="stDataFrame"] { border: 1px solid var(--ops-line); border-radius: 10px; overflow: hidden; }

    @media (max-width: 760px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .ops-title { font-size: 2.15rem; }
        .scenario-detail, .scenario-title { min-height: auto; }
    }
</style>
"""


def inject_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

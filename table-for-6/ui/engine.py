"""Cached solves and the shared dark map, used by every page."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from t6.data import HOODS, SLOTS, CUISINES, TAG_NAMES, GENDERS
from t6.service import build, run_all, describe_table, find_user_table
from t6.solve import solve_model_b
from .theme import COLORS

TONIGHT_N = 36


def profile_key():
    p = st.session_state.get("profile")
    return tuple(sorted(p.items())) if p else None


@st.cache_data(show_spinner=False, max_entries=48)
def solve_b(N, seed, profile_items):
    prof = dict(profile_items) if profile_items else None
    inst = build(N, seed, 0.08, 0.0, "none", prof)
    sol = solve_model_b(inst, certify=False, ip_time=20, max_iter=60, seed=seed)
    return inst, sol


@st.cache_data(show_spinner=False, max_entries=64)
def solve_everything(N, seed, lam, gamma, mode, profile_items, run_a):
    prof = dict(profile_items) if profile_items else None
    inst = build(N, seed, lam, float(gamma), mode, prof)
    sols = run_all(inst, run_a=run_a, a_time=20.0, seed=seed)
    return inst, sols


def tables_of(inst, sol):
    out = [describe_table(inst, *x) for x in sol.tables]
    for d, (S, v, t) in zip(out, sol.tables):
        d["members"], d["v"], d["t"] = list(S), int(v), int(t)
    return out


def dark_map(inst, sol, color="#C8A96A", height=520, highlight=None, you=False):
    """Tile-free night map: homes, venues, and gold threads between them."""
    fig = go.Figure()
    fig.add_shape(type="rect", x0=-122.385, x1=-122.31, y0=37.70, y1=37.92,
                  fillcolor="rgba(70,110,120,.10)", line=dict(width=0), layer="below")
    fig.add_annotation(x=-122.3475, y=37.727, text="<i>the Bay</i>", showarrow=False,
                       font=dict(family="Cormorant Garamond, serif", size=16, color="rgba(160,190,200,.55)"))
    for k, (S, v, t) in enumerate(sol.tables):
        hi = highlight is None or k == highlight
        x, y = [], []
        for i in S:
            x += [inst.home[i, 1], inst.v_loc[v, 1], None]
            y += [inst.home[i, 0], inst.v_loc[v, 0], None]
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", hoverinfo="skip",
                                 line=dict(width=1.6 if (highlight is not None and hi) else 1.0, color=color),
                                 opacity=0.85 if hi and highlight is not None else (0.45 if hi else 0.08)))
    fig.add_trace(go.Scatter(x=inst.home[:, 1], y=inst.home[:, 0], mode="markers", hoverinfo="skip",
                             marker=dict(size=5, color="rgba(238,231,216,.75)")))
    used = [(k, v) for k, (_, v, _) in enumerate(sol.tables)]
    fig.add_trace(go.Scatter(
        x=[inst.v_loc[v, 1] for _, v in used], y=[inst.v_loc[v, 0] for _, v in used], mode="markers",
        marker=dict(size=[20 if highlight == k else 13 for k, _ in used], color=color,
                    line=dict(color="#0A0D0C", width=2),
                    opacity=[1 if (highlight is None or highlight == k) else .35 for k, _ in used]),
        text=[f"{inst.v_name[v]} · {SLOTS[t]}" for (_, v, t) in sol.tables],
        hovertemplate="%{text}<extra></extra>"))
    for h in HOODS:
        fig.add_annotation(x=h[2], y=h[1] + 0.011, text=h[0].upper(), showarrow=False,
                           font=dict(family="Jost, sans-serif", size=9, color="rgba(156,151,140,.85)"))
    if you:
        fig.add_trace(go.Scatter(x=[inst.home[0, 1]], y=[inst.home[0, 0]], mode="markers+text", hoverinfo="skip",
                                 marker=dict(size=15, color="#E6D2A2", symbol="star"),
                                 text=["you"], textposition="top right",
                                 textfont=dict(family="Cormorant Garamond, serif", size=17, color="#E6D2A2")))
    fig.update_xaxes(visible=False, range=[-122.53, -122.22])
    fig.update_yaxes(visible=False, range=[37.715, 37.895], scaleanchor="x", scaleratio=1 / np.cos(np.radians(37.8)))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      hoverlabel=dict(bgcolor="#0F1614", bordercolor="#C8A96A",
                                      font=dict(family="Jost, sans-serif", color="#EEE7D8")))
    return fig


def profile_form():
    """The questionnaire. Returns True when submitted."""
    hood_names = [h[0] for h in HOODS]
    with st.form("profile_form", border=False):
        c1, c2, c3 = st.columns(3, gap="large")
        with c1:
            hood = st.selectbox("Your neighborhood", hood_names, index=0)
            transport = st.radio("Getting there", ["Transit or walking", "Driving"], horizontal=True)
            age = st.slider("Age", 21, 60, 28)
            gender = st.selectbox("Gender", GENDERS, index=0)
            table_pref = st.radio("Table mix", ["Mixed is great", "Prefer same gender"], horizontal=True)
        with c2:
            interests = st.multiselect("A few interests (up to 5)", TAG_NAMES,
                                       default=["Live music", "Cooking", "Film"], max_selections=5)
            loves = st.multiselect("Cuisines you love", CUISINES, default=["Japanese", "Italian"])
            budget = st.select_slider("Budget", ["$", "$$", "$$$"], value="$$")
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<p style='color:var(--mist);font-size:.9rem'>Nothing here is a filter. Every answer nudges a "
                        "score, and the optimizer seats the whole city at once.</p>", unsafe_allow_html=True)
        with c3:
            r_rest = st.slider("Dinner at a restaurant", 1, 5, 5)
            r_cafe = st.slider("Weekend coffee", 1, 5, 3)
            r_bar = st.slider("Drinks at a bar", 1, 5, 4)
            st.markdown("<p style='font-family:var(--sans);text-transform:uppercase;letter-spacing:.2em;"
                        "font-size:.68rem;color:var(--gold);margin:.6rem 0 .2rem'>When are you free?</p>",
                        unsafe_allow_html=True)
            avail = [st.checkbox(s, value=(k != 1), key=f"slot{k}") for k, s in enumerate(SLOTS)]
        submitted = st.form_submit_button("Seal my invitation")
    if submitted:
        if not any(avail):
            st.warning("Pick at least one evening you're free.")
            return False
        st.session_state.profile = dict(
            hood=hood_names.index(hood), car=(transport == "Driving"), age=age, gender=GENDERS.index(gender),
            same_gender=(table_pref == "Prefer same gender"),
            interests=tuple(TAG_NAMES.index(t) for t in interests),
            type_pref=(r_rest, r_cafe, r_bar),
            cuisine_pref=tuple(5 if c in loves else 2 for c in CUISINES),
            budget=["$", "$$", "$$$"].index(budget) + 1,
            avail=tuple(bool(a) for a in avail),
            slot_pref=tuple(1.0 if a else 0.0 for a in avail),
        )
        st.session_state.sealed_at = st.session_state.get("sealed_at", 0) + 1
    return submitted


__all__ = ["solve_b", "solve_everything", "tables_of", "dark_map", "profile_form", "profile_key",
           "find_user_table", "describe_table", "COLORS", "TONIGHT_N"]

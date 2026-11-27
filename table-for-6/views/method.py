from pathlib import Path
import streamlit as st
from ui.theme import show, img, hero

ROOT = Path(__file__).resolve().parents[1]

hero(img("pour", 2200), "The method", "The science of<br>a good table.",
     "An integer program, a column generator, and a few honest numbers. No crystal ball.", short=True)

show("""<div class="sec"><div class="reveal center"><div class="eyebrow">The question</div>
<p class="statement">Given <em>N</em> strangers, a city of venues and three evenings, how do you seat everyone
so the whole city has the <em>best possible night?</em></p><hr class="rule"></div></div>""")

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">I. The score</div>
<h2>What a good evening <em>is worth</em></h2><p>Each guest's value at a table adds up their taste for the venue and hour,
how well they get along with each tablemate, and subtracts travel time and tolls.</p></div></div>""")
st.latex(r"U_{ig} \;=\; p_{i v_g t_g} \;+\; \tfrac{1}{|S_g|-1}\sum_{j\in S_g\setminus\{i\}} q_{ij}\;-\;\lambda_d\, d_{i v_g t_g}\;-\;\lambda_\tau\,\tau_{i v_g}")
show("""<p style="color:var(--mist);text-align:center">Here <i>p</i> is satisfaction (0 to 10), <i>q</i><sub>ij</sub> is the chemistry between guests
<i>i</i> and <i>j</i>, <i>d</i> is minutes of travel and <i>τ</i> is the bridge toll.</p>""")

c1, c2 = st.columns(2, gap="large")
with c1:
    show("""<div class="sec tight"><div class="mcard reveal" style="border-color:#8197BF"><div class="eyebrow">II. Model A</div>
<h4>The compact MILP</h4><p>Seat guests one by one. Binary <i>x</i><sub>ik</sub> puts guest <i>i</i> at table <i>k</i>, <i>z</i><sub>k</sub> opens the table,
and <i>y</i><sub>ijk</sub> records that <i>i</i> and <i>j</i> share it, linearized with <i>y</i><sub>ijk</sub> ≤ <i>x</i><sub>ik</sub> and <i>y</i><sub>ijk</sub> ≤ <i>x</i><sub>jk</sub>.</p>
<p>Exact, but the relaxation is weak: a fractional guest can be "a sixth at every table", so branch and bound has little to prune.
It stalls from 24 guests on.</p></div></div>""")
    st.latex(r"\max \sum_{i,k} c_{ik}x_{ik} + \sum_k\sum_{i<j} q_{ij}y_{ijk} - M\sum_i u_i")
    st.latex(r"\textstyle\sum_k x_{ik}+u_i=1,\quad L z_k \le \sum_i x_{ik} \le U z_k")
    st.latex(r"\textstyle 3\sum_{i:\,\ell_i=\ell} x_{ik} - 2\sum_i x_{ik} \le 2 + U s_k")
with c2:
    show("""<div class="sec tight"><div class="mcard reveal" style="border-color:#C8A96A"><div class="eyebrow">III. Model B</div>
<h4>Column generation</h4><p>Choose whole tables instead. Each column <i>g</i> is a complete table with value <i>C</i><sub>g</sub>, and the master
problem picks which tables to open. A pricing step uses the duals <i>π</i><sub>i</sub> and <i>μ</i><sub>vt</sub> to discover new tables worth adding.</p>
<p>The relaxation is tight, every table rule becomes a number per column, and weak duality gives a certified upper bound.</p></div></div>""")
    st.latex(r"\max \sum_g C_g\lambda_g - M\sum_i u_i")
    st.latex(r"\textstyle\sum_g A_{ig}\lambda_g+u_i=1,\quad \sum_{g\in\mathcal G_{vt}}\lambda_g\le R_{vt}")
    st.latex(r"\bar C_g = \sum_{i\in S_g}\big[(1+\sigma_i)U_{ig}-\pi_i\big]-\kappa e_g-\mu_{v_g t_g} > 0")

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">IV. The add-ons</div>
<h2>Fair, close, <em>and actually full</em></h2></div>
<div class="stats reveal">
 <div class="stat"><b>θ</b><span><span style="color:var(--ivory)">Fairness floor.</span> Weight <i>γ</i> = 10 lifts the worst-off guest from −0.45 to 3.9 for 1.2% of total value.</span></div>
 <div class="stat"><b>λ<sub style="font-size:.4em">d</sub></b><span><span style="color:var(--ivory)">Value of time.</span> Pricing a minute at 0.08 points cuts the average trip from 50 to 23 minutes.</span></div>
 <div class="stat"><b>α</b><span><span style="color:var(--ivory)">No-show guarantee.</span> Each table has at least a 90% chance of four guests, checked with a Poisson-binomial DP.</span></div>
 <div class="stat"><b>ℓ<sub style="font-size:.4em">i</sub></b><span><span style="color:var(--ivory)">Gender is a rule.</span> Ask for a same-gender table and you only get one. Every other table is mixed, with at most 4 of 6 guests sharing a gender. Never traded for points.</span></div>
</div></div>""")

show("""<div class="sec tight"><div class="sechead reveal"><div class="eyebrow">V. The evidence</div>
<h2>What the <em>experiments</em> say</h2><p>From the report. Model B matches Model A's proven optimum on 9 of 10 small instances,
beats Greedy by about 9.5% from 60 guests up, and seats 240 guests in about three and a half minutes.</p></div></div>""")
for f, cap in [("fig_quality_scale_cg.png", "Quality against the certified bound, solve time, and column generation converging."),
               ("fig_tradeoffs.png", "What the add-ons buy: travel against satisfaction, the fairness floor, and no-show protection."),
               ("fig_map.png", "Random seating against Model B on the same 60 guests.")]:
    show(f"""<div class="reveal" style="background:#F4EFE4;padding:1.6rem 1.6rem 1rem;margin:0 0 .6rem">
<img src="app/static/{f}" style="width:100%;display:block"></div><p style="color:var(--mist);font-size:.9rem;margin-bottom:2.4rem">{cap}</p>""")

show("""<div class="fullbleed band" style="height:60vh"><div class="ph" style="background-image:url('""" + img("skyline_dusk", 2200) + """')"></div>
<div class="q reveal"><small>The fine print</small><p>Simulated guests. Real math. A slightly smaller city.</p></div></div>""")

pdf = ROOT / "report" / "main.pdf"
st.markdown("<br><br>", unsafe_allow_html=True)
if pdf.exists():
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        st.download_button("Download the full report", pdf.read_bytes(), file_name="Table for 6 - report.pdf",
                           mime="application/pdf", width="stretch")

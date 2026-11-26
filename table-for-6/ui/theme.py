"""Look and feel: palette, fonts, global CSS, shared page pieces (nav, hero bands, footer)."""
import html
import streamlit as st

# Photography: free Unsplash photos (Unsplash License), hot-linked from images.unsplash.com.
U = "https://images.unsplash.com/"
PHOTOS = {
    "candle_dinner": "photo-1778694277039-5cbf0b9a1fcf",
    "toast_white": "photo-1527529482837-4698179dc6ce",
    "laughing": "photo-1681641092941-b1acee507ee0",
    "glasses_up": "photo-1558346489-19413928158b",
    "bar_glow": "photo-1770334597610-8335702e8ab1",
    "dark_dining": "photo-1709548145082-04d0cde481d4",
    "dark_dining2": "photo-1680209668065-26985bc92268",
    "lamps": "photo-1552960226-639240203497",
    "cocktail": "photo-1778104959337-5260c89e2293",
    "pour": "photo-1683744129473-77f257db55fd",
    "cafe": "photo-1501339847302-ac426a4a7cbb",
    "bridge_fog": "photo-1635793902077-97d544d5c6b3",
    "bridge_night": "photo-1685946900453-8154d1154afc",
    "skyline_dusk": "photo-1768066360882-14302bb37971",
    "bridge_lights": "photo-1532403540890-3078c4024caf",
    "long_table": "photo-1536392706976-e486e2ba97af",
    "candles_row": "photo-1562050344-f7ad946cee35",
}
HERO_LOCAL = "app/static/hero.jpg"   # Amy's cheese-board shot, served by Streamlit static serving
VENUE_PHOTO = {"restaurant": "dark_dining", "cafe": "cafe", "bar": "cocktail"}

# method colors on the dark theme
COLORS = {"Random": "#77716A", "Greedy": "#B9805E", "Model A": "#8197BF", "Model B": "#C8A96A"}


def img(key, w=2000, h=None):
    q = f"?auto=format&fit=crop&w={w}&q=72" + (f"&h={h}" if h else "")
    return U + PHOTOS[key] + q


def H(text):
    return html.escape(str(text))


def show(markup):
    """Raw HTML through markdown (keeps inline SVG). Blank lines and indents would break the HTML block."""
    st.markdown("\n".join(l.strip() for l in markup.splitlines() if l.strip()), unsafe_allow_html=True)


CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400;1,500&family=Jost:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{
  --night:#0A0D0C; --deep:#0F1614; --teal:#15221F; --card:#121A18; --line:rgba(200,169,106,.22);
  --gold:#C8A96A; --gold2:#E6D2A2; --ivory:#EEE7D8; --mist:#9C978C; --wine:#6B2333;
  --serif:'Cormorant Garamond', 'Times New Roman', serif; --sans:'Jost', 'Helvetica Neue', sans-serif;
}
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"]{ background:var(--night) !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stSidebarCollapsedControl"]{ display:none !important; }
[data-testid="stMain"]{ overflow-x:hidden; }
.block-container{ padding:0 2.2rem 0 !important; max-width:1240px !important; }
[data-testid="stMainBlockContainer"]{ padding-top:0 !important; }
html, body, .stApp, p, li, label, input, textarea, button{ font-family:var(--sans); }
h1 *, h2 *, h3 *, h4 *{ font-family:inherit !important; }
h1 a, h2 a, h3 a{ display:none !important; }
p, li{ color:var(--ivory); font-weight:300; font-size:1.02rem; line-height:1.7; }
h1,h2,h3,h4{ font-family:var(--serif) !important; color:var(--ivory) !important; font-weight:300 !important; letter-spacing:.005em; }
a{ color:var(--gold); }
::selection{ background:var(--gold); color:var(--night); }

/* ---------- motion ---------- */
@keyframes rise{ from{ opacity:0; transform:translateY(34px);} to{ opacity:1; transform:none;} }
@keyframes fade{ from{ opacity:0;} to{ opacity:1;} }
@keyframes kenburns{ from{ transform:scale(1.12);} to{ transform:scale(1.0);} }
@keyframes drift{ from{ transform:translateX(0);} to{ transform:translateX(-50%);} }
@keyframes spin{ to{ transform:rotate(360deg);} }
@keyframes flicker{ 0%,100%{opacity:.85} 45%{opacity:1} 50%{opacity:.7} 55%{opacity:.95} }
@keyframes cue{ 0%{ transform:translateY(-100%);} 100%{ transform:translateY(100%);} }
@keyframes seat{ from{ opacity:0; transform:scale(.4);} to{ opacity:1; transform:scale(1);} }
@keyframes unseal{ 0%{ transform:scale(1) rotate(0); opacity:1;} 60%{ transform:scale(1.15) rotate(-12deg); opacity:1;} 100%{ transform:scale(.2) rotate(-40deg); opacity:0;} }
@keyframes letter{ from{ transform:translateY(60px) scale(.97); opacity:0; clip-path:inset(100% 0 0 0);} to{ transform:none; opacity:1; clip-path:inset(0 0 0 0);} }
@keyframes shimmer{ from{ background-position:-200% 0;} to{ background-position:200% 0;} }
.in{ animation:rise 1.1s cubic-bezier(.2,.7,.2,1) both; }
.d1{ animation-delay:.15s } .d2{ animation-delay:.35s } .d3{ animation-delay:.55s } .d4{ animation-delay:.75s }
@supports (animation-timeline: view()){
  .reveal{ animation:rise linear both; animation-timeline:view(); animation-range:entry 5% cover 28%; }
  .reveal-img img, .reveal-img .ph{ animation:kenburns linear both; animation-timeline:view(); animation-range:entry 0% exit 100%; }
}
@media (prefers-reduced-motion: reduce){ *{ animation:none !important; transition:none !important; } }

/* ---------- nav ---------- */
[data-testid="stElementContainer"]:has(style), [data-testid="stElementContainer"]:has(script), [data-testid="stElementContainer"]:has(> [data-testid="stHtml"]:empty){ display:none !important; }
[data-testid="stLayoutWrapper"]:has(> .st-key-topnav){ position:absolute !important; height:0; }
.st-key-topnav{ position:fixed !important; top:0; left:0; right:0; z-index:1000; padding:1.1rem 2.6rem .9rem;
  background:linear-gradient(180deg, rgba(10,13,12,.78), rgba(10,13,12,.35)); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  border-bottom:1px solid rgba(200,169,106,.14); }
.st-key-topnav [data-testid="stHorizontalBlock"]{ align-items:center; flex-wrap:nowrap !important; gap:.4rem; }
.st-key-topnav [data-testid="stPageLink"] a, .st-key-topnav [data-testid="stPageLink-NavLink"]{
  background:transparent !important; padding:.2rem .1rem !important; border-radius:0 !important; }
.st-key-topnav [data-testid="stPageLink"] p, .st-key-topnav [data-testid="stPageLink-NavLink"] span{
  font-family:var(--sans) !important; text-transform:uppercase; letter-spacing:.24em; font-size:.74rem !important;
  color:var(--ivory) !important; font-weight:400; position:relative; white-space:nowrap; }
.st-key-topnav [data-testid="stPageLink"] a:hover p, .st-key-topnav [data-testid="stPageLink"] a:hover span{ color:var(--gold) !important; }
.st-key-topnav [data-testid="stColumn"]:nth-child(3) [data-testid="stPageLink"]{ display:flex; justify-content:flex-end; }
.st-key-topnav [data-testid="stColumn"]:nth-child(2){ display:flex; justify-content:center; }
.seal{ width:64px; height:64px; display:block; margin:auto; }
.seal .ring{ transform-origin:50% 50%; animation:spin 40s linear infinite; }
.seal:hover .ring{ animation-duration:6s; }
.navlinks{ display:flex; gap:2.2rem; }

/* ---------- hero ---------- */
.fullbleed{ width:100vw; position:relative; left:50%; margin-left:-50vw; }
.hero{ height:100vh; min-height:620px; overflow:hidden; position:relative; background:#000; }
.hero .ph{ position:absolute; inset:0; background-size:cover; background-position:center 60%;
  animation:kenburns 16s cubic-bezier(.2,.6,.2,1) both; }
.hero .veil{ position:absolute; inset:0; background:
  radial-gradient(ellipse at 50% 40%, rgba(0,0,0,0) 0%, rgba(0,0,0,.35) 60%, rgba(0,0,0,.8) 100%),
  linear-gradient(180deg, rgba(10,13,12,.25) 0%, rgba(10,13,12,0) 35%, rgba(10,13,12,.9) 100%); }
.hero .copy{ position:absolute; left:0; right:0; bottom:13vh; text-align:center; padding:0 1.5rem; }
.hero h1{ font-size:clamp(3rem, 8.2vw, 7.4rem) !important; line-height:.92 !important; font-style:italic; margin:0 !important; }
.hero .kick{ font-family:var(--sans); text-transform:uppercase; letter-spacing:.42em; font-size:.74rem; color:var(--gold2); margin-bottom:1.4rem; }
.hero .lede{ max-width:34rem; margin:1.4rem auto 0; color:rgba(238,231,216,.82); font-size:1.08rem; }
.hero .corner{ position:absolute; bottom:2.2rem; right:2.6rem; font-family:var(--sans); letter-spacing:.24em; text-transform:uppercase;
  font-size:.74rem; color:var(--ivory); border-bottom:1px solid var(--ivory); padding-bottom:.4rem; }
.hero .cue{ position:absolute; left:50%; bottom:0; width:1px; height:9vh; background:rgba(238,231,216,.18); overflow:hidden; }
.hero .cue::after{ content:''; position:absolute; inset:0; background:var(--gold); animation:cue 2.2s ease-in-out infinite; }
.hero.short{ height:72vh; min-height:480px; }
.hero.short .copy{ bottom:10vh; }

/* ---------- type blocks ---------- */
.eyebrow{ font-family:var(--sans); text-transform:uppercase; letter-spacing:.38em; font-size:.7rem; color:var(--gold); margin-bottom:1rem; }
.statement{ font-family:var(--serif) !important; font-weight:300 !important; font-size:clamp(2rem, 4.4vw, 3.9rem) !important; line-height:1.12 !important; color:var(--ivory);
  max-width:62rem; margin:0 auto; text-align:center; }
.statement em{ color:var(--gold2); }
.sec{ padding:8.5rem 0 5rem; }
.sec.tight{ padding:5rem 0 3rem; }
.sechead h2{ font-size:clamp(2.4rem, 5vw, 4.2rem) !important; line-height:1 !important; margin:0 0 1rem !important; }
.sechead h2 em{ color:var(--gold2); }
.sechead p{ color:var(--mist); max-width:40rem; font-size:1.06rem; }
.center{ text-align:center; } .center p{ margin-left:auto; margin-right:auto; }
.rule{ width:64px; height:1px; background:var(--gold); margin:1.6rem auto; border:0; }

/* ---------- marquee ---------- */
.marquee{ overflow:hidden; border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:1.3rem 0; }
.marquee .track{ display:flex; width:max-content; animation:drift 60s linear infinite; }
.marquee:hover .track{ animation-play-state:paused; }
.marquee span{ font-family:var(--serif); font-style:italic; font-size:2.1rem; color:var(--ivory); padding:0 1.6rem; white-space:nowrap; }
.marquee span.dot{ color:var(--gold); font-style:normal; padding:0; }

/* ---------- acts / image cards ---------- */
.acts{ display:grid; grid-template-columns:repeat(3,1fr); gap:1.4rem; }
.act{ position:relative; height:560px; overflow:hidden; cursor:default; background:#000; }
.act .ph{ position:absolute; inset:0; background-size:cover; background-position:center; transition:transform 1.6s cubic-bezier(.2,.7,.2,1), filter 1.2s; filter:brightness(.55) saturate(.85); }
.act:hover .ph{ transform:scale(1.08); filter:brightness(.75) saturate(1); }
.act .txt{ position:absolute; left:1.8rem; right:1.8rem; bottom:1.8rem; }
.act .num{ font-family:var(--serif); font-style:italic; color:var(--gold); font-size:1.4rem; }
.act h3{ font-size:2.3rem !important; margin:.2rem 0 .4rem !important; }
.act .more{ max-height:0; opacity:0; overflow:hidden; transition:max-height .9s ease, opacity .9s ease; color:rgba(238,231,216,.86); font-size:.98rem; }
.act:hover .more{ max-height:12rem; opacity:1; }
.act .line{ width:0; height:1px; background:var(--gold); transition:width .9s ease; margin-top:.8rem; }
.act:hover .line{ width:100%; }

.band{ height:78vh; min-height:480px; position:relative; overflow:hidden; display:flex; align-items:center; justify-content:center; }
.band .ph{ position:absolute; inset:-10% 0; background-size:cover; background-position:center; background-attachment:fixed; filter:brightness(.42); }
.band .q{ position:relative; text-align:center; max-width:52rem; padding:0 1.5rem; }
.band .q p{ font-family:var(--serif) !important; font-style:italic; font-size:clamp(1.9rem, 4vw, 3.4rem) !important; line-height:1.15 !important; color:var(--ivory); font-weight:300; }
.band .q small{ font-family:var(--sans); letter-spacing:.32em; text-transform:uppercase; font-size:.7rem; color:var(--gold); }

.split{ display:grid; grid-template-columns:1.1fr 1fr; gap:4.5rem; align-items:center; }
.split .frame{ height:640px; overflow:hidden; position:relative; }
.split .frame .ph{ position:absolute; inset:0; background-size:cover; background-position:center; }
.split .frame::after{ content:''; position:absolute; inset:18px; border:1px solid rgba(230,210,162,.45); pointer-events:none; }

.trio{ display:grid; grid-template-columns:2fr 1fr 1fr; gap:1.2rem; }
.venue{ position:relative; height:460px; overflow:hidden; }
.venue .ph{ position:absolute; inset:0; background-size:cover; background-position:center; filter:brightness(.6) grayscale(.25); transition:all 1.2s cubic-bezier(.2,.7,.2,1); }
.venue:hover .ph{ filter:brightness(.85) grayscale(0); transform:scale(1.05); }
.venue .lab{ position:absolute; left:1.5rem; bottom:1.3rem; }
.venue .lab b{ font-family:var(--serif); font-weight:300; font-style:italic; font-size:2.2rem; color:var(--ivory); display:block; }
.venue .lab span{ font-family:var(--sans); letter-spacing:.28em; text-transform:uppercase; font-size:.66rem; color:var(--gold2); }

.stats{ display:grid; grid-template-columns:repeat(4,1fr); border-top:1px solid var(--line); }
.stat{ padding:2.4rem 1.4rem 1.4rem; border-right:1px solid var(--line); }
.stat:last-child{ border-right:0; }
.stat b{ font-family:var(--serif); font-weight:300; font-size:4.2rem; color:var(--gold2); display:block; line-height:1; }
.stat span{ color:var(--mist); font-size:.92rem; display:block; margin-top:.8rem; }

/* ---------- spotlight (cursor-follow) ---------- */
.spot{ position:relative; min-height:520px; overflow:hidden; background:#050706; cursor:none; --x:50%; --y:50%; }
.spot .ph{ position:absolute; inset:0; background-size:cover; background-position:center; filter:brightness(.9);
  -webkit-mask-image:radial-gradient(circle 190px at var(--x) var(--y), #000 0%, rgba(0,0,0,.35) 45%, transparent 75%);
  mask-image:radial-gradient(circle 190px at var(--x) var(--y), #000 0%, rgba(0,0,0,.35) 45%, transparent 75%); }
.spot .msg{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; pointer-events:none; text-align:center; }
.spot .msg p{ font-family:var(--serif) !important; font-style:italic; font-size:clamp(1.8rem,3.6vw,3rem) !important; color:var(--ivory); margin:0; }
.spot .msg small{ font-family:var(--sans); letter-spacing:.3em; text-transform:uppercase; font-size:.68rem; color:var(--gold); margin-top:1rem; }
.spot .glow{ position:absolute; width:16px; height:16px; border-radius:50%; background:var(--gold); left:var(--x); top:var(--y);
  transform:translate(-50%,-50%); box-shadow:0 0 40px 12px rgba(200,169,106,.35); animation:flicker 3s infinite; pointer-events:none; }

/* ---------- buttons & widgets ---------- */
.cta{ display:inline-block; border:1px solid var(--gold); color:var(--gold2) !important; text-decoration:none !important;
  font-family:var(--sans); letter-spacing:.3em; text-transform:uppercase; font-size:.74rem; padding:1.05rem 2.4rem;
  background:linear-gradient(90deg, transparent 0%, transparent 50%, var(--gold) 50%) right/220% 100%; transition:all .7s ease; }
.cta:hover{ background-position:left; color:var(--night) !important; }
[data-testid="stPageLink"] a.cta-link, .st-key-cta [data-testid="stPageLink"] a{ border:1px solid var(--gold) !important; border-radius:0 !important;
  padding:1rem 2.3rem !important; background:transparent !important; transition:background .6s ease; }
.st-key-cta [data-testid="stPageLink"] a:hover{ background:var(--gold) !important; }
.st-key-cta [data-testid="stPageLink"] p, .st-key-cta [data-testid="stPageLink"] span{ font-family:var(--sans) !important; letter-spacing:.3em; text-transform:uppercase;
  font-size:.74rem !important; color:var(--gold2) !important; }
.st-key-cta [data-testid="stPageLink"] a:hover p, .st-key-cta [data-testid="stPageLink"] a:hover span{ color:var(--night) !important; }
.st-key-cta{ align-items:center; }

.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button{ background:transparent !important; color:var(--gold2) !important; border:1px solid var(--gold) !important;
  border-radius:0 !important; padding:.95rem 2.4rem !important; transition:all .6s ease; }
.stButton > button p, .stFormSubmitButton > button p, .stDownloadButton > button p{ font-family:var(--sans) !important; letter-spacing:.3em; text-transform:uppercase; font-size:.74rem !important; color:inherit !important; }
.stButton > button:hover, .stFormSubmitButton > button:hover, .stDownloadButton > button:hover{ background:var(--gold) !important; color:var(--night) !important; }
[data-testid="stForm"]{ background:linear-gradient(180deg, rgba(21,34,31,.65), rgba(15,22,20,.65)); border:1px solid var(--line) !important; border-radius:0; padding:2.4rem 2.6rem; }
[data-testid="stWidgetLabel"] p{ font-family:var(--sans) !important; text-transform:uppercase; letter-spacing:.2em; font-size:.68rem !important; color:var(--gold) !important; }
div[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input{ background:rgba(10,13,12,.6) !important; border-radius:0 !important; border-color:var(--line) !important; }
[data-baseweb="tag"]{ background:transparent !important; border:1px solid var(--gold) !important; border-radius:0 !important; }
[data-baseweb="tag"] span{ color:var(--gold2) !important; }
[data-testid="stExpander"]{ border:1px solid var(--line) !important; border-radius:0 !important; background:var(--card); }
[data-testid="stExpander"] summary p{ font-family:var(--serif) !important; font-size:1.3rem !important; font-style:italic; }
[data-testid="stPills"] button, [data-testid="stButtonGroup"] button{ border-radius:0 !important; }
.stSlider [data-baseweb="slider"] div[role="slider"]{ box-shadow:0 0 0 5px rgba(200,169,106,.18); }
[data-testid="stCaptionContainer"] p{ color:var(--mist) !important; }

/* ---------- data pieces ---------- */
table.score{ width:100%; border-collapse:collapse; font-family:var(--sans); font-size:.95rem; }
table.score th{ text-align:right; font-weight:400; color:var(--gold); padding:.9rem .8rem; border-bottom:1px solid var(--gold);
  font-size:.64rem; text-transform:uppercase; letter-spacing:.2em; }
table.score th:first-child, table.score td:first-child{ text-align:left; white-space:nowrap; }
table.score td{ text-align:right; padding:1rem .8rem; border-bottom:1px solid var(--line); color:var(--ivory); font-weight:300; }
table.score tr{ transition:background .4s; }
table.score tr:hover td{ background:rgba(200,169,106,.06); }
table.score td.best{ color:var(--gold2); font-weight:500; }
table.score td.best::after{ content:' ✦'; color:var(--gold); font-size:.7rem; }
table.score td .meta{ color:var(--mist); font-size:.8rem; }
.dot{ display:inline-block; width:.6rem; height:.6rem; border-radius:50%; margin-right:.7rem; vertical-align:middle; }
.bars .row{ display:grid; grid-template-columns:7rem 1fr 4.2rem; align-items:center; gap:1rem; margin:.9rem 0; }
.bars .row span{ font-size:.92rem; color:var(--ivory); }
.bars .track{ height:6px; background:rgba(238,231,216,.07); position:relative; overflow:hidden; }
.bars .fill{ height:100%; transform-origin:left; animation:growx 1.6s cubic-bezier(.2,.7,.2,1) both; }
@keyframes growx{ from{ transform:scaleX(0);} to{ transform:scaleX(1);} }
.bars .pct{ text-align:right; font-family:var(--serif); font-size:1.4rem; color:var(--gold2); }

.mcard{ border-top:1px solid; padding:1.4rem 0 0; }
.mcard h4{ font-size:1.9rem !important; margin:0 0 .3rem !important; font-style:italic; }
.mcard p{ color:var(--mist); font-size:.96rem; margin:.3rem 0; }
.mcard p b{ color:var(--ivory); font-weight:400; }

.tcard{ position:relative; overflow:hidden; height:430px; margin-bottom:1.2rem; background:#000; border:1px solid var(--line); }
.tcard .ph{ position:absolute; inset:0; background-size:cover; background-position:center; filter:brightness(.38) saturate(.8); transition:all 1.1s cubic-bezier(.2,.7,.2,1); }
.tcard:hover .ph{ filter:brightness(.18) saturate(.6); transform:scale(1.06); }
.tcard .top{ position:absolute; top:1.3rem; left:1.4rem; right:1.4rem; display:flex; justify-content:space-between; }
.tcard .top span{ font-family:var(--sans); letter-spacing:.26em; text-transform:uppercase; font-size:.62rem; color:var(--gold2); }
.tcard .body{ position:absolute; left:1.4rem; right:1.4rem; bottom:1.3rem; transition:transform .9s cubic-bezier(.2,.7,.2,1); transform:translateY(calc(100% - 7.6rem)); }
.tcard:hover .body{ transform:none; }
.tcard h4{ font-size:2rem !important; margin:0 !important; line-height:1.05 !important; }
.tcard .kind{ color:var(--mist); font-size:.86rem; margin:.3rem 0 .8rem; }
.tcard ul{ list-style:none; padding:0; margin:.4rem 0 0; border-top:1px solid var(--line); }
.tcard li{ font-size:.86rem; padding:.32rem 0; border-bottom:1px solid rgba(200,169,106,.12); display:flex; justify-content:space-between; line-height:1.3; }
.tcard li i{ color:var(--mist); font-style:normal; }
.chips{ margin:.2rem 0 .3rem; }
.chips span{ display:inline-block; border:1px solid rgba(200,169,106,.5); padding:.12rem .6rem; margin:.18rem .3rem 0 0;
  font-size:.66rem; letter-spacing:.16em; text-transform:uppercase; color:var(--gold2); }

/* ---------- invitation ---------- */
.letter{ position:relative; background:linear-gradient(160deg, #17241F 0%, #0E1513 100%); border:1px solid var(--line); padding:3.4rem 3.4rem 3rem;
  animation:letter 1.6s .9s cubic-bezier(.2,.7,.2,1) both; overflow:hidden; }
.letter::before{ content:''; position:absolute; inset:14px; border:1px solid rgba(200,169,106,.3); pointer-events:none; }
.letter::after{ content:''; position:absolute; inset:0; background:linear-gradient(110deg, transparent 30%, rgba(230,210,162,.09) 50%, transparent 70%);
  background-size:200% 100%; animation:shimmer 3.2s 2.4s ease-in-out 1 both; pointer-events:none; }
.waxwrap{ display:flex; justify-content:center; height:0; position:relative; z-index:3; }
.wax{ width:120px; height:120px; margin-top:-10px; animation:unseal 1.2s .2s cubic-bezier(.6,0,.4,1) both; }
.letter h2{ font-size:clamp(2.6rem,5vw,4.3rem) !important; font-style:italic; margin:.2rem 0 .4rem !important; line-height:1 !important; }
.letter .when{ font-family:var(--sans); letter-spacing:.3em; text-transform:uppercase; font-size:.72rem; color:var(--gold2); }
.letter .facts{ display:grid; grid-template-columns:repeat(4,1fr); border-top:1px solid var(--line); border-bottom:1px solid var(--line); margin:1.8rem 0; }
.letter .facts div{ padding:1rem .2rem; }
.letter .facts b{ display:block; font-family:var(--serif); font-weight:300; font-size:1.9rem; color:var(--ivory); }
.letter .facts span{ font-size:.62rem; letter-spacing:.24em; text-transform:uppercase; color:var(--mist); }
.roundtable{ display:block; margin:0 auto; max-width:440px; width:100%; overflow:visible; }
.roundtable .s{ animation:seat .8s cubic-bezier(.2,.7,.2,1.4) both; transform-box:fill-box; transform-origin:center; cursor:pointer; }
.roundtable .s circle{ transition:all .4s; }
.roundtable .s:hover circle.c{ fill:var(--gold); }
.roundtable .s .tip{ opacity:0; transition:opacity .35s; pointer-events:none; }
.roundtable .s:hover .tip{ opacity:1; }
.guests{ display:grid; grid-template-columns:repeat(auto-fit, minmax(190px,1fr)); gap:1rem; }
.guest{ border:1px solid var(--line); padding:1rem 1.1rem; transition:border-color .5s, background .5s; }
.guest:hover{ border-color:var(--gold); background:rgba(200,169,106,.05); }
.guest b{ font-family:var(--serif); font-weight:400; font-style:italic; font-size:1.35rem; color:var(--ivory); display:block; }
.guest span{ font-size:.82rem; color:var(--mist); display:block; }


/* ---------- invitation wizard ---------- */
.rail{ display:grid; grid-template-columns:repeat(6,1fr); position:relative; }
.rail .st{ text-align:center; position:relative; z-index:1; }
.rail .st b{ display:inline-flex; width:46px; height:46px; border-radius:50%; align-items:center; justify-content:center; border:1px solid var(--line);
  font-family:var(--serif); font-style:italic; font-weight:400; font-size:1.15rem; color:var(--mist); background:var(--night); transition:all .6s; }
.rail .st span{ display:block; margin-top:.6rem; font-family:var(--sans); letter-spacing:.26em; text-transform:uppercase; font-size:.6rem; color:var(--mist); }
.rail .st.on b{ border-color:var(--gold); color:var(--night); background:var(--gold); box-shadow:0 0 0 6px rgba(200,169,106,.14), 0 0 30px rgba(200,169,106,.35); }
.rail .st.on span{ color:var(--gold2); }
.rail .st.done b{ border-color:var(--gold); color:var(--gold2); }
.rail .bar{ position:absolute; left:8.33%; right:8.33%; top:23px; height:1px; background:var(--line); z-index:0; }
.rail .bar i{ display:block; height:100%; background:var(--gold); transition:width .8s cubic-bezier(.2,.7,.2,1); }
.st-key-wizard{ border:1px solid var(--line); background:radial-gradient(ellipse at 20% 0%, rgba(200,169,106,.08), transparent 55%),
  linear-gradient(180deg, rgba(21,34,31,.7), rgba(12,18,16,.7)); padding:3rem 3.4rem 2.2rem; position:relative; animation:rise .8s cubic-bezier(.2,.7,.2,1) both; gap:1.3rem; }
.st-key-wizard::before{ content:''; position:absolute; inset:12px; border:1px solid rgba(200,169,106,.16); pointer-events:none; }
.qhead h2{ font-size:clamp(2.2rem,4.4vw,3.6rem) !important; line-height:1.02 !important; margin:0 0 .5rem !important; }
.qhead h2 em{ color:var(--gold2); }
.qhead p{ color:var(--mist) !important; margin:0 0 .6rem; }
.st-key-wizard [data-testid="stButtonGroup"] button{ border-radius:0 !important; border-color:var(--line) !important; background:transparent !important;
  padding:.55rem 1.1rem !important; transition:all .35s; }
.st-key-wizard [data-testid="stButtonGroup"] button p{ font-family:var(--sans) !important; font-size:.92rem !important; letter-spacing:.04em; color:var(--ivory) !important; }
.st-key-wizard [data-testid="stButtonGroup"] button:hover{ border-color:var(--gold) !important; }
.st-key-wizard [data-testid="stButtonGroup"] button[kind$="Active"], .st-key-wizard [data-testid="stButtonGroup"] button[aria-checked="true"],
.st-key-wizard [data-testid="stButtonGroup"] button[aria-pressed="true"]{ background:var(--gold) !important; border-color:var(--gold) !important; }
.st-key-wizard [data-testid="stButtonGroup"] button[kind$="Active"] p, .st-key-wizard [data-testid="stButtonGroup"] button[aria-checked="true"] p,
.st-key-wizard [data-testid="stButtonGroup"] button[aria-pressed="true"] p{ color:var(--night) !important; }
.st-key-w_hood [data-testid="stButtonGroup"] button, .st-key-w_i [data-testid="stButtonGroup"] button{ padding:.8rem 1.4rem !important; }
.st-key-w_hood [data-testid="stButtonGroup"] button p, .st-key-w_i [data-testid="stButtonGroup"] button p{ font-family:var(--serif) !important; font-style:italic; font-size:1.3rem !important; }
.st-key-wiznav{ border-top:1px solid var(--line); padding-top:1.4rem; }
.st-key-w_back button{ border-color:transparent !important; }
.st-key-wizard .stTextInput input{ font-family:var(--serif) !important; font-size:1.3rem !important; font-style:italic; padding:.8rem 1rem !important; }
.found{ border:1px solid var(--gold); padding:1.2rem 1.4rem; display:flex; flex-direction:column; gap:.25rem; animation:rise .7s both;
  background:rgba(200,169,106,.05); }
.found b{ font-family:var(--serif); font-weight:400; font-size:1.8rem; font-style:italic; color:var(--ivory); }
.found span{ color:var(--mist); font-size:.92rem; }
.found .tag{ font-size:.6rem; letter-spacing:.3em; text-transform:uppercase; color:var(--gold); }
.found a, .maplink{ font-family:var(--sans); font-size:.68rem; letter-spacing:.26em; text-transform:uppercase; color:var(--gold2) !important;
  text-decoration:none; border-bottom:1px solid var(--gold); align-self:flex-start; padding-bottom:.2rem; margin-top:.4rem; display:inline-block; }
.found.miss{ border-color:rgba(156,151,140,.5); background:transparent; }
.found.miss b{ font-size:1.35rem; color:var(--mist); }
.review{ display:grid; grid-template-columns:1fr 1fr; border-top:1px solid var(--line); }
.review div{ padding:1rem .2rem; border-bottom:1px solid var(--line); }
.review span{ display:block; font-size:.6rem; letter-spacing:.28em; text-transform:uppercase; color:var(--gold); }
.review b{ font-family:var(--serif); font-weight:400; font-size:1.3rem; color:var(--ivory); }
.favbadge{ margin-top:1rem; padding:.7rem 1rem; border-left:2px solid var(--gold); background:rgba(200,169,106,.07); color:var(--gold2); font-size:.92rem; }
.favbadge.dim{ color:var(--mist); border-left-color:var(--mist); background:transparent; }

/* ---------- footer ---------- */
.foot{ margin-top:6rem; padding:4.5rem 0 3rem; border-top:1px solid var(--line); text-align:center; }
.foot .big{ font-family:var(--serif); font-style:italic; font-size:clamp(2.4rem,6vw,5rem); color:var(--ivory); line-height:1; }
.foot .row{ display:flex; justify-content:space-between; margin-top:3rem; font-family:var(--sans); letter-spacing:.24em; text-transform:uppercase; font-size:.62rem; color:var(--mist); flex-wrap:wrap; gap:1rem; }
.foot a{ color:var(--mist); text-decoration:none; } .foot a:hover{ color:var(--gold); }

/* math */
.katex{ color:var(--ivory); font-size:1.25em; }
[data-testid="stMarkdownContainer"] sub{ font-size:.7em; }
/* plotly and images */
.stPlotlyChart{ background:transparent !important; }
[data-testid="stImage"] img{ border-radius:0; }

@media (max-width: 900px){
  .acts, .trio, .split, .stats{ grid-template-columns:1fr; }
  .act{ height:420px; } .act .more{ max-height:none; opacity:1; }
  .split .frame{ height:380px; }
  .letter{ padding:2.2rem 1.4rem; } .letter .facts{ grid-template-columns:repeat(2,1fr); }
  .st-key-topnav{ padding:.8rem 1rem; } .navlinks{ gap:1rem; }
  .st-key-topnav [data-testid="stPageLink"] p{ letter-spacing:.12em; font-size:.62rem !important; }
  .block-container{ padding:0 1rem !important; }
  .band .ph{ background-attachment:scroll; }
  .lettergrid{ grid-template-columns:1fr !important; }
  .st-key-wizard{ padding:2rem 1.2rem 1.4rem; } .review{ grid-template-columns:1fr; } .rail .st span{ display:none; }
  .tcard .body{ transform:none; } .tcard .ph{ filter:brightness(.25); }
}
</style>
"""

SPOT_JS = """
<script>
(function(){
  function wire(el){
    if(el.dataset.wired) return; el.dataset.wired = 1;
    el.addEventListener('mousemove', function(e){
      var r = el.getBoundingClientRect();
      el.style.setProperty('--x', (e.clientX - r.left) + 'px');
      el.style.setProperty('--y', (e.clientY - r.top) + 'px');
    });
  }
  function scan(){ document.querySelectorAll('.spot').forEach(wire); }
  scan(); new MutationObserver(scan).observe(document.body, {childList:true, subtree:true});
})();
</script>
"""


def seal_svg(size=64, text="TABLE FOR SIX · BY INVITATION · SAN FRANCISCO · "):
    return f"""<svg class="seal" viewBox="0 0 120 120" width="{size}" height="{size}" aria-label="Table for 6">
  <defs><path id="sealc" d="M60,60 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0"/></defs>
  <g class="ring"><text font-family="Jost, sans-serif" font-size="8.4" letter-spacing="2.6" fill="#E6D2A2">
  <textPath href="#sealc">{text}</textPath></text></g>
  <circle cx="60" cy="60" r="34" fill="none" stroke="#C8A96A" stroke-width=".8"/>
  <text x="60" y="71" text-anchor="middle" font-family="Cormorant Garamond, serif" font-style="italic" font-size="34" fill="#EEE7D8">6</text>
</svg>"""


def inject():
    st.markdown("\n".join(l for l in CSS.splitlines() if l.strip()), unsafe_allow_html=True)
    st.html(SPOT_JS, unsafe_allow_javascript=True)


def hero(photo_url, kicker, title_html, lede="", corner="", short=False, pos="center 60%"):
    show(f"""<div class="fullbleed hero{' short' if short else ''}">
  <div class="ph" style="background-image:url('{photo_url}');background-position:{pos}"></div><div class="veil"></div>
  <div class="copy"><div class="kick in">{kicker}</div><h1 class="in d1">{title_html}</h1>
  {f'<p class="lede in d2">{lede}</p>' if lede else ''}</div>
  {f'<div class="corner in d3">{corner}</div>' if corner else ''}<div class="cue"></div></div>""")


def sechead(eyebrow, title_html, sub="", center=False, cls="sec"):
    show(f"""<div class="{cls}"><div class="sechead reveal{' center' if center else ''}"><div class="eyebrow">{eyebrow}</div>
<h2>{title_html}</h2>{f'<p>{sub}</p>' if sub else ''}</div></div>""")


def footer():
    show(f"""<div class="foot"><div class="eyebrow">Until next time</div><div class="big">See you at the table.</div>
<div class="row"><span>Table for 6 · IEOR 240 · Fall 2026</span><span>Simulated guests · real math</span>
<span>Photography via <a href="https://unsplash.com" target="_blank">Unsplash</a></span></div></div>""")

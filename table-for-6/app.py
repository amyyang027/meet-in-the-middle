"""Table for 6: a multi-page site. Run locally:  streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="Table for 6", page_icon="🕯️", layout="wide", initial_sidebar_state="collapsed")

from ui.theme import inject, seal_svg, footer, show  # noqa: E402

inject()

pages = {
    "home": st.Page("views/home.py", title="Table for 6", url_path="home", default=True),
    "invite": st.Page("views/invitation.py", title="The Invitation · Table for 6", url_path="invitation"),
    "tonight": st.Page("views/tonight.py", title="Tonight · Table for 6", url_path="tonight"),
    "lab": st.Page("views/lab.py", title="The Lab · Table for 6", url_path="lab"),
    "method": st.Page("views/method.py", title="The Method · Table for 6", url_path="method"),
}
current = st.navigation(list(pages.values()), position="hidden")

with st.container(key="topnav"):
    c = st.columns([1, 1, 1.1, 1, 1], vertical_alignment="center")
    c[0].page_link(pages["invite"], label="The Invitation")
    c[1].page_link(pages["tonight"], label="Tonight")
    with c[2]:
        show(f'<a href="/" target="_self" title="Home">{seal_svg(66)}</a>')
    c[3].page_link(pages["lab"], label="The Lab")
    c[4].page_link(pages["method"], label="The Method")

st.session_state["_pages"] = pages
current.run()
footer()

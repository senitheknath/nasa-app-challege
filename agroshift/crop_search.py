"""Debounced, bounded crop-name suggestions using Streamlit's built-in component API."""

import streamlit as st
from streamlit.components.v2 import component
from .knowledge import search_crops
from .finder_style import TOKENS

_SEARCH = component(
    "crop_name_search",
    html='<label for="crop-query">Find a crop</label><input id="crop-query" type="search" list="crop-names" autocomplete="off" maxlength="150" placeholder="Search by crop name or scientific name"><datalist id="crop-names"></datalist>',
    css="""label{display:block;font:14px/1.5 Inter,sans-serif;color:INK;margin-bottom:8px}
input{box-sizing:border-box;width:100%;padding:.7rem .8rem;font:16px Inter,sans-serif;color:INK;background:WASH;border:1px solid CONTROL;border-radius:10px;min-height:44px}
input:focus-visible{outline:3px solid BLUE;outline-offset:2px}
input::placeholder{color:MUTED}""".replace(
        "INK", TOKENS["ink"]
    )
    .replace("WASH", TOKENS["wash"])
    .replace("BLUE", TOKENS["blue"])
    .replace("MUTED", TOKENS["muted"])
    .replace("CONTROL", TOKENS["control"]),
    js="""export default function({parentElement,data,setStateValue}){
 const input=parentElement.querySelector('input');
 const names=parentElement.querySelector('datalist');
 if(!input.dataset.initialized){input.value=data.query||'';input.dataset.initialized='yes';}
 names.replaceChildren();
 for(const name of data.names||[]){const option=document.createElement('option');option.value=name;names.appendChild(option);}
 let timer;
 const send=()=>{clearTimeout(timer);setStateValue('query',input.value);};
 const change=()=>{clearTimeout(timer);timer=setTimeout(send,300);};
 input.addEventListener('input',change);
 input.addEventListener('change',send);
 const key=e=>{if(e.key==='Enter'){e.preventDefault();send();}};
 input.addEventListener('keydown',key);
 return ()=>{clearTimeout(timer);input.removeEventListener('input',change);input.removeEventListener('change',send);input.removeEventListener('keydown',key);};
}""",
)


def crop_query():
    def changed():
        value = st.session_state["crop_autocomplete"].get("query", "")
        st.session_state["catalogue_query"] = (
            value[:150] if isinstance(value, str) else ""
        )

    query = st.session_state.get("catalogue_query", "")
    _SEARCH(
        key="crop_autocomplete",
        data={
            "query": query,
            "names": [r["name"] for r in search_crops(query, limit=10)],
        },
        default={"query": query},
        on_query_change=changed,
    )
    return query

"""
supabase_client.py
Shared Supabase client — cached so only one connection is made per session.
"""
from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """Anon key client — subject to RLS. Use for all normal reads/writes."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


@st.cache_resource(show_spinner=False)
def get_admin_supabase() -> Client:
    """Service role client — bypasses RLS. Use only for trusted server-side operations."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)

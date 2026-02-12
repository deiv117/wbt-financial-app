# database.py
import streamlit as st
from supabase import create_client, Client

# Conexión única
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def get_categories():
    res = supabase.table("user_categories").select("*").execute()
    return sorted(res.data, key=lambda x: x['name'].lower()) if res.data else []

def get_all_inputs():
    res = supabase.table("user_imputs").select("*, user_categories(id, name, emoji, budget)").execute()
    return res.data if res.data else []

def save_input(data):
    return supabase.table("user_imputs").insert(data).execute()

def delete_input(input_id):
    return supabase.table("user_imputs").delete().eq("id", input_id).execute()

def update_input(input_id, data):
    return supabase.table("user_imputs").update(data).eq("id", input_id).execute()

def get_profile(user_id):
    res = supabase.table("profiles").select("*").eq("id", user_id).maybe_single().execute()
    return res.data if (hasattr(res, 'data') and res.data) else {}

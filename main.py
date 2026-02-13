import streamlit as st
import pandas as pd
from database import init_db, login_user, register_user, recover_password, get_user_profile, get_transactions, get_categories
from styles import get_custom_css

# IMPORTANTE: Borramos la línea que decía "from views import..."
# Y dejamos solo estas, que apuntan a los archivos específicos:
from views.dashboard import render_main_dashboard
from views.transactions import render_dashboard
from views.categories import render_categories
from views.profile import render_profile
from views.import_data import render_import

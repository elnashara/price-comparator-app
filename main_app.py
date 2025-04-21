import streamlit as st
from app.auth import Authenticator
from app.price_comparator import PriceComparator

def main():
    # Check if already authenticated
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        # Show login form
        auth = Authenticator(username="admin", password="admin123")
        if auth.login():
            st.session_state.authenticated = True
            st.rerun()  # ✅ rerun after login to clear form
        else:
            st.stop()
    else:
        # Show price comparator only
        app = PriceComparator()
        app.run()

if __name__ == "__main__":
    main()

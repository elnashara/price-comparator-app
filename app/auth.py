import streamlit as st

class Authenticator:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def login(self):
        st.title("🔐 Login Required")
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        login_btn = st.button("Login")

        if login_btn:
            if user_input == self.username and pass_input == self.password:
                st.success("Login successful!")
                return True
            else:
                st.error("Invalid username or password")
        return False

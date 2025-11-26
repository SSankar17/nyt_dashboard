import streamlit as st
import os



# to run app, copy paste in terminal: streamlit run Main_Page_-_Streamlit_App.py



st.set_page_config(
    page_title="NYT Bestsellers Dashboard - Home Page",
    layout="centered"
)

README_FILE_PATH = "readme.md"

#read and display the readme
def display_readme():
    """Reads the content of readme.md and displays it using st.markdown."""

    with open(README_FILE_PATH, 'r', encoding='utf-8') as f:
        readme_content = f.read()
        st.markdown(readme_content, unsafe_allow_html=True)
    

# mainpage
display_readme()

st.markdown("---")
st.info("Navigate to the sidebar to see the various research questions and analyses available in this dashboard!")
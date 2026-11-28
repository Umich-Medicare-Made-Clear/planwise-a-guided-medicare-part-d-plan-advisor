
import streamlit as st

st.title("What matters most to you?")
st.write(
    "A few more questions will help us understand what you value "
    "when choosing a prescription drug plan."
)

st.divider()

# Explanation Preference
st.subheader("Your cost preferences")

exp_preference = st.radio(
    "Which would you prioritize when having plans explained to you?",
    [
        "Estimated annual total",
        "Monthly premium and prescription payments",
        "Why costs may vary during the year",
        "Balanced overview",
        "I'm not sure"
    ],
    index=None
)

st.divider()

# Navigation
back_col, continue_col = st.columns([1, 3])

with back_col:
    if st.button("Back"):
        st.switch_page("pages/3_Pharmacy.py")

with continue_col:
    if st.button("Continue", use_container_width=True):

        if exp_preference is None:
            st.error("Please select a cost preference.")

        else:
            st.session_state.cost_preference = exp_preference

            st.switch_page("pages/5_Recommendations.py")


def collect_intake_data(session_state):
    """
    Collect all user intake answers into one organized dictionary.
    """

    intake_data = {
        # About the user
        "zip_code": session_state.get("zip_code", ""),
        "assistance": session_state.get("assistance", ""),
        "part_d_experience": session_state.get("part_d_experience", ""),

        # Medications
        "no_medications": session_state.get("no_medications", False),
        "medications": [
            dict(med)
            for med in session_state.get("medications", [])
        ],

        # Pharmacy preferences
        "pharmacy": session_state.get("pharmacy", ""),
        "no_pharmacy_preference": session_state.get(
            "no_pharmacy_preference", False
        ),
        "switch_pharmacy": session_state.get("switch_pharmacy", ""),

        # Plan preferences
        "exp_preference": session_state.get("exp_preference", "")
    }

    return intake_data

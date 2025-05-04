# chinese_flashcard_app.py
import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION ---
REVIEW_STEPS = [0, 1, 2, 4, 7, 15, 30, 90, 180]
TODAY = datetime.date.today()

# --- LOAD DATA ---
def load_data():
    try:
        df = pd.read_csv("character_data.csv")
        df["learned_date"] = pd.to_datetime(df["learned_date"]).dt.date
        if "set_nr" not in df.columns:
            df["set_nr"] = 0
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["set_nr","character", "pinyin", "example", "learned_date", "correct", "wrong"])

# --- SAVE DATA ---
def save_data(df):
    df.to_csv("character_data.csv", index=False)

# --- REVIEW DATE CALCULATOR ---
def get_due_characters(df):
    due_today = []
    for _, row in df.iterrows():
        if pd.isna(row["learned_date"]):
            continue
        learned = row["learned_date"]
        for step in REVIEW_STEPS:
            due_date = learned + datetime.timedelta(days=step)
            if due_date == TODAY:
                due_today.append(row["character"])
                break
    return df[df["character"].isin(due_today)]

# --- CREATE REVIEW PLAN TABLE ---
def build_review_table(df):
    table = []
    for _, row in df.iterrows():
        base = {
            "set_nr": row["set_nr"],
            "character": row["character"],
            "learned_date": row["learned_date"],
            "correct": row["correct"] if "correct" in row else 0,  # Ensure correct column exists
            "wrong": row["wrong"] if "wrong" in row else 0         # Ensure wrong column exists
        }

        for day in REVIEW_STEPS[1:]:
            review_date = row["learned_date"] + datetime.timedelta(days=day)
            label = f"Day {day} ({review_date.strftime('%Y-%m-%d')})"

            # For Day 1, check if user has clicked "Right" or "Wrong" (completed)
            if day == 1:
                if row["correct"] > 0 or row["wrong"] > 0:  # If any interaction
                    base[label] = "✅"
                else:
                    base[label] = "--"  # If not interacted yet
            # For other days (Day 2, Day 4, etc.), follow the usual review date logic
            elif review_date < TODAY:
                if row["correct"] > 0 or row["wrong"] > 0:
                    base[label] = "✅"
                else:
                    base[label] = "❌"
            elif review_date == TODAY:
                base[label] = "❌"
            else:
                base[label] = "--"
        
        table.append(base)

    return pd.DataFrame(table)

# --- AUTHENTICATION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "yilai":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password")
        st.stop()

check_password()

# --- APP UI ---
st.title("📚 伊莱汉字学习")

df = load_data()

menu = st.sidebar.radio("Choose mode:", ["Flashcard", "Dashboard", "Maintain Sets"])

if menu == "Maintain Sets":
    action = st.radio("What would you like to do?", ["New Set", "Edit Set", "Delete Set"])

    if action == "New Set":
        st.header("➕ Add New Character to a New Set")
        with st.form("add_new_set_form"):
            new_set_nr = st.number_input("New Set Number (required)", min_value=1, step=1)
            new_set_date = st.date_input("Learned Date for Set", TODAY)
            new_char = st.text_input("Character")
            new_pinyin = st.text_input("Pinyin")
            new_example = st.text_input("Example sentence")
            submitted = st.form_submit_button("Add Character to New Set")
            if submitted:
                if new_char:
                    df = df.append({
                        "set_nr": new_set_nr,
                        "character": new_char,
                        "pinyin": new_pinyin,
                        "example": new_example,
                        "learned_date": new_set_date,
                        "correct": 0,
                        "wrong": 0
                    }, ignore_index=True)
                    save_data(df)
                    st.success(f"Character added to set {new_set_nr}!")
                else:
                    st.error("Please enter a character.")

    elif action == "Edit Set":
        st.header("✏️ Edit Existing Set")
        edit_set_options = sorted(df["set_nr"].unique())
        set_to_edit = st.selectbox("Select Set to Edit:", edit_set_options)

        # Update learned date for the entire set
        current_date = df[df["set_nr"] == set_to_edit]["learned_date"].min()
        new_set_date = st.date_input("Update Learned Date for Set:", value=current_date)
        if st.button("Update Set Date"):
            df.loc[df["set_nr"] == set_to_edit, "learned_date"] = new_set_date
            save_data(df)
            st.success("Set learned date updated for all characters.")

        # Edit each character
        st.subheader("✏️ Edit Characters in This Set")
        char_df = df[df["set_nr"] == set_to_edit]
        for idx, row in char_df.iterrows():
            with st.expander(f"{row['character']}"):
                new_pinyin = st.text_input(f"Pinyin for {row['character']}", value=row['pinyin'], key=f"pinyin_{idx}")
                new_example = st.text_input(f"Example for {row['character']}", value=row['example'], key=f"example_{idx}")
                if st.button(f"Save {row['character']}", key=f"save_{idx}"):
                    df.at[idx, "pinyin"] = new_pinyin
                    df.at[idx, "example"] = new_example
                    save_data(df)
                    st.success(f"{row['character']} updated")

                if st.checkbox(f"⚠️ Confirm delete {row['character']}", key=f"confirm_delete_{idx}"):
                    if st.button(f"Delete {row['character']}", key=f"delete_{idx}"):
                        df = df.drop(idx)
                        save_data(df)
                        st.success(f"{row['character']} deleted")
                        st.experimental_rerun()

        # Add new character to existing set
        st.subheader("➕ Add Character to This Set")
        with st.form("add_to_existing_set_form"):
            add_char = st.text_input("Character")
            add_pinyin = st.text_input("Pinyin")
            add_example = st.text_input("Example sentence")
            submit_add = st.form_submit_button("Add Character")
            if submit_add:
                if add_char:
                    df = df.append({
                        "set_nr": set_to_edit,
                        "character": add_char,
                        "pinyin": add_pinyin,
                        "example": add_example,
                        "learned_date": new_set_date,
                        "correct": 0,
                        "wrong": 0
                    }, ignore_index=True)
                    save_data(df)
                    st.success(f"Character '{add_char}' added to set {set_to_edit}!")
                    st.experimental_rerun()
                else:
                    st.error("Please enter a character.")

    elif action == "Delete Set":
        st.header("❌ Delete Entire Set")
        set_options = sorted(df["set_nr"].unique())
        set_to_delete = st.selectbox("Select Set to Delete:", set_options)
        if st.checkbox("⚠️ I confirm I want to delete this set"):
            if st.button("Confirm Delete Set"):
                df = df[df["set_nr"] != set_to_delete]
                save_data(df)
                st.success(f"Set {set_to_delete} has been deleted.")
                st.experimental_rerun()

elif menu == "Flashcard":
    st.header(f"🎴 Today's Review ({TODAY.strftime('%Y-%m-%d')})")
    due_df = get_due_characters(df)

    if due_df.empty:
        st.success("No reviews due today! 🎉")
    else:
        for idx, row in due_df.iterrows():
            with st.container():
                st.markdown("---")
                st.markdown(
                    f"""
                    <div class='hanzi-card' style='
                        text-align: center;
                        font-size: 96px;
                        padding: 40px 20px;
                        border: 2px solid #ccc;
                        border-radius: 16px;
                        box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                        margin-bottom: 20px;
                        background-color: #f9f9f9;
                        color: black;
                        font-weight: bold;'>
                        {row["character"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(
                    f"""
                    <details>
                    <summary style='font-size:18px;'>👀 Show Hint</summary>
                    <ul style='font-size:16px;'>
                        <li><strong>Pinyin:</strong> {row['pinyin']}</li>
                        <li><strong>Example:</strong> {row['example']}</li>
                    </ul>
                    </details>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown(f"Right: {row['correct']} | Wrong: {row['wrong']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Right", key=f"correct_{idx}_{row['character']}"):
                        #df.at[idx, "correct"] = 0  # Reset correct value to 0
                        df.at[idx, "correct"] += 1
                        save_data(df)
                        st.session_state.updated = True
                        st.success(f"Marked {row['character']} as correct.")
                
                with col2:
                    if st.button("❌ Wrong", key=f"wrong_{idx}_{row['character']}"):
                        #df.at[idx, "wrong"] = 0  # Reset correct value to 0
                        df.at[idx, "wrong"] += 1
                        save_data(df)
                        st.session_state.updated = True
                        st.success(f"Marked {row['character']} as wrong.")

        if 'updated' in st.session_state and st.session_state.updated:
            st.session_state.updated = False  # Reset the update flag
            st.experimental_rerun()  # Force a rerun using session_state




elif menu == "Dashboard":
    st.header("📊 Dashboard")

    st.subheader("📅 Review Plan")
    set_options = sorted(df["set_nr"].unique())
    selected_set = st.selectbox("Filter by Set Number:", options=set_options)
    filtered_df = df[df["set_nr"] == selected_set]
    review_table = build_review_table(filtered_df)

    st.dataframe(review_table)

    st.subheader("📉 Frequently Wrong Characters")
    wrong_df = df[df["wrong"] >= 2]
    for i, row in wrong_df.iterrows():
      st.markdown(f"- {row['character']} (Wrong: {row['wrong']})")


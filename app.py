import streamlit as st
import sqlite3
import pandas as pd

# --- CONFIGURATION ---
FAMILY_MEMBERS = ["Dillon", "Rache", "Melissa", "Rowen", "Jace"]
CATEGORIES = ["Recipe", "Movie", "Restaurant", "House"]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('family_app.db')
    c = conn.cursor()
    # Create Items Table
    c.execute('''CREATE TABLE IF NOT EXISTS items
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT,
                  added_by TEXT, notes TEXT, status TEXT DEFAULT 'Pending')''')
    # Create Votes Table
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (item_id INTEGER, user TEXT, score INTEGER, tags TEXT)''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("family_app.db")

# --- APP LOGIC ---
def main():
    st.set_page_config(page_title="Kin - Family Consensus", page_icon="🏠")
    init_db()

    # SIDEBAR: Simulate User Switching
    st.sidebar.title("👨‍👩‍👧‍👦 Who is logged in?")
    current_user = st.sidebar.selectbox("Select User", FAMILY_MEMBERS)
    st.sidebar.divider()
    st.sidebar.write(f"Logged in as: **{current_user}**")

    st.title("🏠 Kin: Family Operating System")

    # TABS
    tab1, tab2, tab3 = st.tabs(["📝 Rate & Vote", "📊 Family Dashboard", "➕ Add New"])

    # --- TAB 3: ADD NEW ITEM ---
    with tab3:
        st.header("Add Something to the Ledger")
        with st.form("new_item_form"):
            new_name = st.text_input("Name (e.g., 'Dune 2' or 'Spicy Thai Basil')")
            new_cat = st.selectbox("Category", CATEGORIES)
            new_notes = st.text_area("Initial Notes / Link")
            submitted = st.form_submit_button("Add to Queue")

            if submitted and new_name:
                conn = get_db_connection()
                conn.execute("INSERT INTO items (name, category, added_by, notes) VALUES (?, ?, ?, ?)",
                             (new_name, new_cat, current_user, new_notes))
                conn.commit()
                conn.close()
                st.success(f"Added {new_name}!")
                st.rerun()

    # --- TAB 1: VOTING (THE CORE MECHANIC) ---
    with tab1:
        st.header("Pending Your Review")

        conn = get_db_connection()
        # Get items that exist but haven't been voted on by THIS user yet
        # (This is a simplified SQL logic for the prototype)
        query = f"""
            SELECT * FROM items
            WHERE id NOT IN (SELECT item_id FROM votes WHERE user = '{current_user}')
        """
        pending_items = pd.read_sql(query, conn)

        if pending_items.empty:
            st.info("You're all caught up! No pending votes.")
        else:
            for index, row in pending_items.iterrows():
                with st.container(border=True):
                    st.subheader(f"{row['category']}: {row['name']}")   
                    st.caption(f"Added by {row['added_by']} | Notes: {row['notes']}")

                    with st.form(f"vote_{row['id']}"):
                        score = st.slider("Your Score", 1, 10, 5)
                        tags = st.text_input("One-word Tag (e.g., Spicy, Boring)")
                        submit_vote = st.form_submit_button("Submit Blind Vote")

                        if submit_vote:
                            c = conn.cursor()
                            c.execute("INSERT INTO votes VALUES (?, ?, ?, ?)",
                                       (row['id'], current_user, score, tags))
                            conn.commit()
                            st.success("Vote Cast!")
                            st.rerun()

        conn.close()

    # --- TAB 2: DASHBOARD ---
    with tab2:
        st.header("The Family Ledger")
        conn = get_db_connection()

        # Pull all items
        items_df = pd.read_sql("SELECT * FROM items", conn)
        votes_df = pd.read_sql("SELECT * FROM votes", conn)

        if not items_df.empty:
            for index, item in items_df.iterrows():
                # Get votes for this item
                item_votes = votes_df[votes_df['item_id'] == item['id']]
                
                # LOGIC: Only show score if everyone has voted
                if not item_votes.empty:
                    avg_score = item_votes['score'].mean()
                    voter_count = len(item_votes)

                    # Determine Status
                    status_color = "grey"
                    if avg_score >= 8: status_color = "green"
                    elif avg_score <= 4: status_color = "red"
                    else: status_color = "orange"

                    with st.expander(f"⭐ {avg_score:.1f}/10 - {item['name']} ({item['category']})"):
                        st.metric(label="Family Score", value=f"{avg_score:.1f}")
                        
                        # Show individual breakdowns
                        st.write("Who voted what:")
                        st.dataframe(item_votes[['user', 'score', 'tags']], hide_index=True)

                        # Fun logic: Conflict detection
                        if item_votes['score'].max() - item_votes['score'].min() > 3:
                            st.warning("⚠️ Contested Result! High disagreement.")

                        delete_item = st.form_submit_button("Delete Item")

                        if delete_item:
                            c = conn.cursor()
                            c.execute("DELETE FROM items WHERE id = ?", (item['id']))
                            conn.commit()
                            st.success("Item Deleted!")
                            st.rerun()
                else:
                    st.write("No data yet.")

                conn.close()

if __name__ == "__main__":
    main()
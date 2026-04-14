import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# =========================
# 🔌 DB CONNECTION
# =========================
conn = sqlite3.connect("church.db", check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

# =========================
# 🏗️ INIT DATABASE
# =========================
def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        birthday DATE,
        age INTEGER,
        status TEXT,
        role TEXT,
        cell_leader TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        topic TEXT,
        status TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_progress_unique
    ON progress(member_id, topic)
    """)

    cursor.execute("PRAGMA foreign_keys = ON")


# Add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE members ADD COLUMN contact TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE members ADD COLUMN address TEXT")
    except:
        pass

    try:
        cursor.execute("ALTER TABLE members ADD COLUMN facebook TEXT")
    except:
        pass

    


    conn.commit()


init_db()

# =========================
# 📥 LOAD DATA
# =========================
def load_members():
    return pd.read_sql("SELECT * FROM members", conn)

def load_progress():
    return pd.read_sql("""
        SELECT p.id, m.full_name, p.member_id, p.topic, p.status
        FROM progress p
        JOIN members m ON m.id = p.member_id
    """, conn)

# =========================
# 🖥️ UI SETUP
# =========================
st.set_page_config(page_title="Church Tracker", layout="wide")
st.title("🛡️ Church Discipleship System (SQLite)")

tabs = st.tabs(["📊 Overview", "👥 Members", "📖 Progress", "👑 Leaders", "Attendance"])

# =========================
# TAB 1 - MEMBERS
# =========================
with tabs[1]:
    members_df = load_members()

    st.subheader("👥 Members")

    st.dataframe(
        members_df,
        use_container_width=True,
        hide_index=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Add Member"):
            st.session_state.show_add = True

    with col2:
        selected = st.selectbox(
            "Select Member to Edit",
            members_df["full_name"].tolist()
        )

        if st.button("✏️ Edit Member"):
            st.session_state.edit_member = selected
    
    with col3:

        members = pd.read_sql("SELECT id, full_name FROM members", conn)
        member_map = dict(zip(members["full_name"], members["id"]))

        selected_delete = st.selectbox("Select member to delete", list(member_map.keys()))
        confirm = st.checkbox("⚠️ Confirm deletion")

        if st.button("🗑️ Delete Member"):
            if confirm:
                member_id = member_map[selected_delete]

                cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
                conn.commit()

                st.success(f"✅ Deleted {selected_delete}")
                st.rerun()
            else:
                st.warning("Please confirm deletion first.")

    # -------------------------
    # ADD MEMBER
    # -------------------------

    if "show_add" not in st.session_state:
        st.session_state.show_add = False

    if "edit_member" not in st.session_state:
        st.session_state.edit_member = None

    if st.session_state.show_add:
        st.markdown("## ➕ Add Member")

        with st.container():
            name = st.text_input("Full Name")
            birthday = st.date_input("Birthday", value=date(2000, 1, 1))
            contact = st.text_input("Contact Number")
            address = st.text_input("Address")
            facebook = st.text_input("Facebook")

            status = st.selectbox("Status", ["Active", "Inactive"])
            role = st.selectbox("Role", ["Member", "Leader"])

            leaders_df = pd.read_sql("SELECT full_name FROM members WHERE role='Leader'", conn)
            leader_list = leaders_df["full_name"].tolist() if not leaders_df.empty else []

            cell_leader = st.selectbox("Cell Leader", ["None"] + leader_list)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Save Member"):
                    age = date.today().year - birthday.year

                    cursor.execute("""
                        INSERT INTO members (
                            full_name, birthday, age, status, role, cell_leader,
                            contact, address, facebook
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        name, birthday, age, status, role, cell_leader,
                        contact, address, facebook
                    ))

                    conn.commit()
                    st.success("✅ Member Added!")
                    st.session_state.show_add = False
                    st.rerun()

            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_add = False
                    st.rerun()

    
    if st.session_state.edit_member:

        # =========================
        # 🔥 GET MEMBER LIST (SAFE)
        # =========================
        members = pd.read_sql("SELECT id, full_name FROM members", conn)

        selected_id = members[
            members["full_name"] == st.session_state.edit_member
        ]["id"].values[0]

        # =========================
        # 🔥 LOAD FRESH DATA FROM DB (NOT CACHE)
        # =========================
        member = pd.read_sql(
            "SELECT * FROM members WHERE id = ?",
            conn,
            params=(int(selected_id),)
        ).iloc[0]

        # =========================
        # 🔥 LEADERS LIST
        # =========================
        leaders_df = pd.read_sql(
            "SELECT full_name FROM members WHERE role='Leader'",
            conn
        )
        leader_list = leaders_df["full_name"].tolist()

        # =========================
        # UI
        # =========================
        st.markdown(f"## ✏️ Edit: {member['full_name']}")

        name = st.text_input("Full Name", value=member["full_name"])
        birthday = st.date_input("Birthday", value=pd.to_datetime(member["birthday"]))

        contact = st.text_input("Contact", value=member["contact"] if "contact" in member else "")
        address = st.text_input("Address", value=member["address"] if "address" in member else "")
        facebook = st.text_input("Facebook", value=member["facebook"] if "facebook" in member else "")

        status = st.selectbox(
            "Status",
            ["Active", "Inactive"],
            index=0 if member["status"] == "Active" else 1
        )

        role = st.selectbox(
            "Role",
            ["Member", "Leader"],
            index=0 if member["role"] == "Member" else 1
        )

        cell_leader = st.selectbox(
            "Cell Leader",
            ["None"] + leader_list,
            index=0
        )

        # =========================
        # BUTTONS
        # =========================
        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Update Member"):

                # =========================
                # 🔥 DEBUG CHECK (IMPORTANT)
                # =========================
                st.write("DEBUG ID:", int(selected_id))

                cursor.execute("""
                    UPDATE members
                    SET full_name = ?,
                        birthday = ?,
                        contact = ?,
                        address = ?,
                        facebook = ?,
                        status = ?,
                        role = ?,
                        cell_leader = ?
                    WHERE id = ?
                """, (
                    name,
                    birthday,
                    contact,
                    address,
                    facebook,
                    status,
                    role,
                    cell_leader,
                    int(selected_id)
                ))

                conn.commit()

                st.write("Rows affected:", cursor.rowcount)

                st.success("✅ Updated Successfully")

                st.session_state.edit_member = None
                st.rerun()

        with col2:
            if st.button("❌ Close"):
                st.session_state.edit_member = None
                st.rerun()
    

# =========================
# TAB 2 - PROGRESS (GRID VIEW)
# =========================


with tabs[2]:
    st.subheader("📖 Discipleship Progress Tracker")

    # =========================
    # ONLY 2 OPTIONS
    # =========================
    status_options = ["🔴Not Done", "🟢Done"]

    # =========================
    # ABSOLUTE SAFE LOAD
    # =========================
    members = pd.read_sql("SELECT id, full_name FROM members", conn)
    progress = pd.read_sql("SELECT member_id, topic, status FROM progress", conn)

    # =========================
    # TOPIC STRUCTURE
    # =========================
    TOPICS = {
        "Life Start (5)": ["LS1", "LS2", "LS3", "LS4", "LS5"],
        "14 Foundational (14)": [
            "F1","F2","F3","F4","F5","F6","F7",
            "F8","F9","F10","F11","F12","F13","F14"
        ],
        "Buhay Nga Naman (12)": [
            "BN1","BN2","BN3","BN4","BN5","BN6",
            "BN7","BN8","BN9","BN10","BN11","BN12"
        ],
        "Tara Na (12)": [
            "TN1","TN2","TN3","TN4","TN5","TN6",
            "TN7","TN8","TN9","TN10","TN11","TN12"
        ]
    }

    # =========================
    # STORE ALL UPDATES
    # =========================
    all_updates = []

    # =========================
    # BUILD GRID PER GROUP
    # =========================
    for group_name, topics in TOPICS.items():

        st.markdown(f"### 📘 {group_name}")

        grid_rows = []

        for _, m in members.iterrows():

            row = {
                "Member": m["full_name"],
                "member_id": int(m["id"])
            }

            member_prog = progress[progress["member_id"] == m["id"]]

            for topic in topics:
                match = member_prog[member_prog["topic"] == topic]

                if not match.empty:
                    row[topic] = match.iloc[0]["status"]
                else:
                    row[topic] = "Not Done"
                
                #row[topic] = color_status(row[topic])

            grid_rows.append(row)

        df = pd.DataFrame(grid_rows)

        # =========================
        # EDITABLE TABLE
        # =========================
        edited = st.data_editor(
            df.drop(columns=["member_id"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                col: st.column_config.SelectboxColumn(
                    col,
                    options=status_options
                )
                for col in df.columns
                if col not in ["Member", "member_id"]
            },
            key=group_name
        )

        # =========================
        # COLLECT UPDATES
        # =========================
        for i, row in edited.iterrows():

            member_id = int(df.iloc[i]["member_id"])

            for topic in topics:

                all_updates.append({
                    "member_id": member_id,
                    "topic": topic,
                    "status": row[topic]
                })

    # =========================
    # SAVE ALL TO DATABASE
    # =========================
    if st.button("💾 Save Progress"):

        try:
            cursor.execute("PRAGMA foreign_keys = ON")

            for u in all_updates:

                cursor.execute("""
                    INSERT INTO progress (member_id, topic, status)
                    VALUES (?, ?, ?)
                    ON CONFLICT(member_id, topic)
                    DO UPDATE SET status = excluded.status
                """, (
                    int(u["member_id"]),
                    u["topic"],
                    u["status"]
                ))

            conn.commit()

            st.success("✅ Progress saved successfully!")

        except Exception as e:
            st.error(f"Error: {e}")

# =========================
# TAB 3 - LEADERS
# =========================




with tabs[3]:
    st.subheader("👑 Leader Analytics Dashboard")

    # =========================
    # LOAD DATA
    # =========================
    members = pd.read_sql("SELECT id, full_name, cell_leader FROM members", conn)
    progress = pd.read_sql("SELECT member_id, topic, status FROM progress", conn)

    # =========================
    # CATEGORY MAP
    # =========================
    CATEGORY_MAP = {
        "Life Start": ["LS1","LS2","LS3","LS4","LS5"],
        "14 Foundational": [
            "F1","F2","F3","F4","F5","F6","F7",
            "F8","F9","F10","F11","F12","F13","F14"
        ],
        "Buhay Nga Naman": [
            "BN1","BN2","BN3","BN4","BN5","BN6",
            "BN7","BN8","BN9","BN10","BN11","BN12"
        ],
        "Tara Na": [
            "TN1","TN2","TN3","TN4","TN5","TN6",
            "TN7","TN8","TN9","TN10","TN11","TN12"
        ]
    }

    # =========================
    # FILTER LEADERS
    # =========================
    leaders = members[members["cell_leader"].notna()]["cell_leader"].unique()

    leader_summary = []

    for leader in leaders:

        leader_members = members[members["cell_leader"] == leader]

        if leader_members.empty:
            continue

        member_scores = []

        # =========================
        # CALCULATE EACH MEMBER
        # =========================
        for _, m in leader_members.iterrows():

            member_id = m["id"]
            member_progress = progress[progress["member_id"] == member_id]

            total_topics = len(progress["topic"].unique())
            done_topics = len(member_progress[member_progress["status"] == "🟢Done"])

            overall_percent = 0
            if total_topics > 0:
                overall_percent = (done_topics / total_topics) * 100

            member_scores.append(overall_percent)

        # =========================
        # LEADER AVERAGE
        # =========================
        avg_progress = sum(member_scores) / len(member_scores) if member_scores else 0

        leader_summary.append({
            "Leader": leader,
            "Members": len(leader_members),
            "Average Progress": round(avg_progress, 2)
        })

    # =========================
    # LEADER OVERVIEW TABLE
    # =========================
    st.markdown("## 📊 Leader Overview")

    leader_df = pd.DataFrame(leader_summary).sort_values(
        by="Average Progress",
        ascending=False
    )

    st.dataframe(leader_df, use_container_width=True, hide_index=True)

    st.divider()

    # =========================
    # DETAILED LEADER VIEW
    # =========================
    for leader in leaders:

        with st.expander(f"⭐ Leader: {leader}"):

            leader_members = members[members["cell_leader"] == leader]

            if leader_members.empty:
                st.write("No members")
                continue

            for _, m in leader_members.iterrows():

                member_id = m["id"]
                member_name = m["full_name"]

                member_progress = progress[progress["member_id"] == member_id]

                st.markdown(f"### 👤 {member_name}")

                # =========================
                # CATEGORY ANALYTICS
                # =========================
                for category, topics in CATEGORY_MAP.items():

                    done_count = 0

                    for t in topics:
                        match = member_progress[member_progress["topic"] == t]

                        if not match.empty and match.iloc[0]["status"] == "Done":
                            done_count += 1

                    percent = int((done_count / len(topics)) * 100)

                    st.write(f"**{category}:** {percent}% ({done_count}/{len(topics)})")
                    st.progress(percent / 100)

                st.divider()


with tabs[0]:
    st.subheader("📊 Church Command Dashboard")

    # =========================
    # LOAD DATA
    # =========================
    members = pd.read_sql("SELECT id, full_name, status, cell_leader FROM members", conn)
    progress = pd.read_sql("SELECT member_id, topic, status FROM progress", conn)

    all_topics = progress["topic"].unique().tolist()

    # =========================
    # BASIC STATS
    # =========================
    total_members = len(members)
    active_members = len(members[members["status"] == "Active"])
    inactive_members = total_members - active_members

    done_count = len(progress[progress["status"] == "Done"])
    total_progress = len(progress)

    overall_rate = round((done_count / total_progress) * 100, 2) if total_progress else 0

    # =========================
    # TOP METRICS
    # =========================
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Total Members", total_members)

    with col2:
        st.metric("🟢 Active", active_members)

    with col3:
        st.metric("🔴 Inactive", inactive_members)

    with col4:
        st.metric("📊 Overall Progress", f"{overall_rate}%")

    st.divider()

    # =========================
    # ⚠️ ACTION CENTER
    # =========================
    st.markdown("## ⚠️ Action Center (Needs Attention)")

    action_list = []

    for _, m in members.iterrows():

        member_progress = progress[progress["member_id"] == m["id"]]

        done = len(member_progress[member_progress["status"] == "Done"])

        percent = 0
        if len(all_topics) > 0:
            percent = (done / len(all_topics)) * 100

        # inactive or low progress
        if percent == 0:
            action_list.append((m["full_name"], "❌ No Progress"))
        elif percent < 30:
            action_list.append((m["full_name"], "⚠️ Low Progress"))
        elif m["status"] != "Active":
            action_list.append((m["full_name"], "🔴 Inactive"))

    if action_list:
        for name, reason in action_list:
            st.write(f"- {reason} → {name}")
    else:
        st.success("🎉 No urgent actions needed!")

    st.divider()

    # =========================
    # 📊 CATEGORY HEALTH
    # =========================
    st.markdown("## 📊 Category Health")

    CATEGORY_MAP = {
        "Life Start": ["LS1","LS2","LS3","LS4","LS5"],
        "14 Foundational": [
            "F1","F2","F3","F4","F5","F6","F7",
            "F8","F9","F10","F11","F12","F13","F14"
        ],
        "Buhay Nga Naman": [
            "BN1","BN2","BN3","BN4","BN5","BN6",
            "BN7","BN8","BN9","BN10","BN11","BN12"
        ],
        "Tara Na": [
            "TN1","TN2","TN3","TN4","TN5","TN6",
            "TN7","TN8","TN9","TN10","TN11","TN12"
        ]
    }

    for category, topics in CATEGORY_MAP.items():

        total = 0
        done = 0

        for t in topics:
            cat_prog = progress[progress["topic"] == t]

            total += len(cat_prog)
            done += len(cat_prog[cat_prog["status"] == "🟢Done"])

        percent = round((done / total) * 100, 2) if total else 0

        st.write(f"**{category}:** {percent}%")
        st.progress(percent / 100)

    st.divider()

    # =========================
    # 🏆 TOP & BOTTOM MEMBERS
    # =========================
    
    st.markdown("## 🏆 Member Performance (Progress + Attendance)")

    attendance = pd.read_sql("SELECT * FROM attendance", conn)

    ranking = []

    for _, m in members.iterrows():

        member_id = m["id"]

        # =========================
        # PROGRESS SCORE
        # =========================
        member_progress = progress[progress["member_id"] == member_id]

        done = len(member_progress[member_progress["status"] == "🟢Done"])
        total_topics = len(progress["topic"].unique())

        progress_score = (done / total_topics) * 100 if total_topics else 0

        # =========================
        # ATTENDANCE SCORE
        # =========================
        member_att = attendance[attendance["member_id"] == member_id]

        total_meetings = len(member_att)

        present = len(member_att[member_att["status"] == "Present"])

        attendance_score = (present / total_meetings) * 100 if total_meetings else 0

        # =========================
        # COMBINED SCORE (WEIGHTED)
        # =========================
        combined_score = (progress_score * 0.6) + (attendance_score * 0.4)

        ranking.append({
            "Member": m["full_name"],
            "Progress %": round(progress_score, 2),
            "Attendance %": round(attendance_score, 2),
            "Overall Score": round(combined_score, 2)
        })

    ranking_df = pd.DataFrame(ranking).sort_values(by="Overall Score", ascending=False)

    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
    st.divider()

    # =========================
    # 👑 LEADER SNAPSHOT
    # =========================
    st.markdown("## 👑 Leader Snapshot")

    leader_summary = []

    for leader in members["cell_leader"].dropna().unique():

        leader_members = members[members["cell_leader"] == leader]

        if leader_members.empty:
            continue

        scores = []

        for _, m in leader_members.iterrows():

            member_progress = progress[progress["member_id"] == m["id"]]

            done = len(member_progress[member_progress["status"] == "Done"])
            percent = round((done / len(all_topics)) * 100, 2) if all_topics else 0

            scores.append(percent)

        avg = round(sum(scores) / len(scores), 2) if scores else 0

        leader_summary.append({
            "Leader": leader,
            "Members": len(leader_members),
            "Avg Progress": avg
        })

    leader_df = pd.DataFrame(leader_summary).sort_values(by="Avg Progress", ascending=False)

    st.dataframe(leader_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## 🎂 Upcoming Birthdays")

    from datetime import datetime, timedelta

    members = pd.read_sql("SELECT full_name, birthday FROM members", conn)

    today = datetime.today().date()
    next_30_days = today + timedelta(days=30)

    birthday_list = []

    for _, m in members.iterrows():

        try:
            bday = pd.to_datetime(m["birthday"]).date()

            # set year to current year
            this_year_bday = bday.replace(year=today.year)

            # handle year rollover (Dec → Jan case)
            if this_year_bday < today:
                this_year_bday = bday.replace(year=today.year + 1)

            days_left = (this_year_bday - today).days

            if 0 <= days_left <= 30:

                birthday_list.append({
                    "Name": m["full_name"],
                    "Birthday": this_year_bday.strftime("%Y-%m-%d"),
                    "Days Left": days_left
                })

        except:
            pass

    if birthday_list:
        birthday_df = pd.DataFrame(birthday_list).sort_values(by="Days Left")

        st.dataframe(birthday_df, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 No upcoming birthdays in the next 30 days!")



with tabs[4]:
    st.subheader("📅 Cell Group Attendance")

    members = pd.read_sql("SELECT id, full_name, cell_leader FROM members", conn)
    attendance = pd.read_sql("SELECT * FROM attendance", conn)

    status_options = ["Present", "Absent"]

    # =========================
    # SELECT GROUP + DATE
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        selected_date = st.date_input("📆 Meeting Date")

    with col2:
        groups = members["cell_leader"].dropna().unique().tolist()
        selected_group = st.selectbox("👥 Cell Group", groups)

    group_members = members[members["cell_leader"] == selected_group]

    st.divider()

    # =========================
    # ATTENDANCE INPUT
    # =========================
    attendance_inputs = []

    st.markdown("### Mark Attendance")

    for _, m in group_members.iterrows():

        status = st.selectbox(
            m["full_name"],
            status_options,
            key=f"att_{m['id']}_{selected_date}"
        )

        attendance_inputs.append({
            "member_id": m["id"],
            "status": status
        })

    # =========================
    # SAVE
    # =========================
    if st.button("💾 Save Attendance"):

        try:
            for a in attendance_inputs:

                cursor.execute("""
                    INSERT INTO attendance (member_id, date, status, cell_group)
                    VALUES (?, ?, ?, ?)
                """, (
                    int(a["member_id"]),
                    str(selected_date),
                    a["status"],
                    selected_group
                ))

            conn.commit()
            st.success("✅ Attendance saved!")

        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # =========================
    # 📊 WEEKLY ATTENDANCE CHART
    # =========================
    
    import plotly.graph_objects as go

    st.markdown("### 📊 Weekly Attendance Overview (Stable Scale)")

    if not attendance.empty:

        attendance["date"] = pd.to_datetime(attendance["date"])
        attendance["week"] = attendance["date"].dt.to_period("W").astype(str)

        filtered = attendance[attendance["cell_group"] == selected_group]

        summary = filtered.groupby(["week", "status"]).size().unstack(fill_value=0)

        # ensure columns exist
        if "Present" not in summary.columns:
            summary["Present"] = 0
        if "Absent" not in summary.columns:
            summary["Absent"] = 0

        summary = summary.sort_index()

        max_members = len(group_members)

        # =========================
        # PLOTLY GRAPH (CONTROLLED AXIS)
        # =========================
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=summary.index,
            y=summary["Present"],
            name="Present",
            marker_color="green"
        ))

        fig.add_trace(go.Bar(
            x=summary.index,
            y=summary["Absent"],
            name="Absent",
            marker_color="red"
        ))

        # 🔒 FIXED Y-AXIS
        fig.update_layout(
            barmode="stack",
            yaxis=dict(
                range=[0, max_members],  # 👈 THIS LOCKS SCALE
                title="Number of Members"
            ),
            xaxis_title="Week",
            title="Attendance Overview (Fixed Scale)",
            legend_title="Status"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No attendance records yet.")

    st.divider()

    group_attendance = attendance[attendance["cell_group"] == selected_group]

    if group_attendance.empty:
        st.info("No attendance records yet.")
    else:

        available_dates = sorted(group_attendance["date"].unique(), reverse=True)

        # =========================
        # DATE SELECTOR
        # =========================
        selected_date = st.selectbox("📆 Select Meeting Date", available_dates)

        st.divider()

        # =========================
        # FILTER SELECTED DATE
        # =========================
        day_data = group_attendance[group_attendance["date"] == selected_date]

        present = day_data[day_data["status"] == "Present"]
        absent = day_data[day_data["status"] == "Absent"]

        # =========================
        # SUMMARY
        # =========================
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("🟢 Present", len(present))

        with col2:
            st.metric("🔴 Absent", len(absent))

        with col3:
            st.metric("👥 Total", len(group_members))

        st.divider()

        # =========================
        # PRESENT LIST
        # =========================
        st.markdown("## 🟢 Present Members")

        if not present.empty:
            present_names = members[members["id"].isin(present["member_id"])]

            for name in present_names["full_name"]:
                st.write(f"✔ {name}")
        else:
            st.write("No present members")

        st.divider()

        # =========================
        # ABSENT LIST
        # =========================
        st.markdown("## 🔴 Absent Members")

        if not absent.empty:
            absent_names = members[members["id"].isin(absent["member_id"])]

            for name in absent_names["full_name"]:
                st.write(f"❌ {name}")
        else:
            st.write("No absent members")
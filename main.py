import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client
import streamlit as st

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

# =========================
# 🔌 DB CONNECTION
# =========================

@st.cache_data(ttl=30)
def load_members():
    res = supabase.table("members").select("*").execute()
    return pd.DataFrame(res.data or [])

@st.cache_data(ttl=10)
def load_progress():
    return pd.DataFrame(supabase.table("progress").select("*").execute().data)

@st.cache_data(ttl=10)
def load_attendance():
    return pd.DataFrame(supabase.table("attendance").select("*").execute().data)


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
    st.subheader("👥 Members")

    members_df = load_members()

    if members_df.empty:
        st.warning("No members yet.")
        st.stop()

    # =========================
    # 🔗 MAP FOR LEADERS
    # =========================
    leader_map = dict(zip(members_df["id"], members_df["full_name"]))

    members_df["cell_leader_name"] = members_df["cell_leader_id"].map(leader_map)

    st.dataframe(
        members_df.drop(columns=["cell_leader_id"]),
        use_container_width=True,
        hide_index=True
    )

    col1, col2, col3 = st.columns(3)

    # =========================
    # ➕ ADD
    # =========================
    with col1:
        if st.button("➕ Add Member"):
            st.session_state.show_add = True

    # =========================
    # ✏️ EDIT
    # =========================
    with col2:
        selected = st.selectbox(
            "Select Member",
            members_df["full_name"]
        )

        if st.button("✏️ Edit"):
            st.session_state.edit_member = selected

    # =========================
    # 🗑️ DELETE
    # =========================
    with col3:
        selected_delete = st.selectbox(
            "Delete Member",
            members_df["full_name"]
        )

        confirm = st.checkbox("Confirm delete")

        if st.button("🗑️ Delete"):
            if confirm:
                member_id = members_df[
                    members_df["full_name"] == selected_delete
                ]["id"].values[0]

                supabase.table("members").delete().eq("id", int(member_id)).execute()

                st.success("Deleted!")
                st.rerun()

    # =========================
    # ➕ ADD FORM
    # =========================
    if st.session_state.get("show_add", False):

        st.markdown("## ➕ Add Member")

        name = st.text_input("Full Name")
        birthday = st.date_input("Birthday",value = date(2000, 1, 1),min_value=date(1900, 1, 1), max_value=date.today())

        status = st.selectbox("Status", ["Active", "Inactive"])
        role = st.selectbox("Role", ["Member", "Leader"])

        leaders = members_df[members_df["role"] == "Leader"]

        leader_name = st.selectbox(
            "Cell Leader",
            ["None"] + leaders["full_name"].tolist()
        )

        leader_id = None
        if leader_name != "None":
            leader_id = leaders[
                leaders["full_name"] == leader_name
            ]["id"].values[0]

        if st.button("💾 Save"):

            supabase.table("members").insert({
                "full_name": name,
                "birthday": str(birthday),
                "status": status,
                "role": role,
                "cell_leader_id": int(leader_id) if leader_id else None
            }).execute()

            st.success("Added!")
            st.session_state.show_add = False
            st.cache_data.clear()
            st.rerun()

    # =========================
    # ✏️ EDIT FORM
    # =========================
    if st.session_state.get("edit_member"):

        selected_name = st.session_state.edit_member

        row = members_df[members_df["full_name"] == selected_name].iloc[0]

        st.markdown(f"## ✏️ Edit: {selected_name}")

        name = st.text_input("Full Name", row["full_name"])
        birthday = st.date_input("Birthday", pd.to_datetime(row["birthday"]))

        status = st.selectbox(
            "Status",
            ["Active", "Inactive"],
            index=0 if row["status"] == "Active" else 1
        )

        role = st.selectbox(
            "Role",
            ["Member", "Leader"],
            index=0 if row["role"] == "Member" else 1
        )

        leaders = members_df[members_df["role"] == "Leader"]

        leader_name = st.selectbox(
            "Cell Leader",
            ["None"] + leaders["full_name"].tolist()
        )

        leader_id = None
        if leader_name != "None":
            leader_id = leaders[
                leaders["full_name"] == leader_name
            ]["id"].values[0]

        if st.button("💾 Update"):

            supabase.table("members").update({
                "full_name": name,
                "birthday": str(birthday),
                "status": status,
                "role": role,
                "cell_leader_id": int(leader_id) if leader_id else None
            }).eq("id", int(row["id"])).execute()

            st.success("Updated!")
            st.session_state.edit_member = None
            st.rerun()

        if st.button("❌ Cancel"):
            st.session_state.edit_member = None
            st.rerun()    

# =========================
# TAB 2 - PROGRESS (GRID VIEW)
# =========================

with tabs[2]:
    st.subheader("📖 Discipleship Progress Tracker")

    status_options = ["🔴Not Done", "🟢Done"]

    # =========================
    # ⚡ LOAD (CACHED)
    # =========================
    @st.cache_data(ttl=30)
    def load_data():
        members = supabase.table("members").select("id, full_name").execute().data
        progress = supabase.table("progress").select("*").execute().data
        return pd.DataFrame(members or []), pd.DataFrame(progress or [])

    members, progress = load_data()

    if members.empty:
        st.warning("No members found")
        st.stop()

    if progress.empty:
        progress = pd.DataFrame(columns=["member_id", "topic", "status"])

    # =========================
    # ⚡ PREPROCESS (FAST LOOKUP)
    # =========================
    progress_dict = {
        (row["member_id"], row["topic"]): row["status"]
        for _, row in progress.iterrows()
    }

    # =========================
    # TOPICS
    # =========================
    TOPICS = {
        "Life Start (5)": ["LS1","LS2","LS3","LS4","LS5"],
        "14 Foundational (14)": ["F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12","F13","F14"],
        "Buhay Nga Naman (12)": ["BN1","BN2","BN3","BN4","BN5","BN6","BN7","BN8","BN9","BN10","BN11","BN12"],
        "Tara Na (12)": ["TN1","TN2","TN3","TN4","TN5","TN6","TN7","TN8","TN9","TN10","TN11","TN12"]
    }

    all_updates = []

    # =========================
    # ⚡ BUILD GRID (FAST)
    # =========================
    for group_name, topics in TOPICS.items():

        st.markdown(f"### 📘 {group_name}")

        rows = []

        for _, m in members.iterrows():

            row = {
                "Member": m["full_name"],
                "member_id": m["id"]
            }

            for topic in topics:
                row[topic] = progress_dict.get(
                    (m["id"], topic),
                    "🔴Not Done"
                )

            rows.append(row)

        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df.drop(columns=["member_id"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                col: st.column_config.SelectboxColumn(
                    col,
                    options=status_options
                )
                for col in df.columns if col not in ["Member", "member_id"]
            },
            key=group_name
        )

        # =========================
        # ⚡ COLLECT CHANGES ONLY
        # =========================
        for i, row in edited.iterrows():
            member_id = df.iloc[i]["member_id"]

            for topic in topics:
                new_val = row[topic]
                old_val = df.iloc[i][topic]

                if new_val != old_val:  # 🔥 ONLY CHANGED
                    all_updates.append({
                        "member_id": int(member_id),
                        "topic": topic,
                        "status": new_val
                    })

    # =========================
    # ⚡ SAVE (BULK UPSERT)
    # =========================
    if st.button("💾 Save Progress"):

        if not all_updates:
            st.info("No changes to save.")
        else:
            try:
                supabase.table("progress") \
                    .upsert(all_updates, on_conflict="member_id,topic") \
                    .execute()

                st.success(f"✅ {len(all_updates)} updates saved!")

                load_data.clear()  # 🔥 refresh cache
                st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

# =========================
# TAB 3 - LEADERS
# =========================




with tabs[3]:
    st.subheader("👑 Leader Analytics Dashboard")

    # =========================
    # LOAD FROM SUPABASE (FAST)
    # =========================
    leader_res = supabase.table("leader_progress_summary").select("*").execute()
    member_res = supabase.table("member_progress_summary").select("*").execute()

    leader_df = pd.DataFrame(leader_res.data or [])
    member_df = pd.DataFrame(member_res.data or [])

    if leader_df.empty:
        st.warning("No leader data found")
        st.stop()

    # =========================
    # COMPUTE %
    # =========================
    leader_df["Average Progress"] = (
        leader_df["total_done"] / leader_df["total_topics"]
    ) * 100

    leader_df["Average Progress"] = leader_df["Average Progress"].fillna(0).round(2)

    member_df["Progress %"] = (
        member_df["done_topics"] / member_df["total_topics"]
    ) * 100

    member_df["Progress %"] = member_df["Progress %"].fillna(0).round(2)

    
    # =========================
    # 🔽 EXPANDER (FAST VERSION)
    # =========================
    # build leader name map
    leader_map = dict(zip(member_df["id"], member_df["full_name"]))

    leader_ids = member_df["cell_leader_id"].dropna().unique()

    for leader_id in leader_ids:

        leader_name = leader_map.get(leader_id, "Unknown Leader")

        with st.expander(f"⭐ Leader: {leader_name}"):

            leader_members = member_df[
                member_df["cell_leader_id"] == leader_id
            ]

            if leader_members.empty:
                st.write("No members")
                continue

            for _, m in leader_members.iterrows():

                st.markdown(f"### 👤 {m['full_name']}")

                percent = m["Progress %"]

                st.write(f"Progress: {round(percent, 2)}%")
                st.progress(percent / 100)

                st.divider()


with tabs[0]:
    st.subheader("📊 Church Command Dashboard")
    
    # =========================
    # LOAD ATTENDANCE (SAFE)
    # =========================
    attendance = pd.DataFrame(
        supabase.table("attendance")
        .select("member_id, date, status")
        .execute()
        .data or []
    )

    if attendance.empty:
        attendance = pd.DataFrame(columns=["member_id", "date", "status"])

    # =========================
    # LOAD FROM SUPABASE (FAST)
    # =========================
    stats = pd.DataFrame(
        supabase.table("dashboard_stats").select("*").execute().data
    )

    progress_summary = pd.DataFrame(
        supabase.table("progress_summary").select("*").execute().data
    )

    members_perf = pd.DataFrame(
        supabase.table("member_performance").select("*").execute().data
    )

    if stats.empty:
        st.warning("No data found")
        st.stop()

    # =========================
    # BASIC STATS
    # =========================
    total_members = stats.iloc[0]["total_members"]
    active_members = stats.iloc[0]["active_members"]
    inactive_members = stats.iloc[0]["inactive_members"]

    done_count = progress_summary.iloc[0]["done_count"]
    total_progress = progress_summary.iloc[0]["total_progress"]

    overall_rate = (done_count / total_progress) * 100 if total_progress else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("👥 Total Members", total_members)
    col2.metric("🟢 Active", active_members)
    col3.metric("🔴 Inactive", inactive_members)
    col4.metric("📊 Overall Progress", f"{round(overall_rate,2)}%")

    st.divider()

    st.markdown("## ⚠️ Action Center")

    # =========================
    # 🚨 ATTENDANCE ALERTS
    # =========================
    st.markdown("### 🚨 Attendance Alerts")

    alerts = []

    for _, m in members.iterrows():

        member_id = m["id"]
        name = m["full_name"]

        member_att = attendance[attendance["member_id"] == member_id].sort_values("date")

        if member_att.empty:
            continue

        statuses = member_att["status"].tolist()

        # ❌ ABSENCE COUNT
        absences = statuses.count("Absent")

        if absences >= 3:
            alerts.append(f"🔴 {name} → Absent 3+ times ({absences})")
        elif absences == 2:
            alerts.append(f"⚠️ {name} → Absent 2 times")

        # 🟡 INCONSISTENCY
        present = statuses.count("Present")
        total = len(statuses)

        if total > 0:
            consistency = present / total

            if 0.4 <= consistency <= 0.7:
                alerts.append(f"🟡 {name} → Inconsistent attendance")

    # =========================
    # DISPLAY
    # =========================
    if alerts:
        for a in alerts:
            st.write(a)
    else:
        st.success("🎉 No attendance issues detected!")

    # =========================
    # 🏆 MEMBER PERFORMANCE
    # =========================
    st.markdown("## 🏆 Member Performance")

    # =========================
    # LOAD DATA (ONLY ONCE)
    # =========================
    members = pd.DataFrame(
        supabase.table("members")
        .select("id, full_name, cell_leader_id")
        .execute()
        .data or []
    )

    progress = pd.DataFrame(
        supabase.table("progress")
        .select("member_id, status, topic")
        .execute()
        .data or []
    )

    attendance = pd.DataFrame(
        supabase.table("attendance")
        .select("member_id, status")
        .execute()
        .data or []
    )

    if members.empty:
        st.warning("No members found")
        st.stop()

    # =========================
    # COMPUTE PERFORMANCE
    # =========================
    all_topics = progress["topic"].nunique() if not progress.empty else 1

    ranking = []

    for _, m in members.iterrows():

        member_id = m["id"]

        member_progress = progress[progress["member_id"] == member_id]
        member_att = attendance[attendance["member_id"] == member_id]

        done = len(member_progress[member_progress["status"] == "🟢Done"])
        present = len(member_att[member_att["status"] == "Present"])
        total_att = len(member_att)

        progress_percent = (done / all_topics) * 100
        attendance_percent = (present / total_att) * 100 if total_att else 0

        score = (progress_percent * 0.6) + (attendance_percent * 0.4)

        ranking.append({
            "id": member_id,
            "full_name": m["full_name"],
            "cell_leader_id": m["cell_leader_id"],
            "progress_percent": progress_percent,
            "attendance_percent": attendance_percent,
            "score": score
        })

    members_perf = pd.DataFrame(ranking).fillna(0)

    # =========================
    # MEMBER TABLE
    # =========================
    ranking_df = members_perf.sort_values(by="score", ascending=False)

    st.dataframe(
        ranking_df[[
            "full_name",
            "progress_percent",
            "attendance_percent",
            "score"
        ]].rename(columns={
            "full_name": "Member",
            "progress_percent": "Progress %",
            "attendance_percent": "Attendance %",
            "score": "Overall Score"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # =========================
    # 🎂 UPCOMING BIRTHDAYS
    # =========================
    st.markdown("## 🎂 Upcoming Birthdays")

    from datetime import datetime

    # reload members WITH birthday
    members_bday = pd.DataFrame(
        supabase.table("members")
        .select("full_name, birthday")
        .execute()
        .data or []
    )

    today = datetime.today().date()

    birthday_list = []

    for _, m in members_bday.iterrows():

        if not m.get("birthday"):
            continue

        try:
            bday = pd.to_datetime(m["birthday"]).date()

            # set birthday to this year
            this_year = bday.replace(year=today.year)

            # if already passed, move to next year
            if this_year < today:
                this_year = bday.replace(year=today.year + 1)

            days_left = (this_year - today).days

            if 0 <= days_left <= 30:
                birthday_list.append({
                    "Name": m["full_name"],
                    "Birthday": this_year,
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

    # =========================
    # LOAD MEMBERS (LIGHT)
    # =========================
    members_res = supabase.table("members") \
        .select("id, full_name, cell_leader_id") \
        .execute()

    members = pd.DataFrame(members_res.data or [])

    if members.empty:
        st.warning("No members found.")
        st.stop()

    # =========================
    # MAP LEADERS (ID → NAME)
    # =========================
    leader_map = dict(zip(members["id"], members["full_name"]))

    members["cell_leader_name"] = members["cell_leader_id"].map(leader_map)

    # =========================
    # SELECT DATE + GROUP
    # =========================
    col1, col2 = st.columns(2)

    with col1:
        selected_date = st.date_input("📆 Meeting Date")

    with col2:
        groups = members["cell_leader_id"].dropna().unique().tolist()

        selected_group_id = st.selectbox(
            "👥 Cell Group (Leader)",
            groups,
            format_func=lambda x: leader_map.get(x, "Unknown Leader")
        )

    # =========================
    # FILTER GROUP MEMBERS
    # =========================
    group_members = members[
        members["cell_leader_id"] == selected_group_id
    ]

    # =========================
    # LOAD ATTENDANCE (ONLY THIS GROUP)
    # =========================
    attendance_res = supabase.table("attendance") \
        .select("*") \
        .eq("cell_group", str(selected_group_id)) \
        .execute()

    attendance = pd.DataFrame(attendance_res.data or [])

    if attendance.empty:
        attendance = pd.DataFrame(columns=["member_id", "date", "status", "cell_group"])

    st.divider()

    # =========================
    # ATTENDANCE INPUT
    # =========================
    status_options = ["Present", "Absent"]
    attendance_inputs = []

    st.markdown("### Mark Attendance")

    for _, m in group_members.iterrows():

        status = st.selectbox(
            m["full_name"],
            status_options,
            key=f"att_{m['id']}_{selected_date}"
        )

        attendance_inputs.append({
            "member_id": int(m["id"]),
            "date": str(selected_date),
            "status": status,
            "cell_group": str(selected_group_id)
        })

    # =========================
    # 🔥 BULK UPSERT (FAST)
    # =========================
    if st.button("💾 Save Attendance"):

        try:
            supabase.table("attendance") \
                .upsert(attendance_inputs, on_conflict="member_id,date") \
                .execute()

            st.success("✅ Attendance saved!")

        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # =========================
    # 📊 WEEKLY SUMMARY (SQL VIEW)
    # =========================
    st.markdown("### 📊 Weekly Attendance Overview")

    weekly_res = supabase.table("attendance_weekly_summary") \
        .select("*") \
        .eq("cell_group", selected_group_id) \
        .execute()

    weekly_df = pd.DataFrame(weekly_res.data or [])

    if not weekly_df.empty:

        import plotly.graph_objects as go

        pivot = weekly_df.pivot_table(
            index="week",
            columns="status",
            values="count",
            fill_value=0
        ).sort_index()

        # 🔥 Ensure both columns exist
        pivot = pivot.reindex(columns=["Present", "Absent"], fill_value=0)

        fig = go.Figure()

        fig.add_bar(x=pivot.index, y=pivot["Present"], name="Present")
        fig.add_bar(x=pivot.index, y=pivot["Absent"], name="Absent")

        max_members = len(group_members)


        fig.update_layout(
            barmode="stack",
            yaxis=dict(range=[0, max_members]),
            title="Weekly Attendance"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No attendance records yet.")

    st.divider()

    # =========================
    # 📅 DAILY VIEW (FILTERED ONLY)
    # =========================
    group_attendance = attendance

    if group_attendance.empty:
        st.info("No attendance records yet.")
    else:

        available_dates = sorted(group_attendance["date"].unique(), reverse=True)

        selected_day = st.selectbox("📆 Select Meeting Date", available_dates)

        day_data = group_attendance[group_attendance["date"] == selected_day]

        present = day_data[day_data["status"] == "Present"]
        absent = day_data[day_data["status"] == "Absent"]

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

        present_names = members[members["id"].isin(present["member_id"])]

        for name in present_names["full_name"]:
            st.write(f"✔ {name}")

        st.divider()

        # =========================
        # ABSENT LIST
        # =========================
        st.markdown("## 🔴 Absent Members")

        absent_names = members[members["id"].isin(absent["member_id"])]

        for name in absent_names["full_name"]:
            st.write(f"❌ {name}")

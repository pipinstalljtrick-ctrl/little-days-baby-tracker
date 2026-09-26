import json
import uuid
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(page_title="Little Days", page_icon="L", layout="wide")

EVENT_TYPES = {
    "feed": "Feed",
    "sleep": "Sleep",
    "diaper": "Diaper",
    "note": "Note",
    "growth": "Weight",
}


def get_secret(name):
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def local_now():
    return datetime.now().astimezone()


def combine_local(day, clock):
    return datetime.combine(day, clock).astimezone().isoformat()


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone()


def display_time(value):
    return parse_time(value).strftime("%b %-d, %-I:%M %p")


def event_title(event):
    if event["type"] == "feed":
        return "Feed"
    if event["type"] == "sleep":
        return "Nap" if event.get("end") else "Nap in progress"
    if event["type"] == "diaper":
        return f"{event.get('change', 'Diaper')} diaper"
    if event["type"] == "note":
        return "Note"
    return "Weight recorded"


def event_detail(event, now=None):
    if event["type"] == "feed":
        details = [event.get("method"), event.get("side")]
        if event.get("minutes"):
            details.append(f"{event['minutes']} min")
        if event.get("volume"):
            details.append(f"{event['volume']} ml")
        return " · ".join(item for item in details if item) or "Feed logged"
    if event["type"] == "sleep":
        if not event.get("end"):
            return "Still sleeping"
        minutes = max(0, round((parse_time(event["end"]) - parse_time(event["at"])).total_seconds() / 60))
        return f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes}m"
    if event["type"] == "diaper":
        return "Wet + dirty" if event.get("change") == "Both" else event.get("change", "")
    if event["type"] == "note":
        return event.get("text", "")
    return f"{event.get('weight', '')} {event.get('unit', '')}".strip()


def active_sleep(events):
    return next((item for item in events if item["type"] == "sleep" and not item.get("end")), None)


def load_events(client):
    records = []
    offset = 0
    page_size = 1000
    while True:
        response = (
            client.table("baby_events")
            .select("id,payload")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = response.data or []
        records.extend({**row["payload"], "id": row["id"]} for row in rows if row.get("payload"))
        if len(rows) < page_size:
            break
        offset += page_size
    return sorted(records, key=lambda item: parse_time(item["at"]), reverse=True)


def add_event(client, event):
    event_id = str(uuid.uuid4())
    client.table("baby_events").insert({"id": event_id, "payload": event}).execute()


def update_event(client, event_id, updates):
    client.table("baby_events").update({"payload": updates}).eq("id", event_id).execute()


def remove_event(client, event_id):
    client.table("baby_events").delete().eq("id", event_id).execute()


def import_backup(client, backup, existing_ids):
    if not isinstance(backup, dict) or not isinstance(backup.get("events"), list):
        raise ValueError("This file does not contain a Little Days event history.")

    imported = []
    seen = set(existing_ids)
    for event in backup["events"]:
        if not isinstance(event, dict) or event.get("type") not in EVENT_TYPES or not event.get("at"):
            continue
        parse_time(event["at"])
        event_id = str(event.get("id") or uuid.uuid4())
        if event_id in seen:
            continue
        seen.add(event_id)
        payload = {key: value for key, value in event.items() if key != "id"}
        imported.append({"id": event_id, "payload": payload})

    for offset in range(0, len(imported), 500):
        client.table("baby_events").insert(imported[offset : offset + 500]).execute()
    return len(imported)


def save_auth(client, response):
    st.session_state["tracker_client"] = client
    st.session_state["tracker_user_id"] = str(response.user.id)
    st.session_state["tracker_email"] = response.user.email or ""


def auth_screen(url, anon_key):
    st.title("Little Days")
    st.caption("A private baby log for each caregiver")
    sign_in, sign_up = st.tabs(["Sign in", "Create account"])

    with sign_in:
        with st.form("sign_in_form"):
            email = st.text_input("Email", autocomplete="email")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            try:
                client = create_client(url, anon_key)
                response = client.auth.sign_in_with_password({"email": email.strip(), "password": password})
                save_auth(client, response)
                st.rerun()
            except Exception as error:
                st.error(f"Sign-in failed: {error}")

    with sign_up:
        with st.form("sign_up_form"):
            email = st.text_input("Email", key="signup_email", autocomplete="email")
            password = st.text_input("Password", type="password", key="signup_password", autocomplete="new-password")
            submitted = st.form_submit_button("Create private account", type="primary", use_container_width=True)
        if submitted:
            try:
                client = create_client(url, anon_key)
                response = client.auth.sign_up({"email": email.strip(), "password": password})
                if response.session:
                    save_auth(client, response)
                    st.rerun()
                else:
                    st.success("Account created. Confirm your email, then sign in here.")
            except Exception as error:
                st.error(f"Account creation failed: {error}")

    st.caption("Each account has its own history. Other caregivers cannot see it unless they use the same account.")


def add_forms(client, events):
    feed_tab, sleep_tab, diaper_tab, note_tab, weight_tab = st.tabs(
        ["Feed", "Nap", "Diaper", "Note", "Weight"]
    )
    now = local_now()

    with feed_tab:
        with st.form("feed_form"):
            method = st.radio("How did baby feed?", ["Breast", "Bottle", "Mixed"], horizontal=True)
            left, right = st.columns(2)
            side = left.selectbox("Side", ["Not noted", "Left", "Right", "Both"])
            minutes = right.number_input("Duration (minutes)", min_value=0, max_value=300, value=0)
            left, right = st.columns(2)
            volume = left.number_input("Bottle amount (ml)", min_value=0, max_value=2000, value=0, step=10)
            day = right.date_input("Date", value=now.date(), key="feed_date")
            clock = st.time_input("Time", value=now.time().replace(second=0, microsecond=0), key="feed_time", format="12h")
            submitted = st.form_submit_button("Save feed", type="primary")
        if submitted:
            event = {"type": "feed", "at": combine_local(day, clock), "method": method}
            if side != "Not noted":
                event["side"] = side
            if minutes:
                event["minutes"] = int(minutes)
            if volume:
                event["volume"] = int(volume)
            try:
                add_event(client, event)
                st.success("Feed saved to your account.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not save feed: {error}")

    with sleep_tab:
        ongoing = active_sleep(events)
        if ongoing:
            st.info(f"Nap started {display_time(ongoing['at'])}.")
            with st.form("end_sleep_form"):
                wake_day = st.date_input("Wake-up date", value=now.date(), key="wake_day")
                wake_clock = st.time_input("Wake-up time", value=now.time().replace(second=0, microsecond=0), key="wake_clock", format="12h")
                submitted = st.form_submit_button("End nap", type="primary")
            if submitted:
                end = combine_local(wake_day, wake_clock)
                if parse_time(end) <= parse_time(ongoing["at"]):
                    st.error("Wake-up time must be after the nap started.")
                else:
                    try:
                        updated = {key: value for key, value in ongoing.items() if key != "id"}
                        update_event(client, ongoing["id"], {**updated, "end": end})
                        st.success("Nap saved to your account.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not end nap: {error}")
        else:
            if st.button("Start nap now", type="primary"):
                try:
                    add_event(client, {"type": "sleep", "at": now.isoformat()})
                    st.success("Nap started.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not start nap: {error}")

        with st.expander("Add a completed nap from earlier"):
            with st.form("manual_sleep_form"):
                left, right = st.columns(2)
                start_day = left.date_input("Started", value=now.date(), key="sleep_start_day")
                start_clock = right.time_input("Start time", value=now.time().replace(second=0, microsecond=0), key="sleep_start_clock", format="12h")
                left, right = st.columns(2)
                end_day = left.date_input("Woke up", value=now.date(), key="sleep_end_day")
                end_clock = right.time_input("Wake-up time", value=now.time().replace(second=0, microsecond=0), key="sleep_end_clock", format="12h")
                submitted = st.form_submit_button("Save completed nap")
            if submitted:
                start = combine_local(start_day, start_clock)
                end = combine_local(end_day, end_clock)
                if parse_time(end) <= parse_time(start):
                    st.error("Wake-up time must be after the nap started.")
                else:
                    try:
                        add_event(client, {"type": "sleep", "at": start, "end": end})
                        st.success("Nap saved to your account.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not save nap: {error}")

    with diaper_tab:
        with st.form("diaper_form"):
            change = st.radio("Change", ["Wet", "Dirty", "Both"], horizontal=True)
            day = st.date_input("Date", value=now.date(), key="diaper_date")
            clock = st.time_input("Time", value=now.time().replace(second=0, microsecond=0), key="diaper_time", format="12h")
            submitted = st.form_submit_button("Save diaper", type="primary")
        if submitted:
            try:
                add_event(client, {"type": "diaper", "change": change, "at": combine_local(day, clock)})
                st.success("Diaper change saved to your account.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not save diaper change: {error}")

    with note_tab:
        with st.form("note_form"):
            text = st.text_area("A little detail", placeholder="Something to remember")
            day = st.date_input("Date", value=now.date(), key="note_date")
            clock = st.time_input("Time", value=now.time().replace(second=0, microsecond=0), key="note_time", format="12h")
            submitted = st.form_submit_button("Save note", type="primary")
        if submitted:
            if not text.strip():
                st.error("Add a detail before saving the note.")
            else:
                try:
                    add_event(client, {"type": "note", "text": text.strip(), "at": combine_local(day, clock)})
                    st.success("Note saved to your account.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not save note: {error}")

    with weight_tab:
        with st.form("weight_form"):
            left, right = st.columns(2)
            weight = left.number_input("Weight", min_value=0.001, value=3.0, step=0.1, format="%.3f")
            unit = right.selectbox("Unit", ["kg", "lb"])
            day = st.date_input("Date", value=now.date(), key="weight_date")
            clock = st.time_input("Time", value=now.time().replace(second=0, microsecond=0), key="weight_time", format="12h")
            submitted = st.form_submit_button("Save weight", type="primary")
        if submitted:
            try:
                add_event(client, {"type": "growth", "weight": float(weight), "unit": unit, "at": combine_local(day, clock)})
                st.success("Weight note saved to your account.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not save weight: {error}")


def delete_control(client, event_id):
    pending = st.session_state.get("delete_event_id") == event_id
    if pending:
        confirm, cancel = st.columns(2)
        if confirm.button("Confirm delete", key=f"confirm_{event_id}", type="primary"):
            try:
                remove_event(client, event_id)
                st.session_state.pop("delete_event_id", None)
                st.rerun()
            except Exception as error:
                st.error(f"Could not delete entry: {error}")
        if cancel.button("Cancel", key=f"cancel_{event_id}"):
            st.session_state.pop("delete_event_id", None)
            st.rerun()
    elif st.button("Delete", key=f"delete_{event_id}"):
        st.session_state["delete_event_id"] = event_id
        st.rerun()


def render_history(client, events):
    selected = st.selectbox("Show", ["Everything", *EVENT_TYPES.values()], key="history_filter")
    rows = [item for item in events if selected == "Everything" or EVENT_TYPES.get(item["type"]) == selected]
    if not rows:
        st.info("No history entries yet.")
        return
    for event in rows:
        with st.container(border=True):
            details, action = st.columns([5, 1])
            details.markdown(f"**{event_title(event)}**  \n{display_time(event['at'])}  \n{event_detail(event)}")
            with action:
                delete_control(client, event["id"])


def render_today(events):
    now = local_now()
    today = now.date()
    todays_events = [item for item in events if parse_time(item["at"]).date() == today]
    feeds = sum(item["type"] == "feed" for item in todays_events)
    diapers = sum(item["type"] == "diaper" for item in todays_events)
    start = datetime.combine(today, time.min).astimezone()
    end = start + timedelta(days=1)
    sleep_seconds = 0
    for item in events:
        if item["type"] != "sleep":
            continue
        nap_start = parse_time(item["at"])
        nap_end = parse_time(item["end"]) if item.get("end") else now
        sleep_seconds += max(0, (min(nap_end, end) - max(nap_start, start)).total_seconds())

    feed_metric, sleep_metric, diaper_metric = st.columns(3)
    feed_metric.metric("Feeds today", feeds)
    sleep_metric.metric("Sleep today", f"{sleep_seconds / 3600:.1f} hrs")
    diaper_metric.metric("Diapers today", diapers)

    ongoing = active_sleep(events)
    if ongoing:
        st.info(f"Nap in progress since {display_time(ongoing['at'])}. End it from the Nap tab.")

    st.subheader("Recent moments")
    recent = todays_events[:6]
    if not recent:
        st.info("Nothing logged yet today.")
    for event in recent:
        st.write(f"**{display_time(event['at'])} · {event_title(event)}**  \n{event_detail(event)}")


def render_progress(events):
    now = local_now()
    days = [now.date() - timedelta(days=index) for index in range(6, -1, -1)]
    feed_counts = []
    diaper_counts = []
    sleep_hours = []
    for day in days:
        day_start = datetime.combine(day, time.min).astimezone()
        day_end = day_start + timedelta(days=1)
        feed_counts.append(sum(item["type"] == "feed" and parse_time(item["at"]).date() == day for item in events))
        diaper_counts.append(sum(item["type"] == "diaper" and parse_time(item["at"]).date() == day for item in events))
        seconds = 0
        for item in events:
            if item["type"] != "sleep":
                continue
            nap_start = parse_time(item["at"])
            nap_end = parse_time(item["end"]) if item.get("end") else now
            seconds += max(0, (min(nap_end, day_end) - max(nap_start, day_start)).total_seconds())
        sleep_hours.append(round(seconds / 3600, 1))

    chart_data = pd.DataFrame({
        "Day": [day.strftime("%a %d") for day in days],
        "Feeds": feed_counts,
        "Diapers": diaper_counts,
        "Sleep hours": sleep_hours,
    })
    feed_chart, diaper_chart, sleep_chart = st.columns(3)
    with feed_chart:
        st.subheader("Feeds · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Feeds"]])
    with diaper_chart:
        st.subheader("Diapers · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Diapers"]])
    with sleep_chart:
        st.subheader("Sleep · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Sleep hours"]])

    st.subheader("Weight notes")
    weights = [item for item in events if item["type"] == "growth"]
    if weights:
        st.dataframe(
            [{"Date": display_time(item["at"]), "Weight": f"{item['weight']} {item['unit']}"} for item in weights],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Weight notes will appear here when added.")


def main():
    url = get_secret("SUPABASE_URL").strip()
    anon_key = get_secret("SUPABASE_ANON_KEY").strip()
    if not url or not anon_key:
        st.title("Little Days")
        st.error("The shared database is not configured yet.")
        st.markdown(
            "For local use, copy `.streamlit/secrets.toml.example` to "
            "`.streamlit/secrets.toml` and fill in your Supabase project URL and public anon key. "
            "For Streamlit Cloud, add those values in the app's Secrets settings. "
            "Run `supabase_schema.sql` in the Supabase SQL Editor first."
        )
        st.stop()

    if "tracker_client" not in st.session_state:
        auth_screen(url, anon_key)
        return

    client = st.session_state["tracker_client"]
    st.title("Little Days")
    st.caption(f"Your private baby log · Signed in as {st.session_state.get('tracker_email', '')}")
    top_left, top_right = st.columns([5, 1])
    with top_right:
        if st.button("Sign out"):
            try:
                client.auth.sign_out()
            finally:
                for key in ("tracker_client", "tracker_user_id", "tracker_email", "delete_event_id"):
                    st.session_state.pop(key, None)
                st.rerun()

    try:
        events = load_events(client)
    except Exception as error:
        st.error(f"Could not load your saved history: {error}")
        st.stop()

    today_tab, log_tab, history_tab, progress_tab = st.tabs(["Today", "Log", "History", "Progress"])
    with today_tab:
        st.caption(local_now().strftime("%A, %B %-d"))
        render_today(events)
    with log_tab:
        st.subheader("Add a moment")
        add_forms(client, events)
    with history_tab:
        st.subheader("Your saved history")
        st.caption(f"{len(events)} entries saved to your account")
        export_data = {"exported_at": local_now().isoformat(), "events": events}
        st.download_button(
            "Export history",
            data=json.dumps(export_data, indent=2),
            file_name="little-days-history.json",
            mime="application/json",
        )
        with st.expander("Import history from the older app"):
            st.caption("Choose a JSON backup exported from the original Little Days app. Existing entries are skipped.")
            backup_file = st.file_uploader("Little Days JSON backup", type=["json"], key="history_backup")
            if backup_file and st.button("Import backup", key="import_backup", type="primary"):
                try:
                    backup = json.loads(backup_file.getvalue())
                    imported = import_backup(client, backup, {item["id"] for item in events})
                    st.success(f"Imported {imported} new entries into your account.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not import backup: {error}")
        render_history(client, events)
    with progress_tab:
        st.subheader("A week at a glance")
        render_progress(events)
        st.caption("These notes are for your family. Ask your baby's clinician about feeding, sleep, or growth concerns.")


if __name__ == "__main__":
    main()
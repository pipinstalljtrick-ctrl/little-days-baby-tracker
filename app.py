import html
import json
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from supabase import create_client


st.set_page_config(page_title="Little Days", page_icon="L", layout="wide")

US_FL_OZ_IN_ML = 29.5735295625
FALLBACK_TIMEZONE = ZoneInfo("America/New_York")
HISTORY_PAGE_SIZE = 50

EVENT_TYPES = {
    "feed": "Feed",
    "sleep": "Sleep",
    "diaper": "Diaper",
    "note": "Note",
    "growth": "Weight",
}

DAILY_ENCOURAGEMENTS = (
    "Care is built one small moment at a time.",
    "You and your baby are learning each other every day.",
    "A quiet cuddle is a meaningful kind of progress.",
    "There is no perfect day, only the care you give today.",
    "Pausing to rest is part of showing up.",
    "Small routines can make room for reassuring moments.",
    "Your steady presence matters more than a perfect plan.",
    "Today can be gentle, even if it is not easy.",
    "Each new day is another chance to find your rhythm.",
    "The love is in the ordinary moments, too.",
    "You do not have to do it all at once.",
    "A little care, repeated, goes a long way.",
    "Your best today is enough for today.",
    "Every family finds its own rhythm.",
)


def apply_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');
        :root {
            --paper: #f5f3ed; --white: #fffefa; --ink: #253b35; --muted: #7c8981; --line: #e7e6dc;
            --green: #477968; --dark: #315b4d; --mint: #e7f0e8; --peach: #f3e6d8; --blue: #e8edf0;
            --yellow: #f4efda; --rose: #a66b5c;
        }
        .stApp, [data-testid="stAppViewContainer"] { background: var(--paper); color: var(--ink); }
        .stApp, .stApp p, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp li,
        .stApp span:not([data-testid="stIconMaterial"]) {
            font-family: 'DM Sans', sans-serif;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stAppDeployButton"], .ld-greeting [data-testid="stHeaderActionElements"] { display: none; }
        /* Streamlit styles headings itself, so the serif needs !important to win. */
        .stApp h2, .stApp h3, .ld-greeting h1, .ld-greeting h1 span, .ld-section-title,
        .ld-reminder p:last-child, .ld-reminder p:last-child span {
            font-family: 'DM Serif Display', Georgia, serif !important; font-weight: 400 !important;
        }
        .block-container { max-width: 1120px; padding: 1.2rem 3rem 3.5rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        .stApp h2, .stApp h3 {
            font-family: 'DM Serif Display', Georgia, serif; font-weight: 400; font-size: 1.45rem;
        }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted); }

        /* Brand bar and greeting */
        .ld-topbar {
            display: flex; align-items: center; justify-content: space-between;
            min-height: 52px; border-bottom: 1px solid var(--line); margin-bottom: 0.2rem;
        }
        .ld-brand { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 700; color: var(--ink); }
        .ld-mark {
            width: 30px; height: 30px; display: grid; place-items: center; background: var(--green);
            color: #fff; border-radius: 50% 50% 45% 50%; font: 13px Georgia, serif;
        }
        .ld-sync { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: 11px; }
        .ld-sync i { width: 7px; height: 7px; border-radius: 50%; background: #6a9a75; }
        .ld-greeting { padding: 2rem 0 1.4rem; }
        .ld-eyebrow {
            font-size: 10px; letter-spacing: .13em; text-transform: uppercase; font-weight: 700;
            color: var(--muted); margin: 0 0 8px;
        }
        .ld-greeting h1 {
            font: 44px/1.1 'DM Serif Display', Georgia, serif; font-weight: 400; margin: 0; padding: 0; color: var(--ink);
        }
        .ld-soft { color: #a8b4a7; }
        .ld-subhead { margin: 14px 0 0; color: var(--muted); font-size: 14px; }

        /* Tabs: underline style */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 26px; background: transparent; border-bottom: 1px solid var(--line);
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
            background: transparent; padding: 12px 2px; height: auto; color: #89948d;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] p { font-size: 13px; font-weight: 600; }
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { color: var(--ink); }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--green); height: 2px; }
        [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }

        /* Stat tiles */
        .ld-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 0.4rem 0 1.6rem; }
        .ld-stat {
            min-height: 98px; padding: 17px 19px; background: var(--white); border: 1px solid #eeede6;
            border-radius: 7px; display: flex; align-items: center; justify-content: space-between;
        }
        .ld-stat .ld-eyebrow { margin: 0 0 5px; font-size: 9px; }
        .ld-value { font-size: 25px; font-weight: 600; color: var(--ink); }
        .ld-unit { font-size: 11px; color: var(--muted); margin-left: 4px; font-weight: 500; }
        .ld-icon {
            width: 36px; height: 36px; flex: 0 0 36px; border-radius: 50%; display: grid; place-items: center;
            font-size: 17px; color: var(--dark); font-style: normal;
        }
        .ld-feed { background: var(--mint); } .ld-bottle { background: var(--peach); }
        .ld-sleep { background: var(--blue); } .ld-diaper { background: var(--yellow); }
        .ld-note { background: var(--peach); } .ld-growth { background: var(--mint); }

        /* Timeline of recent moments */
        .ld-section-title { font: 22px 'DM Serif Display', Georgia, serif; color: var(--ink); margin: 0 0 14px; }
        .ld-row {
            display: grid; grid-template-columns: 64px 19px 1fr; gap: 8px; padding: 12px 0;
            border-top: 1px solid var(--line);
        }
        .ld-time { font-size: 11px; color: var(--muted); padding-top: 2px; }
        .ld-marker { display: flex; justify-content: center; position: relative; }
        .ld-marker:before {
            content: ''; width: 8px; height: 8px; border: 2px solid var(--green); border-radius: 50%;
            background: var(--paper); margin-top: 4px; z-index: 1;
        }
        .ld-row:not(:last-child) .ld-marker:after {
            content: ''; position: absolute; top: 13px; bottom: -17px; width: 1px; background: #d9ded5;
        }
        .ld-copy b { font-size: 13px; font-weight: 600; }
        .ld-copy p { font-size: 12px; color: var(--muted); margin: 4px 0 0; }
        .ld-empty { padding: 20px 0; color: var(--muted); font-size: 12px; border-top: 1px solid var(--line); }
        .ld-reminder { background: #ebeee6; padding: 19px 21px; border-radius: 7px; margin-top: 44px; }
        .ld-reminder > span { display: block; color: #7a9b7f; font-size: 22px; margin-bottom: 12px; }
        .ld-reminder p:last-child { font: 16px/1.5 'DM Serif Display', Georgia, serif; color: #476355; margin: 0; }
        .ld-nap-banner {
            background: var(--blue); color: #3f5561; border-radius: 7px; padding: 12px 16px;
            font-size: 13px; margin: -0.6rem 0 1.4rem;
        }

        /* History cards */
        [class*="st-key-history-"] {
            background: var(--white); border: 1px solid #eeede6 !important; border-radius: 7px; padding: 4px 6px;
        }
        .ld-hist { display: flex; align-items: center; gap: 12px; }
        .ld-hist .ld-icon { width: 30px; height: 30px; flex-basis: 30px; font-size: 13px; }
        .ld-hist b { font-size: 13px; font-weight: 600; }
        .ld-hist p { font-size: 12px; color: var(--muted); margin: 2px 0 0; }

        /* Weight rows */
        .ld-weight { display: flex; justify-content: space-between; padding: 12px 0; border-top: 1px solid var(--line); }
        .ld-weight b { font-size: 13px; }
        .ld-weight span { font-size: 12px; color: var(--muted); }

        /* Forms, inputs, buttons */
        [data-testid="stForm"], [data-testid="stExpander"] details {
            background: var(--white); border: 1px solid #eeede6; border-radius: 9px;
        }
        [data-testid="stForm"] { padding: 1.4rem; }
        .stApp label p { color: #59675f; font-size: 12px; font-weight: 600; }
        [data-testid^="stBaseButton-primary"] {
            background: var(--green); border-color: var(--green); border-radius: 6px; color: #fff; font-weight: 700;
        }
        [data-testid^="stBaseButton-primary"]:hover { background: var(--dark); border-color: var(--dark); color: #fff; }
        [data-testid^="stBaseButton-secondary"] {
            background: #e9ece4; border: 0; border-radius: 6px; color: var(--dark); font-weight: 700;
        }
        [data-testid^="stBaseButton-secondary"]:hover { background: #dfe6da; color: var(--dark); }
        [data-testid="stAlert"] { border-radius: 7px; }
        [data-testid="stVegaLiteChart"] { background: var(--white); border: 1px solid #eeede6; border-radius: 7px; padding: 10px; }

        @media (max-width: 780px) {
            .block-container { padding: 1rem 1.6rem 3rem; }
            .ld-stats { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 580px) {
            .block-container { padding: 0.8rem 1rem 2.5rem; }
            .ld-greeting { padding: 1.4rem 0 1rem; }
            .ld-greeting h1 { font-size: 36px; }
            .ld-sync span { display: none; }
            .ld-stats { gap: 6px; }
            .ld-stat { padding: 12px 11px; min-height: 80px; }
            .ld-value { font-size: 21px; }
            .ld-stat .ld-icon { display: none; }
            .ld-reminder { margin-top: 10px; }
            [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 18px; }
            [data-testid="stForm"] { padding: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_secret(name):
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def local_timezone():
    # The viewer's browser reports its IANA timezone (e.g. "America/Chicago") with each session.
    try:
        name = st.context.timezone
        return ZoneInfo(name) if name else FALLBACK_TIMEZONE
    except Exception:
        return FALLBACK_TIMEZONE


def local_now():
    return datetime.now(local_timezone())


def daily_encouragement(day=None):
    day = day or local_now().date()
    return DAILY_ENCOURAGEMENTS[day.toordinal() % len(DAILY_ENCOURAGEMENTS)]


def flash(message):
    # st.rerun() discards anything drawn in the current run, so hold the message for the next one.
    st.session_state["flash_message"] = message


def show_flash():
    message = st.session_state.pop("flash_message", None)
    if message:
        st.toast(message)


EVENT_ICONS = {"feed": "＋", "sleep": "◷", "diaper": "✳", "note": "✎", "growth": "↗"}


def render_brand(email=""):
    status = f'<span class="ld-sync"><i></i><span>Synced · {html.escape(email)}</span></span>' if email else ""
    st.markdown(
        f'<div class="ld-topbar"><div class="ld-brand"><span class="ld-mark">ld</span> little days</div>{status}</div>',
        unsafe_allow_html=True,
    )


def render_greeting():
    st.markdown(
        f'<div class="ld-greeting"><p class="ld-eyebrow">{local_now().strftime("%A, %B %-d")}</p>'
        '<h1>Your little one<span class="ld-soft">’s day</span></h1>'
        f'<p class="ld-subhead">{html.escape(daily_encouragement())}</p></div>',
        unsafe_allow_html=True,
    )


def stat_tile(label, value, unit, icon, tone):
    unit_html = f'<span class="ld-unit">{unit}</span>' if unit else ""
    return (
        f'<div class="ld-stat"><div><p class="ld-eyebrow">{label}</p>'
        f'<span class="ld-value">{value}</span>{unit_html}</div>'
        f'<i class="ld-icon ld-{tone}">{icon}</i></div>'
    )


def timeline_row(event):
    time_label = parse_time(event["at"]).strftime("%-I:%M %p")
    detail = html.escape(event_detail(event))
    return (
        f'<div class="ld-row"><span class="ld-time">{time_label}</span><span class="ld-marker"></span>'
        f'<div class="ld-copy"><b>{html.escape(event_title(event))}</b><p>{detail}</p></div></div>'
    )


def combine_local(day, clock):
    return datetime.combine(day, clock, tzinfo=local_timezone()).isoformat()


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(local_timezone())


def display_time(value):
    return parse_time(value).strftime("%b %-d, %-I:%M %p")


def event_time_label(event):
    start_value = event.get("start")
    end_value = event.get("end")
    if event["type"] != "feed" or not start_value or not end_value:
        return display_time(event["at"])

    start = parse_time(start_value)
    end = parse_time(end_value)
    start_label = display_time(start.isoformat())
    end_label = end.strftime("%-I:%M %p") if start.date() == end.date() else display_time(end.isoformat())
    return f"{start_label} – {end_label}"


def format_ounces(value):
    return f"{round(float(value), 1):g}"


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


def feed_ounces(event):
    if event.get("volume_oz") is not None:
        return float(event["volume_oz"])
    if event.get("volume") is not None:
        return float(event["volume"]) / US_FL_OZ_IN_ML
    return None


def ounces_on(events, day):
    return sum(
        feed_ounces(item) or 0
        for item in events
        if item["type"] == "feed" and parse_time(item["at"]).date() == day
    )


def event_detail(event, now=None):
    if event["type"] == "feed":
        details = [event.get("method"), event.get("side")]
        if event.get("start") and event.get("end"):
            minutes = round((parse_time(event["end"]) - parse_time(event["start"])).total_seconds() / 60)
            if minutes:
                details.append(f"{minutes} min")
        elif event.get("minutes"):
            details.append(f"{event['minutes']} min")
        ounces = feed_ounces(event)
        if ounces is not None:
            details.append(f"{format_ounces(ounces)} oz")
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


def sleep_seconds_on(events, day, now):
    day_start = datetime.combine(day, time.min, tzinfo=local_timezone())
    day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=local_timezone())
    seconds = 0
    for item in events:
        if item["type"] != "sleep":
            continue
        nap_start = parse_time(item["at"])
        nap_end = parse_time(item["end"]) if item.get("end") else now
        seconds += max(0, (min(nap_end, day_end) - max(nap_start, day_start)).total_seconds())
    return seconds


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


def event_fingerprint(event):
    return json.dumps({key: value for key, value in event.items() if key != "id"}, sort_keys=True)


def import_backup(client, backup, existing_events):
    if not isinstance(backup, dict) or not isinstance(backup.get("events"), list):
        raise ValueError("This file does not contain a Little Days event history.")

    # Row ids are unique across every account, and RLS hides other accounts' rows, so a backup's
    # original ids can collide invisibly. Skip duplicates by content and always insert fresh ids.
    imported = []
    seen = {event_fingerprint(event) for event in existing_events}
    for event in backup["events"]:
        if not isinstance(event, dict) or event.get("type") not in EVENT_TYPES or not event.get("at"):
            continue
        parse_time(event["at"])
        fingerprint = event_fingerprint(event)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        payload = {key: value for key, value in event.items() if key != "id"}
        imported.append({"id": str(uuid.uuid4()), "payload": payload})

    for offset in range(0, len(imported), 500):
        client.table("baby_events").insert(imported[offset : offset + 500]).execute()
    return len(imported)


def save_auth(client, response):
    st.session_state["tracker_client"] = client
    st.session_state["tracker_user_id"] = str(response.user.id)
    st.session_state["tracker_email"] = response.user.email or ""


def auth_screen(url, anon_key):
    render_brand()
    render_greeting()
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
            started = now - timedelta(minutes=20)
            left, right = st.columns(2)
            start_day = left.date_input("Started", value=started.date(), key="feed_start_day")
            start_clock = left.time_input(
                "Start time",
                value=started.time().replace(second=0, microsecond=0),
                key="feed_start_time",
                format="12h",
            )
            end_day = right.date_input("Ended", value=now.date(), key="feed_end_day")
            end_clock = right.time_input(
                "End time",
                value=now.time().replace(second=0, microsecond=0),
                key="feed_end_time",
                format="12h",
            )
            left, right = st.columns(2)
            side = left.selectbox("Side", ["Not noted", "Left", "Right", "Both"])
            volume = right.number_input(
                "Bottle amount (oz)",
                min_value=0.0,
                max_value=64.0,
                value=0.0,
                step=0.5,
                format="%.1f",
            )
            submitted = st.form_submit_button("Save feed", type="primary")
        if submitted:
            start_at = combine_local(start_day, start_clock)
            end_at = combine_local(end_day, end_clock)
            if parse_time(end_at) <= parse_time(start_at):
                st.error("End time must be after start time.")
            else:
                minutes = round((parse_time(end_at) - parse_time(start_at)).total_seconds() / 60)
                event = {
                    "type": "feed",
                    "at": start_at,
                    "start": start_at,
                    "end": end_at,
                    "minutes": minutes,
                    "method": method,
                }
                if side != "Not noted":
                    event["side"] = side
                if volume:
                    event["volume_oz"] = round(float(volume), 1)
                try:
                    add_event(client, event)
                    flash("Feed saved to your account.")
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
                        flash("Nap saved to your account.")
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not end nap: {error}")
        else:
            if st.button("Start nap now", type="primary"):
                try:
                    add_event(client, {"type": "sleep", "at": local_now().isoformat()})
                    flash("Nap started.")
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
                        flash("Nap saved to your account.")
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
                flash("Diaper change saved to your account.")
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
                    flash("Note saved to your account.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Could not save note: {error}")

    with weight_tab:
        with st.form("weight_form"):
            left, right = st.columns(2)
            weight = left.number_input("Weight", min_value=0.001, value=7.0, step=0.1, format="%.2f")
            unit = right.selectbox("Unit", ["lb", "kg"])
            day = st.date_input("Date", value=now.date(), key="weight_date")
            clock = st.time_input("Time", value=now.time().replace(second=0, microsecond=0), key="weight_time", format="12h")
            submitted = st.form_submit_button("Save weight", type="primary")
        if submitted:
            try:
                add_event(client, {"type": "growth", "weight": float(weight), "unit": unit, "at": combine_local(day, clock)})
                flash("Weight note saved to your account.")
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
    limit = st.session_state.get("history_limit", HISTORY_PAGE_SIZE)
    for event in rows[:limit]:
        with st.container(border=True, key=f"history-{event['id']}"):
            details, action = st.columns([5, 1], vertical_alignment="center")
            details.markdown(
                f'<div class="ld-hist"><i class="ld-icon ld-{event["type"]}">{EVENT_ICONS.get(event["type"], "•")}</i>'
                f'<div><b>{html.escape(event_title(event))}</b>'
                f'<p>{html.escape(event_time_label(event))} · {html.escape(event_detail(event))}</p></div></div>',
                unsafe_allow_html=True,
            )
            with action:
                delete_control(client, event["id"])
    if len(rows) > limit:
        st.caption(f"Showing {limit} of {len(rows)} entries")
        if st.button("Show more", key="history_show_more"):
            st.session_state["history_limit"] = limit + HISTORY_PAGE_SIZE
            st.rerun()


def render_today(events):
    now = local_now()
    today = now.date()
    todays_events = [item for item in events if parse_time(item["at"]).date() == today]
    feeds = sum(item["type"] == "feed" for item in todays_events)
    diapers = sum(item["type"] == "diaper" for item in todays_events)
    sleep_seconds = sleep_seconds_on(events, today, now)

    st.markdown(
        '<div class="ld-stats">'
        + stat_tile("Feeds today", feeds, "", EVENT_ICONS["feed"], "feed")
        + stat_tile("Bottle today", format_ounces(ounces_on(events, today)), "oz", "◐", "bottle")
        + stat_tile("Sleep today", f"{sleep_seconds / 3600:.1f}", "hrs", EVENT_ICONS["sleep"], "sleep")
        + stat_tile("Diapers today", diapers, "", EVENT_ICONS["diaper"], "diaper")
        + "</div>",
        unsafe_allow_html=True,
    )

    ongoing = active_sleep(events)
    if ongoing:
        st.markdown(
            f'<div class="ld-nap-banner">◷ Nap in progress since {display_time(ongoing["at"])}. '
            "End it from the Log tab.</div>",
            unsafe_allow_html=True,
        )

    timeline, reminder = st.columns([2.6, 1], gap="large")
    recent = todays_events[:6]
    rows = "".join(timeline_row(event) for event in recent) or '<div class="ld-empty">Nothing logged yet today.</div>'
    timeline.markdown(
        f'<p class="ld-eyebrow">So far today</p><p class="ld-section-title">Recent moments</p><div>{rows}</div>',
        unsafe_allow_html=True,
    )
    reminder.markdown(
        '<div class="ld-reminder"><span>✿</span><p class="ld-eyebrow">A gentle reminder</p>'
        "<p>Every feed, cuddle, and quiet moment counts. There’s no perfect way through today.</p></div>",
        unsafe_allow_html=True,
    )


def render_progress(events):
    now = local_now()
    days = [now.date() - timedelta(days=index) for index in range(6, -1, -1)]
    feed_counts = []
    bottle_ounces = []
    diaper_counts = []
    sleep_hours = []
    for day in days:
        feed_counts.append(sum(item["type"] == "feed" and parse_time(item["at"]).date() == day for item in events))
        bottle_ounces.append(round(ounces_on(events, day), 1))
        diaper_counts.append(sum(item["type"] == "diaper" and parse_time(item["at"]).date() == day for item in events))
        sleep_hours.append(round(sleep_seconds_on(events, day, now) / 3600, 1))

    chart_data = pd.DataFrame({
        "Day": [day.strftime("%a %d") for day in days],
        "Feeds": feed_counts,
        "Bottle oz": bottle_ounces,
        "Diapers": diaper_counts,
        "Sleep hours": sleep_hours,
    })
    feed_chart, ounces_chart = st.columns(2)
    with feed_chart:
        st.subheader("Feeds · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Feeds"]], color="#91b49a", x_label="", y_label="", height=220)
    with ounces_chart:
        st.subheader("Bottle oz · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Bottle oz"]], color="#d9b99b", x_label="", y_label="", height=220)
    diaper_chart, sleep_chart = st.columns(2)
    with diaper_chart:
        st.subheader("Diapers · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Diapers"]], color="#cdbf86", x_label="", y_label="", height=220)
    with sleep_chart:
        st.subheader("Sleep · past 7 days")
        st.bar_chart(chart_data.set_index("Day")[["Sleep hours"]], color="#a9c1cf", x_label="", y_label="", height=220)

    st.subheader("Weight notes")
    weights = [item for item in events if item["type"] == "growth"]
    if weights:
        st.markdown(
            "".join(
                f'<div class="ld-weight"><b>{html.escape(str(item["weight"]))} {html.escape(item["unit"])}</b>'
                f'<span>{display_time(item["at"])}</span></div>'
                for item in weights
            ),
            unsafe_allow_html=True,
        )
    else:
        st.info("Weight notes will appear here when added.")


def main():
    apply_styles()
    url = get_secret("SUPABASE_URL").strip()
    anon_key = get_secret("SUPABASE_ANON_KEY").strip()
    if not url or not anon_key:
        render_brand()
        render_greeting()
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
    show_flash()
    render_brand(st.session_state.get("tracker_email", ""))
    greeting, top_right = st.columns([5, 1], vertical_alignment="bottom")
    with greeting:
        render_greeting()
    with top_right:
        if st.button("Sign out"):
            try:
                client.auth.sign_out()
            finally:
                for key in ("tracker_client", "tracker_user_id", "tracker_email", "delete_event_id", "flash_message", "history_limit"):
                    st.session_state.pop(key, None)
                st.rerun()

    try:
        events = load_events(client)
    except Exception as error:
        st.error(f"Could not load your saved history: {error}")
        st.stop()

    today_tab, log_tab, history_tab, progress_tab = st.tabs(["Today", "Log", "History", "Progress"])
    with today_tab:
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
                    imported = import_backup(client, backup, events)
                    flash(f"Imported {imported} new entries into your account.")
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
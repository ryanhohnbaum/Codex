from __future__ import annotations

import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from app.agent import InboxAgent
from app.gmail_client import GmailClient
from app.memory import RulesMemory

load_dotenv()

st.set_page_config(page_title="AI Inbox Agent", page_icon="📥", layout="wide")
st.title("📥 Autonomous AI Inbox Agent")

if "memory" not in st.session_state:
    st.session_state.memory = RulesMemory()
if "agent" not in st.session_state:
    st.session_state.agent = InboxAgent(st.session_state.memory)

memory: RulesMemory = st.session_state.memory
agent: InboxAgent = st.session_state.agent

with st.sidebar:
    st.header("Configuration")
    openai_key = st.text_input("OpenAI API Key", value=os.environ.get("OPENAI_API_KEY", ""), type="password")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    st.caption("Set permanently in a .env file with OPENAI_API_KEY=...")

if not memory.has_rules():
    st.subheader("Phase 1: Onboarding Interview")
    with st.form("onboarding"):
        q1 = st.text_input("How should I handle daily newsletters?")
        q2 = st.text_input("Which domains should I never touch?")
        q3 = st.text_input("What should I usually archive automatically?")
        submitted = st.form_submit_button("Save baseline rules")
        if submitted:
            for idx, pair in enumerate([
                ("keyword", q1, "trash"),
                ("domain", q2.replace("@", "").strip(), "keep"),
                ("keyword", q3, "archive"),
            ]):
                scope, pattern, action = pair
                if pattern:
                    agent.learn_from_user(f"domain:{pattern}" if scope == "domain" else f"domain:{pattern}", action)
            st.success("Baseline memory saved. Continue to fast sweep.")

st.subheader("Phase 2-4: Sweep, Triage, and Cleanup")
max_results = st.slider("Unread emails to scan", min_value=100, max_value=1000, value=300, step=100)

if st.button("Run Inbox Sweep"):
    gmail = GmailClient()
    with st.spinner("Authenticating with Gmail..."):
        gmail.authenticate()
    with st.spinner("Fetching and processing messages asynchronously..."):
        emails = asyncio.run(gmail.fetch_unread_messages(max_results=max_results))
        decisions = asyncio.run(agent.process(emails))
    st.session_state.gmail = gmail
    st.session_state.decisions = decisions
    st.success(f"Analyzed {len(emails)} unread emails across {len(decisions)} batches.")

if "decisions" in st.session_state:
    st.markdown("### Proposed Actions")
    selected = []
    for d in st.session_state.decisions:
        with st.expander(f"{d.group_key} · {len(d.email_ids)} emails · {d.action.upper()} ({d.confidence:.2f})"):
            st.write(d.reason)
            st.write("Sample subjects:")
            for s in d.subjects[:15]:
                st.markdown(f"- {s}")
            if d.action == "ask" or d.confidence < 0.70:
                user_action = st.selectbox(f"Action for {d.group_key}", ["archive", "trash", "keep"], key=d.group_key)
                if st.button(f"Remember decision for {d.group_key}", key=f"mem-{d.group_key}"):
                    agent.learn_from_user(d.group_key, user_action)
                    st.success(f"Saved new rule for {d.group_key} → {user_action}")
            selected.append(d)

    if st.button("Execute Bulk Cleanup"):
        gmail = st.session_state.gmail
        trash_ids = [eid for d in selected if d.action == "trash" and d.confidence >= 0.70 for eid in d.email_ids]
        archive_ids = [eid for d in selected if d.action == "archive" and d.confidence >= 0.70 for eid in d.email_ids]
        with st.spinner("Executing Gmail batch actions..."):
            if trash_ids:
                asyncio.run(gmail.batch_modify(trash_ids, add_labels=["TRASH"]))
            if archive_ids:
                asyncio.run(gmail.batch_modify(archive_ids, remove_labels=["UNREAD", "INBOX"]))
        st.success(f"Done. Trashed {len(trash_ids)} and archived {len(archive_ids)} emails.")

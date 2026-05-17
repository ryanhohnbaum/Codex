# Autonomous AI Inbox Agent

Local Streamlit application that acts as an autonomous Gmail triage agent with persistent memory.

## Features
- First-run onboarding interview that writes baseline rules to `rules_memory.json`.
- Async Gmail scan (`asyncio`) for up to 1,000 unread messages.
- Batch grouping by sender domain and LLM-powered decisioning.
- Human-in-the-loop edge-case prompts that continuously update memory.
- Bulk Gmail execution with `batchModify` in chunks of 500.

## Quickstart
1. Create Google OAuth credentials for Gmail API and save as `credentials.json` in project root.
2. Create `.env` file:
   ```
   OPENAI_API_KEY=your_key_here
   ```
3. Install dependencies:
   ```bash
   pip install -e .
   ```
4. Run app:
   ```bash
   streamlit run app/ui_streamlit.py
   ```

## Notes
- Token is saved to `token.json` after first Google OAuth flow.
- Rules memory is saved to `rules_memory.json` and grows as the agent learns.

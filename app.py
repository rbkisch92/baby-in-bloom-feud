            if st.button("Reset Colors to Selected Theme"):
                state["theme_overrides"] = {}
                reset_colors = THEMES.get(state.get("theme", "Classic Party"), THEMES["Classic Party"])
                state["title_color"] = reset_colors["primary"]
                state["subtitle_color"] = reset_colors["secondary"]
                state["panel_color"] = reset_colors["cream"]
                changed = True

        if state.get("background_image") and st.button("Remove Background"):
            state["background_image"] = ""
            state["background_mime"] = "image/png"
            changed = True

        if changed:
            save_state(state)
            st.rerun()

    # 4) Bring your own questions, if desired.
    with st.sidebar.expander("4. Custom Questions", expanded=False):
        st.caption("Required columns: game_type, question, answer, points. Use game_type values main or fast_money.")
        st.download_button("Download Question Template", data=question_template_csv(), file_name="survey_game_question_template.csv", mime="text/csv")
        uploaded_questions = st.file_uploader("Upload completed CSV template", type=["csv"])
        if uploaded_questions is not None and st.button("Load Uploaded Questions"):
            try:
                main_qs, fast_qs = load_questions_from_upload(uploaded_questions)
                state["questions"] = main_qs
                state["fast_money_questions"] = fast_qs
                state["google_sheet_url"] = ""
                state["questions_source"] = "uploaded CSV"
                state["current_question_index"] = 0
                state["match_question_number"] = 1
                reset_question_state(state)
                save_state(state)
                st.success(f"Loaded {len(main_qs)} main questions and {len(fast_qs)} Fast Money questions from CSV.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not load uploaded questions: {error}")
        st.divider()
        csv_url = st.text_input("Or paste a published Google Sheet CSV URL", value=state.get("google_sheet_url", ""))
        if st.button("Load Questions from URL"):
            try:
                main_qs, fast_qs = load_questions_from_csv(csv_url)
                state["questions"] = main_qs
                state["fast_money_questions"] = fast_qs
                state["google_sheet_url"] = csv_url
                state["questions_source"] = "Google Sheet URL"
                state["current_question_index"] = 0
                state["match_question_number"] = 1
                reset_question_state(state)
                save_state(state)
                st.success(f"Loaded {len(main_qs)} main questions and {len(fast_qs)} Fast Money questions from URL.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not load questions from URL: {error}")

    # 5) Review questions after choosing a theme or uploading custom questions.
    with st.sidebar.expander("5. Questions Preview", expanded=False):
        st.write(f"Main Questions: {len(state.get('questions', []))}")
        for i, item in enumerate(state.get("questions", []), start=1):
            with st.expander(f"{i}. {item.get('question', '')[:45]}"):
                for answer, points in item.get("answers", []):
                    st.write(f"• {answer} — {points}")
        st.write(f"Fast Money Questions: {len(state.get('fast_money_questions', []))}")
        for i, item in enumerate(state.get("fast_money_questions", []), start=1):
            st.caption(f"{i}. {item.get('question', '')}")

    # 6) Lock teams and run the bracket.
    with st.sidebar.expander("6. Teams + Bracket", expanded=True):
        st.write(f"Teams signed up: {len(state.get('teams', {}))}/{state.get('max_teams', 4)}")
        if not state.get("locked"):
            if st.button("Lock Teams + Build Bracket"):
                if len(state.get("teams", {})) < 2:
                    st.error("You need at least 2 teams to play.")
                else:
                    state["locked"] = True
                    selected_team_names = list(state["teams"].keys())[:int(state.get("max_teams", 4))]
                    state["matches"] = build_initial_matches(selected_team_names, int(state.get("max_teams", 4)))
                    state["current_match_index"] = 0
                    state["round_winners"] = []
                    state["match_scores"] = {}
                    state["total_scores"] = {team: 0 for team in selected_team_names}
                    state["tournament_complete"] = False
                    state["champion_team"] = ""
                    state["fast_money_started"] = False
                    state["fast_money_answers"] = {}
                    state["match_question_number"] = 1
                    reset_question_state(state)
                    set_active_match_from_index(state)
                    save_state(state)
                    st.rerun()
        else:
            if st.button("Unlock Teams"):
                state["locked"] = False
                save_state(state)
                st.rerun()

    render_bracket(state)

    if state.get("locked") and not state.get("tournament_complete"):
        render_scoreboard(state)
        render_answer_board(state)
        q_cur = current_question(state)
        st.sidebar.subheader("Reveal Answers")
        for idx, (answer, points) in enumerate(q_cur["answers"]):
            if st.sidebar.button(f"Reveal {idx + 1}: {answer} ({points})"):
                if idx not in state["revealed"]:
                    state["revealed"].append(idx)
                    state["round_bank"] += int(points)
                    state["message"] = f"{answer} is on the board!"
                    save_state(state)
                    st.rerun()
        active = [t for t in state.get("active_teams", []) if t != "BYE"]
        st.sidebar.subheader("Award / Steal")
        for team in active:
            if st.sidebar.button(f"Award Bank to {team}"):
                award_bank(state, team)
                save_state(state)
                st.rerun()
        if st.sidebar.button("1 Strike → Enable Steal"):
            state["strike"] = True
            state["steal_mode"] = True
            state["message"] = "Strike! The other team gets one chance to steal."
            save_state(state)
            st.rerun()
        st.sidebar.subheader("Match Flow")
        if st.sidebar.button("Next Question in Match"):
            advance_question_in_match(state)
            save_state(state)
            st.rerun()
        if st.sidebar.button("End Match / Auto-Advance Winner"):
            end_match_and_advance(state)
            save_state(state)
            st.rerun()
        if st.sidebar.button("Reset Current Question"):
            reset_question_state(state)
            save_state(state)
            st.rerun()

    if state.get("tournament_complete"):
        st.success(f"Tournament Champion Team: {state.get('champion_team')}")
        st.header("Fast Money Individual Championship")
        if not state.get("fast_money_started"):
            if st.button("Start Fast Money Timer"):
                state["fast_money_started"] = True
                state["fast_money_start_time"] = int(time.time())
                state["fast_money_answers"] = {}
                save_state(state)
                st.rerun()
        else:
            remaining = timer_remaining(state)
            st.metric("Fast Money Time Remaining", f"{remaining}s")
            st.progress(remaining / FAST_MONEY_SECONDS)
            if st.button("Restart Fast Money Timer"):
                state["fast_money_start_time"] = int(time.time())
                state["fast_money_answers"] = {}
                save_state(state)
                st.rerun()
        if state.get("fast_money_answers"):
            st.subheader("Leaderboard")
            leaderboard = sorted(state["fast_money_answers"].items(), key=lambda item: item[1].get("score", 0), reverse=True)
            for rank, (player_name, data) in enumerate(leaderboard, start=1):
                st.markdown(f'<div class="score-card"><strong>#{rank} {player_name}</strong><br>{data.get("score", 0)} points</div>', unsafe_allow_html=True)
                with st.expander(f"See {player_name}'s answer matches"):
                    for result in data.get("results", []):
                        st.write(f"{result.get('question')}: typed '{result.get('typed')}' → matched '{result.get('matched')}' ({result.get('similarity')}%) = {result.get('points')} pts")

    st.sidebar.divider()
    if st.sidebar.button("Reset Entire Game"):
        save_state(default_state())
        st.rerun()

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import io
import re
import requests
import sqlite3
import ast
import time
import contextlib
from streamlit_ace import st_ace

# --- INITIALIZATION ---
if 'progress' not in st.session_state:
    st.session_state.progress = {}
if 'current_chapter' not in st.session_state:
    st.session_state.current_chapter = "Welcome"
if 'current_lesson' not in st.session_state:
    st.session_state.current_lesson = "Overview"
if 'show_editor' not in st.session_state:
    st.session_state.show_editor = False
if 'editor_cells' not in st.session_state:
    st.session_state.editor_cells = [{"id": time.time(), "input": "", "output": "", "exec_time": 0.0, "status": None}]
if 'exec_globals' not in st.session_state:
    # Pre-import common libraries for the editor
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    st.session_state.exec_globals = {
        'np': np,
        'pd': pd,
        'plt': plt,
        'sns': sns,
        're': re,
        'sqlite3': sqlite3,
        'time': time,
        'input': lambda prompt="": (_ for _ in ()).throw(RuntimeError(f"Interactive input('{prompt}') is not supported in this editor.\nPlease hardcode your values for testing (e.g., x = 10)."))
    }

# Page Config
st.set_page_config(page_title="E-Learning", page_icon="🎓", layout="wide")

# Load CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Custom Code Editor Style
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{
        width: 380px !important;
        min-width: 380px !important;
    }}
    .floating-code-btn {{
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        background-color: #5cb9ff;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    .floating-code-btn:hover {{
        background-color: #4da8ee;
    }}
    [data-testid="stSidebarUserContent"] {{
        padding-top: 20px !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
    }}
    /* Wrap long code/output lines in sidebar */
    [data-testid="stSidebar"] code {{
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }}
    /* Centered action buttons like Jupyter */
    .stButton>button[key^="add_after"] {{
        border-radius: 5px !important;
        padding: 0px 10px !important;
        font-size: 0.7rem !important;
        background-color: #262730 !important;
        border: 1px solid #464b5d !important;
    }}
    /* --- CLEAN INTERFACE & THEME UNIFICATION --- */
    /* Target all buttons for a unified dark theme */
    .stButton > button, .stFormSubmitButton > button, button[kind="secondary"], button[kind="primary"] {{
        border-radius: 4px !important;
        white-space: nowrap !important;
        width: auto !important;
        min-width: max-content !important;
        padding: 4px 12px !important;
        font-size: 0.82rem !important;
        height: 32px !important;
        line-height: normal !important;
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover, button:hover {{
        background-color: #334155 !important;
        border-color: #5cb9ff !important;
        color: #5cb9ff !important;
    }}
    /* Style the form container to remove the thick white border */
    [data-testid="stForm"], div[data-testid="stForm"] {{
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        padding: 15px !important;
        background-color: #0f172a !important;
    }}
    /* Themed Sidebar Selectbox */
    div[data-testid="stSelectbox"] > div > div {{
        background-color: #1e293b !important;
        color: white !important;
        border: 1px solid #334155 !important;
    }}
    /* Hide any ghost buttons from Ace that might peek through */
    div.stAce button, div[data-testid="stAce"] button {{
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }}
    /* Final polish for code editor borders */
    .ace_editor {{
        border: 1px solid #334155 !important;
        border-radius: 4px !important;
    }}
    /* UNIFY PROGRESS BAR */
    .stProgress > div > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
    }}
    .stProgress > div > div > div > div {{
        background-color: #5cb9ff !important;
    }}
    /* REMOVE TOP DECORATION WHITE LINE */
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0) !important;
    }}
    div[data-testid="stDecoration"] {{
        display: none !important;
    }}
    /* FIX THE THICK WHITE CELL BORDER */
    div[data-testid="stAce"] {{
        background-color: transparent !important;
        padding: 0 !important;
        border: none !important;
    }}
    div.stAce > div {{
        border: 1px solid #334155 !important;
        background-color: transparent !important;
    }}
    /* Dark scrollbar for the sidebar */
    [data-testid="stSidebar"] ::-webkit-scrollbar {{
        width: 6px;
    }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-thumb {{
        background: #334155;
        border-radius: 10px;
    }}
    [data-testid="stSidebar"] ::-webkit-scrollbar-track {{
        background: transparent;
    }}
</style>
""", unsafe_allow_html=True)

# --- UTILS ---
def mark_completed(chapter, lesson, exercise):
    key = f"{chapter}_{lesson}_{exercise}"
    st.session_state.progress[key] = True

def is_completed(chapter, lesson, exercise):
    return st.session_state.progress.get(f"{chapter}_{lesson}_{exercise}", False)

def lesson_summary(title, time, points):
    st.markdown(f"""
    <div class="lesson-card">
        <h3>📖 Lesson: {title}</h3>
        <p style="color: #94a3b8; font-style: italic;">Estimated time: {time}</p>
        <ul style="margin-top: 10px;">
            {''.join([f'<li>{p}</li>' for p in points])}
        </ul>
    </div>
    """, unsafe_allow_html=True)

def exercise_container(name, difficulty, scenario, instruction):
    badge_class = "badge-beginner" if difficulty == "beginner" else "badge-intermediate"
    st.markdown(f"""
    <div class="exercise-box">
        <div class="exercise-header">
            <span class="badge {badge_class}">{difficulty}</span>
            <span>🧩 {name}</span>
        </div>
        <p><b>Scenario:</b> {scenario}</p>
        <p style="color: #cbd5e1; font-size: 0.95rem;"><i>Instruction: {instruction}</i></p>
    </div>
    """, unsafe_allow_html=True)

def render_code_editor():
    st.markdown("#### 💻 Code Editor")
    
    if not st.session_state.editor_cells:
        st.session_state.editor_cells = [{"id": time.time(), "input": "", "output": "", "exec_time": 0.0, "status": None}]

    for i, cell in enumerate(st.session_state.editor_cells):
        cell_id = cell.get("id", i) # Fallback to i for safety
        # --- 1. GLOBAL TOOLBAR (ONLY ABOVE CELL 1) ---
        if i == 0:
            col_g1, col_g2, col_g3, col_g4 = st.columns([1.1, 1.5, 1, 1.2], gap="small")
            with col_g1:
                if st.button("➕Cell", key="global_add"):
                    st.session_state.editor_cells.append({"id": time.time(), "input": "", "output": "", "exec_time": 0.0, "status": None})
                    st.rerun()
            
            with col_g2:
                if st.button(" ▶️All Cells", key="global_run_all"):
                    # Execute EVERY cell in sequence
                    for idx, c in enumerate(st.session_state.editor_cells):
                        code = c.get("input", "").strip()
                        if not code: continue
                        
                        output_capture = io.StringIO()
                        start_time = time.time()
                        try:
                            with contextlib.redirect_stdout(output_capture):
                                exec(code, st.session_state.exec_globals)
                            
                            exec_time = time.time() - start_time
                            output = output_capture.getvalue()
                            if not output:
                                try:
                                    res = eval(code.split('\n')[-1], st.session_state.exec_globals)
                                    if res is not None: output = str(res)
                                except: pass
                            
                            st.session_state.editor_cells[idx]["output"] = output
                            st.session_state.editor_cells[idx]["exec_time"] = exec_time
                            st.session_state.editor_cells[idx]["status"] = "success"
                        except Exception:
                            import traceback
                            st.session_state.editor_cells[idx]["output"] = traceback.format_exc(), "error"
                    st.rerun()

            with col_g2 if False else col_g3: # logic for placement
                if st.button("🧹 All", key="global_clear"):
                    for c in st.session_state.editor_cells:
                        c["output"], c["status"] = "", None
                        c["exec_time"] = 0.0
                    st.rerun()
            with col_g4:
                if st.button("Reset", key="global_reset"):
                    st.session_state.editor_cells = [{"id": time.time(), "input": "", "output": "", "exec_time": 0.0, "status": None}]
                    st.rerun()
            st.markdown("---")

        # --- 2. CELL HEADER (In [ ] and individual Delete) ---
        hdr1, hdr2 = st.columns([5, 1])
        with hdr1:
            st.markdown(f"<p style='color: #5cb9ff; font-family: monospace; font-size: 0.8rem; margin: 0;'>In [{i+1 if cell.get('status') else ' '}]</p>", unsafe_allow_html=True)
        with hdr2:
            if len(st.session_state.editor_cells) > 1:
                if st.button("🗑️", key=f"del_cell_{cell_id}"):
                    st.session_state.editor_cells.pop(i)
                    st.rerun()

        # --- 3. CODE EDITOR (Inside a Form to kill Red Button & Typing Refreshes) ---
        input_text = cell.get("input", "")
        line_count = input_text.count('\n') + 1
        # Allow growth up to 2000px, min 100px
        dynamic_height = max(100, min(2000, line_count * 24 + 40))
        
        with st.form(key=f"cell_form_{cell_id}", clear_on_submit=False):
            # auto_update=True hides the red button
            # st.form blocks the typing-reruns
            cell_input = st_ace(
                value=input_text,
                placeholder="Write code here...",
                language="python",
                theme="monokai",
                key=f"ace_editor_stable_{cell_id}",
                height=dynamic_height,
                font_size=14,
                wrap=False,
                auto_update=True
            )
            
            # --- 4. BUTTONS (Inside the Form) ---
            # Using columns to put Run on left and Clear on far right
            b_col1, b_spacer, b_col2 = st.columns([1, 2, 1.5], gap="small")
            with b_col1:
                run_clicked = st.form_submit_button("▶️ Run")
            with b_col2:
                clear_clicked = st.form_submit_button("🧹 Clear")

        # --- 3. ACTION LOGIC ---
        if run_clicked:
            st.session_state.editor_cells[i]["input"] = cell_input
            output_capture = io.StringIO()
            start_time = time.time()
            try:
                with contextlib.redirect_stdout(output_capture):
                    exec(cell_input, st.session_state.exec_globals)
                exec_time = time.time() - start_time
                output = output_capture.getvalue()
                if not output:
                    try:
                        res = eval(cell_input.strip().split('\n')[-1], st.session_state.exec_globals)
                        if res is not None: output = str(res)
                    except: pass
                st.session_state.editor_cells[i]["output"], st.session_state.editor_cells[i]["exec_time"], st.session_state.editor_cells[i]["status"] = output, exec_time, "success"
            except Exception:
                import traceback
                st.session_state.editor_cells[i]["output"], st.session_state.editor_cells[i]["status"] = traceback.format_exc(), "error"
            st.rerun()
            
        elif clear_clicked:
            st.session_state.editor_cells[i]["input"] = cell_input
            st.session_state.editor_cells[i]["output"] = ""
            st.session_state.editor_cells[i]["status"] = None
            st.session_state.editor_cells[i]["exec_time"] = 0.0
            st.rerun()
            
        # Display Output
        if cell.get("output"):
            if cell.get("status") == "success":
                st.markdown(f"✅ <span style='color: #10b981; font-size: 0.8rem;'>{cell.get('exec_time', 0):.2f}s</span>", unsafe_allow_html=True)
                st.code(cell["output"])
            elif cell.get("status") == "error":
                st.error(cell.get("output", "Unknown error"))
        
        st.markdown("<hr style='margin: 15px 0; border: 0; border-top: 1px solid #333;'>", unsafe_allow_html=True)


# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("<h3 style='margin-bottom: 0;'>📊 Master APDV Module</h3>", unsafe_allow_html=True)
    
    # Toggle and Progress together
    col_toggle, col_prog = st.columns([1, 1])
    with col_toggle:
        btn_label = "❌ Close Code" if st.session_state.show_editor else "💻 Show Code"
        if st.button(btn_label, key="toggle_code_sidebar"):
            st.session_state.show_editor = not st.session_state.show_editor
            st.rerun()
    
    with col_prog:
        total_exercises = 25 
        completed_exercises = len(st.session_state.progress)
        progress_percentage = completed_exercises / total_exercises
        st.progress(progress_percentage)
        st.caption(f"Progress: {int(progress_percentage*100)}%")
    
    chapters = {
        "Welcome": ["Overview"],
        "CH 1: Python Foundations": ["Deep Dive"],
        "CH 2: Data Ingestion (ETL)": ["Deep Dive"],
        "CH 3: Data Cleaning": ["Deep Dive"],
        "CH 4: SQL Management": ["Deep Dive"],
        "CH 5: Visual Insights": ["Deep Dive"],
        "CH 6: CA Practice Lab": ["Deep Dive"],
        "Final Project": ["Retail Pipeline"]
    }
    
    ch_options = list(chapters.keys())
    try:
        curr_idx = ch_options.index(st.session_state.current_chapter)
    except:
        curr_idx = 0
        
    ch_selected = st.selectbox("Select Chapter", ch_options, index=curr_idx, label_visibility="collapsed")
    st.session_state.current_chapter = ch_selected
    
    st.markdown("---")
    
    # Code Editor in Sidebar
    if st.session_state.show_editor:
        render_code_editor()
    else:
        st.info("💡 Click 'Show Code'   to open the editor here!")

# --- MAIN LAYOUT ---
main_col = st.container()

def app_content():
    # --- CHAPTER: WELCOME ---
    if st.session_state.current_chapter == "Welcome":
        st.markdown("<h1>Analytics Programming Mastery</h1>", unsafe_allow_html=True)
        st.write("### The most structured way to learn Data Engineering & Visualization.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            <div class="lesson-card">
                <h3>How to use this course:</h3>
                <ol>
                    <li><b>Learn</b>: Read the high-level theory for each sub-topic.</li>
                    <li><b>Solve</b>: Complete the micro-quiz immediately after reading.</li>
                    <li><b>Progress</b>: Use the slider at the top of each chapter to move through topics.</li>
                    <li><b>Task</b>: Every chapter ends with a coding challenge that tests everything you've learned.</li>
                    <li><b>CA Lab</b>: A dedicated section for Continuous Assessment (CA) practice with real past exam logic.</li>
                </ol>
                <p style="color: #ffcc00; font-weight: bold;">Select "CH 1: Python Foundations" in the sidebar to begin!</p>
            </div>
            """, unsafe_allow_html=True)
    
    # --- CHAPTER 1: FOUNDATIONS ---
    elif st.session_state.current_chapter == "CH 1: Python Foundations":
        st.markdown("<h1>Chapter 1: Python Foundations</h1>", unsafe_allow_html=True)
        
        # Internal Chapter Navigation (Step-by-Step)
        ch1_steps = ["1.1 Scalar Types", "1.2 Operators & Logic", "1.3 String Mastery", "1.4 Collections", "🏆 Chapter 1 Challenge"]
        step = st.select_slider("Chapter Progress", options=ch1_steps, value=st.session_state.get('ch1_step', "1.1 Scalar Types"))
        st.session_state.ch1_step = step
    
        if step == "1.1 Scalar Types":
            st.markdown("### 🧬 1.1 Understanding Scalar Types")
            st.write("""
            In Python, **Scalars** are the most basic units of data. Think of them as the "atoms" of your code. 
            Before you can analyze sales trends or customer behavior, you must understand exactly how Python stores this information.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                #### The Four Core Pillars:
                1. **Integers (`int`)**: Whole numbers. Used for counting (e.g., `num_customers = 50`).
                2. **Floats (`float`)**: Decimal numbers. Used for precision (e.g., `conversion_rate = 0.087`).
                3. **Strings (`str`)**: Text. Always wrapped in quotes (e.g., `name = "Alice"`).
                4. **Booleans (`bool`)**: Logical switches. Either `True` or `False`.
                """)
            
            with col2:
                st.markdown("""
                #### 💡 Pro Tip: Coercion
                Sometimes data arrives in the wrong format (like a number inside a string). 
                We use **Coercion** to fix this:
                - `int("100")` → `100`
                - `str(42)` → `"42"`
                - `float("19.99")` → `19.99`
                """)
    
            st.info("⚠️ **The Boolean Quirk**: In Python, almost anything has a boolean value. `bool(\"False\")` is actually **True** because the string is not empty!")
    
            # QUIZ 1.1
            st.markdown("---")
            exercise_container(
                "Quick Check: Coercion", 
                "beginner", 
                "You are importing a CSV where the 'price' column is loaded as text: `'1250.50'`.",
                "Write the function call to convert this string into a number that supports decimals."
            )
            q1_1 = st.text_input("code: corrected_price = ____('1250.50')", key="q1_1")
            if q1_1.strip().lower() == "float":
                st.success("Correct! `float` is the right choice for decimal values.")
                mark_completed("CH1", "1.1", "quiz")
                if st.button("Move to Next Topic →"):
                    st.session_state.ch1_step = "1.2 Operators & Logic"
                    st.rerun()
    
        elif step == "1.2 Operators & Logic":
            st.markdown("### 🧮 1.2 Operators & Logical Flow")
            st.write("""
            Operators allow you to perform calculations and make comparisons. In Data Analytics, 
            you'll use these to filter datasets (e.g., "Find all sales > $500").
            """)
            
            st.markdown("""
            | Operator | Description | Example |
            | :--- | :--- | :--- |
            | `+`, `-`, `*`, `/` | Basic Math | `total = price * qty` |
            | `//` | Floor Division | `20 // 3` gives `6` |
            | `%` | Modulo (Remainder) | `20 % 3` gives `2` |
            | `==`, `!=` | Equality check | `status == "shipped"` |
            | `>`, `<` | Comparison | `age >= 18` |
            """)
    
            st.markdown("#### Logical Gates: `and`, `or`, `not` ")
            st.write("Use these to combine multiple conditions. For a customer to get a discount, they might need to be (Age > 65) **or** (Member == True).")
    
            # QUIZ 1.2
            st.markdown("---")
            exercise_container(
                "The Discount Logic", 
                "beginner", 
                "You are writing a script for a loyalty program. A user gets a reward if their `points` are over 1000 AND they are an `active` member.",
                "Choose the correct logical operator to combine these conditions."
            )
            q1_2 = st.radio("Selection:", ["and", "or", "not"], key="q1_2", index=None)
            if q1_2 == "and":
                st.success("Correct! Both conditions must be True.")
                mark_completed("CH1", "1.2", "quiz")
                if st.button("Next: String Mastery →"):
                    st.session_state.ch1_step = "1.3 String Mastery"
                    st.rerun()
    
        elif step == "1.3 String Mastery":
            st.markdown("### ✍️ 1.3 String Manipulation")
            st.write("""
            Data is often "noisy." Customer names might have extra spaces, or emails might be in all caps. 
            Python's string methods are your first line of defense in data cleaning.
            """)
            
            st.markdown("""
            #### Key String Methods:
            - `.strip()`: Removes leading/trailing whitespace.
            - `.lower()` / `.upper()`: Standardizes case.
            - `.replace("old", "new")`: Swaps text.
            - `.split(",")`: Turns a string into a list (great for CSV lines).
            - **f-strings**: `f"Hello {name}"` is the cleanest way to insert variables into text.
            """)
    
            # INDEXING & SLICING
            st.code("""
    text = "PYTHON"
    # Indexing starts at 0
    print(text[0]) # 'P'
    # Slicing [start:end_exclusive]
    print(text[0:2]) # 'PY'
            """)
    
            # QUIZ 1.3
            st.markdown("---")
            exercise_container(
                "Cleaning Customer Names", 
                "beginner", 
                "A user entered their name as `'  JOHN SMITH  '`. You need to remove the spaces and make it `'John Smith'`.",
                "Which two methods would you chain together? (e.g. name.method1().method2())"
            )
            q1_3 = st.text_input("code: clean_name = raw_name.____().title()", key="q1_3")
            if q1_3.strip().lower() == "strip":
                st.success("Perfect! `.strip()` removes the spaces, and `.title()` capitalizes the first letters.")
                mark_completed("CH1", "1.3", "quiz")
                if st.button("Next: Collections →"):
                    st.session_state.ch1_step = "1.4 Collections"
                    st.rerun()
    
        elif step == "1.4 Collections":
            st.markdown("### 📚 1.4 Collections: Lists & Dictionaries")
            st.write("""
            In Analytics, we rarely work with one number at a time. We work with **collections** of data.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Lists (`[]`)")
                st.write("An ordered sequence. Good for column data or time-series.")
                st.code("""
    sales = [100, 250, 300]
    sales.append(400) # Add
    sales[0] # Access 1st
                """)
            with col2:
                st.markdown("#### Dictionaries (`{}` )")
                st.write("Key-value pairs. Perfect for structured records.")
                st.code("""
    user = {"name": "Alice", "id": 1}
    print(user["name"]) # "Alice"
                """)
    
            # QUIZ 1.4
            st.markdown("---")
            exercise_container(
                "Accessing the Data", 
                "intermediate", 
                "You have a nested dictionary: `data = {'users': [{'name': 'Bob'}]}`.",
                "How would you access the name 'Bob'?"
            )
            q1_4 = st.text_input("code: target = data['users'][0][____]", key="q1_4")
            if q1_4.strip() in ["'name'", '"name"']:
                st.success("Excellent! You navigated the list inside the dictionary.")
                mark_completed("CH1", "1.4", "quiz")
                if st.button("Final Chapter Challenge! →"):
                    st.session_state.ch1_step = "🏆 Chapter 1 Challenge"
                    st.rerun()
    
        elif step == "🏆 Chapter 1 Challenge":
            st.markdown("### 🏆 Chapter 1 Final Task")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>The Scenario:</b> You are a Junior Data Engineer. You've been given a messy string containing a customer's record:
            <code>"  ID:001 | NAME:ALICE | SPENT:150.50  "</code><br><br>
            
            <b>Your Task:</b> Write a script that:
            1. Removes the extra spaces from the string.
            2. Splits the string by the <code>|</code> character.
            3. Extracts the 'SPENT' value and converts it to a <b>float</b>.
            4. Calculates a 10% tax on that value.
            </div>
            """, unsafe_allow_html=True)
            
            raw_data = "  ID:001 | NAME:ALICE | SPENT:150.50  "
            
            col1, col2 = st.columns(2)
            with col1:
                st.code(f"data = \"{raw_data}\"")
                user_code = st.text_area("Write your solution (Python):", height=200, placeholder="clean_data = ...\nparts = ...\nspent = ...\ntax = ...")
            
            with col2:
                if st.button("Submit Project"):
                    # Basic validation logic (looking for keywords)
                    if ".strip()" in user_code and ".split('|')" in user_code and "float" in user_code:
                        st.success("🎊 AMAZING! You've combined everything from Chapter 1.")
                        st.balloons()
                        mark_completed("CH1", "TASK", "final")
                    else:
                        st.error("Not quite. Remember to use `.strip()`, `.split('|')`, and `float()`.")
    
    # --- CHAPTER 2: DATA INGESTION (ETL) ---
    elif st.session_state.current_chapter == "CH 2: Data Ingestion (ETL)":
        st.markdown("<h1>Chapter 2: Data Ingestion (ETL)</h1>", unsafe_allow_html=True)
        
        ch2_steps = ["2.1 pandas I/O", "2.2 API Connection", "🏆 Chapter 2 Challenge"]
        step = st.select_slider("Chapter Progress", options=ch2_steps, value=st.session_state.get('ch2_step', "2.1 pandas I/O"))
        st.session_state.ch2_step = step
    
        if step == "2.1 pandas I/O":
            st.markdown("### 📊 2.1 The Gateway to pandas")
            st.write("""
            `pandas` is the standard library for data engineering in Python. It allows you to transform raw files 
            (like CSV or Excel) into high-performance **DataFrames**.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                #### Core Ingestion Functions:
                - `pd.read_csv("file.csv")`: The bread and butter of data loading.
                - `pd.read_json("file.json")`: For structured web data.
                - `pd.read_excel("file.xlsx")`: For business reports.
                """)
            with col2:
                st.markdown("""
                #### First Inspection Tools:
                - `df.head()`: See top rows.
                - `df.info()`: Check data types and nulls.
                - `df.describe()`: Get statistical snapshots.
                """)
    
            st.code("""
    import pandas as pd
    df = pd.read_csv("sales.csv", index_col=0)
    print(df.info())
            """)
    
            # QUIZ 2.1
            st.markdown("---")
            exercise_container(
                "The Structural Audit", 
                "beginner", 
                "You've loaded a file and notice some columns have missing values. You need to see which columns are mostly empty.",
                "Which method provides the count of non-null values for every column?"
            )
            q2_1 = st.radio("Selection:", ["df.head()", "df.info()", "df.describe()"], key="q2_1", index=None)
            if q2_1 == "df.info()":
                st.success("Correct! `info()` reveals the 'Non-Null Count' for each column.")
                mark_completed("CH2", "2.1", "quiz")
                if st.button("Next: API Connection →"):
                    st.session_state.ch2_step = "2.2 API Connection"
                    st.rerun()
    
        elif step == "2.2 API Connection":
            st.markdown("### 🌐 2.2 Fetching Live Data (APIs)")
            st.write("""
            APIs allow you to request data directly from a server. This is how you get live stock prices, 
            weather updates, or social media trends.
            """)
            
            st.markdown("""
            #### The requests workflow:
            1. **GET**: Ask the server for data via a URL.
            2. **Status**: Check if the code is `200` (OK).
            3. **JSON**: Convert the response to a Python-usable format with `.json()`.
            """)
            
            st.info("💡 **Common Status Codes:**\n- `200`: Success\n- `401`: Access Denied (Bad API Key)\n- `404`: Not Found\n- `500`: Server Error")
    
            # QUIZ 2.2
            st.markdown("---")
            exercise_container(
                "The API Diagnostic", 
                "beginner", 
                "Your weather script failed. The status code returned is 404.",
                "What does a 404 error usually mean?"
            )
            q2_2 = st.radio("Selection:", ["Success", "Authentication Link Broken", "The resource/URL does not exist"], key="q2_2", index=None)
            if q2_2 == "The resource/URL does not exist":
                st.success("Correct! 404 is 'Not Found'.")
                mark_completed("CH2", "2.2", "quiz")
                if st.button("Final Chapter Challenge! →"):
                    st.session_state.ch2_step = "🏆 Chapter 2 Challenge"
                    st.rerun()
    
        elif step == "🏆 Chapter 2 Challenge":
            st.markdown("### 🏆 Chapter 2 Final Task")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>The Scenario:</b> You are building an ETL pipeline. You need to load a CSV and get a statistical summary.<br><br>
            
            <b>Your Task:</b> Write the code to:
            1. Import pandas.
            2. Load <code>"retail_sales.csv"</code> as a DataFrame called <code>sales_df</code>.
            3. Print the statistical summary (mean, max, min, etc.) of the DataFrame.
            </div>
            """, unsafe_allow_html=True)
            
            user_code_2 = st.text_area("Write your solution (Python):", height=200, key="task2", placeholder="import ...\nsales_df = ...\n...")
            
            if st.button("Submit Project"):
                if "import pandas" in user_code_2 and "read_csv" in user_code_2 and "describe()" in user_code_2:
                    st.success("🎉 HEROIC! You've mastered Data Ingestion.")
                    st.balloons()
                    mark_completed("CH2", "TASK", "final")
                else:
                    st.error("Check your code! Did you use `read_csv` and `describe()`?")
    
    # --- CHAPTER 3: DATA CLEANING ---
    elif st.session_state.current_chapter == "CH 3: Data Cleaning":
        st.markdown("<h1>Chapter 3: Data Cleaning & Extraction</h1>", unsafe_allow_html=True)
        
        ch3_steps = ["3.1 Regex Mastery", "3.2 Web Scraping", "🏆 Chapter 3 Challenge"]
        step = st.select_slider("Chapter Progress", options=ch3_steps, value=st.session_state.get('ch3_step', "3.1 Regex Mastery"))
        st.session_state.ch3_step = step
    
        if step == "3.1 Regex Mastery":
            st.markdown("### 🔍 3.1 Regex for Data Cleaning")
            st.write("""
            **Regular Expressions** (Regex) are patterns used to match character combinations in strings. 
            In data analysis, they are indispensable for extracting information from messy text.
            """)
            
            st.markdown("""
            #### Common Regex Symbols:
            - `\d`: Matches any digit (0-9).
            - `\w`: Matches any alphanumeric character.
            - `\s`: Matches any whitespace (spaces, tabs).
            - `+`: Matches 1 or more of the preceding character.
            - `*`: Matches 0 or more of the preceding character.
            - `.` : Matches any character except newline.
            """)
    
            st.code("""
    import re
    text = "Contact us at 555-1234"
    # Extract phone
    pattern = r"\d{3}-\d{4}"
    print(re.findall(pattern, text))
            """)
    
            # QUIZ 3.1
            st.markdown("---")
            exercise_container(
                "The Digit Hunter", 
                "intermediate", 
                "You have a string of mixed data: `'User_ID_9921_Logged'`. You want to extract only the digits.",
                "Choose the correct regex pattern to find all sequences of digits."
            )
            q3_1 = st.radio("Selection:", [r"\w+", r"\d+", r"\s+"], key="q3_1", index=None)
            if q3_1 == r"\d+":
                st.success("Correct! `\d+` matches one or more consecutive digits.")
                mark_completed("CH3", "3.1", "quiz")
                if st.button("Next: Web Scraping →"):
                    st.session_state.ch3_step = "3.2 Web Scraping"
                    st.rerun()
    
        elif step == "3.2 Web Scraping":
            st.markdown("### 🕸️ 3.2 Web Scraping with BeautifulSoup")
            st.write("""
            Web scraping is the automated process of extracting data from websites. 
            `BeautifulSoup` is the go-to library for parsing HTML.
            """)
            
            st.markdown("""
            #### The Scraping Flow:
            1. Fetch HTML using `requests`.
            2. Create a "Soup" object: `soup = BeautifulSoup(html, 'html.parser')`.
            3. Find elements using `.find()` or `.find_all()`.
            """)
            
            st.warning("⚖️ **Ethics**: Always check a site's `robots.txt` before scraping. Don't spam the server with requests!")
    
            # QUIZ 3.2
            st.markdown("---")
            exercise_container(
                "The Class Identifier", 
                "beginner", 
                "You are trying to find a `div` tag that has a CSS class called 'price-tag'.",
                "How do you specify the class in the `.find()` method?"
            )
            q3_2 = st.radio("Selection:", ["class='price-tag'", "class_='price-tag'", "id='price-tag'"], key="q3_2", index=None)
            if q3_2 == "class_='price-tag'":
                st.success("Exactly! We use `class_` because `class` is a reserved word in Python.")
                mark_completed("CH3", "3.2", "quiz")
                if st.button("Final Chapter Challenge! →"):
                    st.session_state.ch3_step = "🏆 Chapter 3 Challenge"
                    st.rerun()
    
        elif step == "🏆 Chapter 3 Challenge":
            st.markdown("### 🏆 Chapter 3 Final Task")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>The Scenario:</b> You have scraped a product description: <code>"The UltraBook 5000 is on sale for $1,299.99 today!"</code>.<br><br>
            
            <b>Your Task:</b> Code a regex pattern to extract the price.
            1. Use <code>re.findall()</code>.
            2. Pattern should look for the dollar sign and digits.
            </div>
            """, unsafe_allow_html=True)
            
            user_code_3 = st.text_area("Write your solution (Python):", height=200, key="task3")
            
            if st.button("Submit Project"):
                if "re.findall" in user_code_3 and "\\$" in user_code_3 and "\\d" in user_code_3:
                    st.success("🎉 SPOT ON! Your cleaning skills are top-tier.")
                    st.balloons()
                    mark_completed("CH3", "TASK", "final")
                else:
                    st.error("Try again! Make sure to escape the dollar sign using `\\$` in your pattern.")
    
    # --- CHAPTER 4: SQL MANAGEMENT ---
    elif st.session_state.current_chapter == "CH 4: SQL Management":
        st.markdown("<h1>Chapter 4: SQL Management</h1>", unsafe_allow_html=True)
        
        ch4_steps = ["4.1 SQL Basics", "4.2 Joins & Keys", "🏆 Chapter 4 Challenge"]
        step = st.select_slider("Chapter Progress", options=ch4_steps, value=st.session_state.get('ch4_step', "4.1 SQL Basics"))
        st.session_state.ch4_step = step
    
        if step == "4.1 SQL Basics":
            st.markdown("### 🗄️ 4.1 Introduction to SQL")
            st.write("""
            SQL (Structured Query Language) is used to communicate with databases. Unlike Python, 
            which focuses on *how* to do something, SQL focuses on *what* data you want.
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                #### Primary Keywords:
                - `SELECT`: Choose your columns.
                - `FROM`: Choose your table.
                - `WHERE`: Filter your rows.
                - `ORDER BY`: Sort your results.
                """)
            with col2:
                st.markdown("""
                #### Examples:
                `SELECT * FROM users;`  
                `SELECT name FROM sales WHERE revenue > 1000;`
                """)
    
            # QUIZ 4.1
            st.markdown("---")
            exercise_container(
                "Filtering the Database", 
                "beginner", 
                "You need to find all orders where the amount is less than $50.",
                "Choose the correct SQL clause to apply this filter."
            )
            q4_1 = st.radio("Selection:", ["LIMIT 50", "WHERE amount < 50", "ORDER BY 50"], key="q4_1", index=None)
            if q4_1 == "WHERE amount < 50":
                st.success("Correct! `WHERE` is the universal filter in SQL.")
                mark_completed("CH4", "4.1", "quiz")
                if st.button("Next: Joins & Keys →"):
                    st.session_state.ch4_step = "4.2 Joins & Keys"
                    st.rerun()
    
        elif step == "4.2 Joins & Keys":
            st.markdown("### 🔗 4.2 Relationships & Joins")
            st.write("""
            Relational databases work by splitting data into multiple tables and linking them using **Keys**.
            """)
            
            st.markdown("""
            - **Primary Key**: A unique ID for every row in a table.
            - **Foreign Key**: A reference in one table to a Primary Key in another.
            - **JOIN**: Combining tables using these keys.
            """)
    
            st.code("""
    SELECT orders.id, customers.name 
    FROM orders
    JOIN customers ON orders.customer_id = customers.id;
            """)
    
            # QUIZ 4.2
            st.markdown("---")
            exercise_container(
                "Connecting Tables", 
                "intermediate", 
                "You have a 'Products' table and an 'Orders' table. Both share a 'product_id' column.",
                "Which SQL keyword is used to merge these two tables together?"
            )
            q4_2 = st.text_input("code: SELECT * FROM Products ____ Orders ON ...", key="q4_2")
            if q4_2.strip().upper() == "JOIN":
                st.success("Correct! `JOIN` is how we combine relational data.")
                mark_completed("CH4", "4.2", "quiz")
                if st.button("Final Chapter Challenge! →"):
                    st.session_state.ch4_step = "🏆 Chapter 4 Challenge"
                    st.rerun()
    
        elif step == "🏆 Chapter 4 Challenge":
            st.markdown("### 🏆 Chapter 4 Final Task")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>The Scenario:</b> You are analyzing a retail database. You need all customer names from the 'Customers' 
            table who live in 'London'.<br><br>
            
            <b>Your Task:</b> Write the SQL query.
            </div>
            """, unsafe_allow_html=True)
            
            user_sql = st.text_area("Write your SQL query:", height=100)
            if st.button("Submit Query"):
                if "SELECT" in user_sql.upper() and "FROM Customers" in user_sql and "WHERE city = 'London'" in user_sql:
                    st.success("🎉 DATABASE MASTER! You've conquered SQL.")
                    st.balloons()
                    mark_completed("CH4", "TASK", "final")
                else:
                    st.error("Check your syntax! Did you use SELECT, FROM, and WHERE?")
    
    # --- CHAPTER 5: VISUAL INSIGHTS ---
    elif st.session_state.current_chapter == "CH 5: Visual Insights":
        st.markdown("<h1>Chapter 5: Data Visualization</h1>", unsafe_allow_html=True)
        
        ch5_steps = ["5.1 Plot Selection", "5.2 Seaborn Styling", "🏆 Chapter 5 Challenge"]
        step = st.select_slider("Chapter Progress", options=ch5_steps, value=st.session_state.get('ch5_step', "5.1 Plot Selection"))
        st.session_state.ch5_step = step
    
        if step == "5.1 Plot Selection":
            st.markdown("### 📊 5.1 Choosing the Right Chart")
            st.write("""
            Visualization is about choosing the right medium for your message.
            """)
            
            st.markdown("""
            | Data Insight | Best Chart |
            | :--- | :--- |
            | Comparison (e.g. Sales by Dept) | **Bar Chart** |
            | Trends over Time (e.g. Stock Price) | **Line Plot** |
            | Distribution (e.g. Income spreads) | **Histogram** |
            | Relationships (e.g. Price vs. Sales) | **Scatter Plot** |
            """)
    
            # QUIZ 5.1
            st.markdown("---")
            exercise_container(
                "The Trend Tracker", 
                "beginner", 
                "You want to show how 'Daily Users' changed over a 12-month period.",
                "Which chart is most effective for showing this time-series trend?"
            )
            q5_1 = st.radio("Selection:", ["Bar Chart", "Line Plot", "Pie Chart"], key="q5_1", index=None)
            if q5_1 == "Line Plot":
                st.success("Correct! Line plots emphasize the flow and change of data over time.")
                mark_completed("CH5", "5.1", "quiz")
                if st.button("Next: Seaborn Styling →"):
                    st.session_state.ch5_step = "5.2 Seaborn Styling"
                    st.rerun()
    
        elif step == "5.2 Seaborn Styling":
            st.markdown("### 🎨 5.2 Aesthetics & Clarity")
            st.write("""
            Raw charts are hard to read. A professional analyst adds labels, titles, and clean themes.
            """)
            
            st.code("""
    import seaborn as sns
    import matplotlib.pyplot as plt
    
    sns.set_theme(style="whitegrid")
    sns.barplot(x="region", y="sales", data=df)
    plt.title("Regional Sales Distribution")
    plt.xlabel("Region")
    plt.ylabel("Sales ($)")
            """)
    
            # QUIZ 5.2
            st.markdown("---")
            exercise_container(
                "The Labeling Standard", 
                "beginner", 
                "You've created a plot, but the audience doesn't know what the Y-axis represents.",
                "Which matplotlib function would you use to add a label to the Y-axis?"
            )
            q5_2 = st.text_input("code: plt.____('Revenue In USD')", key="q5_2")
            if q5_2.strip().lower() == "ylabel":
                st.success("Exactly! `plt.ylabel()` adds the vertical context.")
                mark_completed("CH5", "5.2", "quiz")
                if st.button("Final Chapter Challenge! →"):
                    st.session_state.ch5_step = "🏆 Chapter 5 Challenge"
                    st.rerun()
    
        elif step == "🏆 Chapter 5 Challenge":
            st.markdown("### 🏆 Chapter 5 Final Task")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>The Scenario:</b> You are presenting to stockholders. You have a DataFrame <code>df</code> with 
            <code>'Year'</code> and <code>'Profit'</code> columns. <br><br>
            
            <b>Your Task:</b> Write the two lines of code to plot a line chart and set the title.
            </div>
            """, unsafe_allow_html=True)
            
            user_viz = st.text_area("Write your solution (Python):")
            if st.button("Submit Project"):
                if "lineplot" in user_viz and "plt.title" in user_viz:
                    st.success("🎉 VIZ WIZARD! Your reports will be legendary.")
                    st.balloons()
                    mark_completed("CH5", "TASK", "final")
                else:
                    st.error("Try again! Use `sns.lineplot()` and `plt.title()`.")
    
    # --- CHAPTER 6: CA PRACTICE LAB ---
    elif st.session_state.current_chapter == "CH 6: CA Practice Lab":
        st.markdown("<h1>Chapter 6: CA Exam Practice Lab</h1>", unsafe_allow_html=True)
        
        ch6_steps = ["6.1 XML Mastery", "6.2 NumPy Analytics", "6.3 Regex Challenge", "🏆 CA Mock Exam"]
        step = st.select_slider("Chapter Progress", options=ch6_steps, value=st.session_state.get('ch6_step', "6.1 XML Mastery"))
        st.session_state.ch6_step = step
    
        if step == "6.1 XML Mastery":
            st.markdown("### 🏺 6.1 Safe XML Ingestion")
            st.write("""
            In the CA, you are often asked to load XML data safely. This means handling errors like **FileNotFound** 
            or **ParseError** so the program doesn't crash.
            """)
            
            lesson_summary(
                "XML Patterns", 
                "30 Minutes", 
                [
                    "Use <code>xml.etree.ElementTree as ET</code>.",
                    "Wrap <code>ET.parse()</code> in a <code>try-except</code> block.",
                    "Extract attributes using <code>.get('attr_name')</code>.",
                    "Extract nested text using <code>.findtext('tag_name')</code>."
                ]
            )
    
            exercise_container(
                "The Safe Loader", 
                "intermediate", 
                "You are loading 'flights.xml'. You must catch the case where the XML is malformed.",
                "Complete the exception type for XML parsing errors."
            )
            
            st.code("""
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse("flights.xml")
    except ET.____ as e:
        print(f"XML is broken: {e}")
            """)
            q6_1 = st.text_input("Fill in the exception class name:", key="q6_1")
            if q6_1 == "ParseError":
                st.success("Correct! ET.ParseError specifically catches malformed XML syntax.")
                mark_completed("CH6", "6.1", "quiz")
                if st.button("Next: NumPy Analytics →"):
                    st.session_state.ch6_step = "6.2 NumPy Analytics"
                    st.rerun()
    
        elif step == "6.2 NumPy Analytics":
            st.markdown("### 📊 6.2 Data Structure Manipulation")
            st.write("""
            A common exam task is converting raw string records into NumPy arrays and handling **'NA'** values 
            programmatically without using standard loops for every operation.
            """)
            
            st.code("""
    import numpy as np
    # Convert strings to floats, mapping 'NA' to NaN
    scores = [10, 'NA', 30]
    arr = np.array([np.nan if x == 'NA' else float(x) for x in scores])
    print(np.nanmean(arr)) # Returns 20.0
            """)
    
            # QUIZ 6.2
            st.markdown("---")
            exercise_container(
                "The NaN Ninja", 
                "intermediate", 
                "You have a NumPy array with missing data (NaN). You want to count how many valid (non-missing) scores exist.",
                "Which logical combination counts non-NaN values?"
            )
            q6_2 = st.radio("Selection:", ["np.sum(arr == np.nan)", "np.sum(~np.isnan(arr))", "len(arr)"], key="q6_2", index=None)
            if q6_2 == "np.sum(~np.isnan(arr))":
                st.success("Correct! `~np.isnan(arr)` creates a boolean mask of valid values, and `sum()` counts the True entries.")
                mark_completed("CH6", "6.2", "quiz")
                if st.button("Next: Regex Challenge →"):
                    st.session_state.ch6_step = "6.3 Regex Challenge"
                    st.rerun()
    
        elif step == "6.3 Regex Challenge":
            st.markdown("### 🔍 6.3 Advanced Pattern Extraction")
            st.write("""
            The CA will test your ability to extract multiple types of entities from a single text block 
            (like Hashtags AND Mentions) using capture groups and specific character classes.
            """)
            
            st.markdown("""
            #### Regex Power Tools:
            - `re.finditer()`: Better than `findall()` if you need capture groups or match positions.
            - `group(1)`: Accesses the first bracketed set `()` in your pattern.
            - `re.IGNORECASE`: Flag to match both `USD` and `usd`.
            """)
    
            # QUIZ 6.3
            st.markdown("---")
            exercise_container(
                "The Mention Threader", 
                "beginner", 
                "You need to find all @mentions. A mention starts with @ and is followed by one or more letters/digits.",
                "Which pattern is most accurate?"
            )
            q6_3 = st.radio("Selection:", [r"@\w+", r"@\d+", r"#\w+"], key="q6_3", index=None)
            if q6_3 == r"@\w+":
                st.success("Correct! `\w` matches letters, digits, and underscores.")
                mark_completed("CH6", "6.3", "quiz")
                if st.button("Go to Mock Exam! →"):
                    st.session_state.ch6_step = "🏆 CA Mock Exam"
                    st.rerun()
    
        elif step == "🏆 CA Mock Exam":
            st.markdown("### 🏆 Comprehensive CA Mock Exam")
            st.markdown("""
            <div class="exercise-box" style="border-left: 5px solid #ffcc00;">
            <b>Exam Scenario:</b> You are given a file <code>reviews.txt</code> with entries like:<br>
            <code>R001 | 5 | Great flight! #smooth @pilot</code><br><br>
            
            <b>Your Task:</b> Code a solution that:
            1. Loads the file and splits each line by <code>' | '</code>.
            2. Uses regex to find ALL <b>hashtags</b> in the text.
            3. Stores the counts of hashtags in a dictionary.
            </div>
            """, unsafe_allow_html=True)
            
            user_exam_code = st.text_area("Write your solution (Python):", height=250, key="ca_exam")
            if st.button("Finish CA Exam"):
                if "split(" in user_exam_code and "re.findall" in user_exam_code and "#" in user_exam_code:
                    st.success("🎊 CA COMPLETE! You've matched the logic from the practice guide.")
                    st.balloons()
                    mark_completed("CH6", "TASK", "final")
                else:
                    st.error("Check your logic! You need to split the line, use regex for '#', and count results.")
    
    # --- FINAL PROJECT ---
    elif st.session_state.current_chapter == "Final Project":
        st.markdown("<h1>🏆 Capstone: The Retail Intelligence Pipeline</h1>", unsafe_allow_html=True)
        
        st.markdown("""
        <div class="lesson-card">
        <h3>The Mission</h3>
        <p>You are the Lead Analyst for <b>Electro-Pulse</b>. Your goal is to build an ETL pipeline that loads sales data, 
        extracts discount codes with Regex, and identifies the most profitable region.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # PROJECT STEP 1
        st.subheader("Step 1: Ingestion")
        exercise_container(
            "Load the Dataset", 
            "intermediate", 
            "The raw sales data is stored as a CSV. You need to load it into a pandas DataFrame.",
            "Use the pandas function to read 'sales_data.csv'."
        )
        p_ex1 = st.text_input("code: df = pd.____('sales_data.csv')", key="p_ex1")
        if p_ex1 == "read_csv":
            st.success("Step 1 Complete!")
            mark_completed("PROJ", "FINAL", "ex1")
            
            # PROJECT STEP 2 (Visible only after Step 1)
            st.divider()
            st.subheader("Step 2: regex Cleaning")
            exercise_container(
                "Extracting Vouchers", 
                "intermediate", 
                "One column has messy notes like 'User applied code SAVE20'. You need to find all SAVExx codes.",
                "Complete the regex pattern to find 'SAVE' followed by two digits."
            )
            p_ex2 = st.text_input("code: pattern = r'SAVE\\____'", key="p_ex2")
            if p_ex2 == "d{2}":
                st.success("Step 2 Complete! You've successfully parsed the voucher codes.")
                mark_completed("PROJ", "FINAL", "ex2")
                
                # PROJECT STEP 3
                st.divider()
                st.subheader("Step 3: Business Insight")
                st.markdown("""
                <div class="exercise-box">
                <b>Scenario:</b> Your visual analysis shows that the 'West' region has high sales but very low profit. 
                Which plot would BEST help you investigate the relationship between 'Discount Amount' and 'Profit Margin'?
                </div>
                """, unsafe_allow_html=True)
                p_ex3 = st.radio("Select the diagnostic plot:", ["Pie Chart", "Scatter Plot", "Histogram"], key="p_ex3", index=None)
                if p_ex3 == "Scatter Plot":
                    st.success("🏆 Project Complete! Scatter plots are perfect for seeing how one variable influences another.")
                    mark_completed("PROJ", "FINAL", "ex3")
                    st.balloons()
                    st.markdown("""
                    ### 🎉 Congratulations!
                    You have completed the **APDV Mastery Course**. You now have the skills to:
                    - Extract data from multiple sources.
                    - Clean text with Regex.
                    - Query SQL databases.
                    - Visualize complex business trends.
                    """)
    
# --- MAIN LAYOUT ---
main_col = st.container()

with main_col:
    app_content()

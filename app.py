import streamlit as st
import chess
import pyrebase
import time
from streamlit.components.v1 import html
from streamlit_autorefresh import st_autorefresh

# =============== FIREBASE CONFIG ===============
firebaseConfig = {
  "apiKey":
  "AIzaSyBKtn3M3gj_OBiP_fSg63omjhAO6t5QmS8",
  "authDomain":
  "fir-chess-ff085.firebaseapp.com",
  "databaseURL":
  "https://fir-chess-ff085-default-rtdb.firebaseio.com/",
  "projectId": "fir-chess-ff085",
  "storageBucket": 
  "fir-chess-ff085.firebasestorage.app",
  "messagingSenderId": "495432935367",
  "appId":
  "1:495432935367:web:13ab4012be185b9d69dbe2",
}

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

# =============== STREAMLIT SETUP ===============
st.set_page_config(page_title="♟️ Firebase Chess", page_icon="♟️", layout="wide")
st.title("♟️ Real-Time Chess (Firebase-Synced, Click-to-Move)")

# =============== SESSION STATE ===============
for key, default in {
    "user": None, "room_id": "", "player_color": None
}.items():
    st.session_state.setdefault(key, default)

# =============== AUTH SECTION ===============
if not st.session_state.user:
    st.sidebar.header("🔐 Login / Sign Up")
    mode = st.sidebar.radio("Select:", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if mode == "Sign Up" and st.sidebar.button("Create Account"):
        try:
            auth.create_user_with_email_and_password(email, password)
            st.sidebar.success("✅ Account created! Log in now.")
        except Exception:
            st.sidebar.error("❌ Error creating account.")
    elif mode == "Login" and st.sidebar.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.user = user
            st.experimental_rerun()
        except Exception:
            st.sidebar.error("❌ Invalid credentials.")
    st.stop()

# =============== ROOM SETUP ===============
st.sidebar.header("🎮 Game Setup")
choice = st.sidebar.radio("Mode:", ["Create Room", "Join Room"])

if choice == "Create Room":
    name = st.sidebar.text_input("Enter your name (White):")
    if st.sidebar.button("Create"):
        if name:
            room_id = str(int(time.time()))
            db.child("rooms").child(room_id).set({
                "fen": chess.Board().fen(),
                "turn": "White",
                "white": name,
                "black": None
            })
            st.session_state.room_id = room_id
            st.session_state.player_color = "White"
            st.sidebar.success(f"✅ Room created! Share ID: {room_id}")
        else:
            st.sidebar.warning("Enter your name.")
elif choice == "Join Room":
    name = st.sidebar.text_input("Enter your name (Black):")
    room_id = st.sidebar.text_input("Enter Room ID:")
    if st.sidebar.button("Join"):
        if name and room_id:
            data = db.child("rooms").child(room_id).get().val()
            if data:
                db.child("rooms").child(room_id).update({"black": name})
                st.session_state.room_id = room_id
                st.session_state.player_color = "Black"
                st.sidebar.success("✅ Joined room!")
            else:
                st.sidebar.error("❌ Room not found.")
        else:
            st.sidebar.warning("Fill both fields.")

if not st.session_state.room_id:
    st.stop()

# =============== GAME SECTION ===============
st_autorefresh(interval=3000,key="refresh")

room_id = st.session_state.room_id
player_color = st.session_state.player_color
data = db.child("rooms").child(room_id).get().val()
if not data:
    st.error("Room not found.")
    st.stop()

fen = data["fen"]
turn = data["turn"]
board = chess.Board(fen)

st.info(f"Room: `{room_id}` | You are **{player_color}** | Turn: **{turn}**")

# =============== JAVASCRIPT CHESSBOARD ===============
chess_html = f"""
<!doctype html>
<html>
<head>
<style>
body {{
  margin:0; background:#f0d9b5; display:flex;
  justify-content:center; align-items:center; height:100vh;
}}
#board {{
  display:grid; grid-template-columns:repeat(8,60px);
  grid-template-rows:repeat(8,60px);
}}
.square {{
  width:60px; height:60px; display:flex; justify-content:center;
  align-items:center; font-size:40px; cursor:pointer;
}}
.light {{ background:#f0d9b5; }} .dark {{ background:#b58863; }}
.selected {{ outline:3px solid #4a90e2; }}
</style>
</head>
<body>
<div id="board"></div>
<script>
const boardEl = document.getElementById('board');
const glyphs = {{'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙','k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟'}};
const fen = "{fen}";
function parseFEN(fen) {{
  const rows = fen.split('/'); const board = [];
  for (let r=0;r<8;r++) {{
    const row=[]; for (let c of rows[r]) {{
      if(/[1-8]/.test(c)) for(let i=0;i<+c;i++) row.push('');
      else row.push(c);
    }}
    board.push(row);
  }} return board;
}}
const boardArr=parseFEN(fen);
for (let r=0;r<8;r++) {{
  for (let c=0;c<8;c++) {{
    const sq=document.createElement('div');
    sq.className='square '+(((r+c)%2)?'dark':'light');
    sq.dataset.square=String.fromCharCode(97+c)+(8-r);
    const p=boardArr[r][c]; if(p) sq.textContent=glyphs[p]||p;
    boardEl.appendChild(sq);
  }}
}}
let selected=null;
boardEl.addEventListener('click',e=>{{
  const sq=e.target.dataset.square;
  if(!sq) return;
  if(!selected) {{
    selected=sq;
    e.target.classList.add('selected');
  }} else {{
    parent.postMessage({{move:selected+sq}},'*');
    selected=null;
    for(let el of document.getElementsByClassName('square')) el.classList.remove('selected');
  }}
}});
</script>
</body></html>
"""

html(chess_html, height=520)

# =============== HANDLE MOVE EVENTS ===============
# JS -> Streamlit bridge
html("""
<script>
window.addEventListener('message', (event) => {
    if (event.data && event.data.move) {
        const params = new URLSearchParams(window.location.search);
        params.set('move', event.data.move);
        window.location.search = params.toString();
    }
});
</script>
""", height=0)

move = st.query_params.get("move", [None])[0]


if move:
    try:
        if turn.lower() == player_color.lower():
            mv = chess.Move.from_uci(move)
            if mv in board.legal_moves:
                board.push(mv)
                db.child("rooms").child(room_id).update({
                    "fen": board.fen(),
                    "turn": "Black" if turn == "White" else "White"
                })
                st.success(f"✅ Move played: {move}")
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.warning("⚠️ Illegal move!")
        else:
            st.warning("⏳ Not your turn!")
    except Exception as e:
        st.error(f"Invalid move: {move}")

# =============== STATUS ===============
st.markdown(f"**Turn:** {turn}")
st.markdown(f"**Moves Played:** {len(board.move_stack)}")

if board.is_checkmate():
    winner = "Black" if turn == "White" else "White"
    st.error(f"♚ Checkmate! {winner} wins!")
elif board.is_stalemate():
    st.warning("🤝 Stalemate!")
elif board.is_check():
    st.info(f"⚠️ {turn} is in check!")

# =============== RESET / LOGOUT ===============
col1, col2 = st.columns(2)
if col1.button("🔄 Reset Game"):
    db.child("rooms").child(room_id).update({
        "fen": chess.Board().fen(),
        "turn": "White"
    })
    st.rerun()
if col2.button("🚪 Logout"):
    st.session_state.user = None
    st.session_state.room_id = ""
    st.session_state.player_color = None
    st.rerun()
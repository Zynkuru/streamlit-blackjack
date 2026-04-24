"""
Blackjack — 3 hands, pure-Python Streamlit app.

Run locally with:
    streamlit run app.py
"""

import random
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUITS  = ["H", "D", "C", "S"]
RANKS  = ["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
CHIP_VALUES       = [1, 5, 25, 100, 500]
STARTING_BANKROLL = 1_000
NUM_HANDS         = 3

HAND_BADGE = {
    "idle":          ("",              ""),
    "waiting":       ("Waiting",       "#7f8c8d"),
    "active":        ("Your Turn ▶",   "#d4af37"),
    "bust":          ("Bust",          "#e74c3c"),
    "stand":         ("Stand",         "#7f8c8d"),
    "blackjack":     ("Blackjack!",    "#d4af37"),
    "blackjack_win": ("Blackjack ♠",   "#f0d060"),
    "won":           ("Win!",          "#2ecc71"),
    "lost":          ("Lost",          "#e74c3c"),
    "push":          ("Push",          "#95a5a6"),
}

# ---------------------------------------------------------------------------
# Card utilities
# ---------------------------------------------------------------------------

def make_deck():
    d = [r + s for s in SUITS for r in RANKS]
    random.shuffle(d)
    return d

def card_value(card):
    r = card[:-1]
    if r in ("J", "Q", "K"): return 10
    if r == "A":              return 11
    return int(r)

def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces  = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces:
        total -= 10; aces -= 1
    return total

def card_url(card):
    if card == "back":
        return "https://deckofcardsapi.com/static/img/back.png"
    r, s = card[:-1], card[-1]
    return f"https://deckofcardsapi.com/static/img/{'0' if r == '10' else r}{s}.png"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state():
    for k, v in {
        "deck":         [],
        "dealer":       [],
        "hands":        [[], [], []],
        "bets":         [0, 0, 0],
        "hand_statuses":["idle", "idle", "idle"],
        "active_hand":  -1,
        "status":       "betting",
        "bankroll":     STARTING_BANKROLL,
        "selected_hand": 0,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ---------------------------------------------------------------------------
# Game actions
# ---------------------------------------------------------------------------

def place_bet(amount):
    ss = st.session_state
    if ss.status != "betting" or amount not in CHIP_VALUES: return
    if amount > ss.bankroll: return
    ss.bankroll -= amount
    ss.bets[ss.selected_hand] += amount

def clear_bet(hand_idx):
    ss = st.session_state
    if ss.status != "betting": return
    ss.bankroll += ss.bets[hand_idx]
    ss.bets[hand_idx] = 0

def _settle_hand(i):
    ss  = st.session_state
    bet = ss.bets[i]
    hs  = ss.hand_statuses[i]
    if hs == "blackjack_win":
        ss.bankroll += bet + (bet * 3) // 2
    elif hs == "won":
        ss.bankroll += bet * 2
    elif hs == "push":
        ss.bankroll += bet
    # bust / lost: bet already left bankroll at place_bet time

def _dealer_play():
    ss = st.session_state
    has_stand = any(ss.hand_statuses[i] == "stand" for i in range(NUM_HANDS))
    if has_stand:
        while hand_value(ss.dealer) < 17:
            ss.dealer.append(ss.deck.pop())

    dv = hand_value(ss.dealer)
    for i in range(NUM_HANDS):
        if ss.bets[i] <= 0:
            continue
        hs = ss.hand_statuses[i]
        if hs in ("bust", "blackjack_win", "push", "lost"):
            continue
        if hs == "stand":
            pv = hand_value(ss.hands[i])
            if dv > 21:           ss.hand_statuses[i] = "won"
            elif pv > dv:         ss.hand_statuses[i] = "won"
            elif dv > pv:         ss.hand_statuses[i] = "lost"
            else:                 ss.hand_statuses[i] = "push"
            _settle_hand(i)

    ss.status      = "resolved"
    ss.active_hand = -1

def _advance_hand():
    ss = st.session_state
    for i in range(ss.active_hand + 1, NUM_HANDS):
        if ss.hand_statuses[i] == "waiting":
            ss.hand_statuses[i] = "active"
            ss.active_hand = i
            return
    _dealer_play()

def deal_hand():
    ss = st.session_state
    if ss.status != "betting" or sum(ss.bets) == 0: return

    ss.deck  = make_deck()
    ss.hands = [[], [], []]
    ss.dealer = []
    active   = [i for i, b in enumerate(ss.bets) if b > 0]

    for _ in range(2):
        for i in active:
            ss.hands[i].append(ss.deck.pop())
        ss.dealer.append(ss.deck.pop())

    dealer_bj = hand_value(ss.dealer) == 21
    statuses  = ["idle"] * NUM_HANDS
    for i in active:
        player_bj = hand_value(ss.hands[i]) == 21
        if player_bj and dealer_bj:  statuses[i] = "push"
        elif player_bj:              statuses[i] = "blackjack_win"
        elif dealer_bj:              statuses[i] = "lost"
        else:                        statuses[i] = "waiting"
    ss.hand_statuses = statuses

    for i in active:
        if ss.hand_statuses[i] in ("blackjack_win", "push", "lost"):
            _settle_hand(i)

    playable = [i for i in active if ss.hand_statuses[i] == "waiting"]
    if playable:
        ss.hand_statuses[playable[0]] = "active"
        ss.active_hand = playable[0]
        ss.status      = "playing"
    else:
        ss.active_hand = -1
        ss.status      = "resolved"

def hit():
    ss  = st.session_state
    idx = ss.active_hand
    if ss.status != "playing" or idx < 0: return
    ss.hands[idx].append(ss.deck.pop())
    if hand_value(ss.hands[idx]) > 21:
        ss.hand_statuses[idx] = "bust"
        _advance_hand()

def stand():
    ss  = st.session_state
    idx = ss.active_hand
    if ss.status != "playing" or idx < 0: return
    ss.hand_statuses[idx] = "stand"
    _advance_hand()

def new_hand():
    ss = st.session_state
    ss.hands         = [[], [], []]
    ss.dealer        = []
    ss.bets          = [0, 0, 0]
    ss.hand_statuses = ["idle"] * NUM_HANDS
    ss.active_hand   = -1
    ss.status        = "betting"
    ss.selected_hand = 0

def reset_bankroll():
    st.session_state.bankroll = STARTING_BANKROLL
    new_hand()

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --gold:       #d4af37;
        --gold-light: #efd58a;
        --cream:      #f5ecd7;
        --ink:        #0a1e16;
        --wood-dark:  #2a180d;
        --wood-mid:   #6b5010;
        --wood-light: #c9a227;
    }

    /* ── Room background ── */
    .stApp {
        background: radial-gradient(ellipse at 50% 0%, #111 0%, #050505 100%) !important;
        font-family: 'Inter', sans-serif;
    }

    /* ── Table surface (the felt) ── */
    .main .block-container {
        max-width: 960px !important;
        padding: 0 0 0 !important;
        background:
            linear-gradient(180deg,
                #1d6040 0%,
                #17543a 25%,
                #124430 55%,
                #0d3828 80%,
                #0a2d20 100%) !important;
        border-left:  10px solid var(--wood-mid) !important;
        border-right: 10px solid var(--wood-mid) !important;
        border-top:   none !important;
        border-bottom: none !important;
        border-radius: 0 !important;
        box-shadow:
            -12px 0 30px rgba(0,0,0,0.9),
            12px 0 30px rgba(0,0,0,0.9),
            0 40px 80px rgba(0,0,0,0.95),
            inset 0 0 120px rgba(0,0,0,0.25) !important;
        margin-top: 0 !important;
    }

    /* ── Table top rail (wood arc at top) ── */
    .table-top-rail {
        background: linear-gradient(180deg,
            #150c04 0%, #2a180d 15%, #4a2e10 30%,
            #6b5010 50%, #c9a227 65%, #efd58a 72%,
            #c9a227 78%, #6b5010 88%, #2a180d 100%);
        padding: 1.8rem 2.5rem 1.2rem;
        text-align: center;
        position: relative;
        border-bottom: 1px solid rgba(212,175,55,0.2);
    }
    .table-top-rail::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg,
            transparent 0%, rgba(255,230,150,0.4) 30%,
            rgba(255,255,200,0.6) 50%,
            rgba(255,230,150,0.4) 70%, transparent 100%);
    }

    /* ── Dealer area ── */
    .dealer-area {
        padding: 1.2rem 2.5rem 0.8rem;
        background: linear-gradient(180deg,
            rgba(30,95,65,0.35) 0%, rgba(20,70,45,0.1) 100%);
        border-bottom: none;
    }

    /* ── Gold rail separator ── */
    .gold-rail {
        height: 16px;
        background: linear-gradient(180deg,
            #3d2200 0%, #6b5010 15%,
            #c9a227 35%, #efd58a 50%,
            #c9a227 65%, #6b5010 85%, #3d2200 100%);
        margin: 0;
        box-shadow:
            0 6px 24px rgba(0,0,0,0.7),
            0 -2px 8px rgba(212,175,55,0.15),
            inset 0 1px 2px rgba(255,240,180,0.3);
    }

    /* ── Player area ── */
    .player-area {
        padding: 1.2rem 2.5rem 0.5rem;
    }

    /* ── Controls area ── */
    .controls-area {
        padding: 0.5rem 2.5rem 1.5rem;
    }

    /* ── Table bottom rail ── */
    .table-bottom-rail {
        background: linear-gradient(0deg,
            #150c04 0%, #2a180d 15%, #4a2e10 30%,
            #6b5010 50%, #c9a227 65%, #efd58a 72%,
            #c9a227 78%, #6b5010 88%, #2a180d 100%);
        padding: 0.8rem 2.5rem;
        text-align: center;
        position: relative;
        border-top: 1px solid rgba(212,175,55,0.2);
    }
    .table-bottom-rail::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg,
            transparent 0%, rgba(255,230,150,0.4) 30%,
            rgba(255,255,200,0.6) 50%,
            rgba(255,230,150,0.4) 70%, transparent 100%);
    }

    /* ── Typography ── */
    h3 {
        font-family: 'Cormorant Garamond', serif !important;
        color: var(--cream) !important;
        font-size: 1.1rem !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        margin-bottom: 0.3rem !important;
    }
    hr {
        border: none !important;
        border-top: 1px solid rgba(212,175,55,0.18) !important;
        margin: 0.6rem 0 !important;
    }

    /* ── Card images ── */
    [data-testid="stImage"] img {
        border-radius: 6px !important;
        box-shadow:
            0 6px 18px rgba(0,0,0,0.75),
            0 2px 4px rgba(0,0,0,0.5) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        transition: transform 0.2s ease !important;
    }
    [data-testid="stImage"] img:hover {
        transform: translateY(-4px) !important;
    }

    /* ── All buttons base ── */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        transition: all 0.14s ease !important;
        border: 1.5px solid var(--gold) !important;
    }
    .stButton > button[kind="secondary"] {
        background: linear-gradient(180deg, #1c4d38 0%, #102d20 100%) !important;
        color: var(--gold-light) !important;
    }
    .stButton > button[kind="secondary"]:hover:not([disabled]) {
        background: linear-gradient(180deg, var(--gold) 0%, #c9a227 100%) !important;
        color: var(--ink) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 14px rgba(212,175,55,0.4) !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, var(--gold) 0%, #c0991f 100%) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }
    .stButton > button[kind="primary"]:hover:not([disabled]) {
        background: linear-gradient(180deg, var(--gold-light) 0%, var(--gold) 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 18px rgba(212,175,55,0.5) !important;
    }
    .stButton > button:active:not([disabled]) {
        transform: translateY(1px) !important;
    }
    .stButton > button[disabled] {
        opacity: 0.25 !important;
    }

    /* ── Chip buttons (5-column horizontal block) ── */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"] {
        display: flex !important;
        justify-content: center !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) button {
        border-radius: 50% !important;
        width: 60px !important; min-width: 60px !important; max-width: 60px !important;
        height: 60px !important; min-height: 60px !important;
        padding: 0 !important;
        font-size: 0.75rem !important; font-weight: 700 !important;
        letter-spacing: 0.02em !important; text-transform: none !important;
        outline-offset: -6px !important;
        box-shadow: 0 5px 14px rgba(0,0,0,0.55), inset 0 1px 2px rgba(255,255,255,0.15) !important;
    }
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) button:hover:not([disabled]) {
        transform: translateY(-6px) !important;
        box-shadow: 0 10px 22px rgba(0,0,0,0.7), 0 0 0 2px rgba(212,175,55,0.35) !important;
    }
    /* $1 white */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"]:nth-child(1) button {
        background: linear-gradient(145deg,#f5f5f5,#b8b8b8) !important;
        color:#222 !important; border-color:#888 !important;
        outline: 2px solid rgba(255,255,255,0.3) !important;
    }
    /* $5 red */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"]:nth-child(2) button {
        background: linear-gradient(145deg,#e74c3c,#a93226) !important;
        color:#fff !important; border-color:#7b241c !important;
        outline: 2px solid rgba(255,100,90,0.35) !important;
    }
    /* $25 green */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"]:nth-child(3) button {
        background: linear-gradient(145deg,#2ecc71,#1a7a40) !important;
        color:#fff !important; border-color:#145a32 !important;
        outline: 2px solid rgba(80,200,120,0.35) !important;
    }
    /* $100 slate */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"]:nth-child(4) button {
        background: linear-gradient(145deg,#5d6d7e,#2c3e50) !important;
        color:#fff !important; border-color:#17202a !important;
        outline: 2px solid rgba(120,150,170,0.3) !important;
    }
    /* $500 purple */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(5)) [data-testid="stColumn"]:nth-child(5) button {
        background: linear-gradient(145deg,#a569bd,#7d3c98) !important;
        color:#fff !important; border-color:#5b2c6f !important;
        outline: 2px solid rgba(180,130,210,0.35) !important;
    }

    /* ── Bankroll metric ── */
    [data-testid="metric-container"] {
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(212,175,55,0.25) !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
    }
    [data-testid="stMetricLabel"] p {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.6rem !important; text-transform: uppercase !important;
        letter-spacing: 0.22em !important; color: var(--gold-light) !important; opacity: 0.8 !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 1.9rem !important; color: var(--cream) !important;
    }

    /* ── Small labels ── */
    .section-label {
        font-family: 'Inter', sans-serif;
        color: var(--gold-light);
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.22em;
        opacity: 0.72;
        margin: 0.6rem 0 0.2rem;
    }

    /* ── Caption ── */
    [data-testid="stCaptionContainer"] p {
        color: var(--gold-light) !important;
        font-size: 0.62rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.2em !important;
        opacity: 0.65 !important;
        text-align: center !important;
    }

    /* ── Warning / alert ── */
    [data-testid="stAlert"] p {
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_cards(cards, width=80):
    if not cards:
        st.write("")
        return
    cols = st.columns(max(len(cards), 5))
    for i, card in enumerate(cards):
        with cols[i]:
            st.image(card_url(card), width=width)


def render_bet_circle(bet, status):
    resolved_win  = status in ("won", "blackjack_win")
    resolved_lose = status in ("bust", "lost")
    resolved_push = status == "push"
    is_active     = status == "active"

    if resolved_win:
        bg, border, color = "rgba(46,204,113,0.18)", "#2ecc71", "#2ecc71"
    elif resolved_lose:
        bg, border, color = "rgba(231,76,60,0.18)",  "#e74c3c", "#e74c3c"
    elif resolved_push:
        bg, border, color = "rgba(150,160,150,0.18)","#95a5a6", "#95a5a6"
    elif is_active:
        bg, border, color = "rgba(212,175,55,0.2)",  "#d4af37", "#d4af37"
    elif bet > 0:
        bg, border, color = "rgba(212,175,55,0.12)", "rgba(212,175,55,0.5)", "#efd58a"
    else:
        bg, border, color = "rgba(255,255,255,0.04)","rgba(255,255,255,0.12)", "rgba(255,255,255,0.2)"

    glow  = "0 0 18px rgba(212,175,55,0.45)" if is_active else "none"
    text  = f"${bet}" if bet > 0 else "BET"
    fsize = "1.1rem" if bet > 0 else "0.6rem"
    fw    = "700" if bet > 0 else "400"
    ls    = "0" if bet > 0 else "0.12em"

    st.markdown(f"""
    <div style="
        width:62px; height:62px; border-radius:50%;
        background:{bg}; border:2px dashed {border};
        box-shadow:{glow};
        display:flex; align-items:center; justify-content:center;
        margin:4px auto 6px;
        font-family:'Cormorant Garamond',serif;
        font-size:{fsize}; font-weight:{fw};
        color:{color}; letter-spacing:{ls};
        transition:all 0.2s;
    ">{text}</div>
    """, unsafe_allow_html=True)


def render_hand_badge(status):
    text, color = HAND_BADGE.get(status, ("", ""))
    if not text:
        st.markdown('<div style="height:22px;"></div>', unsafe_allow_html=True)
        return
    bg = color + "22"
    border = color + "66"
    st.markdown(f"""
    <div style="text-align:center; margin-top:4px;">
        <span style="
            display:inline-block; padding:3px 10px;
            border-radius:20px; border:1px solid {border};
            background:{bg}; color:{color};
            font-family:'Inter',sans-serif; font-size:0.62rem;
            font-weight:700; text-transform:uppercase; letter-spacing:0.14em;
        ">{text}</span>
    </div>
    """, unsafe_allow_html=True)


def render_hand_column(hand_idx):
    ss     = st.session_state
    hand   = ss.hands[hand_idx]
    bet    = ss.bets[hand_idx]
    status = ss.hand_statuses[hand_idx]
    val    = hand_value(hand) if hand else 0

    is_active = (status == "active")
    label_color = "#d4af37" if is_active else "#c8b89a"
    label = f"Hand {hand_idx + 1}" + (f"  —  {val}" if val else "")

    shadow = "text-shadow:0 0 12px rgba(212,175,55,0.5);" if is_active else ""
    st.markdown(
        f'<div style="font-family:\'Cormorant Garamond\',serif;font-size:1.05rem;'
        f'font-weight:600;color:{label_color};text-align:center;'
        f'letter-spacing:0.06em;margin-bottom:0;{shadow}">{label}</div>',
        unsafe_allow_html=True,
    )

    render_bet_circle(bet, status)
    render_cards(hand, width=62)
    render_hand_badge(status)

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Blackjack", page_icon="♠", layout="centered")
    inject_styles()
    init_state()

    ss          = st.session_state
    is_betting  = ss.status == "betting"
    is_playing  = ss.status == "playing"
    is_resolved = ss.status == "resolved"
    reveal_dealer = is_resolved
    broke = ss.bankroll == 0 and sum(ss.bets) == 0 and is_betting

    # ── Table top rail ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="table-top-rail">
        <div style="font-family:'Cormorant Garamond',serif; color:#d4af37;
                    font-size:clamp(1.8rem,4vw,2.6rem); letter-spacing:0.12em;
                    text-shadow:0 2px 12px rgba(0,0,0,0.7),0 0 28px rgba(212,175,55,0.3);">
            ♠ &nbsp; Blackjack &nbsp; ♣
        </div>
        <div style="font-family:'Inter',sans-serif; color:#efd58a;
                    font-size:0.62rem; text-transform:uppercase; letter-spacing:0.26em;
                    opacity:0.7; margin-top:5px;">
            Dealer stands on 17 &nbsp;·&nbsp; Blackjack pays 3 to 2 &nbsp;·&nbsp; 3 hands
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Dealer section ────────────────────────────────────────────────────────
    st.markdown('<div class="dealer-area">', unsafe_allow_html=True)
    if ss.dealer:
        d_cards = ss.dealer if reveal_dealer else [ss.dealer[0], "back"]
        d_val   = hand_value(ss.dealer) if reveal_dealer else card_value(ss.dealer[0])
    else:
        d_cards, d_val = [], 0

    st.subheader("Dealer" + (f"  —  {d_val}" if d_val else ""))
    render_cards(d_cards, width=72)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Gold table rail ───────────────────────────────────────────────────────
    st.markdown('<div class="gold-rail"></div>', unsafe_allow_html=True)

    # ── Player hand columns ───────────────────────────────────────────────────
    st.markdown('<div class="player-area">', unsafe_allow_html=True)
    col0, col1, col2 = st.columns(3)
    with col0: render_hand_column(0)
    with col1: render_hand_column(1)
    with col2: render_hand_column(2)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Controls ──────────────────────────────────────────────────────────────
    st.markdown('<div class="controls-area">', unsafe_allow_html=True)
    st.markdown("---")

    # Bankroll
    st.metric("Bankroll", f"${ss.bankroll}")

    if is_betting and not broke:
        # Hand selector
        st.markdown('<p class="section-label">Betting on</p>', unsafe_allow_html=True)
        sel0, sel1, sel2 = st.columns(3)
        for idx, col in enumerate([sel0, sel1, sel2]):
            with col:
                bet_label = f"Hand {idx + 1}  ${ss.bets[idx]}" if ss.bets[idx] else f"Hand {idx + 1}"
                if st.button(
                    bet_label,
                    key=f"sel_{idx}",
                    type="primary" if ss.selected_hand == idx else "secondary",
                    use_container_width=True,
                ):
                    ss.selected_hand = idx
                    st.rerun()

        # Chips
        st.markdown('<p class="section-label">Chips</p>', unsafe_allow_html=True)
        chip_cols = st.columns(len(CHIP_VALUES))
        for i, value in enumerate(CHIP_VALUES):
            with chip_cols[i]:
                if st.button(f"${value}", key=f"chip_{value}",
                             disabled=value > ss.bankroll):
                    place_bet(value)
                    st.rerun()

        # Deal / Clear
        st.write("")
        d_col, c_col = st.columns(2)
        if d_col.button("Deal", disabled=sum(ss.bets) == 0,
                         type="primary", use_container_width=True, key="btn_deal"):
            deal_hand(); st.rerun()
        if c_col.button("Clear Bets", disabled=sum(ss.bets) == 0,
                         use_container_width=True, key="btn_clear"):
            for i in range(NUM_HANDS): clear_bet(i)
            st.rerun()

    elif is_playing:
        active_idx = ss.active_hand
        st.caption(f"Playing Hand {active_idx + 1}  —  value: {hand_value(ss.hands[active_idx])}")
        h_col, s_col = st.columns(2)
        if h_col.button("Hit",   type="primary", use_container_width=True, key="btn_hit"):
            hit(); st.rerun()
        if s_col.button("Stand", use_container_width=True, key="btn_stand"):
            stand(); st.rerun()

    elif is_resolved:
        if st.button("Next Hand", type="primary",
                     use_container_width=True, key="btn_next"):
            new_hand(); st.rerun()

    if broke:
        st.warning("You're out of chips!")
        if st.button("Reset Bankroll", type="primary",
                     use_container_width=True, key="btn_reset"):
            reset_bankroll(); st.rerun()

    # ── Table bottom rail ─────────────────────────────────────────────────────
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="table-bottom-rail">
        <span style="font-family:'Inter',sans-serif; color:#efd58a;
                     font-size:0.6rem; text-transform:uppercase;
                     letter-spacing:0.2em; opacity:0.55;">
            Aces 1 or 11 &nbsp;·&nbsp; Face cards 10
            &nbsp;·&nbsp; Dealer hits on 16, stands on 17
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

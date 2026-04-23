"""
Blackjack with betting — a pure-Python Streamlit app.

Run locally with:
    streamlit run app.py

All game logic and UI are implemented in Python using Streamlit.
No HTML/CSS/JS files required.
"""

import random
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUITS = ["H", "D", "C", "S"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

CHIP_VALUES = [1, 5, 25, 100, 500]
STARTING_BANKROLL = 1000

STATUS_TEXT = {
    "betting": "Place your bet",
    "playing": "",
    "blackjack": "Blackjack! Pays 3 to 2",
    "player_bust": "Bust",
    "dealer_bust": "Dealer busts — you win!",
    "player_wins": "You win!",
    "dealer_wins": "Dealer wins",
    "dealer_blackjack": "Dealer has blackjack",
    "push": "Push",
}

WIN_STATUSES = {"blackjack", "dealer_bust", "player_wins"}
LOSE_STATUSES = {"player_bust", "dealer_wins", "dealer_blackjack"}

# Casino chip visual config: (value, gradient, text_color, border_color, highlight)
CHIP_CONFIG = [
    (1,   "linear-gradient(145deg,#f5f5f5 0%,#d0d0d0 50%,#b0b0b0 100%)", "#222", "#888", "rgba(255,255,255,0.6)"),
    (5,   "linear-gradient(145deg,#e74c3c 0%,#c0392b 50%,#a93226 100%)", "#fff", "#7b241c", "rgba(255,140,130,0.5)"),
    (25,  "linear-gradient(145deg,#2ecc71 0%,#27ae60 50%,#1e8449 100%)", "#fff", "#145a32", "rgba(100,220,140,0.5)"),
    (100, "linear-gradient(145deg,#5d6d7e 0%,#34495e 50%,#2c3e50 100%)", "#fff", "#17202a", "rgba(150,170,190,0.4)"),
    (500, "linear-gradient(145deg,#a569bd 0%,#8e44ad 50%,#7d3c98 100%)", "#fff", "#5b2c6f", "rgba(200,150,220,0.5)"),
]


# ---------------------------------------------------------------------------
# Card utilities
# ---------------------------------------------------------------------------

def make_deck():
    deck = [rank + suit for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_value(card):
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand):
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def card_image_url(card):
    if card == "back":
        return "https://deckofcardsapi.com/static/img/back.png"
    rank = card[:-1]
    suit = card[-1]
    r = "0" if rank == "10" else rank
    return f"https://deckofcardsapi.com/static/img/{r}{suit}.png"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "deck": [],
        "player": [],
        "dealer": [],
        "status": "betting",
        "bankroll": STARTING_BANKROLL,
        "bet": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------------------------
# Game actions
# ---------------------------------------------------------------------------

def settle_bet():
    status = st.session_state.status
    bet = st.session_state.bet
    if status == "blackjack":
        st.session_state.bankroll += bet + (bet * 3) // 2
    elif status in ("player_wins", "dealer_bust"):
        st.session_state.bankroll += bet * 2
    elif status == "push":
        st.session_state.bankroll += bet


def place_bet(amount):
    if st.session_state.status != "betting":
        return
    if amount not in CHIP_VALUES:
        return
    if amount > st.session_state.bankroll:
        return
    st.session_state.bankroll -= amount
    st.session_state.bet += amount


def clear_bet():
    if st.session_state.status != "betting":
        return
    st.session_state.bankroll += st.session_state.bet
    st.session_state.bet = 0


def deal_hand():
    if st.session_state.status != "betting" or st.session_state.bet <= 0:
        return
    st.session_state.deck = make_deck()
    st.session_state.player = [st.session_state.deck.pop(), st.session_state.deck.pop()]
    st.session_state.dealer = [st.session_state.deck.pop(), st.session_state.deck.pop()]

    pv = hand_value(st.session_state.player)
    dv = hand_value(st.session_state.dealer)

    if pv == 21 and dv == 21:
        st.session_state.status = "push"
    elif pv == 21:
        st.session_state.status = "blackjack"
    elif dv == 21:
        st.session_state.status = "dealer_blackjack"
    else:
        st.session_state.status = "playing"

    if st.session_state.status != "playing":
        settle_bet()


def hit():
    if st.session_state.status != "playing":
        return
    st.session_state.player.append(st.session_state.deck.pop())
    if hand_value(st.session_state.player) > 21:
        st.session_state.status = "player_bust"
        settle_bet()


def stand():
    if st.session_state.status != "playing":
        return
    while hand_value(st.session_state.dealer) < 17:
        st.session_state.dealer.append(st.session_state.deck.pop())

    pv = hand_value(st.session_state.player)
    dv = hand_value(st.session_state.dealer)
    if dv > 21:
        st.session_state.status = "dealer_bust"
    elif pv > dv:
        st.session_state.status = "player_wins"
    elif dv > pv:
        st.session_state.status = "dealer_wins"
    else:
        st.session_state.status = "push"
    settle_bet()


def new_hand():
    st.session_state.player = []
    st.session_state.dealer = []
    st.session_state.bet = 0
    st.session_state.status = "betting"


def reset_bankroll():
    st.session_state.bankroll = STARTING_BANKROLL
    st.session_state.bet = 0
    st.session_state.player = []
    st.session_state.dealer = []
    st.session_state.status = "betting"


# ---------------------------------------------------------------------------
# Visual helpers
# ---------------------------------------------------------------------------

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --felt-dark: #0e3324;
        --felt-mid: #17543a;
        --felt-light: #1e6b48;
        --gold: #d4af37;
        --gold-light: #efd58a;
        --cream: #f5ecd7;
        --ink: #0a1e16;
    }

    /* ── Background ── */
    .stApp {
        background: radial-gradient(ellipse at 50% 10%, #225e3e 0%, #17543a 35%, #0e3324 80%, #081a12 100%) !important;
        font-family: 'Inter', sans-serif;
    }

    /* ── Casino table container ── */
    .main .block-container {
        max-width: 800px !important;
        padding: 2.5rem 2.8rem 3.5rem !important;
        background: rgba(10, 38, 22, 0.55) !important;
        border: 2px solid var(--gold) !important;
        border-radius: 24px !important;
        box-shadow:
            0 0 100px rgba(0,0,0,0.7),
            0 0 40px rgba(0,0,0,0.5),
            inset 0 0 80px rgba(14,51,36,0.6),
            inset 0 1px 4px rgba(212,175,55,0.12) !important;
        margin-top: 1.5rem !important;
        margin-bottom: 3rem !important;
    }

    /* ── Title ── */
    h1 {
        font-family: 'Cormorant Garamond', serif !important;
        color: var(--gold) !important;
        font-size: clamp(2.2rem, 5vw, 3.2rem) !important;
        letter-spacing: 0.1em !important;
        text-shadow:
            0 2px 10px rgba(0,0,0,0.6),
            0 0 30px rgba(212,175,55,0.3),
            0 0 60px rgba(212,175,55,0.1) !important;
        text-align: center !important;
        margin-bottom: 0.1rem !important;
    }

    /* ── Subtitle/caption ── */
    [data-testid="stCaptionContainer"] p {
        font-family: 'Inter', sans-serif !important;
        color: var(--gold-light) !important;
        font-size: 0.68rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.24em !important;
        text-align: center !important;
        opacity: 0.75 !important;
    }

    /* ── Hand labels (Dealer / You) ── */
    h3 {
        font-family: 'Cormorant Garamond', serif !important;
        color: var(--cream) !important;
        font-size: 1.35rem !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.4rem !important;
    }

    /* ── Dividers ── */
    hr {
        border: none !important;
        border-top: 1px solid var(--gold) !important;
        opacity: 0.2 !important;
        margin: 0.8rem 0 !important;
    }

    /* ── Card images ── */
    [data-testid="stImage"] img {
        border-radius: 8px !important;
        box-shadow:
            0 8px 24px rgba(0,0,0,0.75),
            0 2px 6px rgba(0,0,0,0.5),
            0 1px 2px rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }

    [data-testid="stImage"] img:hover {
        transform: translateY(-5px) rotate(1.5deg) !important;
        box-shadow:
            0 14px 32px rgba(0,0,0,0.85),
            0 4px 10px rgba(0,0,0,0.6) !important;
    }

    /* ── All buttons ── */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase !important;
        letter-spacing: 0.14em !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 11px 22px !important;
        transition: all 0.15s ease !important;
        border: 1.5px solid var(--gold) !important;
    }

    /* Secondary (default) buttons */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(180deg, #1c4d38 0%, #102d20 100%) !important;
        color: var(--gold-light) !important;
    }

    .stButton > button[kind="secondary"]:hover:not([disabled]) {
        background: linear-gradient(180deg, var(--gold) 0%, #c9a227 100%) !important;
        color: var(--ink) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 16px rgba(212,175,55,0.4) !important;
    }

    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(180deg, var(--gold) 0%, #c0991f 100%) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
        border-color: var(--gold-light) !important;
    }

    .stButton > button[kind="primary"]:hover:not([disabled]) {
        background: linear-gradient(180deg, var(--gold-light) 0%, var(--gold) 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 20px rgba(212,175,55,0.5) !important;
    }

    .stButton > button:active:not([disabled]) {
        transform: translateY(1px) !important;
        box-shadow: none !important;
    }

    .stButton > button[disabled] {
        opacity: 0.22 !important;
        cursor: not-allowed !important;
    }

    /* ── Metrics (bankroll / bet) ── */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(0,0,0,0.35) 0%, rgba(14,51,36,0.5) 100%) !important;
        border: 1px solid rgba(212,175,55,0.3) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: inset 0 1px 4px rgba(0,0,0,0.4) !important;
    }

    [data-testid="stMetricLabel"] p {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.62rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.24em !important;
        color: var(--gold-light) !important;
        opacity: 0.8 !important;
    }

    [data-testid="stMetricValue"] {
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 2rem !important;
        color: var(--cream) !important;
        line-height: 1.15 !important;
    }

    /* ── Alerts ── */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        text-align: center !important;
    }

    [data-testid="stAlert"] p {
        font-family: 'Cormorant Garamond', serif !important;
        font-size: 1.45rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
    }

    /* ── Section label ("Chips") ── */
    .chip-label {
        font-family: 'Inter', sans-serif;
        color: var(--gold-light);
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.24em;
        opacity: 0.75;
        margin-bottom: 2px;
    }
    </style>
    """, unsafe_allow_html=True)


def render_cards_html(cards):
    """Render cards as custom HTML with shadows and deal animation."""
    if not cards:
        st.markdown('<div style="height:130px;"></div>', unsafe_allow_html=True)
        return

    imgs = ""
    for i, card in enumerate(cards):
        url = card_image_url(card)
        delay = i * 0.08
        imgs += f"""
        <img src="{url}"
             style="
                 width:90px;
                 border-radius:8px;
                 box-shadow:0 8px 24px rgba(0,0,0,0.75),0 2px 6px rgba(0,0,0,0.5);
                 border:1px solid rgba(255,255,255,0.07);
                 animation:dealCard 0.35s ease-out {delay:.2f}s both;
             " />"""

    st.markdown(f"""
    <style>
    @keyframes dealCard {{
        from {{ opacity:0; transform:translateY(-18px) rotate(-4deg); }}
        to   {{ opacity:1; transform:translateY(0)     rotate(0deg);  }}
    }}
    </style>
    <div style="display:flex;gap:10px;min-height:130px;align-items:flex-start;
                padding:4px 0;flex-wrap:wrap;">
        {imgs}
    </div>
    """, unsafe_allow_html=True)


def render_status_html(status):
    """Render outcome message with casino-styled typography."""
    text = STATUS_TEXT.get(status, "")

    if not text or status == "betting":
        st.markdown('<div style="height:54px;"></div>', unsafe_allow_html=True)
        return

    if status in WIN_STATUSES:
        color, glow = "#d4af37", "rgba(212,175,55,0.35)"
    elif status in LOSE_STATUSES:
        color, glow = "#e8a0a0", "rgba(232,160,160,0.25)"
    else:
        color, glow = "#f5ecd7", "rgba(245,236,215,0.2)"

    st.markdown(f"""
    <div style="text-align:center;padding:10px 0;min-height:54px;
                display:flex;align-items:center;justify-content:center;">
        <span style="
            font-family:'Cormorant Garamond',serif;
            font-size:1.65rem;
            font-weight:700;
            color:{color};
            text-shadow:0 0 24px {glow};
            letter-spacing:0.06em;
        ">{text}</span>
    </div>
    """, unsafe_allow_html=True)


def render_chips_html(bankroll):
    """Render casino-style circular chip buttons via iframe component."""
    chips_html = ""
    for value, gradient, text_color, border_color, highlight in CHIP_CONFIG:
        affordable = value <= bankroll
        disabled_attr = "" if affordable else "disabled"
        opacity = "1" if affordable else "0.28"
        cursor = "pointer" if affordable else "not-allowed"
        onclick = f"selectChip({value})" if affordable else ""

        chips_html += f"""
        <button
            {disabled_attr}
            onclick="{onclick}"
            onmouseover="if(!this.disabled){{this.style.transform='translateY(-6px)';this.style.boxShadow='0 10px 24px rgba(0,0,0,0.7),0 0 0 3px rgba(212,175,55,0.4)'}}"
            onmouseout="if(!this.disabled){{this.style.transform='translateY(0)';this.style.boxShadow='0 5px 14px rgba(0,0,0,0.55),inset 0 1px 3px {highlight}'}}"
            onmousedown="if(!this.disabled)this.style.transform='translateY(-2px)'"
            style="
                width:70px; height:70px;
                border-radius:50%;
                background:{gradient};
                color:{text_color};
                border:3px solid {border_color};
                outline:2.5px solid rgba(255,255,255,0.22);
                outline-offset:-7px;
                font-family:'Inter',sans-serif;
                font-size:0.78rem;
                font-weight:700;
                cursor:{cursor};
                opacity:{opacity};
                box-shadow:0 5px 14px rgba(0,0,0,0.55),inset 0 1px 3px {highlight};
                transition:transform 0.13s ease,box-shadow 0.13s ease;
                letter-spacing:0.04em;
                user-select:none;
            ">
            ${value}
        </button>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; padding:12px 0 8px;
    background:transparent;
    display:flex; gap:14px;
    justify-content:center; align-items:center;
  }}
</style>
</head>
<body>
  {chips_html}
  <script>
    function selectChip(v) {{
      var url = new URL(window.parent.location.href);
      url.searchParams.set('chip', v);
      window.parent.location.href = url.toString();
    }}
  </script>
</body>
</html>"""
    components.html(html, height=108, scrolling=False)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Blackjack", page_icon="♠", layout="centered")
    inject_styles()
    init_state()

    # Handle chip click relayed via URL query param
    chip_param = st.query_params.get("chip")
    if chip_param:
        try:
            place_bet(int(chip_param))
        except (ValueError, TypeError):
            pass
        st.query_params.clear()
        st.rerun()

    status = st.session_state.status
    is_betting = status == "betting"
    is_playing = status == "playing"
    is_resolved = not is_betting and not is_playing
    reveal_dealer = status not in ("betting", "playing")
    broke = (
        st.session_state.bankroll == 0
        and st.session_state.bet == 0
        and is_betting
    )

    # ── Header ──────────────────────────────────────────────────────────────
    st.title("♠ Blackjack ♣")
    st.caption("Dealer stands on 17  ·  Blackjack pays 3 to 2")

    st.markdown("---")

    # ── Dealer hand ─────────────────────────────────────────────────────────
    if st.session_state.dealer:
        if reveal_dealer:
            dealer_cards = st.session_state.dealer
            dealer_val = hand_value(st.session_state.dealer)
        else:
            dealer_cards = [st.session_state.dealer[0], "back"]
            dealer_val = card_value(st.session_state.dealer[0])
    else:
        dealer_cards = []
        dealer_val = 0

    dealer_label = "Dealer" + (f" — {dealer_val}" if dealer_val else "")
    st.subheader(dealer_label)
    render_cards_html(dealer_cards)

    # ── Outcome message ──────────────────────────────────────────────────────
    render_status_html(status)

    # ── Player hand ─────────────────────────────────────────────────────────
    player_val = hand_value(st.session_state.player) if st.session_state.player else 0
    player_label = "You" + (f" — {player_val}" if player_val else "")
    st.subheader(player_label)
    render_cards_html(st.session_state.player)

    st.markdown("---")

    # ── Bankroll / Bet ───────────────────────────────────────────────────────
    col_bank, col_bet = st.columns(2)
    col_bank.metric("Bankroll", f"${st.session_state.bankroll}")
    col_bet.metric("Bet", f"${st.session_state.bet}")

    st.write("")

    # ── Chips ────────────────────────────────────────────────────────────────
    if is_betting and not broke:
        st.markdown('<p class="chip-label">Chips</p>', unsafe_allow_html=True)
        render_chips_html(st.session_state.bankroll)

    # ── Action buttons ───────────────────────────────────────────────────────
    st.write("")
    if is_betting and not broke:
        left, right = st.columns(2)
        if left.button(
            "Deal",
            disabled=st.session_state.bet == 0,
            type="primary",
            use_container_width=True,
            key="btn_deal",
        ):
            deal_hand()
            st.rerun()
        if right.button(
            "Clear Bet",
            disabled=st.session_state.bet == 0,
            use_container_width=True,
            key="btn_clear",
        ):
            clear_bet()
            st.rerun()

    elif is_playing:
        left, right = st.columns(2)
        if left.button("Hit", type="primary", use_container_width=True, key="btn_hit"):
            hit()
            st.rerun()
        if right.button("Stand", use_container_width=True, key="btn_stand"):
            stand()
            st.rerun()

    elif is_resolved:
        if st.button(
            "Next Hand",
            type="primary",
            use_container_width=True,
            key="btn_next",
        ):
            new_hand()
            st.rerun()

    if broke:
        st.warning("You're out of chips!")
        if st.button(
            "Reset Bankroll",
            type="primary",
            use_container_width=True,
            key="btn_reset",
        ):
            reset_bankroll()
            st.rerun()

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        "Aces count as 1 or 11  ·  Face cards are 10  ·  Dealer must hit on 16 and stand on 17"
    )


if __name__ == "__main__":
    main()

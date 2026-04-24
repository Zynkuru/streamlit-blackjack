"""
Blackjack — 3 hands, pure-Python Streamlit app.

Run locally with:
    pip install -r requirements.txt
    streamlit run app.py
"""

import random
import time
import streamlit as st
import streamlit.components.v1 as components

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
    """Build a fresh, shuffled 52-card deck like ['7H','AD','10C',...]."""
    deck = []
    for s in SUITS:
        for r in RANKS:
            deck.append(r + s)
    random.shuffle(deck)
    return deck

def card_value(card):
    """Return the blackjack value of one card. Aces count as 11 here."""
    r = card[:-1]
    if r == "J" or r == "Q" or r == "K":
        return 10
    if r == "A":
        return 11
    return int(r)

def hand_value(hand):
    """Sum the cards, then downgrade aces from 11 to 1 if we'd bust."""
    total = 0
    aces = 0
    for c in hand:
        total += card_value(c)
        if c[:-1] == "A":
            aces += 1
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total

def card_url(card):
    """URL for the card image on deckofcardsapi.com (or the face-down back)."""
    if card == "back":
        return "https://deckofcardsapi.com/static/img/back.png"
    r = card[:-1]
    s = card[-1]
    # The API uses "0" in the filename for 10 (e.g. "0H.png")
    if r == "10":
        r = "0"
    return f"https://deckofcardsapi.com/static/img/{r}{s}.png"

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_state():
    """Set up default values in st.session_state on the first run."""
    defaults = {
        "deck": [],
        "dealer": [],
        "hands": [[], [], []],
        "bets": [0, 0, 0],
        "hand_statuses": ["idle", "idle", "idle"],
        "active_hand": -1,
        "status": "betting",
        "bankroll": STARTING_BANKROLL,
        "selected_hand": 0,
    }
    for key in defaults:
        if key not in st.session_state:
            st.session_state[key] = defaults[key]

# ---------------------------------------------------------------------------
# Game actions
# ---------------------------------------------------------------------------

def queue_sound(kind):
    """Remember a sound to play on the next page render.

    The game actions don't play sound directly — they just leave the name in
    session_state, and main() reads it back and plays it on the rerun.
    """
    st.session_state.pending_sound = kind

def place_bet(amount):
    """Move `amount` from the bankroll onto the currently selected hand."""
    ss = st.session_state
    if ss.status != "betting":
        return
    if amount not in CHIP_VALUES:
        return
    if amount > ss.bankroll:
        return
    ss.bankroll -= amount
    ss.bets[ss.selected_hand] += amount
    queue_sound("chip")

def clear_bet(hand_idx):
    """Put the chips on hand `hand_idx` back into the bankroll."""
    ss = st.session_state
    if ss.status != "betting":
        return
    ss.bankroll += ss.bets[hand_idx]
    ss.bets[hand_idx] = 0

def _settle_hand(i):
    """Pay out hand `i` according to its final status."""
    ss = st.session_state
    bet = ss.bets[i]
    hs = ss.hand_statuses[i]
    if hs == "blackjack_win":
        ss.bankroll += bet + (bet * 3) // 2
    elif hs == "won":
        ss.bankroll += bet * 2
    elif hs == "push":
        ss.bankroll += bet
    # bust / lost: the bet was already subtracted in place_bet

def _queue_outcome_sound():
    """After a round resolves, pick a win/lose sound from the hand statuses."""
    ss = st.session_state
    any_win = False
    any_loss = False
    for i in range(NUM_HANDS):
        if ss.bets[i] <= 0:
            continue
        s = ss.hand_statuses[i]
        if s == "won" or s == "blackjack_win":
            any_win = True
        if s == "lost" or s == "bust":
            any_loss = True
    # If both a win and a loss happened, a win is the louder moment
    if any_win:
        queue_sound("win")
    elif any_loss:
        queue_sound("lose")
    # All pushes: stay silent

def _dealer_play():
    """Dealer draws until 17+, then compare each still-in hand to the dealer."""
    ss = st.session_state

    # Does any player hand actually need the dealer to draw?
    has_stand = False
    for i in range(NUM_HANDS):
        if ss.hand_statuses[i] == "stand":
            has_stand = True

    if has_stand:
        while hand_value(ss.dealer) < 17:
            ss.dealer.append(ss.deck.pop())

    dv = hand_value(ss.dealer)
    for i in range(NUM_HANDS):
        if ss.bets[i] <= 0:
            continue
        hs = ss.hand_statuses[i]
        # Skip hands that already have a final outcome
        if hs == "bust" or hs == "blackjack_win" or hs == "push" or hs == "lost":
            continue
        if hs == "stand":
            pv = hand_value(ss.hands[i])
            if dv > 21:
                ss.hand_statuses[i] = "won"
            elif pv > dv:
                ss.hand_statuses[i] = "won"
            elif dv > pv:
                ss.hand_statuses[i] = "lost"
            else:
                ss.hand_statuses[i] = "push"
            _settle_hand(i)

    ss.status = "resolved"
    ss.active_hand = -1
    _queue_outcome_sound()

def _advance_hand():
    """Move play to the next waiting hand, or let the dealer play if none."""
    ss = st.session_state
    for i in range(ss.active_hand + 1, NUM_HANDS):
        if ss.hand_statuses[i] == "waiting":
            ss.hand_statuses[i] = "active"
            ss.active_hand = i
            return
    _dealer_play()

def deal_hand():
    """Start a new round: shuffle, deal 2 cards to each bet hand + dealer."""
    ss = st.session_state
    if ss.status != "betting":
        return
    if sum(ss.bets) == 0:
        return

    ss.deck = make_deck()
    ss.hands = [[], [], []]
    ss.dealer = []

    # Which hand indices actually have a bet on them
    active = []
    for i in range(NUM_HANDS):
        if ss.bets[i] > 0:
            active.append(i)

    # Deal two rounds: one card to each active hand, then one to the dealer
    for _ in range(2):
        for i in active:
            ss.hands[i].append(ss.deck.pop())
        ss.dealer.append(ss.deck.pop())

    # Check for blackjacks (dealer + each active player)
    dealer_bj = hand_value(ss.dealer) == 21
    statuses = ["idle"] * NUM_HANDS
    for i in active:
        player_bj = hand_value(ss.hands[i]) == 21
        if player_bj and dealer_bj:
            statuses[i] = "push"
        elif player_bj:
            statuses[i] = "blackjack_win"
        elif dealer_bj:
            statuses[i] = "lost"
        else:
            statuses[i] = "waiting"
    ss.hand_statuses = statuses

    # Settle hands that are already decided before play starts
    for i in active:
        hs = ss.hand_statuses[i]
        if hs == "blackjack_win" or hs == "push" or hs == "lost":
            _settle_hand(i)

    # Find the first hand that still needs the player to act
    first_playable = -1
    for i in active:
        if ss.hand_statuses[i] == "waiting":
            first_playable = i
            break

    if first_playable >= 0:
        ss.hand_statuses[first_playable] = "active"
        ss.active_hand = first_playable
        ss.status = "playing"
        queue_sound("card")
    else:
        # Everyone got an instant blackjack / push / lost on the deal
        ss.active_hand = -1
        ss.status = "resolved"
        _queue_outcome_sound()

def hit():
    """Player takes a card on the active hand; 22+ means bust → move on."""
    ss = st.session_state
    idx = ss.active_hand
    if ss.status != "playing":
        return
    if idx < 0:
        return
    ss.hands[idx].append(ss.deck.pop())
    queue_sound("card")
    if hand_value(ss.hands[idx]) > 21:
        ss.hand_statuses[idx] = "bust"
        _advance_hand()  # may overwrite sound with win/lose if round ends

def stand():
    """Player keeps their current total; move to the next hand."""
    ss = st.session_state
    idx = ss.active_hand
    if ss.status != "playing":
        return
    if idx < 0:
        return
    ss.hand_statuses[idx] = "stand"
    _advance_hand()

def double_down():
    """Double the current bet, take exactly one more card, then auto-stand.

    Classic rule: only legal on a fresh two-card hand, and the player must
    have enough bankroll to match the original bet.
    """
    ss = st.session_state
    idx = ss.active_hand
    if ss.status != "playing":
        return
    if idx < 0:
        return
    # Doubling is only legal on the initial two-card hand
    if len(ss.hands[idx]) != 2:
        return
    current_bet = ss.bets[idx]
    if current_bet > ss.bankroll:
        return

    # Match the existing bet
    ss.bankroll -= current_bet
    ss.bets[idx] += current_bet

    # Take exactly one card, no more hits after this
    ss.hands[idx].append(ss.deck.pop())
    queue_sound("card")
    if hand_value(ss.hands[idx]) > 21:
        ss.hand_statuses[idx] = "bust"
    else:
        ss.hand_statuses[idx] = "stand"
    _advance_hand()

def new_hand():
    """Clear the table for the next round (keep the bankroll)."""
    ss = st.session_state
    ss.hands = [[], [], []]
    ss.dealer = []
    ss.bets = [0, 0, 0]
    ss.hand_statuses = ["idle"] * NUM_HANDS
    ss.active_hand = -1
    ss.status = "betting"
    ss.selected_hand = 0

def reset_bankroll():
    """Player went broke — restart with $1000 and a fresh round."""
    st.session_state.bankroll = STARTING_BANKROLL
    new_hand()

# ---------------------------------------------------------------------------
# Styles — CSS injected into Streamlit
# ---------------------------------------------------------------------------

def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;900&family=Bebas+Neue&family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --gold:       #d4af37;
        --gold-light: #efd58a;
        --gold-dark:  #8a6e1a;
        --cream:      #f5ecd7;
        --ink:        #0a1e16;
        --felt-core:  #14683f;
        --felt-dark:  #0a3821;
        --wood-dark:  #2a180d;
        --wood-mid:   #6b5010;
    }

    /* ── Room background (outside the table) ────────────────────────────── */
    .stApp {
        background: radial-gradient(ellipse at 50% 0%, #111 0%, #050505 100%) !important;
        font-family: 'Inter', sans-serif;
    }

    /* ── Table surface (the felt) ──────────────────────────────────────── */
    [data-testid="stMainBlockContainer"],
    .main .block-container {
        max-width: 1000px !important;
        padding: 0 !important;
        background:
            radial-gradient(ellipse at 50% 40%,
                #1c7d4e 0%,
                var(--felt-core) 30%,
                #0f4a2e 70%,
                var(--felt-dark) 100%) !important;
        border-left:  14px solid var(--wood-mid) !important;
        border-right: 14px solid var(--wood-mid) !important;
        border-radius: 0 !important;
        box-shadow:
            -12px 0 30px rgba(0,0,0,0.9),
            12px 0 30px rgba(0,0,0,0.9),
            0 40px 80px rgba(0,0,0,0.95),
            inset 0 0 180px rgba(0,0,0,0.45) !important;
        margin-top: 0 !important;
    }

    /* ── Banner area (holds the arched casino headline) ─────────────────── */
    .table-banner {
        padding: 1.5rem 1rem 0.3rem;
        text-align: center;
    }
    .banner-svg {
        width: 100%;
        max-width: 920px;
        display: block;
        margin: 0 auto;
        filter: drop-shadow(0 4px 10px rgba(0,0,0,0.55));
    }
    .banner-insurance {
        font-family: 'Bebas Neue', Impact, sans-serif;
        font-size: clamp(1.3rem, 3vw, 2rem);
        letter-spacing: 0.18em;
        color: rgba(6, 40, 22, 0.72);
        text-shadow: 0 1px 0 rgba(255,255,255,0.05);
        margin-top: -0.4rem;
        padding-bottom: 0.5rem;
    }

    /* ── Dealer section ────────────────────────────────────────────────── */
    .dealer-area {
        padding: 0.6rem 2.5rem 1rem;
        text-align: center;
    }

    /* ── Gold rail separator ───────────────────────────────────────────── */
    .gold-rail {
        height: 12px;
        background: linear-gradient(180deg,
            #3d2200 0%, #6b5010 20%,
            #c9a227 48%, #efd58a 55%,
            #c9a227 65%, #6b5010 85%, #3d2200 100%);
        box-shadow:
            0 6px 18px rgba(0,0,0,0.6),
            inset 0 1px 2px rgba(255,240,180,0.3);
    }

    /* ── Player hands area ─────────────────────────────────────────────── */
    .player-area {
        padding: 1.2rem 2rem 0.6rem;
    }

    /* ── Controls area ─────────────────────────────────────────────────── */
    .controls-area {
        padding: 0.5rem 2.5rem 1.5rem;
    }

    /* ── Table bottom rail ─────────────────────────────────────────────── */
    .table-bottom-rail {
        background: linear-gradient(0deg,
            #150c04 0%, #2a180d 15%, #4a2e10 30%,
            #6b5010 50%, #c9a227 65%, #efd58a 72%,
            #c9a227 78%, #6b5010 88%, #2a180d 100%);
        padding: 0.8rem 2.5rem;
        text-align: center;
    }

    /* ── Typography ────────────────────────────────────────────────────── */
    h3 {
        font-family: 'Playfair Display', serif !important;
        color: var(--cream) !important;
        font-size: 1.2rem !important;
        letter-spacing: 0.12em !important;
        text-align: center !important;
        margin: 0.8rem 0 0.4rem !important;
        font-weight: 600 !important;
    }
    hr {
        border: none !important;
        border-top: 1px solid rgba(212,175,55,0.2) !important;
        margin: 0.6rem 0 !important;
    }

    /* ── Card row (centered flex) + deal animation ─────────────────────── */
    .cards-row {
        display: flex;
        justify-content: center;
        align-items: flex-end;
        gap: 6px;
        padding: 4px 0;
        min-height: 94px;
        perspective: 800px;
    }
    .cards-row--empty { min-height: 90px; }
    .card-img {
        border-radius: 5px;
        box-shadow:
            0 10px 24px rgba(0,0,0,0.8),
            0 2px 6px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.08);
        transition: transform 0.2s ease;
        animation: deal-card 0.55s cubic-bezier(.2,.7,.3,1.15) both;
        transform-origin: 50% 100%;
    }
    .card-img:hover {
        transform: translateY(-6px);
    }
    @keyframes deal-card {
        0% {
            transform: translate(0, -140px) rotate(-18deg) scale(0.85);
            opacity: 0;
        }
        55% { opacity: 1; }
        100% {
            transform: translate(0, 0) rotate(0) scale(1);
            opacity: 1;
        }
    }

    /* ── Action buttons (deal, hit, stand, reset, hand selector) ───────── */
    .stButton > button {
        font-family: 'Inter', sans-serif !important;
        text-transform: uppercase !important;
        letter-spacing: 0.14em !important;
        font-size: 0.78rem !important;
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
        box-shadow: 0 4px 18px rgba(212,175,55,0.55) !important;
    }
    .stButton > button:active:not([disabled]) {
        transform: translateY(1px) !important;
    }
    .stButton > button[disabled] {
        opacity: 0.3 !important;
        filter: grayscale(0.3);
    }

    /* ──────────────────────────────────────────────────────────────────
       REALISTIC CHIP BUTTONS
       Scoped to the container wrapper `st.container(key="chips_row")`,
       which Streamlit renders with class `st-key-chips_row`. Before, we
       targeted "any 5-column block" — that leaked into card rows and made
       cards show chip styling on hover. Each chip is two layered
       gradients: colored body on top, white edge-spot conic underneath.
       ────────────────────────────────────────────────────────────────── */

    .st-key-chips_row [data-testid="stColumn"] {
        display: flex !important;
        justify-content: center !important;
    }
    .st-key-chips_row button {
        border-radius: 50% !important;
        width: 74px !important;  min-width: 74px !important;  max-width: 74px !important;
        height: 74px !important; min-height: 74px !important;
        padding: 0 !important;
        font-family: 'Bebas Neue', Impact, sans-serif !important;
        font-size: 1.15rem !important;
        font-weight: 400 !important;
        letter-spacing: 0.03em !important;
        text-transform: none !important;
        border: none !important;
        box-shadow:
            0 7px 14px rgba(0,0,0,0.6),
            0 2px 4px rgba(0,0,0,0.4),
            inset 0 2px 3px rgba(255,255,255,0.3),
            inset 0 -3px 4px rgba(0,0,0,0.3) !important;
    }
    .st-key-chips_row button:hover:not([disabled]) {
        transform: translateY(-7px) rotate(-3deg) !important;
        box-shadow:
            0 14px 22px rgba(0,0,0,0.75),
            0 0 0 3px rgba(212,175,55,0.55),
            inset 0 2px 3px rgba(255,255,255,0.35),
            inset 0 -3px 4px rgba(0,0,0,0.3) !important;
    }
    .st-key-chips_row button:focus:not(:hover) { outline: none !important; }

    /* $1 — white chip / black edge spots */
    .st-key-chips_row [data-testid="stColumn"]:nth-child(1) button {
        background:
            radial-gradient(circle,
                #ffffff 0%, #ffffff 46%,
                #7b7b7b 46%, #7b7b7b 50%,
                transparent 50%),
            repeating-conic-gradient(from 11.25deg,
                #2a2a2a 0deg 22.5deg,
                #f0f0f0 22.5deg 45deg) !important;
        color: #222 !important;
    }
    /* $5 — red chip / white edge spots */
    .st-key-chips_row [data-testid="stColumn"]:nth-child(2) button {
        background:
            radial-gradient(circle,
                #e74c3c 0%, #c0392b 46%,
                #8b2410 46%, #8b2410 50%,
                transparent 50%),
            repeating-conic-gradient(from 11.25deg,
                #ffffff 0deg 22.5deg,
                #8b2410 22.5deg 45deg) !important;
        color: #fff !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
    }
    /* $25 — green chip / white edge spots */
    .st-key-chips_row [data-testid="stColumn"]:nth-child(3) button {
        background:
            radial-gradient(circle,
                #2ecc71 0%, #1a7a40 46%,
                #0f5230 46%, #0f5230 50%,
                transparent 50%),
            repeating-conic-gradient(from 11.25deg,
                #ffffff 0deg 22.5deg,
                #0f5230 22.5deg 45deg) !important;
        color: #fff !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
    }
    /* $100 — navy chip / white edge spots */
    .st-key-chips_row [data-testid="stColumn"]:nth-child(4) button {
        background:
            radial-gradient(circle,
                #34495e 0%, #2c3e50 46%,
                #17202a 46%, #17202a 50%,
                transparent 50%),
            repeating-conic-gradient(from 11.25deg,
                #ffffff 0deg 22.5deg,
                #17202a 22.5deg 45deg) !important;
        color: #fff !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
    }
    /* $500 — purple chip / white edge spots */
    .st-key-chips_row [data-testid="stColumn"]:nth-child(5) button {
        background:
            radial-gradient(circle,
                #a569bd 0%, #7d3c98 46%,
                #4a1f60 46%, #4a1f60 50%,
                transparent 50%),
            repeating-conic-gradient(from 11.25deg,
                #ffffff 0deg 22.5deg,
                #4a1f60 22.5deg 45deg) !important;
        color: #fff !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
    }

    /* ── Clickable bet-circle buttons (shown during betting) ──────────────
       Each of the 3 bet slots is wrapped in st.container(key="bet_circle_N"),
       which emits class `st-key-bet_circle_N`. The container is a
       stVerticalBlock (flex-direction: column), so horizontal centering
       needs `align-items: center`, not `justify-content`. */
    [class*="st-key-bet_circle_"] {
        align-items: center !important;
        margin: 6px 0 10px !important;
    }
    [class*="st-key-bet_circle_"] [data-testid="stElementContainer"] {
        width: auto !important;
    }
    [class*="st-key-bet_circle_"] button {
        width: 96px !important;
        height: 96px !important;
        min-width: 96px !important;
        max-width: 96px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        border: 3px dashed rgba(245,236,215,0.3) !important;
        background: rgba(0,0,0,0.2) !important;
        color: rgba(245,236,215,0.55) !important;
        font-family: 'Bebas Neue', Impact, sans-serif !important;
        font-size: 1.05rem !important;
        font-weight: 400 !important;
        letter-spacing: 0.14em !important;
        text-transform: none !important;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.35) !important;
        transition: all 0.25s ease !important;
    }
    [class*="st-key-bet_circle_"] button:hover:not([disabled]) {
        border-color: rgba(212,175,55,0.7) !important;
        color: #efd58a !important;
        background: rgba(212,175,55,0.08) !important;
        box-shadow: 0 0 18px rgba(212,175,55,0.35), inset 0 2px 10px rgba(0,0,0,0.35) !important;
        transform: scale(1.04) !important;
    }
    [class*="st-key-bet_circle_"] button[kind="primary"] {
        border-color: #d4af37 !important;
        background: rgba(212,175,55,0.18) !important;
        color: #d4af37 !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        letter-spacing: 0 !important;
        box-shadow: 0 0 26px rgba(212,175,55,0.6), inset 0 2px 10px rgba(0,0,0,0.35) !important;
    }
    [class*="st-key-bet_circle_"] button[kind="primary"]:hover {
        transform: scale(1.06) !important;
    }
    [class*="st-key-bet_circle_"] button:focus:not(:hover) { outline: none !important; }

    /* ── Bankroll metric ───────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.22) 100%) !important;
        border: 1.5px solid rgba(212,175,55,0.35) !important;
        border-radius: 12px !important;
        padding: 14px 20px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 6px 14px rgba(0,0,0,0.35) !important;
        text-align: center !important;
    }
    [data-testid="stMetricLabel"] p {
        font-family: 'Bebas Neue', Impact, sans-serif !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.26em !important;
        color: var(--gold-light) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Playfair Display', serif !important;
        font-size: 2.1rem !important;
        color: var(--gold) !important;
        text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }

    /* ── Small section labels ──────────────────────────────────────────── */
    .section-label {
        font-family: 'Bebas Neue', Impact, sans-serif;
        color: var(--gold-light);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.28em;
        opacity: 0.92;
        text-align: center;
        margin: 0.9rem 0 0.5rem;
    }

    /* ── Caption (playing-hand indicator) ──────────────────────────────── */
    [data-testid="stCaptionContainer"] p {
        color: var(--gold-light) !important;
        font-size: 0.7rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.22em !important;
        opacity: 0.8 !important;
        text-align: center !important;
    }

    /* ── Alert (out-of-chips warning) ──────────────────────────────────── */
    [data-testid="stAlert"] {
        background: rgba(200,50,40,0.12) !important;
        border: 1px solid rgba(231,76,60,0.4) !important;
        border-radius: 10px !important;
    }
    [data-testid="stAlert"] p {
        font-family: 'Playfair Display', serif !important;
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        color: var(--cream) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sound helper
# ---------------------------------------------------------------------------

def play_sound(kind):
    """Play a short synthesized sound via the Web Audio API.

    We render a hidden iframe (height=0) that contains a <script> tag. The
    script builds a tiny audio graph on the fly — no network calls, no audio
    files shipped with the app. Each `kind` gets its own little tune.

    To make the browser actually re-trigger the sound on repeated calls, the
    HTML we hand to components.html must differ every time. We add a
    time-based comment into the script as a cache-buster.
    """
    # Tiny per-kind audio programs (JavaScript strings).
    # All of them build an OscillatorNode + GainNode and ramp the gain down
    # so the note fades instead of cutting off abruptly.
    if kind == "chip":
        # Short, bright click — like a chip hitting the felt
        script = """
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.connect(g); g.connect(ctx.destination);
          o.type = 'square';
          o.frequency.value = 900;
          g.gain.setValueAtTime(0.08, ctx.currentTime);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
          o.start();
          o.stop(ctx.currentTime + 0.06);
        """
    elif kind == "card":
        # Short downward sweep — like a card sliding across the table
        script = """
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.connect(g); g.connect(ctx.destination);
          o.type = 'sawtooth';
          o.frequency.setValueAtTime(450, ctx.currentTime);
          o.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.12);
          g.gain.setValueAtTime(0.07, ctx.currentTime);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
          o.start();
          o.stop(ctx.currentTime + 0.16);
        """
    elif kind == "win":
        # Three rising notes (C5 → E5 → G5) — a little arpeggio
        script = """
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          function tone(freq, start, dur) {
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.connect(g); g.connect(ctx.destination);
            o.type = 'sine';
            o.frequency.value = freq;
            const t = ctx.currentTime + start;
            g.gain.setValueAtTime(0.14, t);
            g.gain.exponentialRampToValueAtTime(0.001, t + dur);
            o.start(t);
            o.stop(t + dur + 0.02);
          }
          tone(523.25, 0.00, 0.15);
          tone(659.25, 0.12, 0.17);
          tone(783.99, 0.26, 0.35);
        """
    elif kind == "lose":
        # One long downward slide — sad trombone-ish
        script = """
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.connect(g); g.connect(ctx.destination);
          o.type = 'triangle';
          o.frequency.setValueAtTime(350, ctx.currentTime);
          o.frequency.exponentialRampToValueAtTime(90, ctx.currentTime + 0.55);
          g.gain.setValueAtTime(0.13, ctx.currentTime);
          g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
          o.start();
          o.stop(ctx.currentTime + 0.6);
        """
    else:
        return

    # Unique timestamp comment → the HTML string differs each call →
    # Streamlit re-mounts the iframe → the script runs fresh.
    stamp = time.time_ns()
    html = f"<script>/* play {kind} {stamp} */ {script}</script>"
    components.html(html, height=0)

# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_cards(cards, width=72):
    """Show a row of cards centered, with a staggered deal-in animation.

    We build raw <img> tags instead of using st.image, because st.image:
      - lays cards out in a column grid (so they end up left-aligned),
      - wraps every image in a hidden fullscreen button that our chip CSS
        was accidentally styling as a red chip on hover.
    """
    if not cards:
        st.markdown(
            '<div class="cards-row cards-row--empty"></div>',
            unsafe_allow_html=True,
        )
        return

    # Build the row one <img> at a time, with a small stagger per card
    html = '<div class="cards-row">'
    for i, card in enumerate(cards):
        delay = f"{i * 0.09:.2f}s"
        html += f'<img class="card-img" src="{card_url(card)}" '
        html += f'style="width:{width}px; animation-delay:{delay};" '
        html += f'alt="{card}">'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_bet_circle(bet, status):
    """Draw the static dashed circle under a hand (once cards are dealt)."""
    # Pick colors based on the current status
    if status == "won" or status == "blackjack_win":
        bg = "rgba(46,204,113,0.16)"
        border = "#2ecc71"
        color = "#2ecc71"
    elif status == "bust" or status == "lost":
        bg = "rgba(231,76,60,0.16)"
        border = "#e74c3c"
        color = "#e74c3c"
    elif status == "push":
        bg = "rgba(150,160,150,0.16)"
        border = "#95a5a6"
        color = "#95a5a6"
    elif status == "active":
        bg = "rgba(212,175,55,0.18)"
        border = "#d4af37"
        color = "#d4af37"
    elif bet > 0:
        bg = "rgba(212,175,55,0.1)"
        border = "rgba(212,175,55,0.6)"
        color = "#efd58a"
    else:
        bg = "rgba(0,0,0,0.18)"
        border = "rgba(245,236,215,0.25)"
        color = "rgba(245,236,215,0.45)"

    # Gold glow only when this hand is the active one
    if status == "active":
        glow = "0 0 22px rgba(212,175,55,0.55)"
    else:
        glow = "none"

    # Inside-the-circle text: dollar amount or the word "BET"
    if bet > 0:
        text = f"${bet}"
        fsize = "1.6rem"
        fw = "700"
        ls = "0"
        font = "'Playfair Display',serif"
    else:
        text = "BET"
        fsize = "0.85rem"
        fw = "400"
        ls = "0.22em"
        font = "'Bebas Neue',Impact,sans-serif"

    st.markdown(f"""
    <div style="
        width:96px; height:96px; border-radius:50%;
        background:{bg};
        border:3px dashed {border};
        box-shadow:{glow}, inset 0 2px 10px rgba(0,0,0,0.35);
        display:flex; align-items:center; justify-content:center;
        margin: 6px auto 10px;
        font-family:{font};
        font-size:{fsize}; font-weight:{fw};
        color:{color}; letter-spacing:{ls};
        transition:all 0.3s;
    ">{text}</div>
    """, unsafe_allow_html=True)


def render_hand_badge(status):
    """Small 'Your Turn', 'Bust', 'Win!' etc. pill under a hand."""
    # HAND_BADGE is the dict defined at the top of the file
    if status in HAND_BADGE:
        text, color = HAND_BADGE[status]
    else:
        text = ""
        color = ""

    if not text:
        # Empty spacer so the layout height doesn't jump
        st.markdown('<div style="height:22px;"></div>', unsafe_allow_html=True)
        return

    # Add alpha suffixes to the hex color for the badge background/border
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
    """Draw one of the three player columns: label, bet circle, cards, badge."""
    ss = st.session_state
    hand = ss.hands[hand_idx]
    bet = ss.bets[hand_idx]
    status = ss.hand_statuses[hand_idx]

    # Current hand total (0 if no cards yet)
    if hand:
        val = hand_value(hand)
    else:
        val = 0

    is_betting = ss.status == "betting"
    is_active = status == "active"
    is_selected = is_betting and ss.selected_hand == hand_idx
    highlighted = is_active or is_selected

    # Title color + glow: gold when this hand is the focus, cream otherwise
    if highlighted:
        label_color = "#d4af37"
        shadow = "text-shadow:0 0 14px rgba(212,175,55,0.55);"
    else:
        label_color = "#e5d2a0"
        shadow = ""

    # Build the label like "HAND 2" or "HAND 2  ·  17"
    label = f"HAND {hand_idx + 1}"
    if val:
        label = label + f"  ·  {val}"

    st.markdown(
        f'<div style="font-family:\'Bebas Neue\',Impact,sans-serif;'
        f'font-size:0.95rem;font-weight:400;color:{label_color};text-align:center;'
        f'letter-spacing:0.24em;margin-bottom:2px;{shadow}">{label}</div>',
        unsafe_allow_html=True,
    )

    # During betting the circle is a real button (so you can click to select
    # which hand you're betting on). Otherwise it's just a static div.
    if is_betting:
        render_bet_button(hand_idx, bet, is_selected)
    else:
        render_bet_circle(bet, status)

    render_cards(hand, width=62)
    render_hand_badge(status)


def render_bet_button(hand_idx, bet, is_selected):
    """The bet spot during betting — a real button that selects that hand."""
    # Label: dollar amount if we've bet, otherwise "BET"
    if bet > 0:
        label = f"${bet}"
    else:
        label = "BET"

    # Primary style highlights the currently selected hand
    if is_selected:
        btype = "primary"
    else:
        btype = "secondary"

    # Wrap in a container with a known key so the CSS can target it
    with st.container(key=f"bet_circle_{hand_idx}"):
        if st.button(label, key=f"bet_btn_{hand_idx}", type=btype):
            st.session_state.selected_hand = hand_idx
            st.rerun()

# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Blackjack", page_icon="♠", layout="centered")
    inject_styles()
    init_state()

    # If the previous click queued up a sound, fire it off now (before
    # anything else renders so the audio starts while the UI paints).
    pending_sound = st.session_state.get("pending_sound")
    if pending_sound:
        play_sound(pending_sound)
        st.session_state.pending_sound = None

    # Pull out the state flags once so the rest of main() is easy to read
    ss = st.session_state
    is_betting = ss.status == "betting"
    is_playing = ss.status == "playing"
    is_resolved = ss.status == "resolved"
    reveal_dealer = is_resolved
    broke = ss.bankroll == 0 and sum(ss.bets) == 0 and is_betting

    # ── Banner: arched casino headline (inline SVG for the curve) ────────
    st.markdown("""
    <div class="table-banner">
      <svg class="banner-svg" viewBox="0 0 1000 200" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <path id="arcMain" d="M 80 160 Q 500 30 920 160" fill="none"/>
          <path id="arcSub"  d="M 130 190 Q 500 115 870 190" fill="none"/>
          <linearGradient id="goldGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%"   stop-color="#f6e6a7"/>
            <stop offset="45%"  stop-color="#d4af37"/>
            <stop offset="100%" stop-color="#7a5f18"/>
          </linearGradient>
        </defs>
        <text font-family="'Bebas Neue', Impact, sans-serif" font-size="62"
              fill="url(#goldGrad)" letter-spacing="4" text-anchor="middle">
          <textPath href="#arcMain" startOffset="50%">
            BLACKJACK PAYS 3 TO 2
          </textPath>
        </text>
        <text font-family="'Bebas Neue', Impact, sans-serif" font-size="22"
              fill="#efd58a" opacity="0.9" letter-spacing="3" text-anchor="middle">
          <textPath href="#arcSub" startOffset="50%">
            DEALER MUST DRAW TO 16 AND HIT ON SOFT 17
          </textPath>
        </text>
      </svg>
      <div class="banner-insurance">INSURANCE PAYS 2 TO 1</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Dealer section ───────────────────────────────────────────────────
    st.markdown('<div class="dealer-area">', unsafe_allow_html=True)

    # Decide which dealer cards and total to show. The hole (second) card
    # stays face-down until the round is resolved.
    if ss.dealer:
        if reveal_dealer:
            d_cards = ss.dealer
            d_val = hand_value(ss.dealer)
        else:
            d_cards = [ss.dealer[0], "back"]
            d_val = card_value(ss.dealer[0])
    else:
        d_cards = []
        d_val = 0

    if d_val:
        st.subheader(f"Dealer  —  {d_val}")
    else:
        st.subheader("Dealer")
    render_cards(d_cards, width=72)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Gold rail ────────────────────────────────────────────────────────
    st.markdown('<div class="gold-rail"></div>', unsafe_allow_html=True)

    # ── Player hand columns (3 bet zones) ────────────────────────────────
    st.markdown('<div class="player-area">', unsafe_allow_html=True)
    col0, col1, col2 = st.columns(3)
    with col0:
        render_hand_column(0)
    with col1:
        render_hand_column(1)
    with col2:
        render_hand_column(2)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Controls ─────────────────────────────────────────────────────────
    st.markdown('<div class="controls-area">', unsafe_allow_html=True)
    st.markdown("---")

    st.metric("Bankroll", f"${ss.bankroll}")

    if is_betting and not broke:
        # Hint line telling the user which hand the chips will land on
        selected = ss.selected_hand + 1
        st.markdown(
            f'<p class="section-label">Betting on Hand {selected}  '
            '<span style="opacity:0.6;">— click a bet circle to switch</span></p>',
            unsafe_allow_html=True,
        )

        # Chip row — the wrapping container gives a stable `st-key-chips_row`
        # class, which is what the chip CSS in inject_styles() targets.
        with st.container(key="chips_row"):
            chip_cols = st.columns(len(CHIP_VALUES))
            for i in range(len(CHIP_VALUES)):
                value = CHIP_VALUES[i]
                with chip_cols[i]:
                    too_rich = value > ss.bankroll
                    if st.button(f"${value}", key=f"chip_{value}", disabled=too_rich):
                        place_bet(value)
                        st.rerun()

        # Deal / Clear Bets — both disabled if no chips are down
        st.write("")
        no_bets = sum(ss.bets) == 0
        d_col, c_col = st.columns(2)
        if d_col.button("Deal", disabled=no_bets,
                        type="primary", use_container_width=True, key="btn_deal"):
            deal_hand()
            st.rerun()
        if c_col.button("Clear Bets", disabled=no_bets,
                        use_container_width=True, key="btn_clear"):
            for i in range(NUM_HANDS):
                clear_bet(i)
            queue_sound("chip")
            st.rerun()

    elif is_playing:
        active_idx = ss.active_hand
        active_val = hand_value(ss.hands[active_idx])
        current_bet = ss.bets[active_idx]
        num_cards = len(ss.hands[active_idx])
        st.caption(f"Playing Hand {active_idx + 1}  —  value: {active_val}")

        # Double Down is only legal on a fresh two-card hand, and only if
        # the bankroll has enough to match the existing bet.
        can_double = num_cards == 2 and current_bet <= ss.bankroll

        h_col, s_col, d_col = st.columns(3)
        if h_col.button("Hit", type="primary", use_container_width=True, key="btn_hit"):
            hit()
            st.rerun()
        if s_col.button("Stand", use_container_width=True, key="btn_stand"):
            stand()
            st.rerun()
        if d_col.button("Double", disabled=not can_double,
                        use_container_width=True, key="btn_double"):
            double_down()
            st.rerun()

    elif is_resolved:
        if st.button("Next Hand", type="primary",
                     use_container_width=True, key="btn_next"):
            new_hand()
            st.rerun()

    if broke:
        st.warning("You're out of chips!")
        if st.button("Reset Bankroll", type="primary",
                     use_container_width=True, key="btn_reset"):
            reset_bankroll()
            st.rerun()

    # ── Table bottom rail ────────────────────────────────────────────────
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="table-bottom-rail">
        <span style="font-family:'Bebas Neue',Impact,sans-serif; color:#efd58a;
                     font-size:0.75rem; text-transform:uppercase;
                     letter-spacing:0.24em; opacity:0.7;">
            Aces 1 or 11 &nbsp;·&nbsp; Face cards 10
            &nbsp;·&nbsp; Dealer hits on 16, stands on 17
        </span>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

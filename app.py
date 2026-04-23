from __future__ import annotations

import random
import streamlit as st

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


def init_state():
    defaults = {
        "deck": [],
        "player": [],
        "dealer": [],
        "status": "betting",
        "bankroll": STARTING_BANKROLL,
        "bet": 0,
        "last_bankroll": STARTING_BANKROLL,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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


def get_query_params():
    try:
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()  # type: ignore[attr-defined]
        except Exception:
            return {}


def clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()  # type: ignore[attr-defined]
        except Exception:
            pass


def process_action():
    params = get_query_params()
    action = params.get("action")
    amount = params.get("amount")

    if isinstance(action, list):
        action = action[0] if action else None
    if isinstance(amount, list):
        amount = amount[0] if amount else None

    if action == "bet" and amount is not None:
        try:
            place_bet(int(amount))
        except ValueError:
            pass
        clear_query_params()
        st.rerun()
    elif action == "clear_bet":
        clear_bet()
        clear_query_params()
        st.rerun()
    elif action == "deal":
        deal_hand()
        clear_query_params()
        st.rerun()
    elif action == "hit":
        hit()
        clear_query_params()
        st.rerun()
    elif action == "stand":
        stand()
        clear_query_params()
        st.rerun()
    elif action == "new_hand":
        new_hand()
        clear_query_params()
        st.rerun()
    elif action == "reset":
        reset_bankroll()
        clear_query_params()
        st.rerun()


def chip_link(value, disabled=False):
    cls = f"chip chip-{value}"
    if disabled:
        cls += " disabled"
        return f'<span class="{cls}">{value}</span>'
    return f'<a class="{cls}" href="?action=bet&amount={value}">{value}</a>'


def action_link(label, action, disabled=False, primary=False):
    cls = "action-btn"
    if primary:
        cls += " primary"
    if disabled:
        cls += " disabled"
        return f'<span class="{cls}">{label}</span>'
    return f'<a class="{cls}" href="?action={action}">{label}</a>'


def render_cards(cards):
    if not cards:
        return '<div class="cards"></div>'
    imgs = "".join(f'<img src="{card_image_url(card)}" alt="{card}">' for card in cards)
    return f'<div class="cards">{imgs}</div>'


def render_status(status):
    text = STATUS_TEXT.get(status, "")
    cls = "status"
    if status in WIN_STATUSES:
        cls += " win"
    elif status in LOSE_STATUSES:
        cls += " lose"
    elif status == "push":
        cls += " push"
    return f'<div class="{cls}">{text}</div>' if text else '<div class="status"></div>'


def page_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;700&family=Inter:wght@400;600;800&display=swap');

        :root {
            --felt-dark: #0e3324;
            --felt-mid: #17543a;
            --felt-light: #1e6b48;
            --gold: #d4af37;
            --gold-light: #efd58a;
            --cream: #f5ecd7;
            --ink: #0a1e16;
            --shadow: rgba(0, 0, 0, 0.45);
        }

        html, body, [class*="stApp"] {
            margin: 0;
            padding: 0;
            min-height: 100vh;
            background:
                radial-gradient(ellipse 120% 80% at 50% 45%, var(--felt-light) 0%, var(--felt-mid) 40%, var(--felt-dark) 100%),
                var(--felt-dark) !important;
            color: var(--cream) !important;
            font-family: 'Inter', sans-serif;
        }

        [class*="stApp"]::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                radial-gradient(circle at 20% 30%, rgba(255,255,255,0.03) 1px, transparent 1px),
                radial-gradient(circle at 70% 80%, rgba(0,0,0,0.04) 1px, transparent 1px);
            background-size: 3px 3px, 5px 5px;
            opacity: 0.6;
            z-index: 0;
        }

        [data-testid="stHeader"], [data-testid="stToolbar"], footer { visibility: hidden; height: 0; }
        .block-container {
            max-width: 860px;
            margin: 0 auto;
            padding: 32px 20px 48px;
            position: relative;
            z-index: 1;
        }
        main.table {
            max-width: 860px;
            margin: 0 auto;
            position: relative;
            padding: 36px 28px;
            border: 2px solid var(--gold);
            border-radius: 180px / 120px;
            box-shadow:
                inset 0 0 60px rgba(0, 0, 0, 0.4),
                inset 0 0 0 8px rgba(212, 175, 55, 0.12),
                0 20px 60px var(--shadow);
            text-align: center;
        }
        header { margin-bottom: 24px; }
        h1 {
            font-family: 'Cormorant Garamond', serif;
            font-weight: 700;
            font-size: clamp(2.4rem, 6vw, 3.6rem);
            letter-spacing: 0.06em;
            margin: 0;
            color: var(--gold);
            text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
        }
        .subtitle {
            margin: 6px 0 0;
            font-size: 0.78rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--gold-light);
            opacity: 0.72;
        }
        .hand { margin: 14px 0; }
        .hand-label {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 14px;
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.4rem;
            letter-spacing: 0.08em;
            margin-bottom: 10px;
            color: var(--gold-light);
        }
        .value {
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            padding: 2px 10px;
            border: 1px solid var(--gold);
            border-radius: 999px;
            color: var(--cream);
            min-width: 30px;
            min-height: 24px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .value:empty { display: none; }
        .cards {
            min-height: 130px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .cards img {
            width: 92px;
            height: auto;
            border-radius: 8px;
            box-shadow:
                0 6px 14px rgba(0, 0, 0, 0.5),
                0 0 0 1px rgba(0, 0, 0, 0.2);
            animation: deal 0.35s ease-out;
            background: white;
        }
        @keyframes deal {
            from { transform: translateY(-24px) rotate(-6deg); opacity: 0; }
            to { transform: translateY(0) rotate(0); opacity: 1; }
        }
        .status {
            min-height: 34px;
            margin: 12px 0;
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: var(--gold);
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
        }
        .status.win { color: var(--gold-light); }
        .status.lose { color: #e8a0a0; }
        .status.push { color: var(--cream); opacity: 0.85; }
        .info-row {
            display: flex;
            justify-content: center;
            gap: 48px;
            margin: 16px 0 14px;
        }
        .info-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2px;
        }
        .info-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.65rem;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            color: var(--gold-light);
            opacity: 0.7;
        }
        .info-value {
            font-family: 'Cormorant Garamond', serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--gold);
            transition: color 0.3s ease, transform 0.2s ease;
        }
        .info-value.flash { color: var(--gold-light); transform: scale(1.08); }
        .chips {
            display: flex;
            justify-content: center;
            gap: 14px;
            flex-wrap: wrap;
            margin: 10px 0 18px;
        }
        .chip {
            width: 68px;
            height: 68px;
            border-radius: 50%;
            display: grid;
            place-items: center;
            font-family: 'Inter', sans-serif;
            font-weight: 800;
            font-size: 0.95rem;
            color: white;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
            box-shadow:
                0 5px 12px rgba(0, 0, 0, 0.5),
                inset 0 -4px 8px rgba(0, 0, 0, 0.3);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            padding: 0;
            letter-spacing: 0;
            text-decoration: none;
        }
        .chip:hover { transform: translateY(-5px); }
        .chip:active { transform: translateY(-2px); }
        .chip.disabled { opacity: 0.3; pointer-events: none; }
        .chip-1   { background: radial-gradient(circle, #f5f5f5 0 54%, transparent 54.5%), repeating-conic-gradient(#b8b8b8 0deg 30deg, #ffffff 30deg 36deg, #b8b8b8 36deg 60deg); color: #2c3e50; text-shadow: none; }
        .chip-5   { background: radial-gradient(circle, #e74c3c 0 54%, transparent 54.5%), repeating-conic-gradient(#a93226 0deg 30deg, #ffffff 30deg 36deg, #a93226 36deg 60deg); }
        .chip-25  { background: radial-gradient(circle, #27ae60 0 54%, transparent 54.5%), repeating-conic-gradient(#145a32 0deg 30deg, #ffffff 30deg 36deg, #145a32 36deg 60deg); }
        .chip-100 { background: radial-gradient(circle, #34495e 0 54%, transparent 54.5%), repeating-conic-gradient(#17202a 0deg 30deg, #ffffff 30deg 36deg, #17202a 36deg 60deg); }
        .chip-500 { background: radial-gradient(circle, #9b59b6 0 54%, transparent 54.5%), repeating-conic-gradient(#5b2c6f 0deg 30deg, #ffffff 30deg 36deg, #5b2c6f 36deg 60deg); }
        .actions {
            margin-top: 8px;
            display: flex;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
            min-height: 46px;
        }
        .action-btn {
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            padding: 12px 28px;
            border: 1px solid var(--gold);
            border-radius: 4px;
            cursor: pointer;
            background: linear-gradient(180deg, #1a4a35 0%, #123726 100%);
            color: var(--gold-light);
            transition: transform 0.12s ease, background 0.2s ease, box-shadow 0.2s ease;
            text-decoration: none;
            display: inline-block;
        }
        .action-btn:hover {
            background: linear-gradient(180deg, var(--gold) 0%, #b89528 100%);
            color: var(--ink);
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.4);
        }
        .action-btn:active { transform: translateY(0); }
        .action-btn.disabled { opacity: 0.35; pointer-events: none; }
        .footer-note {
            margin-top: 18px;
            font-size: 0.8rem;
            opacity: 0.85;
            text-align: center;
        }
        @media (max-width: 600px) {
            main.table { border-radius: 24px; padding: 24px 14px; }
            .cards img { width: 64px; }
            .chip { width: 58px; height: 58px; font-size: 0.85rem; }
            .chips { gap: 10px; }
            .action-btn { padding: 10px 16px; font-size: 0.8rem; }
            .info-row { gap: 28px; }
            .info-value { font-size: 1.5rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Blackjack", page_icon="♠", layout="centered")
    init_state()
    process_action()
    page_css()

    is_betting = st.session_state.status == "betting"
    is_playing = st.session_state.status == "playing"
    is_resolved = not is_betting and not is_playing
    broke = st.session_state.bankroll == 0 and st.session_state.bet == 0 and is_betting

    if st.session_state.dealer:
        if st.session_state.status in ("betting", "playing"):
            dealer_cards = [st.session_state.dealer[0], "back"]
            dealer_val = card_value(st.session_state.dealer[0])
        else:
            dealer_cards = st.session_state.dealer
            dealer_val = hand_value(st.session_state.dealer)
    else:
        dealer_cards = []
        dealer_val = 0

    player_val = hand_value(st.session_state.player) if st.session_state.player else 0

    chips_html = ""
    if is_betting and not broke:
        for value in CHIP_VALUES:
            disabled = value > st.session_state.bankroll
            chips_html += chip_link(value, disabled=disabled)

    if is_betting and not broke:
        actions_html = (
            action_link("Deal", "deal", disabled=st.session_state.bet == 0, primary=True)
            + action_link("Clear Bet", "clear_bet", disabled=st.session_state.bet == 0)
        )
    elif is_playing:
        actions_html = action_link("Hit", "hit", primary=True) + action_link("Stand", "stand")
    else:
        actions_html = action_link("Next Hand", "new_hand", primary=True)

    reset_html = ""
    if broke:
        reset_html = action_link("Reset Bankroll", "reset", primary=True)

    bankroll_flash = "flash" if st.session_state.bankroll != st.session_state.last_bankroll else ""
    st.session_state.last_bankroll = st.session_state.bankroll

    html = f"""
    <main class="table">
        <header>
            <h1>Blackjack</h1>
            <p class="subtitle">Dealer stands on 17 · Blackjack pays 3 to 2</p>
        </header>

        <section class="hand dealer">
            <div class="hand-label">
                <span>Dealer</span>
                <span class="value">{dealer_val if dealer_val else ""}</span>
            </div>
            {render_cards(dealer_cards)}
        </section>

        {render_status(st.session_state.status)}

        <section class="hand player">
            <div class="hand-label">
                <span>You</span>
                <span class="value">{player_val if player_val else ""}</span>
            </div>
            {render_cards(st.session_state.player)}
        </section>

        <div class="info-row">
            <div class="info-item">
                <span class="info-label">Bankroll</span>
                <span class="info-value {bankroll_flash}">${st.session_state.bankroll}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Bet</span>
                <span class="info-value">${st.session_state.bet}</span>
            </div>
        </div>

        <div class="chips">{chips_html}</div>
        <div class="actions">{actions_html}</div>
        {'<div class="actions" style="margin-top:14px;">' + reset_html + '</div>' if reset_html else ''}

        <p class="footer-note">Aces count as 1 or 11 · Face cards are 10 · Dealer must hit on 16 and stand on 17</p>
    </main>
    """

    st.markdown(html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

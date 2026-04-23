"""
Blackjack with betting — a pure-Python Streamlit app.

Run locally with:
    streamlit run app.py

All game logic and UI are implemented in Python using Streamlit.
No HTML/CSS/JS files required.
"""

import random

import streamlit as st

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
        # 3:2 payout — bet back plus 1.5x winnings
        st.session_state.bankroll += bet + (bet * 3) // 2
    elif status in ("player_wins", "dealer_bust"):
        # Even money — bet back plus equal winnings
        st.session_state.bankroll += bet * 2
    elif status == "push":
        # Bet returned
        st.session_state.bankroll += bet
    # Losing statuses: bet already deducted, stays with house


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
# UI helpers
# ---------------------------------------------------------------------------

def render_cards(cards):
    """Lay cards out in a row using Streamlit columns."""
    if not cards:
        # Keep a bit of vertical space so the table layout stays stable
        st.write("")
        return
    # Use at least 5 columns so a single card sits on the left instead
    # of stretching across the full width.
    n_cols = max(len(cards), 5)
    cols = st.columns(n_cols)
    for i, card in enumerate(cards):
        with cols[i]:
            st.image(card_image_url(card), width=90)


def render_status(status):
    text = STATUS_TEXT.get(status, "")
    if not text:
        return
    if status in WIN_STATUSES:
        st.success(f"**{text}**")
    elif status in LOSE_STATUSES:
        st.error(f"**{text}**")
    elif status == "push":
        st.warning(f"**{text}**")
    else:
        st.info(text)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Blackjack", page_icon="♠", layout="centered")
    init_state()

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

    st.title("♠ Blackjack ♣")
    st.caption("Dealer stands on 17 · Blackjack pays 3 to 2")

    # -------- Dealer hand --------
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
    render_cards(dealer_cards)

    # -------- Status --------
    st.markdown("---")
    render_status(status)

    # -------- Player hand --------
    player_val = hand_value(st.session_state.player) if st.session_state.player else 0
    player_label = "You" + (f" — {player_val}" if player_val else "")
    st.subheader(player_label)
    render_cards(st.session_state.player)

    st.markdown("---")

    # -------- Bankroll / bet --------
    col_bank, col_bet = st.columns(2)
    col_bank.metric("Bankroll", f"${st.session_state.bankroll}")
    col_bet.metric("Bet", f"${st.session_state.bet}")

    # -------- Chips --------
    if is_betting and not broke:
        st.write("**Chips**")
        chip_cols = st.columns(len(CHIP_VALUES))
        for i, value in enumerate(CHIP_VALUES):
            with chip_cols[i]:
                if st.button(
                    f"${value}",
                    key=f"chip_{value}",
                    disabled=value > st.session_state.bankroll,
                    use_container_width=True,
                ):
                    place_bet(value)
                    st.rerun()

    # -------- Action buttons --------
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

    # -------- Footer --------
    st.markdown("---")
    st.caption(
        "Aces count as 1 or 11 · Face cards are 10 · Dealer must hit on 16 and stand on 17"
    )


if __name__ == "__main__":
    main()

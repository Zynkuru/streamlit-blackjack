"""Blackjack with betting — self-contained pure-Python app.

Run locally with:
    python app.py

This single file serves the same visuals and interaction model as the
browser version, but without needing separate HTML/CSS/JS files.
"""

from __future__ import annotations

import json
import os
import random
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Timer
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Game logic
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

STATUS_CLASS = {
    "blackjack": "win",
    "dealer_bust": "win",
    "player_wins": "win",
    "player_bust": "lose",
    "dealer_wins": "lose",
    "dealer_blackjack": "lose",
    "push": "push",
}


def make_deck() -> list[str]:
    deck = [rank + suit for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def card_value(card: str) -> int:
    rank = card[:-1]
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)


def hand_value(hand: list[str]) -> int:
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c[:-1] == "A")
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def card_image_url(card: str) -> str:
    if card == "back":
        return "https://deckofcardsapi.com/static/img/back.png"
    rank = card[:-1]
    suit = card[-1]
    r = "0" if rank == "10" else rank
    return f"https://deckofcardsapi.com/static/img/{r}{suit}.png"


# Single shared game state
game = {
    "deck": [],
    "player": [],
    "dealer": [],
    "status": "betting",
    "bankroll": STARTING_BANKROLL,
    "bet": 0,
}


def settle_bet() -> None:
    status = game["status"]
    bet = game["bet"]
    if status == "blackjack":
        game["bankroll"] += bet + (bet * 3) // 2
    elif status in ("player_wins", "dealer_bust"):
        game["bankroll"] += bet * 2
    elif status == "push":
        game["bankroll"] += bet


def place_bet(amount: int) -> None:
    if game["status"] != "betting":
        return
    if amount not in CHIP_VALUES:
        return
    if amount > game["bankroll"]:
        return
    game["bankroll"] -= amount
    game["bet"] += amount


def clear_bet() -> None:
    if game["status"] != "betting":
        return
    game["bankroll"] += game["bet"]
    game["bet"] = 0


def deal_hand() -> None:
    if game["status"] != "betting" or game["bet"] <= 0:
        return
    game["deck"] = make_deck()
    game["player"] = [game["deck"].pop(), game["deck"].pop()]
    game["dealer"] = [game["deck"].pop(), game["deck"].pop()]

    pv = hand_value(game["player"])
    dv = hand_value(game["dealer"])

    if pv == 21 and dv == 21:
        game["status"] = "push"
    elif pv == 21:
        game["status"] = "blackjack"
    elif dv == 21:
        game["status"] = "dealer_blackjack"
    else:
        game["status"] = "playing"

    if game["status"] != "playing":
        settle_bet()


def hit() -> None:
    if game["status"] != "playing":
        return
    game["player"].append(game["deck"].pop())
    if hand_value(game["player"]) > 21:
        game["status"] = "player_bust"
        settle_bet()


def stand() -> None:
    if game["status"] != "playing":
        return
    while hand_value(game["dealer"]) < 17:
        game["dealer"].append(game["deck"].pop())

    pv = hand_value(game["player"])
    dv = hand_value(game["dealer"])
    if dv > 21:
        game["status"] = "dealer_bust"
    elif pv > dv:
        game["status"] = "player_wins"
    elif dv > pv:
        game["status"] = "dealer_wins"
    else:
        game["status"] = "push"
    settle_bet()


def new_hand() -> None:
    game["player"] = []
    game["dealer"] = []
    game["bet"] = 0
    game["status"] = "betting"


def reset_bankroll() -> None:
    game["bankroll"] = STARTING_BANKROLL
    game["bet"] = 0
    game["player"] = []
    game["dealer"] = []
    game["status"] = "betting"


def state() -> dict:
    reveal_dealer = game["status"] not in ("playing", "betting")
    if game["dealer"]:
        if reveal_dealer:
            dealer_cards = game["dealer"]
            dealer_val = hand_value(game["dealer"])
        else:
            dealer_cards = [game["dealer"][0], "back"]
            dealer_val = card_value(game["dealer"][0])
    else:
        dealer_cards = []
        dealer_val = 0

    return {
        "player": game["player"],
        "dealer": dealer_cards,
        "player_value": hand_value(game["player"]) if game["player"] else 0,
        "dealer_value": dealer_val,
        "status": game["status"],
        "bankroll": game["bankroll"],
        "bet": game["bet"],
        "chip_values": CHIP_VALUES,
        "status_text": STATUS_TEXT.get(game["status"], ""),
        "status_class": STATUS_CLASS.get(game["status"], ""),
    }


# ---------------------------------------------------------------------------
# Embedded assets (same structure as the browser version)
# ---------------------------------------------------------------------------

INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Blackjack</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;700&family=Inter:wght@400;600;800&display=swap\" rel=\"stylesheet\">
    <link rel=\"stylesheet\" href=\"/style.css\">
</head>
<body>
    <main class=\"table\">
        <header>
            <h1>Blackjack</h1>
            <p class=\"subtitle\">Dealer stands on 17 · Blackjack pays 3 to 2</p>
        </header>

        <section class=\"hand dealer\">
            <div class=\"hand-label\">
                <span>Dealer</span>
                <span id=\"dealer-value\" class=\"value\"></span>
            </div>
            <div id=\"dealer-cards\" class=\"cards\"></div>
        </section>

        <div id=\"status\" class=\"status\"></div>

        <section class=\"hand player\">
            <div class=\"hand-label\">
                <span>You</span>
                <span id=\"player-value\" class=\"value\"></span>
            </div>
            <div id=\"player-cards\" class=\"cards\"></div>
        </section>

        <div class=\"info-row\">
            <div class=\"info-item\">
                <span class=\"info-label\">Bankroll</span>
                <span id=\"bankroll\" class=\"info-value\">$1000</span>
            </div>
            <div class=\"info-item\">
                <span class=\"info-label\">Bet</span>
                <span id=\"bet\" class=\"info-value\">$0</span>
            </div>
        </div>

        <div id=\"chips\" class=\"chips\"></div>

        <div class=\"actions\">
            <button id=\"deal\">Deal</button>
            <button id=\"clear\">Clear Bet</button>
            <button id=\"hit\">Hit</button>
            <button id=\"stand\">Stand</button>
            <button id=\"next\">Next Hand</button>
            <button id=\"reset\">Reset Bankroll</button>
        </div>
    </main>

    <script src=\"/script.js\"></script>
</body>
</html>
"""

STYLE_CSS = """:root {
    --felt-dark: #0e3324;
    --felt-mid: #17543a;
    --felt-light: #1e6b48;
    --gold: #d4af37;
    --gold-light: #efd58a;
    --cream: #f5ecd7;
    --ink: #0a1e16;
    --shadow: rgba(0, 0, 0, 0.45);
}

* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    min-height: 100vh;
}

body {
    font-family: 'Inter', sans-serif;
    color: var(--cream);
    background:
        radial-gradient(ellipse 120% 80% at 50% 45%, var(--felt-light) 0%, var(--felt-mid) 40%, var(--felt-dark) 100%),
        var(--felt-dark);
    padding: 32px 20px 48px;
}

body::before {
    content: \"\";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
        radial-gradient(circle at 20% 30%, rgba(255,255,255,0.03) 1px, transparent 1px),
        radial-gradient(circle at 70% 80%, rgba(0,0,0,0.04) 1px, transparent 1px);
    background-size: 3px 3px, 5px 5px;
    opacity: 0.6;
}

.table {
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

header {
    margin-bottom: 24px;
}

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

.hand {
    margin: 14px 0;
}

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

.value:empty {
    display: none;
}

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
    from {
        transform: translateY(-24px) rotate(-6deg);
        opacity: 0;
    }
    to {
        transform: translateY(0) rotate(0);
        opacity: 1;
    }
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

.info-value.flash {
    color: var(--gold-light);
    transform: scale(1.08);
}

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
    cursor: pointer;
    border: none;
    display: grid;
    place-items: center;
    font-family: 'Inter', sans-serif;
    font-weight: 800;
    font-size: 0.95rem;
    color: white;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
    background:
        radial-gradient(circle, var(--chip-light) 0 54%, transparent 54.5%),
        repeating-conic-gradient(
            var(--chip-dark) 0deg 30deg,
            #ffffff 30deg 36deg,
            var(--chip-dark) 36deg 60deg
        );
    box-shadow:
        0 5px 12px rgba(0, 0, 0, 0.5),
        inset 0 -4px 8px rgba(0, 0, 0, 0.3);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    padding: 0;
    letter-spacing: 0;
}

.chip:hover:not(:disabled) {
    transform: translateY(-5px);
    box-shadow:
        0 10px 18px rgba(0, 0, 0, 0.5),
        inset 0 -4px 8px rgba(0, 0, 0, 0.3);
}

.chip:active:not(:disabled) {
    transform: translateY(-2px);
}

.chip:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    transform: none;
}

.chip-1   { --chip-light: #f5f5f5; --chip-dark: #b8b8b8; color: #2c3e50; text-shadow: none; }
.chip-5   { --chip-light: #e74c3c; --chip-dark: #a93226; }
.chip-25  { --chip-light: #27ae60; --chip-dark: #145a32; }
.chip-100 { --chip-light: #34495e; --chip-dark: #17202a; }
.chip-500 { --chip-light: #9b59b6; --chip-dark: #5b2c6f; }

.actions {
    margin-top: 8px;
    display: flex;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
    min-height: 46px;
}

.actions button {
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
}

.actions button:hover:not(:disabled) {
    background: linear-gradient(180deg, var(--gold) 0%, #b89528 100%);
    color: var(--ink);
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0, 0, 0, 0.4);
}

.actions button:active:not(:disabled) {
    transform: translateY(0);
}

.actions button:disabled {
    opacity: 0.35;
    cursor: not-allowed;
}

.actions button[hidden] {
    display: none;
}

@media (max-width: 600px) {
    .table {
        border-radius: 24px;
        padding: 24px 14px;
    }
    .cards img {
        width: 64px;
    }
    .chip {
        width: 58px;
        height: 58px;
        font-size: 0.85rem;
    }
    .chips {
        gap: 10px;
    }
    .actions button {
        padding: 10px 16px;
        font-size: 0.8rem;
    }
    .info-row {
        gap: 28px;
    }
    .info-value {
        font-size: 1.5rem;
    }
}
"""

SCRIPT_JS = """const CHIPS = [1, 5, 25, 100, 500];

function cardImg(card) {
    if (card === \"back\") {
        return \"https://deckofcardsapi.com/static/img/back.png\";
    }
    const rank = card.slice(0, -1);
    const suit = card.slice(-1);
    const r = rank === \"10\" ? \"0\" : rank;
    return `https://deckofcardsapi.com/static/img/${r}${suit}.png`;
}

const STATUS_TEXT = {
    betting: \"Place your bet\",
    playing: \"\",
    blackjack: \"Blackjack! Pays 3 to 2\",
    player_bust: \"Bust\",
    dealer_bust: \"Dealer busts — you win!\",
    player_wins: \"You win!\",
    dealer_wins: \"Dealer wins\",
    dealer_blackjack: \"Dealer has blackjack\",
    push: \"Push\",
};

const STATUS_CLASS = {
    blackjack: \"win\",
    dealer_bust: \"win\",
    player_wins: \"win\",
    player_bust: \"lose\",
    dealer_wins: \"lose\",
    dealer_blackjack: \"lose\",
    push: \"push\",
};

const chipsEl = document.getElementById(\"chips\");
CHIPS.forEach((val) => {
    const btn = document.createElement(\"button\");
    btn.className = `chip chip-${val}`;
    btn.textContent = val;
    btn.dataset.amount = val;
    btn.addEventListener(\"click\", () => api(`bet?amount=${val}`));
    chipsEl.appendChild(btn);
});

let lastBankroll = null;

async function api(endpoint) {
    const res = await fetch(\"/api/\" + endpoint);
    const state = await res.json();
    render(state);
    return state;
}

function render(state) {
    document.getElementById(\"player-cards\").innerHTML = state.player
        .map((c) => `<img src=\"${cardImg(c)}\" alt=\"${c}\">`)
        .join(\"\");
    document.getElementById(\"dealer-cards\").innerHTML = state.dealer
        .map((c) => `<img src=\"${cardImg(c)}\" alt=\"${c}\">`)
        .join(\"\");

    document.getElementById(\"player-value\").textContent = state.player_value || \"\";
    document.getElementById(\"dealer-value\").textContent = state.dealer_value || \"\";

    const bankrollEl = document.getElementById(\"bankroll\");
    bankrollEl.textContent = `$${state.bankroll}`;
    if (lastBankroll !== null && state.bankroll !== lastBankroll) {
        bankrollEl.classList.add(\"flash\");
        setTimeout(() => bankrollEl.classList.remove(\"flash\"), 400);
    }
    lastBankroll = state.bankroll;
    document.getElementById(\"bet\").textContent = `$${state.bet}`;

    const statusEl = document.getElementById(\"status\");
    statusEl.textContent = STATUS_TEXT[state.status] || \"\";
    statusEl.className = \"status \" + (STATUS_CLASS[state.status] || \"\");

    const isBetting = state.status === \"betting\";
    const isPlaying = state.status === \"playing\";
    const isResolved = !isBetting && !isPlaying;
    const broke = state.bankroll === 0 && state.bet === 0 && isBetting;

    setVisible(\"deal\", isBetting && !broke);
    setVisible(\"clear\", isBetting && state.bet > 0);
    setVisible(\"hit\", isPlaying);
    setVisible(\"stand\", isPlaying);
    setVisible(\"next\", isResolved);
    setVisible(\"reset\", broke);

    document.getElementById(\"deal\").disabled = state.bet === 0;

    document.querySelectorAll(\".chip\").forEach((chip) => {
        const amount = parseInt(chip.dataset.amount, 10);
        chip.disabled = !isBetting || amount > state.bankroll;
    });
}

function setVisible(id, visible) {
    const el = document.getElementById(id);
    if (visible) el.removeAttribute(\"hidden\");
    else el.setAttribute(\"hidden\", \"\");
}

document.getElementById(\"deal\").addEventListener(\"click\", () => api(\"deal\"));
document.getElementById(\"clear\").addEventListener(\"click\", () => api(\"clear_bet\"));
document.getElementById(\"hit\").addEventListener(\"click\", () => api(\"hit\"));
document.getElementById(\"stand\").addEventListener(\"click\", () => api(\"stand\"));
document.getElementById(\"next\").addEventListener(\"click\", () => api(\"new_hand\"));
document.getElementById(\"reset\").addEventListener(\"click\", () => api(\"reset\"));

api(\"state\");
"""


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in {"/", "/index.html"}:
            self._send_text(INDEX_HTML, "text/html; charset=utf-8")
            return
        if path == "/style.css":
            self._send_text(STYLE_CSS, "text/css; charset=utf-8")
            return
        if path == "/script.js":
            self._send_text(SCRIPT_JS, "application/javascript; charset=utf-8")
            return

        if path == "/api/state":
            pass
        elif path == "/api/bet":
            try:
                amount = int(params.get("amount", ["0"])[0])
                place_bet(amount)
            except (ValueError, IndexError):
                pass
        elif path == "/api/clear_bet":
            clear_bet()
        elif path == "/api/deal":
            deal_hand()
        elif path == "/api/hit":
            hit()
        elif path == "/api/stand":
            stand()
        elif path == "/api/new_hand":
            new_hand()
        elif path == "/api/reset":
            reset_bankroll()
        else:
            self.send_response(404)
            self.end_headers()
            return

        self._send_json(state())

    def _send_text(self, text: str, content_type: str) -> None:
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, obj: dict) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


PORT = 8000


def open_browser() -> None:
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"Blackjack is running at http://localhost:{PORT}")
    print("A browser tab should open automatically. Press Ctrl+C to stop.")
    Timer(1.0, open_browser).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()

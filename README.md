# Streamlit Blackjack

A classic single-player Blackjack casino game, built entirely in Python with [Streamlit](https://streamlit.io). Play in your browser with chips, bets, and the standard 3-to-2 blackjack payout.

## Features

- Standard Blackjack rules (dealer stands on 17, blackjack pays 3:2)
- $1,000 starting bankroll with chip denominations of $1, $5, $25, $100, and $500
- Hit, Stand, Deal, Clear Bet, Next Hand, and Reset Bankroll actions
- Face-down dealer hole card until the hand resolves
- 100% Python — no HTML, CSS, or JavaScript files

## Play online

Deploy it free on [Streamlit Community Cloud](https://streamlit.io/cloud) — see the deployment section below. Once deployed, your app lives at `https://<your-app-name>.streamlit.app`.

## Run locally

Requires Python 3.9 or newer.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

## How to play

1. **Place your bet** by clicking chips ($1, $5, $25, $100, $500). Click "Clear Bet" to undo.
2. **Deal** — two cards to you, two to the dealer (one face down).
3. **Hit** to take another card, or **Stand** to keep what you have. Over 21 and you bust.
4. Closest to 21 without going over wins. Aces count as 1 or 11. Face cards are 10.

### Payouts

| Outcome | Payout |
|---|---|
| Blackjack (21 on deal) | **3 to 2** |
| Regular win | 1 to 1 |
| Push (tie) | Bet returned |
| Loss | Bet lost |

If you run out of chips, a "Reset Bankroll" button appears to restore you to $1,000.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (see the publishing instructions shared alongside this project).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
3. Click **New app**, pick this repository, set the main file to `app.py`, and click **Deploy**.
4. Your app will be live at `https://<your-app-name>.streamlit.app` within a minute or two.

## Project structure

```
streamlit-blackjack/
├── app.py                 # The entire game (logic + UI)
├── requirements.txt       # Just `streamlit`
├── .streamlit/
│   └── config.toml        # Casino-inspired dark/gold theme
├── .gitignore
└── README.md
```

## Notes

Card images are served from [deckofcardsapi.com](https://deckofcardsapi.com), so an internet connection is required the first time you play (the browser caches them afterward).

## License

MIT

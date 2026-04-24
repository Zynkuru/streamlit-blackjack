# Blackjack on Streamlit!

A popular game played at casinos but this game features 3 hands! 

## Features

- Standard Blackjack rules (dealer stands on 17, blackjack pays 3:2)
- $1,000 starting bankroll with chips of $1, $5, $25, $100, and $500
- Hit, Stand, Deal, Clear Bet, Next Hand, and Reset Bankroll actions
- Face-down dealer hole card until the hand resolves
- 100% Python

## Website

Click on this link to go to the website hosted on Streamlit Cloud: [Play Blackjack!](https://aziz-mansur-blackjack.streamlit.app/) 

## You can also run locally if you would like

Requires Python 3.9 or newer

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

### Payouts

| Outcome | Payout |
|---|---|
| Blackjack (21 on deal) | **3 to 2** |
| Regular win | 1 to 1 |
| Push (tie) | Bet returned |
| Loss | Bet lost |

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

## External Resources

The contents such as card images come from a public source: [deckofcardsapi.com](https://deckofcardsapi.com), therefore please use the internet the first time you launch it!

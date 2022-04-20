# Data-Driven-Trading

A program that executes trades on stocks that are being talked about on the internet.

# Integrations
[Reddit](https://reddit.com '') - Extract internet gossip and rumors

[Macroaxis](https://macroaxis.com '') - Calculate target prices

[Airtable](https://airtable.com '')  - Easy Data Analysis + Historical storage

[Alpaca](https://alpaca.markets/ '') - Execute trades (Paper and Live accounts)


![Flowchart](https://github.com/jarrettdev/Data-Driven-Trading/blob/master/resources/Flowchart.png)


## Usage

- [Setup Alpaca API keys](https://github.com/alpacahq/alpaca-trade-api-python '')
- [Setup Reddit API keys](https://old.reddit.com/prefs/apps/ '')
- [Setup Airtable API keys](https://airtable.com '') (optional step, data is stored locally)
- git clone https://github.com/jarrettdev/Data-Driven-Trading/
- Create a virtualenv
    - python3 -m venv venv
- Activate venv
    - source venv/bin/activate on mac/linux
- Start program
    - python3 reddit_stocks_comment_watch.py

Reach out if you need help setting this up.

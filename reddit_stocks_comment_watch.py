#import packages
import praw
import os
import json
import csv
import time
from datetime import datetime
import traceback
import re
from tqdm import tqdm
import requests
import alpaca_trade_api as tradeapi
from bs4 import BeautifulSoup
import prices
import pandas as pd
import matplotlib.pyplot as plt
import random
from datetime import datetime
import seaborn as sns
import webbrowser

api = tradeapi.REST()
account = api.get_account()

def validate_airtable_kwargs(kwarg, kwarg_name, prefix, char_length=17, print_messages=True):
    """Designed for use with airtable_download() and airtable_upload() functions.
        Checks `api_key`, `base_id` and `record_id` arguments to see if they conform to the expected Airtable API format.
        """
    valid_status = True
    if len(kwarg) != char_length:
        if print_messages is True:
            print("⚠️ Caution: {} not standard length. Make sure API key is {} characters long.".format(kwarg_name, char_length))
        valid_status = False
    if kwarg.startswith(prefix) is False:
        if print_messages is True:
            print("⚠️ Caution: {} doesn't start with `{}`.".format(kwarg_name, prefix))
        valid_status = False
    return valid_status
# %%
def airtable_upload(table, upload_data, typecast = False, api_key = None, base_id = None, record_id = None):
    """Sends dictionary data to Airtable to add or update a record in a given table. 
        Returns new or updated record in dictionary format.
    
    Keyword arguments:
    • table: set to table name
        ◦ see: https://support.airtable.com/hc/en-us/articles/360021333094#table
    • upload_data: a dictionary of fields and corresponding values to upload in format {field : value}
        ◦ example: {"Fruit" : "Apple", "Quantity" : 20}
    • typecast: if set to true, Airtable will attempt "best-effort automatic data conversion from string values"
        • see: "Create Records" or "Update Records" in API Documentation, available at https://airtable.com/api for specific base
    • api_key: retrievable at https://airtable.com/account
        ◦ looks like "key●●●●●●●●●●●●●●"
    • base_id: retrievable at https://airtable.com/api for specific base
        ◦ looks like "app●●●●●●●●●●●●●●"
    • record_id: when included function will update specified record will be rather than creating a new record
        ◦ looks like "rec●●●●●●●●●●●●●●"
        """
    
    # Authorization Credentials
    if api_key == None:
        print("Enter Airtable API key. \n  *Find under Airtable Account Overview: https://airtable.com/account")
        api_key = input()
    headers = {"Authorization" : "Bearer {}".format(api_key),
              'Content-Type': 'application/json'}
    validate_airtable_kwargs(api_key, "API key", "key")

    # Locate Base
    if base_id == None:
        print("Enter Airtable Base ID. \n  *Find under Airtable API Documentation: https://airtable.com/api for specific base]")
        base_id = input()
    url = 'https://api.airtable.com/v0/{}/'.format(base_id)
    path = url + table
    validate_airtable_kwargs(base_id, "Base ID", "app")
    
    # Validate Record ID
    if record_id != None:
        validate_airtable_kwargs(record_id, "Record ID", "rec")
    
    # Validate upload_data
    if type(upload_data) != dict:
        print("❌ Error: `upload_data` is not a dictonary.")
        return

    # Create New Record
    if record_id == None:
        upload_dict = {"records": [{"fields" : upload_data}], "typecast" : typecast}
        upload_json = json.dumps(upload_dict)
        response = requests.post(path, data=upload_json, headers=headers)
        airtable_response = response.json()

    # Update Record
    if record_id != None:
        path = "{}/{}".format(path, record_id)
        upload_dict = {"fields" : upload_data, "typecast" : True}
        upload_json = json.dumps(upload_dict)
        response = requests.patch(path, data=upload_json, headers=headers)
        airtable_response = response.json()
    
    # Identify Errors
    if 'error' in airtable_response:
        identify_errors(airtable_response)
        
    return airtable_response

def identify_errors(airtable_response):
    """Designed for use with airtable_download() and airtable_upload() functions.
        Prints error responses from the Airtable API in an easy-to-read format.
        """
    if 'error' in airtable_response:
        try:
            print('❌ {} error: "{}"'.format(airtable_response['error']['type'], airtable_response['error']['message']))
        except:
            print("❌ Error: {}".format(airtable_response['error']))
    return

def upload_pandas_dataframe(pandas_dataframe, table, api_key, base_id):
    """Uploads a Pandas dataframe to Airtable. If Pandas index values are Airtable Record IDs, will attempt to update 
        record. Otherwise, will create new records."""
    pandas_dicts = pandas_dataframe.to_dict(orient="index")
    for pandas_dict in pandas_dicts:
        record_id = pandas_dict
        if validate_airtable_kwargs(str(record_id), "Record ID", "rec", print_messages=False) is False:
            record_id = None
        upload_data = pandas_dicts[pandas_dict]
        airtable_upload(table, upload_data, api_key=api_key, base_id=base_id, record_id=record_id)
    return

class RedditChecker:
    base_id = ''
    table_name = ''
    api_key = ''
    airtable_url = ''
    with open('airtable_credentials.json', 'r') as creds_file:
        creds = json.load(creds_file)
        base_id = creds['base_id']
        table_name = creds['table_name']
        api_key = creds['api_key']
        airtable_url = "https://api.airtable.com/v0/" + base_id + "/" + table_name
    airtable_headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json"
    }
    main_dir = './data/reddit_stocks'
    #Client edits these parameters
    #============================================
    with open('reddit_credentials.json', 'r') as creds_file:
        creds = json.load(creds_file)
        client_id = creds['client_id']
        client_secret = creds['client_secret']
    #client_id = 'Cdp5_MJZQCzo9A'
    #client_secret = 'esze4IquPXoBizHrOCt1goI7LtOL_Q'
    def __init__(self):
        self.reddit = praw.Reddit(client_id=self.client_id,
                                  client_secret=self.client_secret,
                                  user_agent='stock_bot')
    #============================================

    #Initialize known stocks (NYSE, AMEX, NASDAQ)
    ################################################
    nyse_df = pd.read_csv(f'{main_dir}/exchange_csvs/NYSE.csv')
    amex_df = pd.read_csv(f'{main_dir}/exchange_csvs/AMEX.csv')
    nasdaq_df = pd.read_csv(f'{main_dir}/exchange_csvs/NASDAQ.csv')
    nyse_stocks = list(nyse_df['symbol'])
    amex_stocks = list(amex_df['symbol'])
    nasdaq_stocks = list(nasdaq_df['symbol'])
    all_stocks = list(set(nyse_stocks + amex_stocks + nasdaq_stocks))
    # **
    blocklist = ['EPS', 'WSB', 'OEM', 'ATM', 'GDP', 'RGB', 'LFG']
    for stock in blocklist:
        try:
            all_stocks.remove(f'{stock}')
        except:
            pass
    #reddit instance
    reddit = praw.Reddit(client_id = client_id, client_secret = client_secret, user_agent = 'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0')
    subreddit = None
    new_posts = set()
    #store post id to avoid duplicates
    post_id = None
    old_posts = set()
    def run(self):
        while True:
            # datetime object containing current date and time
            now = datetime.now()
            #print("now =", now)
            # dd/mm/YY H:M:S
            dt_string = now.strftime("%m-%d-%Y-%H_%M")
            current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
            #print("date and time =", dt_string)
            #define how many posts to show each refresh
            subs = ['wallstreetbets', 'stocks', 'investing', 'options', 'daytrading']
            sub_choice = random.choice(subs)
            print(f'Subreddit: {sub_choice}')
            self.subreddit = self.reddit.subreddit(sub_choice)
            self.new_posts = self.subreddit.hot(limit = 50)
            #btc_res = requests.get(btc_url, headers=headers)
            #content = BeautifulSoup(btc_res.text, 'lxml')
            #print(content)
            #btc_price = content.find('input', {'class' : 'newInput inputTextBox alertValue'})['value']
            #print(btc_price)
            price_item = prices.get_indicies()
            for post in self.new_posts:
                stocks = []
                downvotes = int(float(post.ups)/float(post.upvote_ratio) - post.ups)
                p_time = int(post.created_utc)
                p_time = datetime.utcfromtimestamp(p_time).strftime('%Y-%m-%d %H:%M:%S')
                post_text = post.title.replace('.', '').replace('$', '').replace('!', '')
                potential_stocks = re.findall(r'\b[A-Z]{3,}\b[.!?]?', post_text)
                if self.all_stocks:
                    for stock in potential_stocks:
                        print(stock)
                        if stock in self.all_stocks:
                            stocks.append(stock)
                item = {
                    "Date" : p_time,
                    "Author" : post.author,
                    "Title" : post.title,
                    "Comments" : len(post.comments),
                    "Upvote Ratio" : post.upvote_ratio,
                    "Tickers" : " ".join(stocks)
                }
                item.update(price_item)
                item.update({
                    "Upvotes" : post.ups,
                    "Downvotes" : downvotes,
                    "Pinned" : post.pinned,
                    "Is Video" : post.is_video,
                    "Num Reports" : post.num_reports,
                    "Link" : post.url,
                    "Date Of Extraction" : current_time_str
            })

                csv_string = f'{dt_string}_wsb.csv'
                self.to_csv(item, csv_string)

            #sleep for 35 minutes
            print(f'{self.main_dir}/comment_data/{dt_string}_wsb.csv')
            #df = pd.read_csv(f'{self.main_dir}/comment_data/{dt_string}_wsb.csv')
            csv_string = f'{self.main_dir}/comment_data/{dt_string}_wsb.csv'
            self.get_target_prices(csv_string)
            #self.add_to_watchlist(df)
            self.combine_csvs()
            #self.plot_csv()
            print('sleeping for 30 minutes...')
            time.sleep(60*120)

    def buy_stock(self, ticker, quantity, profit_price, stop_price, limit_price):
        try:
            api.submit_order(
                symbol=f'{ticker}',
                side='buy',
                type='market',
                qty=f'{quantity}',
                time_in_force='day',
                order_class='bracket',
                take_profit=dict(
                    limit_price=f'{profit_price}',
                ),
                stop_loss=dict(
                    stop_price=f'{stop_price}',
                    limit_price=f'{limit_price}',
                )
                )
            return 1
        except:
            traceback.print_exc()
            return 0
    #%%
    def get_target_prices(self, csv_string):
        target_objects = []
        df = pd.read_csv(csv_string)
        df = df.dropna(subset=['Tickers'])
        tickers = df['Tickers'].tolist()
        tickers = list(set(tickers))
        for ticker in tickers:
            if (' ' in ticker):
                ticker = ticker.split(' ')[0]
                #Lazy fix for GOOGL
            if (ticker == 'GOOG'):
                ticker = 'GOOGL'
            try:
                url = f'https://macroaxis.com/valuation/{ticker}'
                page = requests.get(url)
                soup = BeautifulSoup(page.text, 'lxml')
                target_price = 0
                try:
                    target_price = page.text.split('<strong>Real Value</strong>  of ')[1].split(' per')[0]
                    if target_price:
                        target_price = target_price.replace(',', '')
                        target_price = target_price.replace('$', '')
                        target_price = float(target_price)
                except:
                    target_price = 0
                    traceback.print_exc()
                if target_price == 0:
                    print(f'skipping {ticker}... no real value')
                    continue
                print(f'Target price for {ticker} is {target_price}')
                # Share Purchase Logic
                # If the target price is 5% greater than the current price, buy at the current price and sell at the target price
                #==============================================================================
                valuation = self.get_current_valuation(ticker)
                actual_price = float(valuation['market_val'])
                target_gain = str(round((1 - (actual_price/target_price)), 2))
                target_gain = float(target_gain)
                #print(target_gain)
                date = str(datetime.now())
                info_url = f'https://macroaxis.com/valuation/{ticker}'
                if target_gain > 0.05:
                    quantity = int(700/actual_price)
                    if quantity > 0:
                        profit_price = target_price
                        stop_price = actual_price - (actual_price * 0.07)
                        limit_price = stop_price - (stop_price * 0.07)
                        stop_price = round(stop_price, 2)
                        limit_price = round(limit_price, 2)
                        #ticker, quantity, profit_price, stop_price, limit_price
                        self.buy_stock(ticker, quantity, profit_price, stop_price, limit_price)
                #==============================================================================
                target_object = {
                    'Ticker': ticker,
                    '3 Month Price Target': float(target_price),
                    'Actual Price': float(actual_price),
                    'Target Difference': target_gain,
                    'Value': valuation['advising_text'],
                    'Date Analyzed': date,
                    'Info': info_url
                }
                #print(target_object)
                target_objects.append(target_object)
            except:
                print(f'{ticker} is not a valid ticker')
                traceback.print_exc()

        target_df = pd.DataFrame(target_objects)

        # Uncomment to update the target prices in your airtable
        #==============================================================================

        #upload_pandas_dataframe(target_df, 'YOUR TABLE NAME', self.api_key, self.base_id)

        #==============================================================================
        target_df.to_csv(f'{self.main_dir}/target_prices/target_prices_new.csv', mode='w', header=True, index=False)
    #%%
    def get_current_valuation(self, ticker):
        try:
            url = f'https://www.macroaxis.com/valuation/{ticker}'
            page = requests.get(url)
            soup = BeautifulSoup(page.text, 'lxml')

            market_val = soup.find('span', {'id': 'symbolQuoteValueFlat'}).text
            if market_val:
                market_val = market_val.replace(',', '')
            advising_text = soup.find('div', {'class': 'adviserValuationText'}).text
            valuation_object = {
                'ticker': ticker,
                'market_val': market_val,
                'advising_text': advising_text
            }
            return valuation_object
            #return valuation_object
        except:
            return {}

    def to_csv(self, item, filename):
        # Check if "playlists.csv" file exists
        file_exists = os.path.isfile(f'{self.main_dir}/comment_data/{filename}')
        if not os.path.exists(f'{self.main_dir}/comment_data'):
            os.makedirs(f'{self.main_dir}/comment_data')
        # Append data to CSV file
        with open(f'{self.main_dir}/comment_data/{filename}', 'a') as csv_file:
            # Init dictionary writer
            writer = csv.DictWriter(csv_file, fieldnames=item.keys())
            # Write header only ones
            if not file_exists:
                writer.writeheader()
            # Write entry to CSV file
            writer.writerow(item)

    def combine_csvs(self):
        #check if comment_data dir exists
        if not os.path.exists(f'{self.main_dir}/comment_data/'):
            os.makedirs(f'{self.main_dir}/comment_data/')
        #create a list of all the csvs in the comment_data folder
        csvs = os.listdir(f'{self.main_dir}/comment_data/')
        #create a list of all the dataframes from the csvs
        frames = [pd.read_csv(f'{self.main_dir}/comment_data/'+csv, low_memory=False) for csv in csvs]
        #concatenate all the dataframes into one dataframe
        df = pd.concat(frames)
        df = df.drop_duplicates('Link')
        #export the dataframe to a csv
        df.to_csv(f'{self.main_dir}/combined_csvs.csv', index=False, mode='a')
        print('combined csvs')

    #adds ticker to macroaxis.com watchlist for portfolio optimization
    def add_to_watchlist(self, df):
        print('Adding tickers to watchlist.')
        top_ten_tickers = df['Tickers'].value_counts().head(10)
        for ticker in top_ten_tickers.keys():
            webbrowser.open(f'https://www.macroaxis.com/stock/{ticker}/')
    
    def plot_csv(self):
        df = pd.read_csv(f'{self.main_dir}/combined_csvs.csv')
        pairplot = sns.pairplot(df)
        heatmap = sns.heatmap(df.corr(), annot=True)
        #plt.show()
        if not os.path.exists(f'{self.main_dir}/data_pics/'):
            os.makedirs(f'{self.main_dir}/data_pics/')
        pairplot.savefig(f'{self.main_dir}/data_pics/wsb_pairplot.png')
        sns.heatmap(df.corr(), annot=True).get_figure().savefig(f'{self.main_dir}/data_pics/wsb_heatmap.png')
        

if __name__ == '__main__':
    RedditChecker = RedditChecker()
    RedditChecker.run()
    

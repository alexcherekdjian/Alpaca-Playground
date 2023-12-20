import os
import smtplib
import alpaca_trade_api as tradeapi
import yfinance as yf
from colorama import Fore

RUN_SETUP = False
CLOSE_ALL = False

startBal = 100000

SEC_KEY = 'HtcO77NCJFynyW2DnbJqoaEpkPSJ113KO9RsJQ6J'
PUB_KEY = 'PKLS9W8PJDB1QUZVB4EQ'
BASE_URL = 'https://paper-api.alpaca.markets'

companies_symb = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'GOOG', 'TSLA', 'NFLX',
                    'UNH', 'LLY', 'JPM', 'V', 'AVGO', 'XOM', 'JNJ', 'PG', 'MA', 'HD', 'ADBE',
                    'COST', 'MRK', 'ABBV', 'CVX', 'CRM', 'WMT', 'KO', 'BAC', 'ACN', 'MCD']

class Action:
    def __init__(self, action, symbol, quantity=0, unrealized_pl=0):
        self.action = action
        self.symbol = symbol
        self.quantity = quantity
        self.unrealized_pl = round(float(unrealized_pl), 2)

    def submit(self):
        txt = None
        color = Fore.LIGHTRED_EX

        amnt_invested = round(get_current_price(self.symbol) * float(self.quantity), 2)

        if round(float(self.quantity)) == 0 or float(amnt_invested) <= 0:
            return
        elif self.action == "close":
            api.close_position(symbol=self.symbol, qty=self.quantity)
            color = Fore.LIGHTGREEN_EX
            amnt_invested = self.unrealized_pl
        else:
            api.submit_order(symbol=self.symbol, qty=self.quantity)

            if self.action == "open":
                color = Fore.LIGHTBLUE_EX

        # report
        print("{}[{}]{} position {} for ${}".format(color, self.action, Fore.RESET, self.symbol, amnt_invested))
        txt = "[{}] position {} for ${}".format(self.action, self.symbol, amnt_invested)
        
        return txt


def get_current_price(symbol):
    
    ticker = yf.Ticker(symbol)
    price = float(ticker.fast_info['lastPrice'])

    return price

def calculate_up_down_days(companies_symb):
    result = {}

    for symbol in companies_symb:
        ticker = yf.Ticker(symbol)
        current_price = float(ticker.fast_info['lastPrice'])
        lastday_price = float(ticker.fast_info['regularMarketPreviousClose'])
        
        price_change = current_price - lastday_price

        if price_change > 0:
            result[symbol] = "up"
        else:
            result[symbol] = "down"
    return result

def send_sms_report(txt_body):
    PHONE_NUMBER = 4089211443
    PHONE_CARRIER = "T-MOBILE"

    AVAIL_PHONE_CARRIER = {"ATT" : "@txt.att.net", "T-MOBILE": "@tmomail.net", "VERIZON": "@vtext.com"}

    DISNEY_BOT_EMAIL = "disneyticketbot@gmail.com"
    PASSWORD = "lpdvoomhohqddjoj"
    RECIEVER_EMAIL = "alexcherekdjian@gmail.com"
    RECIEVER_NUMBER = str(PHONE_NUMBER) + AVAIL_PHONE_CARRIER[PHONE_CARRIER]

    message_subject = "---> Alpaca!!\n"
    message_body = "\n".join(txt_body)

    try:
        server_ssl = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server_ssl.helo()
    except:
        print('Something went wrong in creating the email server')

    sent_from = DISNEY_BOT_EMAIL
    to = [RECIEVER_EMAIL, RECIEVER_NUMBER]

    from email.message import EmailMessage

    msg = EmailMessage()
    msg.set_content(message_body)
    msg['Subject'] = message_subject

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(DISNEY_BOT_EMAIL, PASSWORD)        
        server.sendmail(sent_from, to, msg.as_string())
        server.close()
        print ('===== Text Sent to {} ====='.format(RECIEVER_EMAIL))
    except:
        print('Something went wrong in sending the text')


def update_orders(companies_symb, cash):
    positions = api.list_positions()
    amnt_per_company = cash / len(companies_symb)
    actions = []
    total_investments = 0
    up_down_day = {}

    # retrieve current holdings
    current_holdings = set(position.symbol for position in positions)

    # positions we don't currently hold that we want to invest in
    uninvested_holdings = set(companies_symb) - current_holdings

    # assign each symbol as UP or DOWN day
    up_down_day = calculate_up_down_days(companies_symb)

    # IF WE SELL THAT STOCK TODAY, WE DO NOT WANT TO BUY THAT STOCK TODAY

    # STEP 1) Look at current positions and see whether we need to sell or reinvest more 
    running_total = 0
    
    if len(current_holdings) == 0:
        print("{}\n===== Fully Unvested, no actions to take :) =====\n{}".format(Fore.WHITE, Fore.RESET))
    else:
        for position in positions:
            # current_price = get_current_price(position.symbol)

            # if position is in an up day
            if up_down_day[position.symbol] == "up":
                
                # if we are going to make da money, sell
                if float(position.unrealized_pl) > 0:
                    running_total += float(position.unrealized_pl)
                    actions.append(Action("close", position.symbol, position.qty, unrealized_pl=position.unrealized_pl))

                else:
                    # if we ain't gonna make money, just re-vest the position                     
                    actions.append(Action("re-vest", position.symbol))
                    total_investments += 1

            # if position is in a down day
            elif up_down_day[position.symbol] == "down":
            
                actions.append(Action("re-vest", position.symbol))
                total_investments += 1

    # STEP 2) Look at uninvested positions and see whether we should buy today
    # if its a down day, we put in moneys

    if len(uninvested_holdings) == 0:
        print("{}\n===== Fully Invested, no actions to take :) =====\n{}".format(Fore.LIGHTGREEN_EX, Fore.RESET))
    else:
        for symbol in uninvested_holdings:
            if up_down_day[symbol] == "down":
                actions.append(Action("open", symbol))
                total_investments += 1

    amnt_per_company = round(cash / total_investments, 2)

    txt_body = []
    # complete all actions
    for action in actions:
        
        if action.action == "open" or action.action == "re-vest":
            current_price = get_current_price(symbol=action.symbol)
            quantity = round(amnt_per_company / current_price, 2)
            action.quantity = quantity

        txt = action.submit()

        if txt != None:
            txt_body.append(txt)

    print("{} Total Profit - {} {}".format(Fore.LIGHTCYAN_EX, round(running_total, 2), Fore.RESET))
    txt_body.append("\n\n** Total Profit - ${} **".format(round(running_total, 2)))

    send_sms_report(txt_body)


def setup(companies_symb, startBal, clear_open_orders=True):
    # init alpaca purchases
    amnt_per_company = startBal / len(companies_symb)

    open_orders = api.list_orders(status='open')

    if len(open_orders) != 0 and clear_open_orders == True: 
        api.cancel_all_orders()
        print("Canceling all open orders")


    for symb in companies_symb:
        current_price = get_current_price(symbol=symb)

        quantity = round(amnt_per_company / current_price, 2)

        api.submit_order(symbol=symb, qty=quantity)
        print("Submitted order for {} for {:0.2f} shares".format(symb, quantity))



def main():
    # companies = api.list_assets()
    # api = tradeapi.REST(key_id= PUB_KEY, secret_key=SEC_KEY, base_url=BASE_URL, api_version='v2')
    account = api.get_account()
    cash = float(account.cash)

    print("==== Avail Cash -> ${}".format(cash))

    if RUN_SETUP:
        setup(companies_symb, cash)
    elif CLOSE_ALL:
        api.close_all_positions()
    else:
        update_orders(companies_symb, cash)


api = tradeapi.REST(key_id= PUB_KEY, secret_key=SEC_KEY, base_url=BASE_URL, api_version='v2')

main()

import json
import requests
from app import app

from flask import Flask, request, render_template, request, redirect
from flask_bootstrap import Bootstrap
from flask_pymongo import PyMongo

app.config['MONGO_DBNAME'] = 'IA'
app.config['MONGO_URI']= 'mongodb+srv://admin:paQYItRoMs9pfF4N@cluster0-lfs7i.mongodb.net/IA?retryWrites=true&w=majority'


mongo = PyMongo(app)
app = Flask(__name__)
# bootstrap4 is used for styling our front-end
bootstrap = Bootstrap(app)


                                    # Helper functions

# this function checks if a given symbol is in user's favorites folder
# return true if symbol is in favorites else it returns false
def in_favorites(symbol):
    # read the file
    with open('favorites.json') as f:
        # parse JSON to python object and store in data
        data = json.load(f)
    # data["favorites"] holds the favorited symbols of the user
    current_favorites = data["favorites"]
    # check if the passed symbol is in the user's favorites, if yes return true
    # else we return false
    return True if symbol in current_favorites else False

# update_keys function is used to remove the unnecessary indexes in the keys of the returned objects from the API.
def update_keys(stock, characters_to_remove):

    # iterate over each key of the stock object. We have parsed the object to a list, since a list can be mutated
    for key in list(stock):
        # by popping the key from the stock object, we get the value for the popped key while
        # removing it from the keys
        value = stock.pop(key)

        # our updated key holds value after the first n characters of the oringal key, i.e:
        # "01. symbol" will be stored as "symbol" and "07. latest trading day" will be stored as
        # "latest trading day"
        new_key = key[characters_to_remove:]

        # we need to put a new key in each stock object which will tell if the stock is in user's favorite
        if new_key == 'symbol':
            stock['is_favorite'] = in_favorites(value)

        if new_key == 'price':
            # we have parsed the price value to float so we can apply sorting on it from the template
            value = float(value)

        # API sends '--' back when current volume is 0 (market closed?)
        if new_key == 'volume' and value != '--':
            # we have parsed the volume value to float so we can apply sorting on it from the template
            value = int(value)

        # Put the new key in the object
        stock[new_key] = value

    return stock

# this function returns the basic data for the stocks provided in the list
def get_stocks(symbols):
    # the API expects symbols to be comma separated, such as AAPL,MSFT
    # so we insert a comma between each list item by joining with a ','
    # this leaves us with a string of comma separated symbols
    symbols = ','.join(symbols)

    # f before the string signifies that we are using a template string, i.e. a string in which variables can be injected.
    # the symbols string is injected here
    request_url = f'https://www.alphavantage.co/query?function=BATCH_STOCK_QUOTES&apikey=xxx&symbols={symbols}'

    response = requests.get(request_url)

    # parse JSON object to python object
    response_parsed = json.loads(response.content)

    # 'Stock Quotes' attribute has a value that is a
    # list that holds stock objects for requested stocks
    stocks = response_parsed['Stock Quotes']

    # iterate over each stock in the stocks list
    for stock in stocks:
        # BATCH_STOCK_QUOTES return objects have 3 unnecessary characters in its keys, so we remove them
        stock = update_keys(stock, 3)

    return stocks

                                            #ROUTES

@app.route("/")
def index():
    # sort_by variable is sent to the front-end to tell which key should the data be sorted with.
    # if the front-end doesn't send a sortby query parameter then we assign 'symbol' as the default sort key
    sort_by = request.args.get('sortby') or 'symbol'

    # front end will send a reverse = 1 variable as a query parameter if descending order sort is requested,
    # else we assign a 0 to indicate an ascending sort
    should_reverse = request.args.get('reverse') or 0

    # symbols to display on the index page
    symbols = ['MSFT', 'AAPL', 'TSLA', 'FB', 'GOOGL',
               'NFLX', 'PYPL', 'AMZN', 'TWTR', 'WMT']

    # call get_stocks with the specified symbols to get the stocks info
    stocks = get_stocks(symbols)
    return render_template('index.html', stocks=stocks, sort_by=sort_by, should_reverse=int(should_reverse))

@app.route("/stock/info/<symbol>")
def get_stock_info(symbol):

    request_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=xxx"

    # request the API to get quote for the provided symbol
    response = requests.get(request_url)

    # parse JSON to python object
    response_parsed = json.loads(response.content)

    # API sends stock info back in an object whose key is 'Global Quote',
    # so we assign the value for the object in stock variable
    stock = response_parsed['Global Quote']

    # requested stock data was found
    if stock:
        # GLOBAL_QUOTE return object has 4 unnecessary characters in its keys, so we remove them
        stock = update_keys(stock, 4)
        return render_template('stock_info.html', stock=stock)

    # requested stock data wasn't found
    else:
        return render_template('error.html', err_msg='No data found for the requested symbol')

@app.route("/stocks/search")
def search_stocks():

    # front end send the search query in a 'search' query string variable
    query = request.args.get('query')

    request_url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey=xxx"

    # request the API to get data for the provided symbol
    response = requests.get(request_url)

    # parse JSON to python object
    response_parsed = json.loads(response.content)

    # stocks info is returned in an object with key 'bestMatches'
    stocks = response_parsed['bestMatches']

    # iterate over each stock in the stocks list
    for stock in stocks:
       # SYMBOL_SEARCH return object has 3 unnecessary characters in its keys, so we remove them
       update_keys(stock, 3)

    return render_template('search.html', stocks=stocks)

@app.route("/stock/graph/<symbol>")
def get_stock_graph(symbol):

    request_url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey=xxx'
    response = requests.get(request_url)

    # parse JSON to python object
    response_parsed = json.loads(response.content)

    # API sends back intra-day data inside the 'Time Series (5min)' key of the object
    time_object = response_parsed['Time Series (5min)']

    # time_list will store x-axis data, i.e. time
    time_list = []
    # price_lis will hold price data, i.e. price
    price_list = []

    # iterate over the key value pair of each time_objet.
    # the key in this case is equal to the time stamp whereas
    # the value is another object which holds information regarding the price
    for time_stamp, price_object in time_object.items():
        # price is inside the '1. open' key of the price object
        price = price_object['1. open']
        price_list.append(price)
        time_list.append(time_stamp)

    # we need to reverse the time list because the API sends the data in descending order (newer data first),
    # whereas we want to display the graph from older data to newer data
    time_list = list(reversed(time_list))

    # after reversing, the time_list[0] holds the oldest time stamp whereas time_list[-1] holds the newest
    period = time_list[0] + ' to ' + time_list[-1]

    return render_template('stock_graph.html', symbol=symbol, values=price_list, labels=time_list, period=period)

@app.route('/favorites')
def get_favorites():

    sort_by = request.args.get('sortby') or 'symbol'
    should_reverse = request.args.get('reverse') or 0

    # read data from the favorites.json file
    with open('favorites.json') as f:
        data = json.load(f)

    # read favorites
    favorites = data["favorites"]

    # if favorites list has atleast 1 item
    if favorites:
        # fetch stocks data for the favorites
        stocks = get_stocks(favorites)

    # favorites list is empty
    else:
        stocks = []

    return render_template('favorites.html', stocks=stocks, sort_by=sort_by, should_reverse=int(should_reverse))

@app.route('/favorites/update')
def update_favorites():
    # symbol to update is sent by the front end in 'symbol' query string variable
    symbol = request.args.get('symbol')

    with open('favorites.json') as f:
        data = json.load(f)

    current_favorites = data["favorites"]

    # if symbol sent by front end is already in user's favorites
    if symbol in current_favorites:
        # remove the symbol for the favorites list
        current_favorites.remove(symbol)

    # if symbol send by front end is not in user's favorites
    elif symbol not in current_favorites:
        # add symbol to the user's favorites
        current_favorites.append(symbol)

    # update the list in the data['favorites'] with the updated list
    data['favorites'] = current_favorites

    # save updated list
    with open('favorites.json', "w+") as f:
        f.write(json.dumps(data))

    # return a success response JSON object to the front end
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

@app.route("/news")
def get_news():
    # request news api to get news from business category inside the US
    request_url = "https://newsapi.org/v2/top-headlines?country=us&category=business&apiKey=0bc8d1b26f0b43bc8adb3be24274852d"
    response = requests.get(request_url)
    # parse JSON object to python object
    response_parsed = json.loads(response.content)
    # articles data is returned in the 'articles' key
    articles = response_parsed['articles']
    return render_template('news.html', articles=articles)

# register a handler for API limit (5 requests per minute)
@app.errorhandler(Exception)
def exception_handler(error):
    return render_template('error.html', err_msg='API overwhelmed. Please wait for a while between requests.')

import numpy as np
import pandas as pd
from selenium import webdriver
import time
import logging
import yfinance as yf
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime as dt
from datetime import timedelta as td


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(message)s')
file_handler = logging.FileHandler('logs.txt')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



def start_aastha():
    path = 'chromedriver.exe'
    driver = webdriver.Chrome(path)
    try:
        driver.get('https://odin.asthatrade.com/Aero/login')
    except:
        logger.error('Could not pull odin.asthatrade.com')
        return None
    else:
        logger.info('Pulled the page odin.aasthatrade.com')
        return driver


def login(driver,id,password):
    wait = WebDriverWait(driver,10)
    try:
        user_id = wait.until(
        EC.presence_of_element_located((
        By.XPATH,'/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[4]/div/mat-form-field/div/div[1]/div[3]/input')))

        password = wait.until(
        EC.presence_of_element_located((
        By.XPATH,'/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[6]/div/mat-form-field/div/div[1]/div[3]/input')))
    except:
        logger.Error('Could not find the element either for id or password')

    else:
        login = driver.find_element_by_xpath('/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[10]/div/button')
        user_id.send_keys(id)
        password.send_keys(password)
        login.click()
        logger.info('Logged in Sucessfully')
        return driver

def get_nifty_price(driver):
    pass
    return [driver,nifty_price]

def get_nifty_last_30days():
    try:
        nifty_data = yf.download('^NSEI',period='30d')
    except:
        logger.error('Could not get data of nifty for last 30 days from yahoo finance')
    else:
        return nifty_data
def days_to_expiry(nifty_data):
    date = nifty_data.tail(1).index[0]
    for count in range(0,7):
        if (date+td(days=count)).weekday()==3:
            print('Count',count)
            today = date
            thurs = date+td(days=count)
            delta = thurs - today
            return [thurs,delta.days]

def get_prob_of_each_strike(nifty_data,strike_price,days):

    #adding row into nifty_data(last 30 days)
    last_date = nifty_data.index[-1]
    target_date = last_date+td(days=days)
    target_row = pd.DataFrame(data={'Open': 0, 'High': 0, 'Low': 0, 'Close':strike_price, 'Adj Close': 0, 'Volume': 0},index=[target_date])
    nifty_data = pd.concat([nifty_data,target_row])

    # making probabiity data with last 40 days of nifty

    nifty_data= nifty_data[::-1]
    current_price = nifty_data['Close'].iloc[0]

    nifty_data['max_perct'] = nifty_data['Close'].apply(lambda x : ((current_price/x)*100)-100)
    nifty_data['max_perct'] = nifty_data['max_perct'].shift(-1)
    nifty_data.dropna(axis=0,inplace=True)

    nifty_data['days'] = range(days,days+30)
    nifty_data['prob'] = nifty_data.apply(lambda x : check_prob(int(x['days']),x['max_perct']),axis=1)


    # getting info into dict format to process it
    row = nifty_data[nifty_data['prob']==nifty_data['prob'].max()]
    max_perct = row['max_perct'].values[0]
    max_days = row['days'].values[0]
    prob = row['prob'].values[0]
    if max_perct>0:
        trend='Postive'
    else:
        trend='Negative'
    print(f'Strike Price : {strike_price}, Prob is {prob}')


def look_for_best_strikeprice(nifty_price,nifty_data,days):
    strike_dic = {}
    nifty_price = (round(float(nifty_price)/50))*50
    for strike_price in range(nifty_price-1000,nifty_price+1000,50):
        get_prob_of_each_strike(nifty_data,strike_price,days)

    return strike_dic


def check_prob(days,maximum):
    nifty_prob = pd.read_csv('NIfty_prob_data\{}_day.csv'.format(days))
    if maximum > 0:
        times = len(nifty_prob[(nifty_prob['perct'] > maximum)])
    elif maximum < 0:
        times = len(nifty_prob[(nifty_prob['perct'] < maximum)])
    total = len(nifty_prob)
    return 100-((times/total)*100)

nifty_data = get_nifty_last_30days()
print(look_for_best_strikeprice(16411,nifty_data,4))

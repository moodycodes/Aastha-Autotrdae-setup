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
from bs4 import BeautifulSoup
import re


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


def login(driver,id,passw):
    wait = WebDriverWait(driver,10)
    try:
        user_id = wait.until(
        EC.presence_of_element_located((
        By.XPATH,'/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[4]/div/mat-form-field/div/div[1]/div[3]/input')))

        password = wait.until(
        EC.presence_of_element_located((
        By.XPATH,'/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[6]/div/mat-form-field/div/div[1]/div[3]/input')))

    except:
        logger.error('Could not find the element either for id or password')

    else:
        user_id.send_keys(id)
        password.send_keys(passw)
        login = wait.until(
        EC.presence_of_element_located((
        By.XPATH,'/html/body/app-root/app-login/div/div/div[3]/div/div[3]/ul/li[2]/div[2]/app-loginwidget/div/form/div/div/div[10]/div/button')))
        login.click()
        logger.info('Logged in Sucessfully')
        return driver

def get_nifty_price(driver):
    wait = WebDriverWait(driver,10)
    try:
        index = 'nifty'
        while not bool(re.findall(r'\d{5}',index)):
            index = wait.until(
            EC.presence_of_element_located((
            By.CLASS_NAME,'lestSection'))).text
    except:
        logger.error('Could Not Fetch Nifty Price')
    else:
        logger.info('Fetched Nifty Price Successfully')
        return int(re.findall(r'\d{5}',index)[0])

def get_nifty_last_30days():
    try:
        nifty_data = yf.download('^NSEI',period='31d')
        nifty_data = nifty_data[:-1]
    except:
        logger.error('Could not get data of nifty for last 30 days from yahoo finance')
    else:
        logger.info('Fetched Last 30 Days Data From Yahoo Finance')
        return nifty_data

def days_to_expiry(nifty_data):
    date = nifty_data.tail(1).index[0]
    for count in range(0,7):
        if (date+td(days=count)).weekday()==3:
            print('Count',count)
            today = date
            thurs = date+td(days=count)
            delta = thurs - today
            return delta.days

def get_prob_of_strike(nifty_data,days,nifty_prob_39days):

    # making probabiity data with last 40 days of nifty
    nifty_data= nifty_data[::-1]
    current_price = nifty_data['Close'].iloc[0]

    nifty_data['max_perct'] = nifty_data['Close'].apply(lambda x : ((current_price/x)*100)-100)
    nifty_data['max_perct'] = nifty_data['max_perct'].shift(-1,axis=0)
    nifty_data.dropna(axis=0,inplace=True)

    # check lengths of it to fill the days for each trading session
    length = len(nifty_data)


    nifty_data['days'] = range(days,days+length)
    nifty_data['prob'] = nifty_data.apply(lambda x : get_probability(float(x['max_perct']),nifty_prob_39days[nifty_prob_39days['day']==int(x['days'])]),axis=1)
    print(nifty_data)
    # getting info into dict format to process it
    row = nifty_data.loc[nifty_data['prob']==nifty_data['prob'].max()]
    max_perct = row['max_perct'].values[0]
    max_days = row['days'].values[0]
    prob = row['prob'].values[0]

    return [prob,max_perct,max_days]

def look_for_best_strikeprice(driver):
    print(f'Today is {dt.today()}, I am in the look for best strike price')
    cmp = get_nifty_price(driver)
    nifty_data = get_nifty_last_30days()
    nifty_prob_39days = concat_eachday_maxmoves()
    strike_dic = {}
    # checking current scenario to determine whether to sell PE or CE (Whether to be Bullish or Bearish)
    today_date = dt.today()
    today_row= pd.DataFrame(data={'Open': 0, 'High': 0, 'Low': 0, 'Close':cmp, 'Adj Close': 0, 'Volume': 0},index=[today_date])
    nifty_data = pd.concat([nifty_data,today_row])
    print('It is after concatenating current row')
    print(nifty_data)

    current_prob = get_prob_of_strike(nifty_data,1,nifty_prob_39days)
    print(f'Current scenario prob is {current_prob}')

    # Using current scenario to find the best strike wither on downside or upside

    rounded_cmp = (round(float(cmp)/50))*50

    if current_prob[1]>0:
        max_strike = rounded_cmp+1000
        step = 50
    elif current_prob[1]<0:
        max_strike = rounded_cmp-1000
        step = -50

    days = days_to_expiry(nifty_data)
    for strike in range(rounded_cmp,max_strike,step):
        target_date = dt.today()+td(days=days)
        target_row = pd.DataFrame(data={'Open': 0, 'High': 0, 'Low': 0, 'Close':strike, 'Adj Close': 0, 'Volume': 0},index=[target_date])
        nifty_data = pd.concat([nifty_data,target_row])
        print('After Concatenating target Strike')
        print(nifty_data)

        print(get_prob_of_strike(nifty_data,days,nifty_prob_39days))

    print(dt.today())



def get_probability(maximum,nifty_prob):
    if maximum > 0:
        times = len(nifty_prob[(nifty_prob['perct'] > maximum)])
    elif maximum < 0:
        times = len(nifty_prob[(nifty_prob['perct'] < maximum)])
    total = len(nifty_prob)
    return 100-((times/total)*100)




def concat_eachday_maxmoves():
    nifty_prob_39days = pd.DataFrame()
    for day in range(1,40):
        nifty_prob =  pd.read_csv(f'NIfty_prob_data/{day}_day.csv',index_col='Date')
        nifty_prob['day'] = day
        nifty_prob_39days = pd.concat([nifty_prob_39days,nifty_prob])
        nifty_prob_39days.dropna(axis=0,inplace=True)
    return nifty_prob_39days


driver = start_aastha()
login(driver,'id','password')
look_for_best_strikeprice(driver)

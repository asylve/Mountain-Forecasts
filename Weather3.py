from bs4 import BeautifulSoup as bs
from tkinter import *
import requests
import re
import numpy as np
import datetime
import pandas as pd
from urllib.parse import urljoin
from collections import defaultdict
import time
import pickle
import os
import tkinter as tk

window = tk.Tk()

def load_urls(urls_filename):
    """ Returns dictionary of mountain urls saved a pickle file """

    full_path = os.path.join(os.getcwd(), urls_filename)

    with open(full_path, 'rb') as file:
        urls = pickle.load(file)
    return urls


def dump_urls(mountain_urls, urls_filename):
    """ Saves dictionary of mountain urls as a pickle file """

    full_path = os.path.join(os.getcwd(), urls_filename)

    with open(full_path, 'wb') as file:
        pickle.dump(mountain_urls, file)


def get_urls_by_elevation(url):
    """ Given a mountain url it returns a list or its urls by elevation """

    base_url = 'https://www.mountain-forecast.com/'
    full_url = urljoin(base_url, url)


    time.sleep(1) # Delay to not bombard the website with requests
    page = requests.get(full_url)
    soup = bs(page.content, 'html.parser')

    elevation_items = soup.find('ul', attrs={'class':'b-elevation__list'}).find_all('a', attrs={'class':'js-elevation-link'})

    return [urljoin(base_url, item['href']) for item in elevation_items]


def get_mountains_urls(urls_filename, url_list):
    """ Returs dictionary of mountain urls

    If a file with urls doesn't exists then create a new one using "url" and return it
    """

    try:
        mountain_urls = load_urls(urls_filename)

    except:  # Is this better than checking if the file exists? Should I catch specific errors?
        mountain_urls={}
        for url in url_list:
            base_url = 'https://www.mountain-forecast.com/'
            directory_url = urljoin(base_url, url)
            page = requests.get(directory_url)
            soup = bs(page.content, 'html.parser')

            title = soup.title.get_text().split(' Weather')
            mountain_urls.update({title[0] : directory_url})# for item in mountain_items}
        dump_urls(mountain_urls, urls_filename)

    finally:
        return mountain_urls


def clean(text):
    """ Returns a string with leading and trailing spaces removed """

    return re.sub('\s+', ' ', text).strip()  # Is there a way to use only REGEX?


def save_data(rows):
    """ Saves the collected forecasts into a CSV file

    If the file already exists then it updates the old forecasts
    as necessary and/or appends new ones.
    """

    column_names = ['mountain', 'date', 'elevation', 'time', 'summary', 'max_temperature', 'min_temperature']

    today = datetime.date.today()
    dataset_name = os.path.join(os.getcwd(), '{:02d}{}_mountain_forecasts.csv'.format(today.month, today.year))  # i.e. 042019_mountain_forecasts.csv

    try:
        new_df = pd.DataFrame(rows, columns=column_names)
        old_df = pd.read_csv(dataset_name, dtype=object)

        new_df.set_index(column_names[:4], inplace=True)
        old_df.set_index(column_names[:4], inplace=True)

        old_df.update(new_df)
        only_include = ~old_df.index.isin(new_df.index)
        combined = pd.concat([old_df[only_include], new_df])
        combined.to_csv(dataset_name)

    except FileNotFoundError:
        new_df.to_csv(dataset_name, index=False)


def scrape(mountains_urls):
    """ Does the dirty work of scraping the forecasts for each mountain"""

    num_days = 6 #number of days to forecast
    k=0 #index of mountain
    rows = []

    for mountain_name, url in mountains_urls.items():

        # Request Web Page
        page = requests.get(url)
        soup = bs(page.content, 'html.parser')

        #get elevation
        elevation = url.rsplit('/', 1)[-1]
        rows.append([mountain_name, elevation])

        # Get data from header
        forecast_table = soup.find('table', attrs={'class': 'forecast__table forecast__table--js'})  # Default unit is metric
        days = forecast_table.find('tr', attrs={'data-row': 'days'}).find_all('td')[0:num_days]

        # Get rows from body
        times = forecast_table.find('tr', attrs={'data-row': 'time'}).find_all('td')[0:(num_days*3)]
        #winds = forecast_table.find('tr', attrs={'data-row': 'wind'}).find_all('img')  # Use "img" instead of "td" to get direction of wind
        summaries = forecast_table.find('tr', attrs={'data-row': 'summary'}).find_all('td')[0:(num_days*3)]
        #rains = forecast_table.find('tr', attrs={'data-row': 'rain'}).find_all('td')
        #snows = forecast_table.find('tr', attrs={'data-row': 'snow'}).find_all('td')
        max_temps = forecast_table.find('tr', attrs={'data-row': 'max-temperature'}).find_all('td')[0:(num_days*3)]
        min_temps = forecast_table.find('tr', attrs={'data-row': 'min-temperature'}).find_all('td')[0:(num_days*3)]
        #chills = forecast_table.find('tr', attrs={'data-row': 'chill'}).find_all('td')
        #freezings = forecast_table.find('tr', attrs={'data-row': 'freezing-level'}).find_all('td')
        #sunrises = forecast_table.find('tr', attrs={'data-row': 'sunrise'}).find_all('td')
        #sunsets = forecast_table.find('tr', attrs={'data-row': 'sunset'}).find_all('td')
        # Iterate over days
        for i, day in enumerate(days):
            current_day = clean(day.get_text())
            num_cols = int(day['colspan'])
            if i == 0:
                num_cols_last = 0
            else:
                num_cols_last = int(days[i-1]['colspan'])

            if current_day != '': # What if day is empty in the middle? Does it affect the count?

                date = str(datetime.date(datetime.date.today().year, datetime.date.today().month, int(current_day.split(' ')[1])))  # Avoid using date format. Pandas adds 00:00:00 for some reason. Figure out better way to format

                # Iterate over forecast
                for j in range(i*num_cols_last, (i+1)*num_cols):

                    day_of_week = current_day.split(' ', 1)[0]
                    time_cell = clean(times[j].get_text())
                    #wind = clean(winds[j]['alt'])
                    summary = clean(summaries[j].get_text())
                    #rain = clean(rains[j].get_text())
                    #snow = clean(snows[j].get_text())
                    max_temp = clean(max_temps[j].get_text())
                    min_temp = clean(min_temps[j].get_text())
                    #chill = clean(chills[j].get_text())
                    #freezing = clean(freezings[j].get_text())
                    #sunrise = clean(sunrises[j].get_text())
                    #sunset = clean(sunsets[j].get_text())

                    rows[k].append(np.array([day_of_week, date, time_cell, summary, max_temp, min_temp]))

        k += 1

        time.sleep(1)  # Delay to not bombard the website with requests
    return rows
    print(rows)


def scrape_forecasts(urls_filename, url_list):
    """ Call the different functions necessary to scrape mountain weather forecasts and save the data """

    start = time.time()
    print('\nGetting Mountain URLS')
    mountains_urls = get_mountains_urls(urls_filename, url_list)
    print('URLs for {} Mountains collected\n'.format(len(mountains_urls)))

    print('Scraping forecasts...\n')
    forecasts = scrape(mountains_urls)

    print('Saving forecasts...\n')
    #save_data(forecasts)

    img_dir = 'weather_diagrams/'
    weather_types = ["clear","cloudy","some clouds","mod. rain", "light rain", "heavy rain","rain shwrs","mod. snow","heavy snow","light snow","snow shwrs","risk tstorm"]

    img=[] #this holds the list of images
    for i, weather in enumerate(weather_types): #loop over types of weather
        img.append(tk.PhotoImage(file=img_dir+weather+".ppm")) #add the image to the list
        img[i] = img[i].subsample(5) #shrink the image

    img_dict=dict(zip(weather_types, img)) #create the dictionary with names of weather and images

    for i in range(2,len(forecasts[0])): #loops over times, this prints the table header

        if forecasts[0][2][2]=="PM": shift=0 #do not shifts the headers when there are only two entries that day
        else:shift=1 #otherwise shift the headers one right

        if (i-2)%3 == shift: #only print the date once for each day
            label = tk.Label(window, text=forecasts[0][i][0]).grid(row=0, column=i-1) #prints the day of week
            label = tk.Label(window, text=forecasts[0][i][1]).grid(row=1, column=i-1) #prints the date
        label = tk.Label(window, text=forecasts[0][i][2]).grid(row=2, column=i-1) #prints the time of day

    for k in range(0,len(mountains_urls)): #loops over mountains

        label = tk.Label(window, text=forecasts[k][0]).grid(row=(len(forecasts[k][2])-3)*k+3, column=0) #labels the mountain in the left column
        for i in range(2,len(forecasts[k])):#loops over times, skips the first two elements of the array which are the mountain name and height

            for j in range(3,len(forecasts[k][2])):#loops over weather forecast elements for each time (eg. rain, temperature), skips the first three elements which are the day of week, date and time of day
                if j%3 == 0: #place an image in every 3rd slot (skip over temps)
                    label = tk.Label(window, image=img_dict[forecasts[k][i][j]])
                    label.grid(row=j+(len(forecasts[k][2])-3)*k, column=i-1) #prints the date
                    label.image=img #needed to stop 'garbage collection'
                else: #otherwise print the text directly
                    label = tk.Label(window, text=forecasts[k][i][j]).grid(row=j+(len(forecasts[k][2])-3)*k, column=i-1)

    print('All done! The process took {} seconds\n'.format(round(time.time() - start, 2)))

if __name__ == '__main__':

    scrape_forecasts('mountains_urls.pickle', ['peaks/Mount-Brew-Lillooet-Ranges/forecasts/2891','peaks/Mount-Matier/forecasts/2783','peaks/Brandywine-Mountain/forecasts/1500', 'peaks/Stawamus-Chief/forecasts/702', 'peaks/Mount-Seymour/forecasts/1449','peaks/Slesse-Peak/forecasts/2393','peaks/Hozomeen-Mountain/forecasts/2458','peaks/Yak-Peak/forecasts/2039'])
    window.mainloop()

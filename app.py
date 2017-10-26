#!/usr/bin/env python

import urllib
import requests
import json
import os
import datetime

from flask import Flask
from flask import request
from flask import make_response


from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)

    print('Response:')
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def processRequest(req):
    if req.get("result").get("action") == "search_weather":
        baseurl = "https://query.yahooapis.com/v1/public/yql?"
        result = req.get("result")
        parameters = result.get("parameters")
        city = parameters.get("geo-city")
        day = parameters.get("date")
        yql_query = makeYqlQuery(city)
        if yql_query is None:
            return {}
        yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
        result = urlopen(yql_url).read()
        data = json.loads(result)
        res = makeWebhookResult(data, day)
        return res
    if req.get("result").get("action") == 'search_country_capital':
        country_data = getCountryData(req)
        speech = makeCountryCapitalSpeech(country_data)
        response = makeWebhookCountryResult(country_data, speech)
        response['contextOut'].append({'name': 'capital_info',
                                       'parameters': {'geo-city': country_data['capital']}});
        return response

    if req.get("result").get("action") == 'search_country_population':
        print('action: ', 'search_country_population')
        country_data = getCountryData(req)
        speech = makeCountryPopulationSpeech(country_data)
        print('speech: ', speech)
        return makeWebhookCountryResult(country_data, speech)

    if req.get("result").get("action") == 'search_country_summary':
        print('action: ', 'search_country_summary')
        country_data = getCountryData(req)
        print('country_data: ', country_data)
        speech = makeCountrySummarySpeech(country_data)
        print('speech: ', speech)
        return makeWebhookCountryResult(country_data, speech)

    if req.get("result").get("action") == 'select_topic':
        result = req.get("result")
        parameters = result.get("parameters")
        topic = parameters.get("topic")
        if topic == 'countries':
            speech = 'Which country do you want to learn more about?'
            return {
                "speech": speech,
                "displayText": speech,
                "contextOut": [{'name': 'topic_country'}],
                "data": {},
                "source": ""
            }
        if topic == 'weather':
            speech = 'Weather for which city?'
            return {
                "speech": speech,
                "displayText": speech,
                "contextOut": [{'name': 'topic_weather'}]
            }
        if topic == 'both' or topic == 'unkown':
            speech = 'Lets start with weather. For which city to want to search the weather?'
            return {
                "speech": speech,
                "displayText": speech,
                "contextOut": [{'name': 'topic_weather'}],
                "data": {},
                "source": ""
            }
        else:
            speech = 'At the moment I can only give information about countries and weather.'
            return {
                "speech": speech,
                "displayText": speech,
            }

    return {}


def getCountryData(req):
    result = req.get("result")
    parameters = result.get("parameters")
    country = parameters.get("geo-country")
    print('country: ', country)
    headers = {
        'X-Mashape-Key': 'B6wPYVylOhmshZvPcJg3moPyTEudp1j1l6ZjsneQrJFpQ42Dh0',
        'Accept': 'application/json',
    }
    url = 'https://restcountries-v1.p.mashape.com/name/{}'.format(country)
    result = requests.get(url, headers=headers)
    return result.json()[0]

def makeCountryCapitalSpeech(data):
    return 'The Capital of {} is {}'.format(data['name'], data['capital'])


def makeCountryPopulationSpeech(data):
    return '{} has {} inhabitants'.format(data['name'], data['population'])

def makeCountrySummarySpeech(data):
    return '{} is located in {}, it has {} inhabitants. It\'s capital is {}'.format(
        data['name'], data['subregion'], data['population'], data['capital'])


def makeWebhookCountryResult(data, speech):
    return {
        "speech": speech,
        "displayText": speech,
        "data": data,
        "contextOut": [],
        "source": "rest-countries-v1"
    }

def makeYqlQuery(city):
    print('city: ', city)
    if city is None:
        return None

    return "select * from weather.forecast where u='C' and woeid in (select woeid from geo.places(1) where text='" + \
           city + "')"


def makeWebhookResult(data, day):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    if day:
        print('day: ', day)
        forecasts = item.get('forecast')
        condition = (item for item in forecasts if datetime.datetime.strptime(item['date'], '%d %b %Y') ==
            datetime.datetime.strptime(day, '%Y-%m-%d')).__next__()
        if condition is None:
            return {}
        speech = day + ' in ' + location.get('city') + ': ' + condition.get('text') + \
                 ', high temperature is ' + condition.get('high') + ' ' + units.get('temperature') + \
                 ', low temperature is ' + condition.get('low') + ' ' + units.get('temperature')

    else:
        condition = item.get('condition')
        if condition is None:
            return {}
        speech = "Today in " + location.get('city') + ": " + condition.get('text') + \
                 ", the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        "data": data,
        "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print ("Starting app on port %d" % port)

    app.run(debug=True, port=port, host='0.0.0.0')



import concurrent.futures
import re
import urllib
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import nltk
import pandas as pd
import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from pandas import DataFrame
from tqdm import tqdm


def get_domain(url):
    match = re.search(r'https?://(?:www\.)?(.*?)(?:/|$)', url)
    if match:
        return match.group(1)
    else:
        return None


def generate_ngrams_without_stopwords(tokens, n):
    stop_words = {'будто', 'даже', 'вот', 'то', 'тоже', 'этот', 'все', 'него', 'были', 'более', 'ж', 'этого', 'его',
                  'ему', 'том', 'такой', 'вдруг', 'и', 'у', 'потому', 'другой', 'сам', 'ты', 'была', 'того', 'они',
                  'нас', 'про', 'надо', 'здесь', 'конечно', 'им', 'сейчас', 'может', 'только', 'раз', 'мы', 'тогда',
                  'ли', 'чуть', 'об', 'разве', 'не', 'ней', 'а', 'без', 'при', 'эту', 'между', 'хоть', 'ей', 'ни', 'ее',
                  'о', 'если', 'этой', 'эти', 'теперь', 'этом', 'ним', 'вам', 'от', 'но', 'со', 'так', 'нее', 'к',
                  'там', 'ну', 'он', 'под', 'из', 'в', 'во', 'чем', 'по', 'впрочем', 'ведь', 'еще', 'уж', 'уже', 'есть',
                  'чтоб', 'над', 'мне', 'себя', 'наконец', 'тебя', 'чтобы', 'же', 'них', 'тот', 'совсем', 'свою', 'с',
                  'что'}
    ngrams_result = []
    for i in range(len(tokens) - n + 1):
        ngram = tokens[i:i + n]
        if all(word not in stop_words for word in ngram):
            if all(len(word) <= 20 for word in ngram):
                ngrams_result.append(tuple(ngram))
    return ngrams_result


def get_wordstat_data(n_grams):
    wordstat_url = 'http://xmlriver.com/wordstat/json'
    user_id = '2649'
    key = '34ef24652b78ed0abf1707b67f914850bad01b48'

    wordstat_results = []
    unique_n_grams = set(n_grams)

    unique_wordstat_results = set()

    for n_gram_tuple in unique_n_grams:
        n_gram_str = ' '.join(n_gram_tuple)
        encoded_n_gram = urllib.parse.quote(n_gram_str)
        url = f"{wordstat_url}?user={user_id}&key={key}&query={encoded_n_gram}"
        response = requests.get(url)
        wordstat_data = response.json()

        suggestions = wordstat_data.get('content', {}).get('includingPhrases', {}).get('items', [])[:5]
        for suggestion in suggestions:
            phrase = suggestion.get('phrase')
            number = suggestion.get('number')
            unique_wordstat_results.add((phrase, number))

    wordstat_results = [{"Запрос": phrase, "Спрос": number} for phrase, number in unique_wordstat_results]

    if not wordstat_results:
        print("Отсутствуют результаты для формирования DataFrame")
        return pd.DataFrame()

    return pd.DataFrame(wordstat_results)


def check_positions(url_pars):
    user_id = '2649'
    key = '34ef24652b78ed0abf1707b67f914850bad01b48'
    yandex_url = 'http://xmlriver.com/search_yandex/xml'
    google_url = 'http://xmlriver.com/search/xml'

    response = requests.get(url_pars)
    soup = BeautifulSoup(response.content, 'html.parser')

    title_text = soup.title.string
    title_text = re.sub(r'[^\w\s-]', '', title_text)
    title_text = re.sub(r'-', ' ', title_text)
    title_tokens = nltk.word_tokenize(title_text.lower())
    title_words = [word for word in title_tokens if word not in stopwords.words('russian')]
    title_tri_grams = generate_ngrams_without_stopwords(title_words, 3)[:3]
    title_four_grams = generate_ngrams_without_stopwords(title_words, 4)[:4]

    wordstat_df: DataFrame = get_wordstat_data(title_tri_grams + title_four_grams)

    def check_single_query(query):
        global domain
        result = {"Запрос": query, "Yandex": None, "Google": None}
        domain = get_domain(url_pars)

        yandex_response = requests.get(yandex_url, params={'key': key, 'user': user_id, 'query': query})
        yandex_tree = ET.fromstring(yandex_response.content)
        yandex_error = yandex_tree.find('response/error')
        if yandex_error is not None:
            print(f"Yandex Error: Code: {yandex_error.get('code')}, Message: {yandex_error.text}\n")
        else:
            position = None
            for idx, item in enumerate(yandex_tree.findall('response/results/grouping/group/doc/url')):
                if domain in item.text:
                    position = idx + 1
                    break
            result["Yandex"] = position if position else '80'

        google_response = requests.get(google_url, params={'key': key, 'user': user_id, 'query': query})
        google_tree = ET.fromstring(google_response.content)
        google_error = google_tree.find('response/error')
        if google_error is not None:
            print(f"Google Error: Code: {google_error.get('code')}, Message: {google_error.text}\n")
        else:
            position = None
            for idx, item in enumerate(google_tree.findall('response/results/grouping/group/doc/url')):
                if domain in item.text:
                    position = idx + 1
                    break
            result["Google"] = position if position else '100'
        return result

    results = []
    queries = wordstat_df["Запрос"].to_list()
    if "Запрос" not in wordstat_df.columns:
        print("Отсутствует столбец 'Запрос' в DataFrame")
        return pd.DataFrame()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_single_query, query): query for query in queries}
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(queries), desc="Отправляю запросы"):
            results.append(future.result())

    positions_df = pd.DataFrame(results)
    df = pd.merge(wordstat_df, positions_df, on="Запрос")

    now = datetime.now()
    # dt_string = now.strftime("%d-%m-%Y")
    filename = f"keywords_report.csv"  # {dt_string}
    df.to_csv(filename, index=False)

    return df


# result = check_positions("https://cryptoteh.ru/glaz-boga-kak-rabotaet-telegram-bot-kak-im-polzovatsya/")
result = check_positions("https://www.runlab.ru/reviews/kak-vyibrat-pravilnyie-krossovki-dlya-bega.html")
print(result)

# TODO
# 1. Из присланных запросов вордстата взять не первые 5, а 5 наиболее релевантных по TF-IDF
# 2. Для триграмм и четвергограмм взять не только из title страницы, а ещё по 2шт из 3х title на первых местах выдачи
# 3. В результатах есть + у запросов, их нужно убрать, потому что частотность с операторами снимается с ошибкой
# 3.1. Добавить второй столбец со "спросом". нужно сделать дополнительный запрос этих же запросов с кавычками
# 4. Сделать второй инструмент, который на вход принимает поисковые запросы, кластеризует их по гуглу

import concurrent.futures
import re
import time
import urllib
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import nltk
import pandas as pd
import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from pandas import DataFrame
from tqdm import tqdm
from transliterate import translit

start_time = time.time()


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
    user_id = '2649'
    key = '34ef24652b78ed0abf1707b67f914850bad01b48'

    wordstat_results = []
    suggestion_phrases = []

    # этап 1: сбор запросов
    for n_gram_tuple in n_grams:
        n_gram_str = ' '.join(n_gram_tuple)
        encoded_n_gram = urllib.parse.quote(n_gram_str)
        url = f"http://xmlriver.com/wordstat/json?regions=225&user={user_id}&key={key}&query={encoded_n_gram}"
        response = requests.get(url)
        wordstat_data = response.json()

        suggestions = wordstat_data.get('content', {}).get('includingPhrases', {}).get('items', [])[:5]
        for suggestion in suggestions:
            phrase = suggestion.get('phrase').replace('+', '')
            suggestion_phrases.append(phrase)

    stage_1_end_time = time.time()
    print(f"Конец сбора запросов, время: {round(stage_1_end_time - start_time, 1)} секунд")

    # этап 2: запросы без кавычек
    for phrase in suggestion_phrases:
        encoded_phrase = urllib.parse.quote(phrase)
        url = f"http://xmlriver.com/wordstat/json?regions=225&user={user_id}&key={key}&query={encoded_phrase}"
        response = requests.get(url)
        wordstat_data = response.json()

        info = wordstat_data.get('content', {}).get('includingPhrases', {}).get('info', [])
        number = int(info[2].split(' ')[0]) if len(info) > 2 else 0

        # сохраняем запрос и число в результатах, оставляя место для числа в кавычках
        wordstat_results.append({"Запрос": phrase, "Спрос": number, '"Спрос"': None})

    stage_2_end_time = time.time()
    print(f"Конец сбора спроса, время: {round(stage_2_end_time - stage_1_end_time, 1)} секунд")

    # этап 3: запросы в кавычках
    for i, result in enumerate(wordstat_results):
        encoded_phrase_quoted = urllib.parse.quote(result["Запрос"])
        url_quoted = f'http://xmlriver.com/wordstat/json?regions=225&user={user_id}&key={key}&query="{encoded_phrase_quoted}"'
        response_quoted = requests.get(url_quoted)
        wordstat_data_quoted = response_quoted.json()

        info_quoted = wordstat_data_quoted.get('content', {}).get('includingPhrases', {}).get('info', [])
        number_quoted = int(info_quoted[2].split(' ')[0]) if len(info_quoted) > 2 else 0

        # добавляем число в кавычках в результаты
        wordstat_results[i]['"Спрос"'] = number_quoted

    stage_3_end_time = time.time()
    print(f'Конец сбора "спроса", время: {round(stage_3_end_time - stage_2_end_time, 1)} секунд')

    if not wordstat_results:
        print("Отсутствуют результаты для формирования DataFrame")
        return pd.DataFrame()

    df = pd.DataFrame(wordstat_results)

    return df


def contains_english_words(string: str, num_words: int) -> bool:
    words = nltk.word_tokenize(string.lower())
    first_words = words[:num_words]
    english_words = [word for word in first_words if re.match(r'[a-z]', word)]
    return len(english_words) > 0


def transliterate_title(title: str) -> str:
    return translit(title, "ru")


def check_positions():
    user_id = '2649'
    key = '34ef24652b78ed0abf1707b67f914850bad01b48'
    yandex_url = 'http://xmlriver.com/search_yandex/xml'
    google_url = 'http://xmlriver.com/search/xml'

    # url_pars = "https://cryptoteh.ru/glaz-boga-kak-rabotaet-telegram-bot-kak-im-polzovatsya"
    url_pars = "https://onespot.one/all-posts/kak-poluchit-galochku-v-telegram-verifikaciya-kanala"

    response = requests.get(url_pars)
    soup = BeautifulSoup(response.content, 'html.parser')

    title_text = soup.title.string
    title_text = re.sub(r'[^\w\s-]', '', title_text)
    title_text = re.sub(r'-', ' ', title_text)

    title_text_transliterated = ""
    if contains_english_words(title_text, 5):
        title_text_transliterated = transliterate_title(title_text)

    title_tokens = nltk.word_tokenize(title_text.lower())
    title_words = [word for word in title_tokens if word not in stopwords.words('russian')]
    title_tri_grams = generate_ngrams_without_stopwords(title_words, 3)[:3]
    title_four_grams = generate_ngrams_without_stopwords(title_words, 4)[:4]

    title_tri_grams_translit = []
    title_four_grams_translit = []
    if title_text_transliterated:
        title_tokens_translit = nltk.word_tokenize(title_text_transliterated.lower())
        title_words_translit = [word for word in title_tokens_translit if word not in stopwords.words('russian')]
        title_tri_grams_translit = generate_ngrams_without_stopwords(title_words_translit, 3)[:3]
        title_four_grams_translit = generate_ngrams_without_stopwords(title_words_translit, 4)[:4]

    wordstat_df: DataFrame = get_wordstat_data(
        title_tri_grams + title_four_grams + title_tri_grams_translit + title_four_grams_translit)

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
            from urllib.parse import urlparse
            answerbox_url = google_tree.find('response/answerbox/url')
            if answerbox_url is not None and domain == urlparse(answerbox_url.text).netloc:
                position = 1
            else:
                # Проверяем узел `zeroposition`
                zeroposition_url = google_tree.find('response/addresults/zeroposition/url')
                if zeroposition_url is not None and domain == urlparse(zeroposition_url.text).netloc:
                    position = 1
                else:
                    # Если домен не найден в `zeroposition`, продолжаем поиск в `doc`
                    for idx, item in enumerate(google_tree.findall('response/results/grouping/group/doc/url')):
                        if domain == urlparse(item.text).netloc:
                            position = idx + 2  # Увеличиваем индекс на 2, потому что у нас есть `zeroposition`
                            break
            result["Google"] = position if position else '100'
            # print(result)
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

    results = [result for result in results if result is not None]
    positions_df = pd.DataFrame(results)
    df = pd.merge(wordstat_df, positions_df, on="Запрос")

    # now = datetime.now()
    # dt_string = now.strftime("%d-%m-%Y")
    stage_5_end_time = time.time()
    print(f"Финиш, время выполения: {stage_5_end_time} секунд")
    filename = f"keywords_report.csv"  # {dt_string}
    df.to_csv(filename, index=False)

    return df


# result = check_positions("https://cryptoteh.ru/glaz-boga-kak-rabotaet-telegram-bot-kak-im-polzovatsya/")
result = check_positions()
print(result)

# TODO
# 1. Из присланных запросов вордстата взять не первые 5, а 5 наиболее релевантных по TF-IDF
# 2. Для триграмм и четвергограмм взять не только из title страницы, а ещё по 2шт из 3х title на первых местах выдачи
# 3.1. Добавить второй столбец со "спросом". нужно сделать дополнительный запрос этих же запросов с кавычками
# 4. Сделать второй инструмент, который на вход принимает поисковые запросы, кластеризует их по гуглу

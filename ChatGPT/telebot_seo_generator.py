import openai
import telebot
from telebot import types
import emoji
import sqlite3

# "[На новые лимиты (visa,mc,мир,Юmoney)](https://yoomoney.ru/to/410015884273666)\n"

token="6092023526:AAFM9JjNthNbv0eJEyY8lDA66AZKluEjlqE"
bot=telebot.TeleBot(token)


@bot.message_handler(commands=['start'])
def start_message(message):
    conn = sqlite3.connect('/home/dietbear/PycharmProjects/test1/ChatGPT/db/database', check_same_thread=False)
    cursor = conn.cursor()
    id = message.from_user.id
    user_name = message.from_user.first_name
    user_sname = message.from_user.last_name
    username = message.from_user.username

    cursor.execute(f"SELECT limits FROM user_limits WHERE user_id = {id}")
    limits_count = cursor.fetchone()
    if limits_count == None:
        cursor.execute(
            'INSERT or IGNORE INTO user_limits (user_id, user_name, user_surname, username) VALUES (?, ?, ?, ?)',
            (id, user_name, user_sname, username))
        conn.commit()
        # db_table_val(user_id=id, user_name=user_name, user_surname=user_sname, username=username)

        bot.send_message(message.chat.id, f"Привет, {user_name} ✌️\n\n"
                                          f"Начислил тебе лимитов. Нажми ещё раз на /start",
                         parse_mode='Markdown', disable_web_page_preview=True)
        bot.send_message(message.chat.id, "Многое ещё в процессе..")
    else:
        bot.send_message(message.chat.id,f"Привет, {user_name} ✌️\n\n"
                                         f"{emoji.emojize(':red_exclamation_mark:')} У тебя осталось {limits_count[0]} запросов,"
                                         f" новое начисление N раз в неделю.\n\n"
                                         "Команды и функции генератора:\n"
                                         "/help — (не работает) Справка по боту\n\n"
                                         f"/gt     —  Подкину идей для информационки по ключу\n"
                                         f"/gh    —  Составлю структуру h1-6 в формате ТЗ\n"
                                         f"/gm   —  Напишу 3 CTA description по ключу\n"
                                         f"/ga    — (не работает) Генерация анкоров для ссылок",

                                        parse_mode='Markdown', disable_web_page_preview=True)
        bot.send_message(message.chat.id, "*Тут будет инфа о новых инструментах или другие новости")


@bot.message_handler(func=lambda message: True, commands=['gt'])
def get_themes(message):
    mesg = bot.send_message(message.chat.id, text='Ищем идеи для тем по своему ВЧ-запросу: ')
    bot.register_next_step_handler(mesg, action1)

def action1(message):
    user_answer = message.text
    conn = sqlite3.connect('/home/dietbear/PycharmProjects/test1/ChatGPT/db/database', check_same_thread=False)
    cursor = conn.cursor()
    id = message.from_user.id
    user_name = message.from_user.first_name
    user_sname = message.from_user.last_name
    username = message.from_user.username

    ### Модуль проверки и списания лимитов ###

    cursor.execute(f"SELECT limits, username FROM user_limits WHERE user_id = {id}")
    result = cursor.fetchone()
    if result[0] != 0:
        openai.api_key = "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"
        limit_count = result[0]
        new_limit_count = int(limit_count) - 1
        cursor.execute(f'UPDATE user_limits SET limits={new_limit_count} WHERE user_id={id}')  # обновляем записи в таблице.
        conn.commit()

        ### Отправка запроса ###
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": f"Собери SEO контент-план из разных информационных статей на тему «{user_answer}»"
                }
            ]
        )
        # 01 Найди 10 уникальных тем для статей «{promt}»

        answer_gpt = completion.choices[0].message.content
        bot.send_message(message.chat.id, text=answer_gpt)
    else:
        bot.send_message(message.chat.id, text=f'{user_name}, у тебя закончились лимиты. Дай обратную связь по боту @bulgakov_seo, я накину ещё {emoji.emojize(":winking_face:")}')



@bot.message_handler(func=lambda message: True, commands=['gm'])
def get_meta(message):
    mesg = bot.send_message(message.chat.id, text='Пишем 5 вариантов CTA description по ВЧ-ключу: ')
    bot.register_next_step_handler(mesg, action)

def action(message):
    user_answer = message.text

    conn = sqlite3.connect('/home/dietbear/PycharmProjects/test1/ChatGPT/db/database', check_same_thread=False)
    cursor = conn.cursor()
    id = message.from_user.id
    user_name = message.from_user.first_name
    user_sname = message.from_user.last_name
    username = message.from_user.username
    cursor.execute(f"SELECT limits, username FROM user_limits WHERE user_id = {id}")
    result = cursor.fetchone()
    if result[0] != 0:
        openai.api_key = "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"
        limit_count = result[0]
        new_limit_count = int(limit_count) - 1
        cursor.execute(f'UPDATE user_limits SET limits={new_limit_count} WHERE user_id={id}')  # обновляем записи в таблице.
        conn.commit()
        openai.api_key = "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"
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": f"Напиши 3 CTA description не больше 200 символов для страницы сайта «{user_answer}»"
                }
            ]
        )

        answer_gpt = completion.choices[0].message.content
        bot.send_message(message.chat.id, text=answer_gpt)
    else:
        bot.send_message(message.chat.id, text=f'{user_name}, у тебя закончились лимиты. Дай обратную связь по боту @bulgakov_seo, я накину ещё {emoji.emojize(":winking_face:")}')


@bot.message_handler(func=lambda message: True, commands=['gh'])
def get_headers(message):
    mesg = bot.send_message(message.chat.id, text='Создаём структуру h1-6 в формате ТЗ, я пользуюсь такой формулой (пример) «Телеграм боты: виды ботов, что умеют боты в телеграм, как создать бота в телеграм без программирования»')
    mesg = bot.send_message(message.chat.id, text='А теперь вводи тему статьи: ')
    bot.register_next_step_handler(mesg, action)

def action(message):
    user_answer = message.text
    conn = sqlite3.connect('/home/dietbear/PycharmProjects/test1/ChatGPT/db/database', check_same_thread=False)
    cursor = conn.cursor()
    id = message.from_user.id
    user_name = message.from_user.first_name
    user_sname = message.from_user.last_name
    username = message.from_user.username
    cursor.execute(f"SELECT limits, username FROM user_limits WHERE user_id = {id}")
    result = cursor.fetchone()
    if result[0] != 0:
        openai.api_key = "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"
        limit_count = result[0]
        new_limit_count = int(limit_count) - 1
        cursor.execute(f'UPDATE user_limits SET limits={new_limit_count} WHERE user_id={id}')  # обновляем записи в таблице.
        conn.commit()
        openai.api_key = "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"
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": f"Создай структуру заголовков h1-6 для статьи «{user_answer}»"
                },
                {
                    "role": "user",
                    "content": "Для каждого заголовка h2-6 напиши идеи для содержания в формате вопроса"
                }
            ]
        )
        # ### УДАЧНЫЕ ЗАПРОСЫ ###
        # # 01 "Для каждого заголовка h2-6 напиши идеи для содержания"
        # # 02 "Для каждого заголовка h2-6 напиши по 4 идеи для содержания в формате вопроса"

        answer = completion.choices[0].message.content
        bot.send_message(message.chat.id, text=answer)
    else:
        bot.send_message(message.chat.id, text=f'{user_name}, у тебя закончились лимиты. Дай обратную связь по боту @bulgakov_seo, я накину ещё {emoji.emojize(":winking_face:")}')

@bot.message_handler(func=lambda message: True, commands=['ga'])
def get_headers(message):
    mesg = bot.send_message(message.chat.id, text='Создаём структуру h1-6 в формате ТЗ, я пользуюсь такой формулой (пример) «Телеграм боты: виды ботов, что умеют боты в телеграм, как создать бота в телеграм без программирования»')
    mesg = bot.send_message(message.chat.id, text='А теперь вводи тему статьи: ')
    bot.register_next_step_handler(mesg, action)

def action(message):
    user_answer = message.text
    conn = sqlite3.connect('/home/dietbear/PycharmProjects/test1/ChatGPT/db/database', check_same_thread=False)
    cursor = conn.cursor()
    id = message.from_user.id
    user_name = message.from_user.first_name
    user_sname = message.from_user.last_name
    username = message.from_user.username
    cursor.execute(f"SELECT limits, username FROM user_limits WHERE user_id = {id}")
    result = cursor.fetchone()
    if result[0] != 0:
        openai.api_key = "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"
        limit_count = result[0]
        new_limit_count = int(limit_count) - 1
        cursor.execute(f'UPDATE user_limits SET limits={new_limit_count} WHERE user_id={id}')  # обновляем записи в таблице.
        conn.commit()
        openai.api_key = "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"
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": f"Создай структуру заголовков h1-6 для статьи «{user_answer}»"
                },
                {
                    "role": "user",
                    "content": "Для каждого заголовка h2-6 напиши идеи для содержания в формате вопроса"
                }
            ]
        )
        ### УДАЧНЫЕ ЗАПРОСЫ ###
        # 01 "Для каждого заголовка h2-6 напиши идеи для содержания"
        # 02 "Для каждого заголовка h2-6 напиши по 4 идеи для содержания в формате вопроса"

        answer = completion.choices[0].message.content
        bot.send_message(message.chat.id, text=answer)
    else:
        bot.send_message(message.chat.id, text=f'{user_name}, у тебя закончились лимиты. Дай обратную связь по боту @bulgakov_seo, я накину ещё {emoji.emojize(":winking_face:")}')


bot.polling(none_stop=True)


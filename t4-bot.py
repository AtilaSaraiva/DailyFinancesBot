import asyncio
import logging

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_polling
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from datetime import datetime
import aiogram.utils.markdown as md
import pandas as pd
import csv

# Token do bot
API_TOKEN =

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()
bot = Bot(token=API_TOKEN, loop=loop) #Criando o objeto do bot
storage = MemoryStorage() #Criando o storage
dp = Dispatcher(bot,storage=storage) #Criando o dispatcher que vai responder as mensagens
Index = ['dia_gasto','gasto','hora_gasto','saldo','budget','saldo_do_dia','next_income_day','days_left','last_budget_calc']

#i = f[0].split('&')

try:
    with open("storage.csv","r") as f:
        nomes = f.readline().rstrip('\n').split('&')
        del nomes[0]
        print(nomes)
        for i in range(len(nomes)):
            nomes[i] = int(nomes[i])
    sto = pd.read_csv("storage.csv",names=nomes,sep='&',index_col=0,skiprows=1)
    sto = sto.fillna('')
    sto.loc['saldo',:] = float(sto.loc['saldo',:])
    sto.loc['budget',:] = float(sto.loc['budget',:])
    sto.loc['saldo_do_dia',:] = float(sto.loc['saldo_do_dia',:])
    sto.loc['days_left',:] = int(sto.loc['days_left',:])
except:
    sto = pd.DataFrame(data=None,index=Index)
print(sto)


# States
NORMAL = 'normal state'
INCOME = "income"
INCOMEDAY = "process the income day"

def string_para_dia(dia):
    """Essa função transforma uma string de data no formado dd/mm/aaa para o formato da biblioteca datetime"""
    dia_split = dia.split('/')
    return datetime(int(dia_split[2]),int(dia_split[1]),int(dia_split[0]))

def dia_para_string(dia):
    """Essa função faz o oposto da função string_para_dia, tranformando um objeto da biblioteca database para uma string de data no formato dd/mm/aaaa"""
    return f"{dia.day}/{dia.month}/{dia.year}"


@dp.message_handler(state=NORMAL,commands=['stop'])
async def limpar_dados(message: types.Message):
    """Essa função limpa todos os dados para o caso do usuário encontrar um bug"""
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    markup = types.ReplyKeyboardRemove()
    await bot.send_message(message.chat.id,"Hello darkness my old friend...",reply_markup = markup)
    await state.reset_data()
    await state.reset_state()
    del sto[message.chat.id]

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Essa função é ativada sempre que o usuário inserir o comando /start, iniciando o relacionamento do bot com ele"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Retirando o teclado customizado caso ele ainda esteja sendo utilizando
    markup = types.ReplyKeyboardRemove()

    # Mensagem de boas vinda
    await bot.send_message(message.chat.id,"Hi! I am a bot that will give you daily budgets every day. However, there is more, because if you save some money today, it will be added to your tomorrow's budget. In that manner, you can accumulate 'saving streaks' for multiple days to buy something you want, or even to hangout with your friends.\n\nI hope you will have a fruitful experience, so if you have any suggestion please get in contact with my developer @atila09", reply_markup = markup)

    # Define valores iniciais para as variáveis do storage
    await state.update_data(dia_gasto='',gasto='',hora_gasto='',saldo=0,budget=0,saldo_do_dia=0)
    sto.loc[:,message.chat.id] = [0,0,0,0,0,0,0,0,0]

    # Envia mensagem para o usuário para pegar o valor de dinheiro que ele tem no total
    await bot.send_message(message.chat.id,"How much money do you have right now?")

    # Define o estado como o da variável INCOME para invocar automaticamente a função dinheiro_porra, e perguntar quando o usuário receberá o próximo dinheros
    await state.set_state(INCOME)

@dp.message_handler(commands=['wallet'])
async def somar_gastos(message: types.Message):
    """Essa função permite que o usuário tenha acesso ao valor que pode ser gasto ainda no dia bem como quanto ainda tem para gastar"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    #print(sto.loc[:,message.chat.id])
    if not message.chat.id in sto.columns:
        # Retirando o teclado customizado caso ele ainda esteja sendo utilizando
        markup = types.ReplyKeyboardRemove()

        await bot.send_message(message.chat.id,"Hey! You Should first use the command /start so we may start our beautiful relationship",reply_markup = markup)

    else:
        await state.set_state(NORMAL)
        await state.update_data(
                dia_gasto=sto.loc['dia_gasto',message.chat.id],
                gasto=sto.loc['gasto',message.chat.id],
                hora_gasto=sto.loc['hora_gasto',message.chat.id],
                saldo=sto.loc['saldo',message.chat.id],
                budget=sto.loc['budget',message.chat.id],
                saldo_do_dia=sto.loc['saldo_do_dia',message.chat.id],
                next_income_day=sto.loc['next_income_day',message.chat.id],
                days_left=sto.loc['days_left',message.chat.id],
                last_budget_calc=sto.loc['last_budget_calc',message.chat.id])

        data = await state.get_data()

        # Calcula quanto foi gasto
        x = data['gasto']
        gastos = x.split(';')
        gastos.pop(0)
        soma = 0.0
        for num in gastos:
            soma = soma + float(num)

        # Calculo de quanto sobrou
        grana = data['saldo'] - soma

        # Recuperação do último dia de uso do comando /wallet
        last_budget_calc = string_para_dia(data['last_budget_calc'])

        # Cálculo de quanto sobra do que pode ser gasto do dia
        daily_budget = data['budget']
        today_budget = data['saldo_do_dia']
        next_inc_day = data['next_income_day']
        next_inc_day = string_para_dia(next_inc_day)
        if (datetime.now() - next_inc_day).days > 0:
            dias_passados = (next_inc_day - last_budget_calc).days
            if dias_passados>0:
                today_budget = today_budget + dias_passados.days * daily_budget - soma
            else:
                await bot.send_message(message.chat.id,f"Já passou do seu dia de recebimento do próximo dinheiro, então primeiro atualize o quanto de dinheiro você tem")
        else:
            dias_passados = datetime.now() - last_budget_calc
            today_budget = today_budget + dias_passados.days * daily_budget - soma

        # String da data do uso do comando
        today = dia_para_string(datetime.now())

        # Atualização dos dados
        await state.update_data(last_budget_calc=today,
                        saldo_do_dia=today_budget,
                        gasto='',
                        dia_gasto='',
                        hora_gasto='',
                        saldo=grana)

        sto.loc['last_budget_calc',message.chat.id] = today
        sto.loc['saldo_do_dia',message.chat.id] = today_budget
        sto.loc['gasto',message.chat.id] = ''
        sto.loc['dia_gasto',message.chat.id] = ''
        sto.loc['hora_gasto',message.chat.id] = ''
        sto.loc['saldo',message.chat.id] = grana
        sto.to_csv(path_or_buf="storage.csv",sep='&')

        # Envia feedback para usuário
        await bot.send_message(message.chat.id,f"If you entered you data correctly you surely have a total amount of ${round(grana,2)}\n\nYou can still spend ${round(today_budget,2)} today, since your daily budget is ${round(daily_budget,2)}")

@dp.message_handler(commands=['income'])
async def income(message: types.Message):
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    #print(sto.loc[:,message.chat.id])
    if not message.chat.id in sto.columns:
        # Retirando o teclado customizado caso ele ainda esteja sendo utilizando
        markup = types.ReplyKeyboardRemove()

        await bot.send_message(message.chat.id,"Hey! You Should first use the command /start so we may start our beautiful relationship",reply_markup = markup)

    else:
        await state.set_state(NORMAL)
        await state.update_data(
                dia_gasto=sto.loc['dia_gasto',message.chat.id],
                gasto=sto.loc['gasto',message.chat.id],
                hora_gasto=sto.loc['hora_gasto',message.chat.id],
                saldo=sto.loc['saldo',message.chat.id],
                budget=sto.loc['budget',message.chat.id],
                saldo_do_dia=sto.loc['saldo_do_dia',message.chat.id],
                next_income_day=sto.loc['next_income_day',message.chat.id],
                days_left=sto.loc['days_left',message.chat.id],
                last_budget_calc=sto.loc['last_budget_calc',message.chat.id])

        # Envia mensagem para o usuário para pegar o valor de dinheiro que ele tem no total
        await bot.send_message(message.chat.id,"How much money have you received?")

        # Define o estado como o da variável INCOME para invocar automaticamente a função dinheiro_porra, e perguntar quando o usuário receberá o próximo dinheros
        await state.set_state(INCOME)

@dp.message_handler()
async def recover_data(message: types.Message):
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    #print(sto.loc[:,message.chat.id])
    if not message.chat.id in sto.columns:
        # Retirando o teclado customizado caso ele ainda esteja sendo utilizando
        markup = types.ReplyKeyboardRemove()

        await bot.send_message(message.chat.id,"Hey! You Should first use the command /start so we may start our beautiful relationship",reply_markup = markup)

    else:
        await state.set_state(NORMAL)
        await state.update_data(
                dia_gasto=sto.loc['dia_gasto',message.chat.id],
                gasto=sto.loc['gasto',message.chat.id],
                hora_gasto=sto.loc['hora_gasto',message.chat.id],
                saldo=sto.loc['saldo',message.chat.id],
                budget=sto.loc['budget',message.chat.id],
                saldo_do_dia=sto.loc['saldo_do_dia',message.chat.id],
                next_income_day=sto.loc['next_income_day',message.chat.id],
                days_left=sto.loc['days_left',message.chat.id],
                last_budget_calc=sto.loc['last_budget_calc',message.chat.id])

        dados = await state.get_data()
        gasto = dados['gasto']

        # Armazena tanto o valor gasto, quanto a data e hora do gasto
        try:
            num = float(message.text)
            gasto = gasto + ';' + message.text
            data_gasto = datetime.now()
            dia = f"{data_gasto.day}/{data_gasto.month}/{data_gasto.year}"
            hora = f"{data_gasto.hour}:{data_gasto.minute}"
            dias_despesas = dados['dia_gasto']
            dias_despesas = dias_despesas + ';' + dia
            horas_despesas = dados['hora_gasto'] + ';' + hora

            # Armazena os dados novos no storage do usuário
            await state.update_data(gasto=gasto,dia_gasto=dias_despesas,hora_gasto=horas_despesas)
            sto.loc['gasto',message.chat.id] = gasto
            sto.loc['dia_gasto',message.chat.id] = dias_despesas
            sto.loc['hora_gasto',message.chat.id] = horas_despesas

            sto.to_csv(path_or_buf="storage.csv",sep='&')

        except ValueError:
            # Caso o valor inserido pelo usuário esteja errado, o feedback do erro é enviado
            await message.reply("This is not a number is it? You probably wrote a command wrongly or a number with comma instead of dot decimal separator")


@dp.message_handler(state=INCOME)
async def dinheiro_porra(message: types.Message):
    """Essa função pega o quanto de dinheiro o usuário tem, e pergunta quando recebe o próximo"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Pega o dicionário com os dados do storage do usuário
    data = await state.get_data()

    try:
        # Pega o quanto de dinheiro o usuário tem a partir do valor que ele inseriu
        total_income = data['saldo'] + float(message.text)

        # Anota esse valor no storage do usuário
        await state.update_data(saldo=total_income)
        sto.loc['saldo',message.chat.id] = total_income

        # Define o estado como o da variável INCOMEDAY, para invocar a função dinheiro_porra2 para pegar quando o usuário recebe dinheiro de novo
        await state.set_state(INCOMEDAY)

        # Envia pergunta para o usuário pra saber quando ele recebe dinheiro de novo
        await message.reply("Hey when will you receive your next income? Please answer in dd/mm format.")

    except:
        await message.reply("I don't understand what you've said, please write a number with dot as decimal separator")


@dp.message_handler(state=INCOMEDAY)
async def dinheiro_porra2(message: types.Message):
    """Essa função pega o quando o usuário vai pegar o próximo dinheiro e já calcula o daily budget dele de quebra"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    try:
        # Pega a string digitada pelo usuário que em tese contem a data de recebimento da próxima grana
        # e de quebra separa o dia e o mês pela barra \
        next_inc_day = message.text.split('/')

        # Pega a data atual exata
        current_inc_day = datetime.now()

        # Verifica se a data de recebimento do próximo dinheiro é depois da virada do ano e age de acordo
        if int(next_inc_day[1]) >= current_inc_day.month:
            nid_object = datetime(datetime.now().year,int(next_inc_day[1]),int(next_inc_day[0]))
        else:
            nid_object = datetime(datetime.now().year+1,int(next_inc_day[1]),int(next_inc_day[0]))

        # Pega o dia de hoje
        current_inc_day = datetime.today()

        # Calcula quanto tempo falta para o próximo recebimento
        days_left_inc = nid_object - current_inc_day

        # Transforma o objeto de data do próximo recebimento para string para ser armazenado
        nid_str = dia_para_string(nid_object)
        await state.update_data(next_income_day=nid_str)
        await state.update_data(days_left=days_left_inc.days)
        sto.loc['next_income_day',message.chat.id] = nid_str
        sto.loc['days_left',message.chat.id] = days_left_inc.days

        # Pega os dados do storage do usuário
        dados = await state.get_data()

        # Pega o saldo prévio do usuário
        saldo = dados['saldo']

        # Mostra no terminal quantos dias faltam para o próximo recebimento para monitorar bugs
        print(saldo,days_left_inc.days,dia_para_string(current_inc_day),nid_str)

        # Cálculo do daily_budget
        daily_budget = saldo / (days_left_inc.days + 2)

        # Cria uma string para o dia de inserção dos dados
        dia = f"{current_inc_day.day}/{current_inc_day.month}/{current_inc_day.year}"

        # Atualiza os dados no storage
        await state.update_data(budget=daily_budget,saldo_do_dia=daily_budget,last_budget_calc=dia)
        sto.loc['budget',message.chat.id] = daily_budget
        sto.loc['saldo_do_dia',message.chat.id] = daily_budget
        sto.loc['last_budget_calc',message.chat.id] = dia

        # Cria teclado para facilitar o uso do comando /wallet
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
        markup.add("/wallet")

        # Manda pro usuário o feedback
        await message.reply(f"Ok! That means you can spend ${round(daily_budget,2)} per day\n\nNow you just need to type every expense you make and i will jot it down.\n\nWhen you need to know how much money you have and today's daily budget you should use the /wallet command.",reply_markup=markup)

        #Redefine o state para que agora as msgs do usuário ativem as funções somar_gastos e get_expense
        await state.set_state(NORMAL)

    except:
        await message.reply(f"I don't quite understand what you've said, please write in the dd/mm format")


@dp.message_handler(state=NORMAL,commands=['income'])
async def income(message: types.Message):
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Envia mensagem para o usuário para pegar o valor de dinheiro que ele tem no total
    await bot.send_message(message.chat.id,"How much money have you received?")

    # Define o estado como o da variável INCOME para invocar automaticamente a função dinheiro_porra, e perguntar quando o usuário receberá o próximo dinheros
    await state.set_state(INCOME)


@dp.message_handler(state=NORMAL,commands=['wallet'])
async def somar_gastos(message: types.Message):
    """Essa função permite que o usuário tenha acesso ao valor que pode ser gasto ainda no dia bem como quanto ainda tem para gastar"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Pega os dados do storage do usuário
    data = await state.get_data()

    # Calcula quanto foi gasto
    x = data['gasto']
    gastos = x.split(';')
    gastos.pop(0)
    soma = 0.0
    for num in gastos:
        soma = soma + float(num)

    # Calculo de quanto sobrou
    grana = float(data['saldo']) - soma

    # Recuperação do último dia de uso do comando /wallet
    last_budget_calc = string_para_dia(data['last_budget_calc'])

    # Cálculo de quanto sobra do que pode ser gasto do dia
    daily_budget = data['budget']
    today_budget = data['saldo_do_dia']
    next_inc_day = data['next_income_day']
    next_inc_day = string_para_dia(next_inc_day)
    if (datetime.now() - next_inc_day).days > 0:
        dias_passados = (next_inc_day - last_budget_calc).days
        if dias_passados>0:
            today_budget = today_budget + dias_passados.days * daily_budget - soma
        else:
            await bot.send_message(message.chat.id,f"Já passou do seu dia de recebimento do próximo dinheiro, então primeiro atualize o quanto de dinheiro você tem")
    else:
        dias_passados = datetime.now() - last_budget_calc
        today_budget = today_budget + dias_passados.days * daily_budget - soma

    # String da data do uso do comando
    today = dia_para_string(datetime.now())

    # Atualização dos dados
    await state.update_data(last_budget_calc=today,
                      saldo_do_dia=today_budget,
                      gasto='',
                      dia_gasto='',
                      hora_gasto='',
                      saldo=grana)

    sto.loc['last_budget_calc',message.chat.id] = today
    sto.loc['saldo_do_dia',message.chat.id] = today_budget
    sto.loc['gasto',message.chat.id] = ''
    sto.loc['dia_gasto',message.chat.id] = ''
    sto.loc['hora_gasto',message.chat.id] = ''
    sto.loc['saldo',message.chat.id] = grana
    sto.to_csv(path_or_buf="storage.csv",sep='&')

    # Envia feedback para usuário
    await bot.send_message(message.chat.id,f"If you entered you data correctly you surely have a total amount of ${round(grana,2)}\n\nYou can still spend ${round(today_budget,2)} today, since your daily budget is ${round(daily_budget,2)}")


@dp.message_handler(state=NORMAL)
async def get_expense(message: types.Message):
    """Essa função recebe os gastos"""
    # Pega o estado da conversa do usuário para que se acesse os dados do usuário
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)

    # Pega os dados do storage do usuário
    dados = await state.get_data()
    gasto = dados['gasto']

    # Armazena tanto o valor gasto, quanto a data e hora do gasto
    try:
        num = float(message.text)
        gasto = gasto + ';' + message.text
        data_gasto = datetime.now()
        dia = f"{data_gasto.day}/{data_gasto.month}/{data_gasto.year}"
        hora = f"{data_gasto.hour}:{data_gasto.minute}"
        dias_despesas = dados['dia_gasto']
        dias_despesas = dias_despesas + ';' + dia
        horas_despesas = dados['hora_gasto'] + ';' + hora

        # Armazena os dados novos no storage do usuário
        await state.update_data(gasto=gasto,dia_gasto=dias_despesas,hora_gasto=horas_despesas)
        sto.loc['gasto',message.chat.id] = gasto
        sto.loc['dia_gasto',message.chat.id] = dias_despesas
        sto.loc['hora_gasto',message.chat.id] = horas_despesas

        sto.to_csv(path_or_buf="storage.csv",sep='&')

    except ValueError:
        # Caso o valor inserido pelo usuário esteja errado, o feedback do erro é enviado
        await message.reply("This is not a number is it? You probably wrote a command wrongly or a number with comma instead of dot decimal separator")

    # Mostra no terminal os dados armazenados até então
    #print(await state.get_data())


if __name__ == '__main__':
    start_polling(dp, loop=loop, skip_updates=True)

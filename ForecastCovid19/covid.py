import pandas as pd
import numpy as np
# import matplotlib.pyplot as plt
# import seaborn as sns
import streamlit as st 

from datetime import datetime

import plotly.offline as py
import plotly.graph_objs as go

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout


def data_estado(estado, df):
    dfe = df.loc[df["Estado"] == estado]
    dfe.loc[dfe["Casos Acumulados"] == 0, "Casos Acumulados"] = None
    dfe.dropna(inplace=True)
    dfe.reset_index(drop=True, inplace=True)
    return dfe


def data_regiao(regiao, df):
    dfr = df.loc[df["Região"] == regiao]
    dfr.loc[dfr["Casos Acumulados"] == 0, "Casos Acumulados"] = None
    dfr.dropna(inplace=True)
    dfr.reset_index(drop=True, inplace=True)
    return dfr


@st.cache()
def plot_estado(dfe, estado, mode, color):
    trace = [go.Bar(x = dfe["Data"], 
                y = dfe[mode],
                marker = {"color":"{}".format(color)},
                opacity=0.8)]

    layout = go.Layout(title='{} de COVID-19 - {}'.format(mode,estado),
                    yaxis={'title':mode},
                    xaxis={'title': 'Data do registro'})

    fig = go.Figure(data=trace, layout=layout)
    return(fig)


@st.cache()
def plot_regiao(dfr, regiao, mode, colorint, colorstepint):

    estados = list(dfr["Estado"].unique())
    trace = []
    i = 0
    for estado in estados:
        color = colorint+i
        dfe = data_estado(estado, dfr)
        trace.append(go.Bar(x = dfe["Data"], 
                    y = dfe[mode],
                    name="{}".format(estado),
                    marker = {"color":"#{}".format(color)},
                    opacity=0.6))
        i += colorstepint
        
    layout = go.Layout(title='{} de COVID-19 - {}'.format(mode,regiao),
                    yaxis={'title':mode},
                    xaxis={'title': 'Data do registro'},
                    barmode="stack")

    fig = go.Figure(data=trace, layout=layout)
    return(fig)


@st.cache()
def plot_brasil(df, mode, colorint, colorstepint):

    regioes = list(df["Região"].unique())
    trace = []
    i = 0
    for regiao in regioes:
        color = colorint+i
        dfr = data_regiao(regiao, df)
        trace.append(go.Bar(x = dfr["Data"], 
                    y = dfr[mode],
                    name="{}".format(regiao),
                    marker = {"color":"#{}".format(color)},
                    opacity=0.6))
        i += colorstepint
        
    layout = go.Layout(title='{} de COVID-19 no Brasil'.format(mode),
                    yaxis={'title':mode},
                    xaxis={'title': 'Data do registro'},
                    barmode="stack")

    fig = go.Figure(data=trace, layout=layout)
    return(fig)


def TimeStempToStr(ts):
    try:
        aux1 = datetime.strptime(str(ts), '%Y-%m-%d %H:%M:%S') 
        aux2 = aux1.strftime('%m/%d/%Y').split("/")
        aux3 =  aux2[2]+"-"+aux2[0]+"-"+aux2[1]
        return aux3
    except:
        return ts


@st.cache()
def forecast(df, length_generator, fc_period):
    full_scaler = MinMaxScaler()
    scaled_full_data = full_scaler.fit_transform(df)

    length = length_generator
    n_features = 1
    generator = TimeseriesGenerator(scaled_full_data, scaled_full_data, length=length, batch_size=1)

    model = Sequential()
    model.add(LSTM(100,activation="relu",input_shape=(length,n_features))) # can add dropout too
    model.add(Dense(1))
    model.compile(optimizer="adam", loss="mse")
    model.fit(generator,epochs=75)


    forecast = []
    forecast_period = fc_period
    first_eval_batch  = scaled_full_data[-length:]
    current_batch = first_eval_batch.reshape((1,length,n_features))

    for i in range(forecast_period):
        
        # get prediction 1 time atamp ahead ([0] is for grabbing just the number insede the brackets)
        current_pred = model.predict(current_batch)[0]
        
        # store prediction
        forecast.append(current_pred)
        
        # update batch to now include prediction and drop first value
        current_batch = np.append(current_batch[:,1:,:],[[current_pred]],axis=1)
        

    forecast = full_scaler.inverse_transform(forecast)
    forecast_index = pd.date_range(start="2020-05-05", periods=forecast_period, freq="D")
    forecast_df = pd.DataFrame(data=forecast,index=forecast_index,columns=["Forecast"])
    forecast_df["Forecast"] = forecast_df["Forecast"].apply(lambda x: int(x))
  
    return forecast_df


@st.cache()
def plot_previsao(df, local, color1, color2):
    ncasos = df.groupby("Data").sum()["Casos Acumulados"].values
    date = df.groupby("Data").sum()["Casos Acumulados"].index

    dfcasos = pd.DataFrame(data=ncasos,index=date,columns=["Número de Casos"])
    dfcasos.loc[dfcasos["Número de Casos"] == 0, "Número de Casos"] = None
    dfcasos.dropna(inplace=True)

    forecast_df = forecast(dfcasos, 20, 10)

    dfresult = pd.concat([dfcasos, forecast_df])
    dfresult.reset_index(inplace=True)
    dfresult["Data"] = dfresult["index"].apply(TimeStempToStr)

    trace = [go.Bar(x = dfresult["Data"], 
                y = dfresult["Número de Casos"],
                name = 'Casos confirmados',
                marker = {"color":color1},
                opacity=0.8), 
                
            go.Bar(x = dfresult["Data"], 
                y = dfresult["Forecast"],
                name = 'Previsão',
                marker = {"color":color2},
                opacity=0.8)]

    layout = go.Layout(title='Previsão de COVID-19 no {}'.format(local),
                    yaxis={'title':"Número de casos"},
                    xaxis={'title': 'Data do registro'})

    fig2 = go.Figure(data=trace, layout=layout)

    return fig2


@st.cache()
def plot_previsao_estado(df, estado, color1, color2):
    dfe = data_estado(estado, df)

    return plot_previsao(dfe, estado, color1, color2)


@st.cache()
def plot_previsao_regiao(df, regiao, color1, color2):
    dfr = data_regiao(regiao, df)

    return plot_previsao(dfr, regiao, color1, color2)


@st.cache()
def plot_obt_previsao(df, local, color1, color2):
    nobitos = df.groupby("Data").sum()["Óbitos Acumulados"].values
    date = df.groupby("Data").sum()["Óbitos Acumulados"].index

    dfobitos = pd.DataFrame(data=nobitos,index=date,columns=["Número de Óbitos"])
    dfobitos.loc[dfobitos["Número de Óbitos"] == 0, "Número de Óbitos"] = None
    dfobitos.dropna(inplace=True)

    forecast_df = forecast(dfobitos, 14, 10)

    dfresult = pd.concat([dfobitos, forecast_df])
    dfresult.reset_index(inplace=True)
    dfresult["Data"] = dfresult["index"].apply(TimeStempToStr)
    dfresult.to_csv("result.csv")

    trace = [go.Bar(x = dfresult["Data"], 
                y = dfresult["Número de Óbitos"],
                name = 'Óbitos confirmados',
                marker = {"color":color1},
                opacity=0.8), 
                
            go.Bar(x = dfresult["Data"], 
                y = dfresult["Forecast"],
                name = 'Previsão',
                marker = {"color":color2},
                opacity=0.8)]

    layout = go.Layout(title='Previsão do número de óbitos de COVID-19 no {}'.format(local),
                    yaxis={'title':"Número de óbitos"},
                    xaxis={'title': 'Data do registro'})

    fig2 = go.Figure(data=trace, layout=layout)

    return fig2


@st.cache()
def plot_previsao_obt_estado(df, estado, color1, color2):
    dfe = data_estado(estado, df)

    return plot_obt_previsao(dfe, estado, color1, color2)


@st.cache()
def plot_previsao_obt_regiao(df, regiao, color1, color2):
    dfr = data_regiao(regiao, df)

    return plot_obt_previsao(dfr, regiao, color1, color2)





####################################################################
st.title("COVID-19 Brasil - Análise e Previsão")

st.info(''' Esta aplicação tem como objetivo apresentar uma análise regional de COVID-19 no Brasil, 
                exibindo de forma gráfica os casos confirmados e número de óbitos. Os dados foram retirados do 
                [painel oficial do Ministério da Saúde](https://covid.saude.gov.br/), atualizado em: 17:30 03/05/2020. O diferencial desta aplição,
                é capacidade de realizar uma previsão dos novos casos de COVID-19 para as próximas duas semanas. 
                Todas as **previsões foram realizadas utilizando Redes Neurais Recorrentes** e TensowFlow. O link 
                com o **código fonte** deste *dashboard* se encontra no final da página. ''')

df = pd.read_csv("arquivo_geral.csv", sep=";")
df.rename(columns={"regiao":"Região", "estado":"Estado", "data":"Data", 
            "casosNovos": "Casos Novos", "casosAcumulados":"Casos Acumulados", 
            "obitosNovos":"Óbitos Novos", "obitosAcumulados":"Óbitos Acumulados"}, inplace=True)

siglas_estados = list(df["Estado"].unique())

siglas_regiao = list(df["Região"].unique())

caso = "Casos Acumulados"
obito = "Óbitos Acumulados"


st.markdown("---")
###############################################################
st.title("Casos confirmados no Brasil")

st.markdown("**Casos**")

figb = plot_brasil(df, caso, 902030, 12345)
st.plotly_chart(figb)

st.markdown("**Óbitos**")

figbo = plot_brasil(df, obito, 100000, 12345)
st.plotly_chart(figbo)



###############################################################
st.title("Casos confirmados por região")

regiao = st.selectbox("Selecione uma regiao: ", siglas_regiao)
dfr = data_regiao(regiao, df)

st.markdown("**Casos**")

figr = plot_regiao(dfr, regiao, caso, 123456, 98765)
st.plotly_chart(figr)

st.markdown("**Óbitos**")

figro = plot_regiao(dfr, regiao, obito, 678901, 8765)
st.plotly_chart(figro)



###############################################################
st.title("Casos confirmados por estados")

estado = st.selectbox("Selecione um estado: ", siglas_estados)
dfe = data_estado(estado, df)

st.markdown("**Casos**")

fige = plot_estado(dfe, estado, caso, "#ffa07a")
st.plotly_chart(fige)

st.markdown("**Óbitos**")

figeo = plot_estado(dfe, estado, obito, "#4ba07b")
st.plotly_chart(figeo)







####################################################################
####################################################################
st.markdown("---")
st.title("Previsão dos novos casos de COVID-19 no Brasil")
st.warning("A previsão pode demorar alguns segundos.")

st.markdown("**Casos**")
if st.checkbox("Plotar previsão"):
    st.plotly_chart(plot_previsao(df, "Brasil", "#a020f0", "#ff1493"))

st.markdown("**Óbitos**")
if st.checkbox("Plotar previsão de óbitos"):
    st.plotly_chart(plot_obt_previsao(df, "Brasil", "#fb8e8e", "#fbcd8e"))




#####################################################
st.title("Previsão de casos por região")
st.warning("A previsão pode demorar alguns segundos.")
prev_regiao = st.selectbox("Selecione uma regiao", siglas_regiao)

st.markdown("**Casos**")
if st.checkbox("Plotar previsão por regiao"):
    st.plotly_chart(plot_previsao_regiao(df, prev_regiao, "#008b8b", "#cd5c5c"))

st.markdown("**Óbitos**")
if st.checkbox("Plotar previsão de óbitos por região"):
    st.plotly_chart(plot_previsao_obt_regiao(df, prev_regiao, "#2c34ae", "#71b8cb"))




#####################################################
st.title("Previsão de casos por estado")
st.warning("A previsão pode demorar alguns segundos.")
prev_estado = st.selectbox("Selecione um estado", siglas_estados)

st.markdown("**Casos**")
if st.checkbox("Plotar previsão por estado"):
    st.plotly_chart(plot_previsao_estado(df, prev_estado, "#ffd700", "#9acd32"))

st.markdown("**Óbitos**")
if st.checkbox("Plotar previsão de óbitos por estado"):
    st.plotly_chart(plot_previsao_obt_estado(df, prev_estado, "#427350", "#e39d53"))


################################################################################
st.markdown("---")
st.info("**Autor:** [Rafael Loni](https://www.linkedin.com/in/rafael-loni/) ")
st.info("**Código Fonte:** [GitHub](https://github.com/rafaelloni) ")
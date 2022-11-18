#!/usr/bin/env python
# encoding: utf-8
import json
from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse
import os

# librerias requeridas
from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from fake_useragent import UserAgent
from random import randint
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time
import re
import base64
from flask_cors import CORS
import datetime
from datetime import date
from datetime import datetime

app = Flask(__name__)
CORS(app)
api = Api(app)

# obtiene html parseado de las inmobiliarias del sii
def get_soup_sii(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/105.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-CL,es;q=0.8,en-US;q=0.5,en;q=0.3',
        # 'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1',
        'Sec-GPC': '1',
    }

    response = requests.get(url, headers=headers)
    html_text = response.text
    
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup

def fix_data(data):
    return {
            "tasa_fija": float(data['tasa_fija'].strip('%').replace(",","."))/100,
            "total_dividendo_clp": float(data['total_dividendo_clp'].strip('$').replace(".","")),
            "total_dividendo_uf":  float(data['total_dividendo_uf'].strip('UF').strip().replace(",","."))
    }

def get_fake_credentials():
    # fake_person = requests.get('https://api.generadordni.es/v2/profiles/person?results=1')
    # fake_person = json.loads(fake_person.text)[0]

    # fake_rut = get_fake_rut()
    # fake_name = fake_person['name']
    # fake_lastname1 = fake_person['surname']
    # fake_lastname2 = fake_person['surnname2']
    # fake_email = fake_person['email']
    fake_rut = '20.038.354-0'
    fake_number = '257' + ''.join(["{}".format(randint(0, 9)) for num in range(0, 4)])
    fake_name = 'John'
    fake_lastname1 = 'Doe'
    fake_lastname2 = 'Doe'
    fake_email = 'jon_doe@gmail.com'
    
    return fake_rut, fake_name, fake_lastname1, fake_lastname2, fake_email, fake_number

#
@app.route('/v1/getInmobiliarias', methods=['GET'])
def get_inmobiliarias_sii():
    # arreglo final que tendrá la data
    data = []

    years = list(range(2006, 2016))
    urls_sii = [f'https://www.sii.cl/e_contabilidad/inscritos_{year}.htm' for year in years]
    for url in urls_sii:
        soup = get_soup_sii(url)

        rows = soup.find("table", {"class": "tabla"}).find("tbody").find_all("tr")

        for row in rows:
            cells = row.find_all("td")

            # obtenemos rut y razon social
            rut = cells[1].get_text()
            razon_social = cells[2].get_text()
        
            # hacemos el objeto con la data
            object_ = {'rut': rut,
                        'razon_social': razon_social,
            }

            data.append(object_)
        
    return {'data': data}, 200 

@app.route('/v1/getPropRecommendations', methods=['POST'])
def get_prop_recommendation():
    # hay que pasarle datos de esta manera
    # {
    # "historial": [{"titulo": "casa1", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1000, "tipoVenta": "Arriendo", "superficie": 50},
    #              {"titulo": "casa2", "comuna": "Ñuñoa", "latitude": 40, "longitude": 4, "habitaciones": 2, "banos": 3031, "precio": 6000, "tipoVenta": "Arriendo", "superficie": 5000},
    #              {"titulo": "casa3", "comuna": "Ñuñoa", "latitude": 40, "longitude": 4, "habitaciones": 2, "banos": 3031, "precio": 6000, "tipoVenta": "Arriendo", "superficie": 5000}],
    # "propiedades": [{"titulo": "casa1", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1000, "tipoVenta": "Arriendo", "superficie": 50},
    #          {"titulo": "casa2", "comuna": "Ñuñoa", "latitude": 40, "longitude": 4, "habitaciones": 2, "banos": 3031, "precio": 6000, "tipoVenta": "Arriendo", "superficie": 5000},
    #          {"titulo": "casa3", "comuna": "Ñuñoa", "latitude": 40, "longitude": 4, "habitaciones": 2, "banos": 3031, "precio": 6000, "tipoVenta": "Arriendo", "superficie": 5000},
    #          {"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 4, "habitaciones": 2, "banos": 3061, "precio": 60600, "tipoVenta": "Arriendo", "superficie": 300},
    #          {"titulo": "casa5", "comuna": "Ñuñoa", "latitude": 20, "longitude": 4, "habitaciones": 2, "banos": 3011, "precio": 6600, "tipoVenta": "Arriendo", "superficie": 5300},
    #          {"titulo": "casa6", "comuna": "Ñuñoa", "latitude": 70, "longitude": 46, "habitaciones": 2, "banos": 231, "precio": 4000, "tipoVenta": "Arriendo", "superficie": 5800}]
    # }
    
    json_data = json.loads(request.data)

    # guardamos los datos de la request
    historial_propiedades = json_data['historial']
    total_propiedades = json_data['propiedades']

    # print("historial propiedades tipo", type(historial_propiedades))
    # print("historial propiedades", historial_propiedades)

    # print("total propiedades tipo", type(total_propiedades))
    # print("total propiedades", total_propiedades)
    # # print(total_propiedades)

    # removemos del total de propiedades las que están en el historial
    for propiedad in historial_propiedades:
        if propiedad in total_propiedades:
            total_propiedades.remove(propiedad)

    print(total_propiedades)

    historial_propiedades = pd.DataFrame(historial_propiedades)
    total_propiedades = pd.DataFrame(total_propiedades)
    

    m = historial_propiedades.shape[0]

    df = pd.concat([historial_propiedades, total_propiedades])
    df = df[['latitude', 'longitude', 'tipoVenta', 'habitaciones', 'banos', 'superficie', 'precio']].replace("Arriendo", 0).replace("Venta", 1)

    scaler = MinMaxScaler()
    scaler.fit(df)
    scaled = scaler.fit_transform(df)
    scaled_df = pd.DataFrame(scaled, columns=df.columns)

    meta = scaled_df.iloc[:m,:]
    meta2 = scaled_df.iloc[m:,:]

    meanX = meta['latitude'].mean()
    meanY = meta['longitude'].mean()
    meanT = meta['tipoVenta'].mean()
    meanH = meta['habitaciones'].mean()
    meanB = meta['banos'].mean()
    meanS = meta['superficie'].mean()
    meanP = meta['precio'].mean()

    meta2['score'] = abs(meanX-meta2['latitude'])*10 + abs(meanY-meta2['longitude'])*10 + abs(meanT-meta2['tipoVenta'])*30 + abs(meanH-meta2['habitaciones'])*10 + abs(meanB-meta2['banos'])*10 + abs(meanS-meta2['superficie'])*10 + abs(meanP-meta2['precio'])*20

    total_propiedades['score'] = meta2['score'].to_numpy()

    total_propiedades = total_propiedades.fillna(0)
    total_propiedades = total_propiedades.head(5)
    # print(total_propiedades)
    #
    # revisar cuantos datos faltan por columna
    # print("Número de datos NaN por feature Test: \n")
    # print(total_propiedades.isnull().sum(axis = 0))

    # print(jsonify(total_propiedades.sort_values(by='score').to_dict(orient='records')))
    # print(jsonify(total_propiedades.sort_values(by='score').to_dict(orient='records')))

    return jsonify(total_propiedades.sort_values(by='score').to_dict(orient='records'))

@app.route('/v1/getUserRecommendations', methods=['POST'])
def get_user_recommendation():
    json_data = json.loads(request.data)
    
    # guardamos los datos de la request
    usuario = json_data['usuario']
    propiedades = json_data['propiedades']
    usuarios = json_data['usuarios']

    # df_usuarios = pd.DataFrame(usuarios)
    # print(df_usuarios)
    # usuario = {"nombre": "Lucio", "tipo": 'Particular', 
    #         "historial": [{"titulo": "casa1", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1000, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa2", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 2000, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa3", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1200, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50}]
    # }

    # propiedades = [{"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50},
    # {"titulo": "casa5", "comuna": "Santiago", "latitude": -100, "longitude": 200, "habitaciones": 5, "banos": 20100, "precio": 100000, "tipoVenta": "Arriendo", "superficie": 500}, 
    # {"titulo": "casa6", "comuna": "Macul", "latitude": 15, "longitude": 25, "habitaciones": 6, "banos": 201000, "precio": 1000000, "tipoVenta": "Arriendo", "superficie": 5000}, 
    # {"titulo": "casa7", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1300, "tipoVenta": "Arriendo", "superficie": 50}, 
    # {"titulo": "casa8", "comuna": "San Joaquin", "latitude": 100, "longitude": 200, "habitaciones": 9, "banos": 2010000, "precio": 10000, "tipoVenta": "Venta", "superficie": 500000}]

    # usuarios = [{"nombre": "Lucio",
    #         "historial": [{"titulo": "casa1", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1000, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa2", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 2000, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa3", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1200, "tipoVenta": "Arriendo", "superficie": 50}, 
    #                         {"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50}]
    # },
    # {"nombre": "Lucio2", "tipo": "Particular",
    # "historial":
    # [{"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50},
    # {"titulo": "casa5", "comuna": "Santiago", "latitude": -100, "longitude": 200, "habitaciones": 5, "banos": 20100, "precio": 100000, "tipoVenta": "Arriendo", "superficie": 500}, 
    # {"titulo": "casa6", "comuna": "Macul", "latitude": 15, "longitude": 25, "habitaciones": 6, "banos": 201000, "precio": 1000000, "tipoVenta": "Arriendo", "superficie": 5000}, 
    # {"titulo": "casa7", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1300, "tipoVenta": "Arriendo", "superficie": 50}, 
    # {"titulo": "casa8", "comuna": "San Joaquin", "latitude": 100, "longitude": 200, "habitaciones": 9, "banos": 2010000, "precio": 10000, "tipoVenta": "Venta", "superficie": 500000}],
    # },
    # {"nombre": "Lucio3", "tipo": "Particular",
    #         "historial":
    # [{"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50},
    # {"titulo": "casa5", "comuna": "Santiago", "latitude": -100, "longitude": 200, "habitaciones": 5, "banos": 20100, "precio": 100000, "tipoVenta": "Arriendo", "superficie": 500}, 
    # {"titulo": "casa6", "comuna": "Macul", "latitude": 15, "longitude": 25, "habitaciones": 6, "banos": 201000, "precio": 1000000, "tipoVenta": "Arriendo", "superficie": 5000}, 
    # {"titulo": "casa7", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1300, "tipoVenta": "Arriendo", "superficie": 50}, 
    # {"titulo": "casa8", "comuna": "San Joaquin", "latitude": 100, "longitude": 200, "habitaciones": 9, "banos": 2010000, "precio": 10000, "tipoVenta": "Venta", "superficie": 500000}],
    # },
    # {"nombre": "Lucio4", "tipo": "Inmobiliaria",
    #         "historial":
    # [{"titulo": "casa4", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1500, "tipoVenta": "Arriendo", "superficie": 50},
    # {"titulo": "casa5", "comuna": "Santiago", "latitude": -100, "longitude": 200, "habitaciones": 5, "banos": 20100, "precio": 100000, "tipoVenta": "Arriendo", "superficie": 500}, 
    # {"titulo": "casa6", "comuna": "Macul", "latitude": 15, "longitude": 25, "habitaciones": 6, "banos": 201000, "precio": 1000000, "tipoVenta": "Arriendo", "superficie": 5000}, 
    # {"titulo": "casa7", "comuna": "Ñuñoa", "latitude": 10, "longitude": 20, "habitaciones": 1, "banos": 2010, "precio": 1300, "tipoVenta": "Arriendo", "superficie": 50}, 
    # {"titulo": "casa8", "comuna": "San Joaquin", "latitude": 100, "longitude": 200, "habitaciones": 9, "banos": 2010000, "precio": 10000, "tipoVenta": "Venta", "superficie": 500000}]
    # }
    # ]

    df = pd.DataFrame(propiedades)
    df = df[['latitude', 'longitude', 'tipoVenta', 'habitaciones', 'banos', 'superficie', 'precio']].replace("Arriendo", 0).replace("Venta", 1)

    scaler = MinMaxScaler()
    scaler.fit(df)

    def getScore(user, user2):
        user2Aux = user2

        try:
            metadata = pd.DataFrame(user['historial'])
            metadata2 = pd.DataFrame(user2['historial'])
        except:
           user2Aux['score'] = 99999999999
           return user2Aux

        m = metadata.shape[0]
        dfAux = pd.concat([metadata, metadata2])
        dfAux = dfAux[['latitude', 'longitude', 'tipoVenta', 'habitaciones', 'banos', 'superficie', 'precio']].replace("Arriendo", 0).replace("Venta", 1)

        scaled = scaler.fit_transform(dfAux)
        scaled_df = pd.DataFrame(scaled, columns=dfAux.columns)

        meta = scaled_df.iloc[:m,:]
        meta2 = scaled_df.iloc[m:,:]

        meanX = meta['latitude'].mean()
        meanY = meta['longitude'].mean()
        meanT = meta['tipoVenta'].mean()
        meanH = meta['habitaciones'].mean()
        meanB = meta['banos'].mean()
        meanS = meta['superficie'].mean()
        meanP = meta['precio'].mean()

        meanX2 = meta2['latitude'].mean()
        meanY2 = meta2['longitude'].mean()
        meanT2 = meta2['tipoVenta'].mean()
        meanH2 = meta2['habitaciones'].mean()
        meanB2 = meta2['banos'].mean()
        meanS2 = meta2['superficie'].mean()
        meanP2 = meta2['precio'].mean()

        user2Aux['score'] = abs(meanX-meanX2)*10 + abs(meanY-meanY2)*10 + abs(meanT-meanT2)*30 + abs(meanH-meanH2)*10 + abs(meanB-meanB2)*10 + abs(meanS-meanS2)*10 + abs(meanP-meanP2)*20

        return user2Aux

    usersWithScore = list()

    for usuario2 in usuarios:
        usersWithScore.append(getScore(usuario, usuario2))

    # print(usersWithScore[0])
    # df_final = pd.DataFrame(usersWithScore)
    df_final = pd.DataFrame(usersWithScore).sort_values(by='score')

    df_final = df_final.fillna(0)
    df_final = df_final.iloc[1:,:]
    df_final = df_final[df_final['tipo'] == 'Particular']
    # print(total_propiedades)
    #
    # revisar cuantos datos faltan por columna
    # print("Número de datos NaN por feature Test: \n")
    # print(total_propiedades.isnull().sum(axis = 0))

    # print(jsonify(total_propiedades.sort_values(by='score').to_dict(orient='records')))
    # print(jsonify(total_propiedades.sort_values(by='score').to_dict(orient='records')))

    return jsonify(df_final.sort_values(by='score').to_dict(orient='records'))

@app.route('/v1/getBancoSantander', methods=['POST'])
def banco_santander():
    # datos desde el usuario al realizar simulación
    json_data = json.loads(request.data)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    
    driver.get("https://www.santander.cl/simuladores/simulador_hipotecario/simulador.asp")

    # obtenemos persona falsa
    fake_rut, fake_name, fake_lastname1, fake_lastname2, fake_email, fake_number = get_fake_credentials()

    input_rut = driver.find_element_by_id('d_rut')
    input_rut.send_keys('11.111.111-1')

    # time.sleep(2)

    input_nombre = driver.find_element_by_id('nombre')
    input_nombre.send_keys(fake_name)

    # time.sleep(2)

    input_apaterno = driver.find_element_by_name('apaterno')
    input_apaterno.send_keys(fake_lastname1)

    # time.sleep(2)

    input_amaterno = driver.find_element_by_name('amaterno')
    input_amaterno.send_keys(fake_lastname2)

    # time.sleep(2)

    input_email = driver.find_element_by_name('email')
    input_email.send_keys(fake_email)

    # time.sleep(2)

    input_telefono = driver.find_element_by_name('telefono')
    input_telefono.send_keys(fake_number)

    # time.sleep(2)

    input_codigoarea = driver.find_element_by_id('codigoarea')
    for option in input_codigoarea.find_elements_by_tag_name('option'):
        if option.text == '72':
            option.click() # select() in earlier versions of webdriver
            break

    # time.sleep(2)

    input_region = driver.find_element_by_id('region')
    for option in input_region.find_elements_by_tag_name('option'):
        if option.text == 'Region Metropolitana':
            option.click() # select() in earlier versions of webdriver
            break

    # time.sleep(2)

    input_comuna = driver.find_element_by_id('comuna')
    options = [option for option in input_comuna.find_elements_by_tag_name('option')]
    option = random.choice(options).click()

    # time.sleep(2)

    input_valor_propiedad = driver.find_element_by_id('valor_propiedad')
    input_valor_propiedad.send_keys(json_data['valor_propiedad_uf']) # fijo 3000

    # time.sleep(2)

    input_valor_pie = driver.find_element_by_id('valor_pie')
    input_valor_pie.send_keys(json_data['valor_pie_uf']) # fijo 1000 valor_pie

    # time.sleep(2)

    # plazo de crédito (años) random
    input_años = driver.find_element_by_id('plazo')
    for option in input_años.find_elements_by_tag_name('option'):
        if option.text == json_data['plazo_credito']:
            option.click()
            break    

    # time.sleep(2)

    # enviar y simular
    btn_preguntas_enviar = driver.find_element_by_id('btn_preguntas_enviar')
    btn_preguntas_enviar.click()

    time.sleep(2)

    # esperamos un poco y elegimos el tramo de renta
    input_tramos = driver.find_element_by_id('tramos')
    for option in input_tramos.find_elements_by_tag_name('option'):
        if option.text == '$ 2.500.001 - $ 5.000.000':
            option.click() # select() in earlier versions of webdriver
            break

    # time.sleep(2)

    # hacemos click en continuar        
    btn_continuar = driver.find_element(By.XPATH, '//*[@id="renta"]/form/fieldset/a').click()

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    table_dividendo_soup = soup.find_all("table", {"class": "d-dividendo"})[0]
    rows = table_dividendo_soup.find("tbody").find_all('tr')

    # ahora obtenemos los datos de la página
    lista_row = []

    for row in rows[2]:
        if row.text != "Simulación" and row != "\n":
            lista_row.append(row.text)

    # por mientras solo obtendremos estas variables para Banco Santander
    años_credito, tasa_fija, desgravamen, incendio_sismo, total_dividendo_clp, total_dividendo_uf = lista_row
    
    data = {'tasa_fija': tasa_fija,
            'total_dividendo_clp': total_dividendo_clp,
            'total_dividendo_uf': total_dividendo_uf  }

    driver.close()

    return fix_data(data), 200

@app.route('/v1/getBancoEstado', methods=['POST'])
def banco_estado():
    # datos desde el usuario al realizar simulación
    json_data = json.loads(request.data)

    # seteamos user-agent falso
    ua = UserAgent()
    user_agent = ua.random

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f'user-agent={user_agent}')

    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    driver.get('https://www.bancoestado.cl/imagenes/nuevo_form/asesor/hipotecario/index.html')

    
    # fijamos en comprar una propiedad siempre
    
    input_que_necesitas = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "opcion_01")))
    # input_que_necesitas = driver.find_element_by_id('opcion_01')
    for option in input_que_necesitas.find_elements_by_tag_name('option'):
        if option.text == 'Comprar una Propiedad':
            option.click() # select() in earlier versions of webdriver
            break

    # elegimos tipo de vivienda (lo haremos al azar por el momento)
    input_vivienda = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "tipo_01")))
    #  input_vivienda = driver.find_element_by_id('tipo_01')
    options = [option for option in input_vivienda.find_elements_by_tag_name('option') if option.text != "Seleccione tipo de vivienda"]
    option = random.choice(options).click()

    input_region = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "region_01")))
    # region (metropolitana)
    # input_region = driver.find_element_by_id('region_01')
    for option in input_region.find_elements_by_tag_name('option'):
        if option.text == 'Metropolitana de Santiago':
            option.click() # select() in earlier versions of webdriver
            break

    # elegimos condicion de la vivienda (lo haremos al azar por el momento)
    input_condicion = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "condicion_01")))
    # input_condicion = driver.find_element_by_id('condicion_01')
    options = [option for option in input_condicion.find_elements_by_tag_name('option') if option.text != "Selecciona Condición Vivienda"]
    option = random.choice(options).click()

    # obtenemos persona falsa
    fake_rut, fake_name, fake_lastname1, fake_lastname2, fake_email, fake_number = get_fake_credentials()

    input_nombre = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "nombre_01")))
    # input_nombre = driver.find_element_by_id('nombre_01')
    input_nombre.send_keys(fake_name + " " + fake_lastname1 + " " + fake_lastname2)

    input_rut = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "rut_01")))
    # input_rut = driver.find_element_by_id('rut_01')
    input_rut.send_keys('11.111.111-1')

    input_email = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "email_01")))
    # input_email = driver.find_element_by_name('email_01')
    input_email.send_keys(fake_email)

    # valor en UF propiedad
    input_valor_propiedad = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "uf_01")))
    input_valor_propiedad = driver.find_element_by_id('uf_01')
    input_valor_propiedad.send_keys(json_data['valor_propiedad_uf']) # fijo 3000


    # plazo de entrega, siempre inmediata
    input_plazo_entrega = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "plazo_entrega")))
    # input_plazo_entrega = driver.find_element_by_id('plazo_entrega')
    for option in input_plazo_entrega.find_elements_by_tag_name('option'):
        if option.text == 'Inmediata':
            option.click() # select() in earlier versions of webdriver
            break


    # valor del pie en UF
    input_valor_pie = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "uf_03")))
    # input_valor_pie = driver.find_element_by_id('uf_03')
    input_valor_pie.send_keys(json_data['valor_pie_uf']) # fijo 1000 valor_pie

    # plazo de crédito (años)
    input_años = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "plazo_credito")))
    input_años = driver.find_element_by_id('plazo_credito')
    for option in input_años.find_elements_by_tag_name('option'):
        if option.text == json_data['plazo_credito'] + " años":
            option.click()
            break    

    # click en continuar
    btn_enviar = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "procesaPaso1")))
    # btn_enviar = driver.find_element_by_id('procesaPaso1')
    btn_enviar.click()
    
    
    column_index = 0
    encontrar_plazo_elegido = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[7]/table[1]/thead/tr[2]')))
    # encontrar_plazo_elegido = driver.find_element(By.XPATH,'/html/body/div[1]/div/div[7]/table[1]/thead/tr[2]')
    for row in encontrar_plazo_elegido.find_elements_by_css_selector('th'):
        if row.get_attribute("class") == "elegida":
            print(row.get_attribute("class"))
            break
        column_index+=1

    values = []
    tabla = driver.find_element(By.XPATH, '/html/body/div[1]/div/div[7]/table[1]/tbody')
    for row in tabla.find_elements_by_css_selector('tr'):
        values.append(row.find_elements_by_tag_name('td')[column_index].text)
        
    tasa_fija, _, _, total_dividendo_uf, total_dividendo_clp, _ = values

    data_return = {'tasa_fija': tasa_fija,
            'total_dividendo_clp': total_dividendo_clp,
            'total_dividendo_uf': total_dividendo_uf  }
    
    driver.close()

    return fix_data(data_return), 200

@app.route('/v1/getBancoItau', methods=['POST'])
def banco_itau():
    # seteamos user-agent falso
    ua = UserAgent()
    user_agent = ua.random

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f'user-agent={user_agent}')

    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)
    
    driver.get("https://ww2.itau.cl/personas/creditos/simulador-hipotecario")

    # obtenemos persona falsa
    fake_rut, fake_name, fake_lastname1, fake_lastname2, fake_email, fake_number = get_fake_credentials()

    input_rut = driver.find_element_by_id('rut')
    input_rut.send_keys(fake_rut)

    time.sleep(3)

    driver.find_element_by_id('btn-form-paso-1').click()

    time.sleep(5)

    input_name = driver.find_element_by_id('nombre')
    input_name.send_keys(fake_name)

    input_apellido1 = driver.find_element_by_id('apellidoPaterno')
    input_apellido1.send_keys(fake_lastname1)

    input_apellido2 = driver.find_element_by_id('apellidoMaterno')
    input_apellido2.send_keys(fake_lastname2)

    input_email = driver.find_element_by_id('email')
    input_email.send_keys(fake_email)

    input_telefono = driver.find_element_by_id('telefono')
    input_telefono.send_keys('998277441')

    time.sleep(1)

    driver.find_element_by_id('btn-form-paso-2').click()

    time.sleep(3)

    # click en casa
    driver.find_element(By.XPATH, '//*[@id="id-form-paso-2"]/div/div/div[2]/div/div/div[1]/label').click()

    # valorPropiedad
    input_valor_propiedad = driver.find_element_by_id('valorPropiedad')
    input_valor_propiedad.send_keys(3000) # fijo 3000

    # montoDelPie
    input_valor_pie = driver.find_element_by_id('montoDelPie')
    input_valor_pie.clear()
    input_valor_pie.send_keys(1000) # fijo 3000

    time.sleep(1)

    driver.find_element_by_id('btn-form-paso-3').click()

    time.sleep(3)

    # click tasa fija
    driver.find_element(By.XPATH, '//*[@id="id-form-paso-4"]/div/div/div[2]/div/div/div[1]/div/label').click()

    input_años = driver.find_element_by_id('plazoTotal')
    input_años.send_keys(10) # entre 5 - 25

    # simular
    driver.find_element_by_id('btn-form-paso-4').click()

    wait = WebDriverWait(driver, 10)
    wait.until(lambda driver: driver.current_url != "https://ww2.itau.cl/personas/creditos/simulador-hipotecario")

    tasa_fija = driver.find_element_by_id('tasaAnual').text
    total_dividendo_uf, total_dividendo_clp = driver.find_element_by_id('dividendo').text.split(" / ")

    data = {'tasa_fija': tasa_fija,
                'total_dividendo_clp': total_dividendo_clp,
                'total_dividendo_uf': total_dividendo_uf  }

    driver.close()

    return fix_data(data), 200 

# Retorna una lista de la forma [dias, horas, minutos] de un datetime
def days_hours_minutes(td):
    return [td.days, td.seconds//3600, (td.seconds//60)%60]

@app.route('/v1/getNews', methods=['GET'])
def get_news():
    # arreglo final que tendrá la data
    data = []

    # palabras importantes que deben estar en el encabezado de la noticia, sino, la descarta y pasa a la siguiente
    significant_words = {'inmobiliaria', 'inmobiliarias', 'Inmobiliaria', 'Inmobiliarias',
                        'fraude', 'fraudes', 'Fraude', 'Fraudes',
                            'bienes raíces', 'bienes raices', 'Bienes raíces', 'Bienes raices',
                            'vivienda', 'viviendas', 'Vivienda', 'Viviendas',
                            'residencial', 'residenciales', 'Residencial', 'Residenciales',
                            'estafa', 'estafas', 'Estafa', 'Estafas'}
    # lista con urls de donde sacar las noticias
    urls_list = ['https://news.google.com/search?q=arriendos%20chile when%3A14d&hl=es-419&gl=CL&ceid=CL%3Aes-419', 
                    'https://news.google.com/search?q=inmobiliaria%20chile when%3A14d&hl=es-419&gl=CL&ceid=CL%3Aes-419']
    
    for url in urls_list:
        html_text = requests.get(url).text
        soup = BeautifulSoup(html_text, 'html.parser')

        news_title_html = soup.find_all("article")


        for news in news_title_html:
            # chequeamos si el atributo de h3 es nulo (a veces ocurre) entonces saltamos esa noticia simplemente
            if news.h3 == None:
                continue

            # chequeamos si en el titulo están presentes al menos 1 de las palabras importantes
            if not(any(x in news.h3.text for x in significant_words)):
                continue

            # se extrae la encriptacion y se almacena con expresion regular
            image_encripted = re.search("([A-Z])\w+", news.get('jslog'))[0] +  '=='
            url_encripted = re.search("([A-Z])\w+", news.a.get('jslog'))[0] +  '=='
            
            # la desencriptamos
            try:
                decripted_url = base64.b64decode(url_encripted)
                decripted_image = base64.b64decode(image_encripted)
            except:
                continue
            # la obtenemos con otra regex
            url_image_regex = '(https?:\/\/.*\.(?:png|jpg|jpeg))'
            url_regex = '(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])'
            
            # tratamos cuando no tiene ni url ni imagen
            try:
                if re.search(url_regex, decripted_url.decode('utf-8')) == None:
                    continue
                
                if re.search(url_image_regex, decripted_image.decode('utf-8')) == None:
                    continue
            except:
                continue    
            # obtenemos hace cuanto fue la noticia desde que se realiza el scraping
            # today = datetime.now()
            # dates_diference = today - news_datetime_release

            
            # datos para retornarlos en el json
            news_title = news.h3.text
            url = re.search(url_regex, decripted_url.decode('utf-8'))[0]
            url_image = re.search(url_image_regex, decripted_image.decode('utf-8'))[0]
            news_datetime_release = datetime.strptime(news.find("time")['datetime'].replace("T", " ").replace("Z", ""), "%Y-%m-%d %H:%M:%S")

            # days_hours_minutes_difference =  self.days_hours_minutes(dates_diference)
            
            # hacemos el objeto con la data
            object_ = {'news_title': news_title,
                    'url': url,
                    'url_image': url_image,
                    'news_datetime_release': str(news_datetime_release.date())
            }
            
            data.append(object_)
        
    # ordenamos la data según fecha de la noticia de la más reciente a la más antigua     
    data = sorted(data, key=lambda d: d['news_datetime_release'], reverse=True) 

    # hacemos slice de 10
    data = data[:10]
    # retornamos un json con la lista de noticias scrapeadas
    return {'data': data}, 200 




if __name__ == "__main__":  
    app.run()
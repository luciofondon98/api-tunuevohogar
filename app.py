#!/usr/bin/env python
# encoding: utf-8
import json
from flask import Flask, request, jsonify

# librerias requeridas
from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

app = Flask(__name__)

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

    print(json_data)

    # guardamos los datos de la request
    usuario = json_data['usuario']
    propiedades = json_data['propiedades']
    usuarios = json_data['usuarios']


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

        print("user", user)
        print("user2", user2)

        user2Aux = user2

        try:
            metadata = pd.DataFrame(user['historial'])
            metadata2 = pd.DataFrame(user2['historial'])
        except:
            return 99999999999

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



if __name__ == "__main__":  
    app.run()
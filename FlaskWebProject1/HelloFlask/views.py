
from datetime import datetime
from gc import callbacks
from flask import Flask, render_template
from HelloFlask import app
import mysql.connector
from mysql.connector import errorcode
from gremlin_python.driver import client, serializer, protocol
from gremlin_python.driver.protocol import GremlinServerError
import mysql.connector
from mysql.connector import errorcode
import sys
import traceback
import asyncio
import json
import time
import re
import os
import unidecode


if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

config = {
  'host':'proyecto-terminal.mysql.database.azure.com',
  'user':'director@proyecto-terminal',
  'password':'Terla1313',
  'database':'nombrestendencias',
  'client_flags': [mysql.connector.ClientFlag.SSL],
  'ssl_ca': '<path-to-SSL-cert>/DigiCertGlobalRootG2.crt.pem'
}



@app.route('/')
@app.route('/home')
def home():
    now = datetime.now()
    formatted_now = now.strftime("%A, %d %B, %Y at %X")

    return render_template(
        "index.html",
        content = "Hello, Flask! on " + formatted_now)


@app.route('/api/data')
def get_data():
  return app.send_static_file('data.json')


@app.route('/about/<content>')
def about(content):
    return render_template(
        "about.html",
        title = "About HelloFlask",
        content = content)


@app.route('/tendencias')
def tendencias():
    try:
       conn = mysql.connector.connect(**config)
       print("Connection established")
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with the user name or password")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
      else:
        print(err)
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tendencia order by tuits desc limit 10;")
        rows = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
    return render_template("tendencias.html", title= "Selecionar tema de tendencia", rows = rows)

@app.route('/resultado')
def resultado():   
     return render_template("resultado.html", title="resultados")

@app.route('/datos/<grafo>')
def datos(grafo):
    try:
        conn = mysql.connector.connect(**config)
        print("Connection established")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tendencia where grafo = "+str(grafo)+";")
        rows = cursor.fetchall()
        for row in rows:
            tem = row[1]
            tuits = row[2]
        conn.commit()
        cursor.close()
        conn.close()
        cliente = client.Client('wss://tendencias.gremlin.cosmos.azure.com:443/', 'g',
                           username="/dbs/ProyectoTerminal/colls/tendencia"+ str(grafo) +"",
                           password="sTFKKjM662CHmYlqApb84htpahDb0AEPBurUlPYXF3ac0bdNihJhU2EaECP6NoQJUUCFRaFATgkfsiFgtf8yBA==",
                           message_serializer=serializer.GraphSONSerializersV2d0())
        quer = "g.V().hasLabel('tuit').values('creado').min()"
        centralid = []
        callback = cliente.submitAsync(quer)
        if callback.result() is not None:
            re = int(callback.result().all().result()[0])
        else:
            print("no se pudo consultar: {0}".format(quer))

        quer2 ="g.V().has('tuit','creado',"+str(re)+")"
        callback = cliente.submitAsync(quer2)
        if callback.result() is not None:
            nod = callback.result().all().result()

        validar = len(nod)
        if validar == 0:
            print("no hay tuits ese dia")
        elif validar == 1:
            idTop=str(nod[0]["id"])
            quer3 = "g.V('"+idTop+"').inE().count()"
            print("\n>esto hay {0}".format(quer3))
            callback = cliente.submitAsync(quer3)
            if callback.result() is not None:
                aristas = callback.result().all().result()[0]
            print(aristas)
            print("solo tiene un tuit ese dia y ese nodo tiene: "+str(aristas)+" aristas de retui")
            
        else:
            bandera = 0
            for n in nod:
                if bandera==0:
                    quer3 = "g.V('"+str(n["id"])+"').inE('Retuit_de').count()"
                    print("\n>esto hay {0}".format(quer3))
                    callback = cliente.submitAsync(quer3)
                    if callback.result() is not None:
                        aristas = callback.result().all().result()[0]
                        centralid.append((n["id"],aristas))

                    else:
                        print("no tiene relaciones")
            if len(centralid) >> 0:
                print(centralid)
                pels_sorted = sorted(centralid, reverse=True, key=lambda tupla: tupla[1])
                print(pels_sorted)
                top=pels_sorted[0]
                print(top)
                idTop = str(top[0])
                print("El tuit con id: "+idTop+" es el top al tener: "+str(top[1])+" Aristas")

        quer4 = "g.V('"+idTop+"').values()"
        print("\n>esto hay {0}".format(quer4))
        callback = cliente.submitAsync(quer4)
        if callback.result() is not None:
              data = callback.result().all().result()
              fec = str(data[0])
              tex = data[1]
              iduser = data[2]
              nom_user = data[3]
              foll_user = str(data[4])
              resolved = "Se analizo con exito"
              #print("Datos del nodo "+ idTop +" Fecha :"+ fec + " Texto: "+ tex + " IdUsuario: "+ iduser + " nombre usuario: "+ nom_user + " Cantidad de seguidores: "+ foll_user)
        else:
            print("Error en la consulta de datos (4)")
            fec = ""
            tex = ""
            iduser = ""
            nom_user = ""
            foll_user = ""
            resolved= "No se pudo analizar debido a la falta de datos"
        print("Datos del nodo "+ idTop +" Fecha :"+ fec + " Texto: "+ tex + " IdUsuario: "+ iduser + " nombre usuario: "+ nom_user + " Cantidad de seguidores: "+ foll_user +" resolved: " + resolved)

    except Exception as e:
        print("Error en las consultas de azure ----> "+str(e))

    return render_template("datos.html", tem = tem, tuits = tuits, id = idTop, fec = fec, tex = tex, foll = foll_user, resolved = resolved)

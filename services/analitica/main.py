import pika
import os
import math
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

class Analitica():
    bucket = "rabbit" 
    org = "org"
    token_influx= "token-secreto"
    influx_url= "http://influxdb:8086"
    valor_max= -math.inf
    valor_min= math.inf
    contador_pasos= 0
    suma_pasos= 0
    dias_10k= 0
    dias_5k= 0
    valor_anterior=0 
    dias_mejores_anterior= 0


    def agregar_maximo(self, _medida):
        if _medida > self.valor_max:
            #print("Nuevo valor maximo: {}".format(_medida), flush=True)
            self.valor_max= _medida
            self.escribir_bd("Pasos", "Pasos Maximos", self.valor_max)

    def agregar_minimo(self, _medida):
        if _medida < self.valor_min:
            #print("Nuevo valor minimo: {}".format(_medida), flush=True)
            self.valor_min= _medida
            self.escribir_bd("Pasos", "Pasos Minimos", self.valor_min)


    def tomar_promedio(self, _mensaje):
        self.contador_pasos += 1
        self.suma_pasos += _mensaje   
        promedio= self.suma_pasos / self.contador_pasos  
        #print("Promedio: {}".format(promedio), flush=True) 
        self.escribir_bd("Pasos", "Pasos Promedios", promedio)   

    def dias1_10k(self, _mensaje):
        if _mensaje >= 10000:
            self.dias_10k += 1
            #print("Dias con mas de 10k pasos: {}".format(self.dias_10k), flush=True)
            self.escribir_bd("Pasos", "Dias con mas de 10k pasos", self.dias_10k)    

    def dias1_5k(self, _mensaje):
        if _mensaje <= 5000:
            self.dias_5k += 1
        else:
            self.dias_5k = 0
        #print("Dias con menos de 5k pasos: {}".format(self.dias_5k), flush=True)   
        self.escribir_bd("Pasos", "Dias con menos de 5k pasos", self.dias_5k)




    def dias1_mejores_anterior(self, _mensaje):
        if _mensaje > self.valor_anterior:
            self.dias_mejores_anterior += 1
        else:
            self.dias_mejores_anterior = 0
        #print("Dias con mejores pasos que el anterior: {}".format(self.dias_mejores_anterior), flush=True)
        self.valor_anterior= _mensaje
        self.escribir_bd("Pasos", "Dias con mejores pasos que el anterior", self.dias_mejores_anterior)

    def tomar_medida(self, _mensaje):
        mensaje= _mensaje.split('=')
        medida= float(mensaje[-1])
        #print("Medida: {}".format(medida), flush=True)
        self.agregar_maximo(medida)
        self.agregar_minimo(medida)
        self.tomar_promedio(medida)
        self.dias1_10k(medida)
        self.dias1_5k(medida)
        self.dias1_mejores_anterior(medida)
    
    def escribir_bd(self, tag, variable, valor):
        
        client = InfluxDBClient(url=self.influx_url, token=self.token_influx, org=self.org)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        point = Point("Analitica").tag("Reloj_inteligente", tag).field(variable, valor)
        write_api.write(bucket=self.bucket, record=point)






if __name__== '__main__':
    analitica= Analitica()
    url= os.environ.get('AMQP_URL', 'amqp://guest:guest@rabbit:5672/%2F')
    params= pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    channel.queue_declare(queue='mensajes')
    channel.queue_bind(exchange='amq.topic', queue='mensajes', routing_key='#')

    def callback(ch, method, properties, body):
        global analitica
        mensaje = body.decode('utf-8')
    
        analitica.tomar_medida(mensaje)

    channel.basic_consume( queue='mensajes', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

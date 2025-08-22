#!/usr/bin/env python3
"""
Script simple para probar las colas SQS en LocalStack
"""

import boto3
import json
import sys
from datetime import datetime

# Cliente SQS para LocalStack
sqs = boto3.client(
    'sqs',
    endpoint_url='http://localhost:4566',
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)

def send_test_message(ambiente, tipo_cola, id_mensaje=12345):
    """Enviar mensaje de prueba a una cola específica"""
    queue_name = f"{ambiente}-andina-core-{tipo_cola}"
    
    try:
        # Obtener URL de la cola
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        # Mensaje de prueba
        message = {
            "id": id_mensaje,
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "ambiente": ambiente,
            "tipo": tipo_cola
        }
        
        # Enviar mensaje
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        print(f"✅ Mensaje enviado a {queue_name}")
        print(f"   ID: {response['MessageId']}")
        print(f"   Contenido: {json.dumps(message, indent=2)}")
        
    except Exception as e:
        print(f"❌ Error enviando a {queue_name}: {str(e)}")

def list_all_queues():
    """Listar todas las colas disponibles"""
    print("\n📋 Colas disponibles en LocalStack:")
    print("=" * 50)
    
    response = sqs.list_queues()
    queues = response.get('QueueUrls', [])
    
    for queue_url in queues:
        queue_name = queue_url.split('/')[-1]
        print(f"  • {queue_name}")
    
    print(f"\nTotal: {len(queues)} colas")

def main():
    print("🚀 Test de SQS en LocalStack")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  python test_sqs.py list                    # Listar todas las colas")
        print("  python test_sqs.py dev                     # Enviar a dev-masivo-suscripcion-cotizacion")
        print("  python test_sqs.py qa masivo-kit          # Enviar a qa-masivo-kit")
        print("  python test_sqs.py all                     # Enviar a todas las colas de suscripcion")
        return
    
    comando = sys.argv[1]
    
    if comando == "list":
        list_all_queues()
        
    elif comando == "all":
        # Enviar a todas las colas de suscripcion-cotizacion
        for env in ["dev", "qa", "uat"]:
            send_test_message(env, "masivo-suscripcion-cotizacion", 10000 + ord(env[0]))
            print()
            
    elif comando in ["dev", "qa", "uat"]:
        # Si especifica ambiente, usar masivo-suscripcion-cotizacion por defecto
        tipo = sys.argv[2] if len(sys.argv) > 2 else "masivo-suscripcion-cotizacion"
        send_test_message(comando, tipo)
        
    else:
        print(f"❌ Comando no reconocido: {comando}")

if __name__ == "__main__":
    main()
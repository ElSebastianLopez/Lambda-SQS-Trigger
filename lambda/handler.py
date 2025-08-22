import json
import os
import requests
from datetime import datetime

def handler(event, context):
    """
    Lambda que detecta el ambiente y tipo de cola para llamar al endpoint correcto
    """
    print(f"=== Lambda ejecutada: {datetime.now().isoformat()} ===")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'unknown')}")
    
    # Configuración de endpoints por ambiente y tipo
    # AQUÍ CONFIGURAS TUS ENDPOINTS REALES
    endpoints_config = {
        "dev": {
            "base_url": "http://host.docker.internal:8091/dev",
            "endpoints": {
                "masivo-kit": "",  # Agregar cuando tengas el endpoint
                "masivo-cotizacion": "",  # Agregar cuando tengas el endpoint
                "masivo-emision": "",  # Agregar cuando tengas el endpoint
                "masivo-suscripcion-cotizacion": "/cotizacion/api/v1/lambda/process-sqs-event"
            }
        },
        "qa": {
            "base_url": "http://localhost:8092/qa",  # Cambiar por tu URL real de QA
            "endpoints": {
                "masivo-kit": "",
                "masivo-cotizacion": "",
                "masivo-emision": "",
                "masivo-suscripcion-cotizacion": "/cotizacion/api/v1/lambda/process-sqs-event"
            }
        },
        "uat": {
            "base_url": "http://localhost:8093/uat",  # Cambiar por tu URL real de UAT
            "endpoints": {
                "masivo-kit": "",
                "masivo-cotizacion": "",
                "masivo-emision": "",
                "masivo-suscripcion-cotizacion": "/cotizacion/api/v1/lambda/process-sqs-event"
            }
        }
    }
    
    # Headers comunes
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Procesar cada mensaje
    for record in event.get('Records', []):
        try:
            # Extraer info del ARN
            event_source_arn = record.get('eventSourceARN', '')
            queue_name = event_source_arn.split(':')[-1]
            
            print(f"\n📨 Procesando mensaje de: {queue_name}")
            
            # Detectar ambiente y tipo de cola
            # Formato: dev-andina-core-masivo-suscripcion-cotizacion
            parts = queue_name.split('-')
            ambiente = parts[0] if len(parts) > 0 else None
            
            # Detectar tipo de cola
            queue_type = None
            if 'masivo-kit' in queue_name:
                queue_type = 'masivo-kit'
            elif 'masivo-cotizacion' in queue_name and 'suscripcion' not in queue_name:
                queue_type = 'masivo-cotizacion'
            elif 'masivo-emision' in queue_name:
                queue_type = 'masivo-emision'
            elif 'masivo-suscripcion-cotizacion' in queue_name:
                queue_type = 'masivo-suscripcion-cotizacion'
            
            print(f"🏷️  Ambiente detectado: {ambiente}")
            print(f"📦 Tipo de cola: {queue_type}")
            
            # Verificar si tenemos configuración para este ambiente
            if ambiente not in endpoints_config:
                print(f"❌ No hay configuración para ambiente: {ambiente}")
                continue
                
            # Obtener endpoint
            env_config = endpoints_config[ambiente]
            endpoint_path = env_config['endpoints'].get(queue_type, '')
            
            if not endpoint_path:
                print(f"⏭️  No hay endpoint configurado para {queue_type} en {ambiente}")
                continue
                
            # Construir URL completa
            full_url = env_config['base_url'] + endpoint_path
            print(f"🎯 URL del servicio: {full_url}")
            
            # Preparar el evento para enviar
            message_body = record.get('body', '{}')
            lambda_event = {
                "Records": [{
                    "messageId": record.get('messageId'),
                    "receiptHandle": record.get('receiptHandle'),
                    "body": message_body,
                    "attributes": record.get('attributes', {}),
                    "eventSourceARN": event_source_arn,
                    "_metadata": {
                        "environment": ambiente,
                        "queueType": queue_type,
                        "processedAt": datetime.now().isoformat()
                    }
                }]
            }
            
            # Llamar al endpoint
            try:
                print(f"📤 Llamando endpoint...")
                response = requests.post(
                    full_url,
                    json=lambda_event,
                    headers=headers,
                    timeout=30,
                    verify=False  # Para desarrollo local
                )
                
                print(f"✅ Respuesta: {response.status_code}")
                if response.status_code == 200:
                    print(f"📄 Body: {response.text[:200]}...")  # Primeros 200 chars
                else:
                    print(f"❌ Error: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                print(f"🔌 Error de conexión - Servicio no disponible")
            except requests.exceptions.Timeout:
                print(f"⏱️  Timeout al llamar el servicio")
            except Exception as e:
                print(f"❌ Error inesperado: {str(e)}")
                
        except Exception as e:
            print(f"❌ Error procesando registro: {str(e)}")
            
    return {
        "statusCode": 200,
        "body": json.dumps("Procesamiento completado")
    }
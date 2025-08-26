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
    
    # Obtener URLs base de variables de entorno
    base_url_emision = os.environ.get('BASE_URL_EMISION', 'http://localhost:8080')
    base_url_suscripcion = os.environ.get('BASE_URL_SUSCRIPCION', 'http://localhost:8080')
    
    # Obtener endpoints de variables de entorno
    endpoint_polizas = os.environ.get('ENDPOINT_POLIZAS', '/api/v1/lambda/process-sqs-event/emision')
    endpoint_kit = os.environ.get('ENDPOINT_KIT', '/api/v1/lambda/process-sqs-event/kit')
    endpoint_suscripcion_cotizacion = os.environ.get('ENDPOINT_SUSCRIPCION_COTIZACION', '/api/v1/lambda/process-sqs-event')
    
    # Mapeo de tipos de cola a configuración (URL base + endpoint)
    queue_config = {
        "masivo-polizas": {
            "base_url": base_url_emision,
            "endpoint": endpoint_polizas
        },
        "masivo-kit": {
            "base_url": base_url_emision,
            "endpoint": endpoint_kit
        },
        "masivo-suscripcion-cotizacion": {
            "base_url": base_url_suscripcion,
            "endpoint": endpoint_suscripcion_cotizacion
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
            parts = queue_name.split('-')
            ambiente = parts[0] if len(parts) > 0 else None
            
            # Detectar tipo de cola
            queue_type = None
            if 'masivo-polizas' in queue_name:
                queue_type = 'masivo-polizas'
            elif 'masivo-kit' in queue_name:
                queue_type = 'masivo-kit'
            elif 'masivo-suscripcion-cotizacion' in queue_name:
                queue_type = 'masivo-suscripcion-cotizacion'
            
            print(f"🏷️  Ambiente detectado: {ambiente}")
            print(f"📦 Tipo de cola: {queue_type}")
            
            # Obtener configuración para este tipo de cola
            config = queue_config.get(queue_type)
            
            if not config:
                print(f"⏭️  No hay configuración para tipo de cola: {queue_type}")
                continue
                
            # Obtener URL base y endpoint específicos
            base_url = config['base_url']
            endpoint_path = config['endpoint']
            
            # Construir URL completa
            full_url = base_url.rstrip('/') + endpoint_path
            print(f"🎯 URL del servicio: {full_url}")
            
            # Preparar el evento para enviar
            message_body = record.get('body', '{}')
            print(f"📦 Cuerpo del mensaje: {message_body}")
            
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
                    print(f"📄 Body: {response.text[:200]}...")
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
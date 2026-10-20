# Archivos de referencia del contrato v1.2

Ejemplos de formato de la salida del detector, generados con los componentes simulados de
`tests/simulados.py` mediante `python -m contracts.generar_referencias`.

No son salidas del modelo real: sus probabilidades no tienen significado. Sirven para validar el
esquema en las pruebas automáticas y para construir el mapeo de n8n hacia DFIR-IRIS y Wazuh sin
depender del modelo. Todos los indicadores están defangeados y usan dominios reservados para
documentación (RFC 2606) e IPv4 de documentación (RFC 5737).

| Archivo | Ruta del modelo | Clase |
|---|---|---|
| `phishing.json` | `en_v3` | phishing |
| `spam.json` | `es_v1` | spam |
| `legitimo.json` | `es_v1` | legítimo |

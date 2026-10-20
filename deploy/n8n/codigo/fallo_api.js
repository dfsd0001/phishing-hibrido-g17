// Fallo seguro: si la API no responde, el correo pasa a la cola de revisión manual. Nunca se cierra.
const idEjecucion = $execution.id;
const detalle = ($json.error && ($json.error.message || JSON.stringify($json.error))) || 'sin detalle';

const iris_payload = {
  alert_title: '[G17] Revisión manual: el detector no respondió',
  alert_description: `La API del detector falló (${String(detalle).slice(0, 300)}). Triaje manual obligatorio.`,
  alert_source: 'G17-detector-phishing',
  alert_source_ref: `fallo-api-${idEjecucion}`,
  alert_severity_id: 1, // Medium
  alert_status_id: 2, // New
  alert_customer_id: Number($env.IRIS_CUSTOMER_ID || 1),
  alert_tags: 'g17,revision_manual,fallo_api',
  alert_note: '',
};

const evento_wazuh = {
  g17_evento: 'analisis_correo',
  id_analisis: `fallo-api-${idEjecucion}`,
  clasificacion: { clase: 'desconocida', riesgo: -1, nivel_riesgo: 'desconocido' },
  idioma_detectado: 'desconocido',
  advertencias: 'fallo_api',
  n_urls: 0,
};

return { json: { origen: 'fallo_api', requiere_iris: true, iris_payload, evento_wazuh, analisis: null } };

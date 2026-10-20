// Convierte la respuesta de la API (contrato JSON v1.2) en una alerta de DFIR-IRIS y un evento de Wazuh.
// Política de uso: el modelo sugiere y el analista decide. El flujo nunca cierra un caso por sí mismo.
const r = $json;
const c = r.clasificacion || {};
const advertencias = Array.isArray(r.advertencias) ? r.advertencias : [];

// Con un idioma no soportado la clase del modelo no es fiable (en pruebas, un correo en francés
// recibió riesgo 91). El correo se envía siempre a revisión manual y sin etiqueta de phishing.
const revisionManual = advertencias.includes('idioma_no_soportado');
const esPhishing = c.clase === 'phishing' && !revisionManual;
const requiereIris = esPhishing || revisionManual;

// Identificadores de severidad en DFIR-IRIS v2.4.29. "Medium" tiene el id 1 porque lo crea una
// migración antes que el resto: 1 Medium, 2 Unspecified, 3 Informational, 4 Low, 5 High, 6 Critical.
const SEVERIDAD = { medium: 1, low: 4, high: 5, critical: 6 };
let severidad = SEVERIDAD.low;
if (revisionManual) {
  severidad = SEVERIDAD.medium;
} else if (c.nivel_riesgo === 'critico') {
  severidad = SEVERIDAD.critical;
} else if (esPhishing) {
  severidad = SEVERIDAD.high;
}

const iocs = r.iocs || { urls: [], ips: [] };
const asunto = (r.correo && r.correo.asunto_defang) || '(sin asunto)';
const titulo = esPhishing
  ? `[G17] Phishing (riesgo ${c.riesgo}/100): ${asunto}`
  : `[G17] Revisión manual (idioma ${r.idioma_detectado}): ${asunto}`;
const p = c.probabilidades || {};
const descripcion = [
  `Clase sugerida: ${c.clase} - riesgo ${c.riesgo}/100 - nivel ${c.nivel_riesgo}`,
  `Probabilidades: legítimo ${p.legitimo} - spam ${p.spam} - phishing ${p.phishing}`,
  `Modelo: ${r.modelo && r.modelo.version} (${r.ruta_modelo}) - idioma ${r.idioma_detectado}`,
  `Advertencias: ${advertencias.length ? advertencias.join(', ') : 'ninguna'}`,
  `URL (defangeadas): ${(iocs.urls || []).join(' | ') || 'ninguna'}`,
  `IP (defangeadas): ${(iocs.ips || []).join(' | ') || 'ninguna'}`,
  `MITRE ATT&CK: ${(r.mitre_attack || []).map((m) => m.tecnica).join(', ')}`,
  `SHA-256 del correo: ${r.correo && r.correo.sha256} - id_analisis ${r.id_analisis}`,
  revisionManual
    ? 'Idioma no soportado: el puntaje no es fiable. Triaje manual obligatorio.'
    : 'Puntaje generado por el modelo: orientativo. La decisión de triaje corresponde al analista.',
].join('\n');

const etiquetas = esPhishing
  ? ['g17', 'phishing', 'T1566', r.ruta_modelo]
  : ['g17', 'revision_manual', r.ruta_modelo];

const iris_payload = {
  alert_title: titulo.slice(0, 200),
  alert_description: descripcion,
  alert_source: 'G17-detector-phishing',
  alert_source_ref: r.id_analisis,
  alert_source_event_time: r.timestamp_utc,
  alert_severity_id: severidad,
  alert_status_id: 2, // New
  alert_customer_id: Number($env.IRIS_CUSTOMER_ID || 1),
  alert_tags: etiquetas.join(','),
  alert_note: '',
  // El contrato solo contiene la huella del correo, el asunto y los IOC defangeados.
  alert_source_content: r,
};

// Control de defanging en la capa de integración: ningún IOC vivo sale de n8n.
const serializado = JSON.stringify(iris_payload);
if (/\b(?:https?|ftp):\/\//i.test(serializado) || /\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b/.test(serializado)) {
  throw new Error('IOC vivo detectado en la alerta: se bloquea el envío');
}

// Con idioma no soportado se marca la clase como no fiable para que Wazuh aplique la regla 100503
// y no las reglas de phishing 100501 y 100502.
const clasificacion = revisionManual
  ? { clase: 'no_fiable', riesgo: c.riesgo, nivel_riesgo: 'no_fiable', clase_modelo: c.clase }
  : { clase: c.clase, riesgo: c.riesgo, nivel_riesgo: c.nivel_riesgo };

const evento_wazuh = {
  g17_evento: 'analisis_correo',
  id_analisis: r.id_analisis,
  clasificacion,
  idioma_detectado: r.idioma_detectado,
  ruta_modelo: r.ruta_modelo,
  advertencias: advertencias.join(','),
  n_urls: iocs.n_urls || 0,
  latencia_ms: r.latencia_ms,
};

return { json: { origen: 'api', requiere_iris: requiereIris, iris_payload, evento_wazuh, analisis: r } };

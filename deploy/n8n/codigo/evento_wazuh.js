// Envía el evento a Wazuh (POST /events) y construye la respuesta del flujo.
//
// Límites de la API de Wazuh 4.14.8, verificados en su código fuente: 50 inicios de sesión cada
// 300 s por IP y 30 solicitudes por minuto a /events. El token JWT (válido 900 s) se guarda en los
// datos estáticos del flujo y se reutiliza para no bloquear la IP por exceso de inicios de sesión.
const base = $('¿Requiere alerta IRIS?').item.json;
const vieneDeIris = base.requiere_iris === true;

let irisAlertaId = null;
let irisEstado = 'no_requerida';
if (vieneDeIris) {
  const respuestaIris = $json;
  irisAlertaId = (respuestaIris && respuestaIris.data && respuestaIris.data.alert_id) || null;
  irisEstado = respuestaIris && respuestaIris.status === 'success' && irisAlertaId
    ? 'creada'
    : `error: ${JSON.stringify(respuestaIris).slice(0, 200)}`;
}

const evento = { ...base.evento_wazuh, iris_alerta_id: irisAlertaId === null ? '' : String(irisAlertaId) };
const urlWazuh = $env.WAZUH_URL || 'https://wazuh:55000';
const datos = $getWorkflowStaticData('global');

const codigoHttp = (error) =>
  error.httpCode ||
  (error.response && error.response.status) ||
  error.statusCode ||
  (String(error.message).match(/status code (\d{3})/) || [])[1] ||
  '';

const iniciarSesion = async () => {
  const respuesta = await this.helpers.httpRequest({
    method: 'POST',
    url: `${urlWazuh}/security/user/authenticate`,
    auth: { username: $env.WAZUH_API_USER, password: $env.WAZUH_API_PASSWORD },
    skipSslCertificateValidation: true,
    json: true,
    timeout: 15000,
  });
  datos.wz_token = respuesta.data.token;
  datos.wz_exp = Date.now() + 800 * 1000;
};

const enviarEvento = () =>
  this.helpers.httpRequest({
    method: 'POST',
    url: `${urlWazuh}/events`,
    headers: { Authorization: `Bearer ${datos.wz_token}` },
    body: { events: [JSON.stringify(evento)] },
    skipSslCertificateValidation: true,
    json: true,
    timeout: 15000,
  });

let wazuhEstado;
try {
  if (!datos.wz_token || !datos.wz_exp || Date.now() > datos.wz_exp) {
    await iniciarSesion();
  }
  let respuesta;
  try {
    respuesta = await enviarEvento();
  } catch (error) {
    if (String(codigoHttp(error)) !== '401') {
      throw error;
    }
    await iniciarSesion();
    respuesta = await enviarEvento();
  }
  wazuhEstado = respuesta && respuesta.data && respuesta.data.total_affected_items === 1
    ? 'enviado'
    : `respuesta: ${JSON.stringify(respuesta).slice(0, 200)}`;
} catch (error) {
  const codigo = String(codigoHttp(error));
  wazuhEstado = codigo === '429' ? 'limitado_429' : `error ${codigo}: ${String(error.message).slice(0, 150)}`;
}

const analisis = base.analisis || {};
const c = analisis.clasificacion;
return {
  json: {
    id_analisis: evento.id_analisis,
    origen: base.origen,
    clase: c ? c.clase : null,
    riesgo: c ? c.riesgo : null,
    nivel_riesgo: c ? c.nivel_riesgo : null,
    ruta_modelo: analisis.ruta_modelo || null,
    advertencias: analisis.advertencias || [],
    iris: { requerida: vieneDeIris, estado: irisEstado, alerta_id: irisAlertaId },
    wazuh: { estado: wazuhEstado },
    latencia_api_ms: analisis.latencia_ms || null,
  },
};

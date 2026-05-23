const API = window.location.origin;
const casosLocales = {};

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  event.currentTarget.classList.add('active');
  if (id === 'dashboard') cargarDashboard();
}

function setDemo(cedula, nombre) {
  document.getElementById('cedula').value = cedula;
  document.getElementById('nombre').value = nombre;
}

const loadingMsgs = [
  'Validando cédula ecuatoriana...',
  'Consultando póliza en Notion...',
  'Verificando pre-existencias...',
  'Agente IA analizando cobertura...',
  'Enviando notificaciones...',
];
let loadingIdx = 0;
let loadingInterval;

function startLoading() {
  loadingIdx = 0;
  document.getElementById('loading').style.display = 'flex';
  document.getElementById('loading-msg').textContent = loadingMsgs[0];
  loadingInterval = setInterval(() => {
    loadingIdx = (loadingIdx + 1) % loadingMsgs.length;
    document.getElementById('loading-msg').textContent = loadingMsgs[loadingIdx];
  }, 900);
}

function stopLoading() {
  clearInterval(loadingInterval);
  document.getElementById('loading').style.display = 'none';
}

async function procesarAdmision() {
  const cedula = document.getElementById('cedula').value.trim();
  const nombre = document.getElementById('nombre').value.trim();
  const medico = document.getElementById('medico').value.trim();
  const motivo = document.getElementById('motivo').value.trim();

  if (!cedula || !nombre || !medico || !motivo) {
    alert('Por favor completa todos los campos obligatorios (*)');
    return;
  }

  const btn = document.getElementById('btn-submit');
  btn.disabled = true;
  document.getElementById('resultado').style.display = 'none';
  startLoading();

  const payload = {
    cedula_paciente: cedula,
    nombre_paciente: nombre,
    hospital_id: document.getElementById('hospital').value,
    motivo_emergencia: motivo,
    tipo_emergencia: document.getElementById('tipo').value,
    codigo_cie10: document.getElementById('cie10').value || null,
    es_accidente_transito: document.getElementById('soat').checked,
    medico_admision: medico,
    email_medico: document.getElementById('email_medico').value || null,
  };

  try {
    const resp = await fetch(`${API}/api/webhook/admision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await resp.json();
    stopLoading();

    if (!resp.ok) {
      mostrarError(data.detail || 'Error al procesar la admisión');
      return;
    }

    casosLocales[data.caso_id] = data;
    mostrarResultado(data);

  } catch (err) {
    stopLoading();
    mostrarError('No se pudo conectar con el servidor. Verifica que el backend esté corriendo en el puerto 8000.');
  } finally {
    btn.disabled = false;
  }
}

function mostrarResultado(data) {
  const estado = (data.estado_cobertura || '').toLowerCase();
  const iconos = { confirmada:'', en_revision:'', alerta_critica:'', sin_cobertura:'' };
  const colores = { confirmada:'var(--green)', en_revision:'var(--yellow)', alerta_critica:'var(--red)', sin_cobertura:'var(--muted)' };
  const barColores = { confirmada:'#34d399', en_revision:'#fbbf24', alerta_critica:'#f87171', sin_cobertura:'#64748b' };

  const alertas = (data.alertas || []).map(a => `<li>${a}</li>`).join('') || '<li>Sin alertas adicionales</li>';
  const notifs = (data.notificaciones_enviadas || []).map(n =>
    `<div class="notif-item"><span class="${n.includes('✓') ? 'notif-ok' : ''}">${n.includes('✓') ? '✓' : '✗'}</span>${n}</div>`
  ).join('') || '<div class="notif-item" style="color:var(--muted)">Notificaciones en modo demo (ver consola)</div>';

  const score = data.score_cobertura || 0;
  const notion = data.notion_caso_url ? `<a href="${data.notion_caso_url}" target="_blank" style="color:var(--accent);font-size:12px;font-family:var(--mono)">Ver en Notion ↗</a>` : '';

  const html = `
    <div class="result-header">
      <div>
        <div class="result-estado" style="color:${colores[estado]}">${iconos[estado] || 'ℹ️'} ${data.estado_cobertura}</div>
        <div style="font-size:13px;color:var(--muted);margin-top:4px">${data.paciente} · ${data.hospital}</div>
      </div>
      <div style="text-align:right">
        <div class="result-caso">${data.caso_id}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px">Score: ${score}/100</div>
        ${notion}
      </div>
    </div>
    <div class="score-bar-wrap">
      <div class="score-bar" style="width:${score}%;background:${barColores[estado]}"></div>
    </div>
    <div class="result-resumen">${data.resumen}</div>
    <div class="result-grid">
      <div class="result-box">
        <div class="result-box-title"> Alertas</div>
        <ul>${alertas}</ul>
      </div>
      <div class="result-box">
        <div class="result-box-title"> Cobertura disponible</div>
        <div style="font-size:26px;font-weight:700;color:${colores[estado]}">$${(data.limite_disponible || 0).toLocaleString('es-EC', {minimumFractionDigits:2})}</div>
        <div style="font-size:12px;color:var(--muted);margin-top:4px">Urgencia: <strong style="color:var(--text)">${data.nivel_urgencia}</strong></div>
      </div>
    </div>
    <div class="result-box" style="margin-top:12px">
      <div class="result-box-title"> Notificaciones enviadas</div>
      <div class="notif-list">${notifs}</div>
    </div>
  `;

  const rc = document.getElementById('resultado');
  rc.className = `result-card rc-${estado}`;
  rc.innerHTML = html;
  rc.style.display = 'block';
  rc.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function mostrarError(msg) {
  const rc = document.getElementById('resultado');
  rc.className = 'result-card rc-alerta_critica';
  rc.innerHTML = `<div style="color:var(--red);font-size:16px;font-weight:600"> Error</div><div style="margin-top:8px;color:var(--muted);font-size:14px">${msg}</div>`;
  rc.style.display = 'block';
}

async function cargarDashboard() {
  try {
    const [statsResp, casosResp] = await Promise.all([
      fetch(`${API}/api/dashboard/stats`),
      fetch(`${API}/api/webhook/casos`),
    ]);
    if (statsResp.ok) {
      const s = await statsResp.json();
      document.getElementById('st-total').textContent = s.total_casos;
      document.getElementById('st-conf').textContent = s.confirmados;
      document.getElementById('st-rev').textContent = s.en_revision;
      document.getElementById('st-crit').textContent = s.alertas_criticas;
    }
    if (casosResp.ok) {
      const { casos } = await casosResp.json();
      renderCasos(casos);
    }
  } catch (e) {
    console.error('Dashboard error:', e);
  }
}

function renderCasos(casos) {
  const cl = document.getElementById('cases-list');
  if (!casos || casos.length === 0) {
    cl.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted);font-family:var(--mono);font-size:13px">No hay casos registrados aún.<br>Procesa una admisión para verla aquí.</div>';
    return;
  }
  const dotClass = { CONFIRMADA:'dot-confirmada', EN_REVISION:'dot-en_revision', ALERTA_CRITICA:'dot-alerta_critica', SIN_COBERTURA:'dot-sin_cobertura' };
  const badgeClass = { CONFIRMADA:'badge-confirmada', EN_REVISION:'badge-en_revision', ALERTA_CRITICA:'badge-alerta_critica', SIN_COBERTURA:'badge-sin_cobertura' };
  cl.innerHTML = casos.reverse().map(c => `
    <div class="case-card">
      <div class="case-status-dot ${dotClass[c.estado_cobertura] || 'dot-sin_cobertura'}"></div>
      <div class="case-info">
        <div class="case-name">${c.paciente}</div>
        <div class="case-meta">${c.caso_id} · ${c.hospital} · ${c.tipo_emergencia} · ${new Date(c.timestamp).toLocaleTimeString('es-EC')}</div>
      </div>
      <span class="case-badge ${badgeClass[c.estado_cobertura] || 'badge-sin_cobertura'}">${c.estado_cobertura}</span>
    </div>
  `).join('');
}

setInterval(() => {
  const dashActive = document.getElementById('page-dashboard').classList.contains('active');
  if (dashActive) cargarDashboard();
}, 8000);
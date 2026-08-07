import { writeFileSync } from 'node:fs';

const spec = {
  openapi: '3.0.3',
  info: { title: 'DC IOC Platform API', version: '1.0.0' },
  servers: [{ url: 'http://localhost:8000' }],
  paths: {},
  components: { schemas: {} },
};

const s = (name, def) => { spec.components.schemas[name] = def; };

// ---- Schemas ----
s('Alarm', {
  type: 'object',
  properties: {
    id: { type: 'string' },
    level: { type: 'string', enum: ['crit', 'warn', 'info'] },
    system: { type: 'string' },
    message: { type: 'string' },
    status: { type: 'string' },
    time: { type: 'string' },
    owner: { type: 'string' },
    source: { type: 'string' },
    domain: { type: 'string' },
    title: { type: 'string' },
    created_at: { type: 'string' },
  },
  required: ['level', 'system', 'message', 'status', 'time'],
});

s('AlarmEvent', {
  type: 'object',
  properties: {
    id: { type: 'string' },
    ruleId: { type: 'string' },
    ruleName: { type: 'string' },
    metric: { type: 'string' },
    level: { type: 'string', enum: ['crit', 'warn', 'info'] },
    system: { type: 'string' },
    message: { type: 'string' },
    value: { type: 'number' },
    threshold: { type: 'number' },
    unit: { type: 'string' },
    status: { type: 'string', enum: ['active', 'acknowledged', 'resolved', 'suppressed'] },
    triggeredAt: { type: 'string' },
    acknowledgedAt: { type: 'string' },
    acknowledgedBy: { type: 'string' },
    resolvedAt: { type: 'string' },
    resolvedBy: { type: 'string' },
    note: { type: 'string' },
    autoResolved: { type: 'boolean' },
    escalationCount: { type: 'integer' },
    source: { type: 'string' },
    domain: { type: 'string' },
    title: { type: 'string' },
    time: { type: 'string' },
    created_at: { type: 'string' },
    owner: { type: 'string' },
  },
  required: ['id', 'ruleId', 'ruleName', 'metric', 'level', 'system', 'message', 'value', 'threshold', 'status', 'triggeredAt'],
});

s('AlarmRuleDef', {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    ruleCode: { type: 'string' },
    category: { type: 'string' },
    metric: { type: 'string' },
    warnLo: { type: 'number' },
    warnHi: { type: 'number' },
    critLo: { type: 'number' },
    critHi: { type: 'number' },
    unit: { type: 'string' },
    enabled: { type: 'boolean' },
    source: { type: 'string' },
    status: { type: 'string', enum: ['enabled', 'disabled', 'silenced'] },
    created: { type: 'string' },
    updated: { type: 'string' },
  },
  required: ['id', 'category', 'metric', 'enabled', 'status'],
});

s('Cabinet', {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    name: { type: 'string' },
    room: { type: 'string' },
    status: { type: 'string' },
    temperature: { type: 'number' },
    humidity: { type: 'number' },
    power: { type: 'number' },
  },
});

s('Equipment', {
  type: 'object',
  properties: {
    id: { type: 'integer' },
    name: { type: 'string' },
    room: { type: 'string' },
    status: { type: 'string' },
    type: { type: 'string' },
  },
});

s('Ticket', {
  type: 'object',
  properties: {
    id: { type: 'string' },
    title: { type: 'string' },
    system: { type: 'string' },
    level: { type: 'string' },
    owner: { type: 'string' },
    sla: { type: 'string' },
    description: { type: 'string' },
    state: { type: 'string' },
    source: { type: 'string' },
    sourceAlarmId: { type: 'string' },
  },
});

s('DashboardOverview', {
  type: 'object',
  properties: {
    total_devices: { type: 'integer' },
    online_devices: { type: 'integer' },
    online_rate: { type: 'number' },
    today_alarms: { type: 'integer' },
    pue: { type: 'number' },
    wue: { type: 'number' },
    it_load_mw: { type: 'number' },
    cool_load_mw: { type: 'number' },
    availability: { type: 'number' },
    free_cool_hours: { type: 'number' },
    alarms: {
      type: 'object',
      properties: { crit: { type: 'integer' }, warn: { type: 'integer' }, info: { type: 'integer' } },
    },
  },
});

s('ExternalDevice', {
  type: 'object',
  properties: {
    id: { type: 'string' },
    name: { type: 'string' },
    domain: { type: 'string' },
    protocol: { type: 'string' },
    ip: { type: 'string' },
    port: { type: 'integer' },
    status: { type: 'string' },
  },
});

s('Paginated', {
  type: 'object',
  properties: {
    items: { type: 'array', items: {} },
    total: { type: 'integer' },
    page: { type: 'integer' },
    page_size: { type: 'integer' },
  },
});

// ---- Paths ----
const $ref = (name) => ({ $ref: `#/components/schemas/${name}` });
const ok = (schema) => ({ '200': { description: 'OK', content: { 'application/json': { schema } } } });
const pathParam = (name, type) => ({ name, in: 'path', required: true, schema: { type } });
const queryParam = (name, type) => ({ name, in: 'query', schema: { type } });

spec.paths = {
  '/api/cabinets': {
    get: { parameters: [queryParam('page', 'integer'), queryParam('size', 'integer'), queryParam('room', 'string')], responses: ok($ref('Paginated')) },
  },
  '/api/cabinets/{cabinetId}/metrics': {
    get: { parameters: [pathParam('cabinetId', 'integer'), queryParam('minutes', 'integer'), queryParam('step_sec', 'integer')], responses: ok({ type: 'object', properties: { temperature: { type: 'array', items: { type: 'number' } }, humidity: { type: 'array', items: { type: 'number' } }, power: { type: 'array', items: { type: 'number' } } } }) },
  },
  '/api/equipment': {
    get: { parameters: [queryParam('page', 'integer'), queryParam('size', 'integer'), queryParam('room', 'string'), queryParam('status', 'string'), queryParam('keyword', 'string')], responses: ok({ type: 'object', properties: { items: { type: 'array', items: $ref('Equipment') }, total: { type: 'integer' }, page: { type: 'integer' }, page_size: { type: 'integer' } } }) },
  },
  '/api/equipment/{id}': {
    get: { parameters: [pathParam('id', 'integer')], responses: ok($ref('Equipment')) },
  },
  '/api/equipment/{equipmentId}/metrics': {
    get: { parameters: [pathParam('equipmentId', 'integer'), queryParam('minutes', 'integer'), queryParam('step_sec', 'integer')], responses: ok({ type: 'object', properties: { temperature: { type: 'array', items: { type: 'number' } }, humidity: { type: 'array', items: { type: 'number' } }, power: { type: 'array', items: { type: 'number' } } } }) },
  },
  '/api/tickets': {
    get: { parameters: [queryParam('page', 'integer'), queryParam('size', 'integer'), queryParam('state', 'string'), queryParam('system', 'string'), queryParam('domain', 'string')], responses: ok({ type: 'object', properties: { items: { type: 'array', items: $ref('Ticket') }, total: { type: 'integer' }, page: { type: 'integer' }, page_size: { type: 'integer' } } }) },
    post: { requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { title: { type: 'string' }, system: { type: 'string' }, level: { type: 'string' }, owner: { type: 'string' }, sla: { type: 'string' }, description: { type: 'string' }, source: { type: 'string' }, sourceAlarmId: { type: 'string' } }, required: ['title', 'system', 'level'] } } } }, responses: ok($ref('Ticket')) },
  },
  '/api/tickets/{id}': {
    get: { parameters: [pathParam('id', 'string')], responses: ok($ref('Ticket')) },
    put: { parameters: [pathParam('id', 'string')], requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { title: { type: 'string' }, system: { type: 'string' }, level: { type: 'string' }, owner: { type: 'string' }, sla: { type: 'string' }, description: { type: 'string' } } } } } }, responses: ok($ref('Ticket')) },
    delete: { parameters: [pathParam('id', 'string')], responses: { '200': { description: 'OK' } } },
  },
  '/api/tickets/{id}/transition/{state}': {
    post: { parameters: [pathParam('id', 'string'), pathParam('state', 'string')], requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { state: { type: 'string' }, operator: { type: 'string' }, note: { type: 'string' } }, required: ['state', 'operator'] } } } }, responses: ok($ref('Ticket')) },
  },
  '/api/tickets/from-alarm/{alarmId}': {
    post: { parameters: [pathParam('alarmId', 'string')], requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { title: { type: 'string' }, system: { type: 'string' }, level: { type: 'string' }, owner: { type: 'string' }, sla: { type: 'string' }, description: { type: 'string' }, source: { type: 'string' }, sourceAlarmId: { type: 'string' } }, required: ['title', 'system', 'level'] } } } }, responses: ok($ref('Ticket')) },
  },
  '/api/ops/assistant/ask': {
    post: { requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { question: { type: 'string' }, context: { type: 'string' } }, required: ['question'] } } } }, responses: ok({ type: 'object', properties: { answer: { type: 'string' }, sources: { type: 'array', items: { type: 'string' } } } }) },
  },
  '/api/ops/assistant/status': {
    get: { responses: ok({ type: 'object', properties: { available: { type: 'boolean' }, model: { type: 'string' }, error: { type: 'string' } } }) },
  },
  '/api/alarms/active': {
    get: { responses: ok({ type: 'object', properties: { total: { type: 'integer' }, items: { type: 'array', items: $ref('Alarm') } } }) },
  },
  '/api/alarms/active/{id}/ack': {
    post: { parameters: [pathParam('id', 'string')], responses: ok({ type: 'object', properties: { ok: { type: 'boolean' } } }) },
  },
  '/api/alarms/active/{id}/resolve': {
    post: { parameters: [pathParam('id', 'string')], responses: ok({ type: 'object', properties: { ok: { type: 'boolean' } } }) },
  },
  '/api/alarm-rules': {
    get: { responses: ok({ type: 'array', items: $ref('AlarmRuleDef') }) },
    post: { requestBody: { content: { 'application/json': { schema: $ref('AlarmRuleDef') } } }, responses: ok($ref('AlarmRuleDef')) },
  },
  '/api/alarm-rules/{id}': {
    put: { parameters: [pathParam('id', 'string')], requestBody: { content: { 'application/json': { schema: $ref('AlarmRuleDef') } } }, responses: ok($ref('AlarmRuleDef')) },
    delete: { parameters: [pathParam('id', 'string')], responses: { '200': { description: 'OK' } } },
  },
  '/api/alarm-rules/{id}/status': {
    patch: { parameters: [pathParam('id', 'string')], requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { status: { type: 'string', enum: ['enabled', 'disabled', 'silenced'] } } } } } }, responses: ok($ref('AlarmRuleDef')) },
  },
  '/api/alarm-rules/{id}/toggle': {
    patch: { parameters: [pathParam('id', 'string')], requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { enabled: { type: 'boolean' } } } } } }, responses: ok($ref('AlarmRuleDef')) },
  },
  '/api/dashboard/overview': {
    get: { responses: ok($ref('DashboardOverview')) },
  },
  '/api/external/devices': {
    get: { parameters: [queryParam('domain', 'string'), queryParam('protocol', 'string'), queryParam('skip', 'integer'), queryParam('limit', 'integer')], responses: ok({ type: 'object', properties: { items: { type: 'array', items: $ref('ExternalDevice') }, total: { type: 'integer' } } }) },
  },
  '/api/external/thing-models': {
    get: { responses: ok({ type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, name: { type: 'string' }, properties: { type: 'object' } } } }) },
  },
  '/api/external/devices/{deviceId}/metrics/realtime': {
    get: { parameters: [pathParam('deviceId', 'string')], responses: ok({ type: 'object', properties: { value: { type: 'number' }, timestamp: { type: 'string' } } }) },
  },
  '/api/external/devices/{deviceId}/metrics/history': {
    get: { parameters: [pathParam('deviceId', 'string'), queryParam('minutes', 'integer'), queryParam('step_sec', 'integer')], responses: ok({ type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: { timestamp: { type: 'string' }, value: { type: 'number' } } } } } }) },
  },
  '/api/auth/login': {
    post: { requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { username: { type: 'string' }, password: { type: 'string' } }, required: ['username', 'password'] } } } }, responses: ok({ type: 'object', properties: { access_token: { type: 'string' }, refresh_token: { type: 'string' }, user: { type: 'object' } } }) },
  },
  '/api/auth/register': {
    post: { requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { username: { type: 'string' }, password: { type: 'string' }, display_name: { type: 'string' }, email: { type: 'string' } }, required: ['username', 'password'] } } } }, responses: ok({ type: 'object', properties: { ok: { type: 'boolean' }, message: { type: 'string' } } }) },
  },
  '/api/auth/refresh': {
    post: { requestBody: { content: { 'application/json': { schema: { type: 'object', properties: { refresh_token: { type: 'string' } }, required: ['refresh_token'] } } } }, responses: ok({ type: 'object', properties: { access_token: { type: 'string' }, refresh_token: { type: 'string' }, user: { type: 'object' } } }) },
  },
  '/api/audit/logs': {
    get: { parameters: [queryParam('page', 'integer'), queryParam('size', 'integer'), queryParam('action', 'string'), queryParam('user', 'string')], responses: ok({ type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: { id: { type: ['integer', 'string'] }, timestamp: { type: 'string' }, action: { type: 'string' }, resource: { type: 'string' }, username: { type: 'string' }, ip: { type: 'string' }, status_code: { type: 'integer' }, detail: { type: 'string' } } } }, total: { type: 'integer' }, page: { type: 'integer' }, page_size: { type: 'integer' } } }) },
  },
  '/api/knowledge': {
    get: { parameters: [queryParam('category', 'string'), queryParam('domain', 'string')], responses: ok({ type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, title: { type: 'string' }, category: { type: 'string' }, domain: { type: 'string' }, type: { type: 'string' }, summary: { type: 'string' }, content: { type: 'string' }, tags: { type: 'array', items: { type: 'string' } }, version: { type: 'string' } } } }) },
  },
  '/api/knowledge/import': {
    post: { requestBody: { content: { 'multipart/form-data': { schema: { type: 'object', properties: { file: { type: 'string', format: 'binary' } }, required: ['file'] } } } }, responses: ok({ type: 'object', properties: { ok: { type: 'boolean' }, count: { type: 'integer' }, message: { type: 'string' } } }) },
  },
};

writeFileSync('openapi.json', JSON.stringify(spec, null, 2));
console.log('openapi.json written successfully');

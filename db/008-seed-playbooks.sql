-- db/008-seed-playbooks.sql
-- Seeds the library: pb_eje_default (encodes the CURRENT EJE cadence so nothing is lost when sends
-- migrate onto runs, audit F3) and pb_001 (the reconstructed Daniela sequence from OUTREACH_PLAYBOOKS.md).
-- Idempotent: safe to re-run.

insert into playbooks (id, name, version, channel_set, mode, author, status) values
  ('pb_eje_default', 'Cadencia EJE por defecto', 1, '{email,instagram_dm}', 'broad', 'eje', 'active'),
  ('pb_001_channel_switch_reopen', 'Cambio de canal y reapertura', 1, '{email,instagram_dm,voice_note}', 'broad', 'eje', 'active')
on conflict (id) do nothing;

-- pb_eje_default: 1er email -> IG DM (+2d) -> 2do email (+5d) -> stop. Mirror of app.html ISEJE cadence.
insert into playbook_steps (playbook_id, step_no, trigger, channel, intent, required_fields, next_state, meta) values
  ('pb_eje_default', 1, '{"start":true}', 'email',
     'Primer email: presentacion breve + por que ellos (un dato real).', '{first_name,company}', null, '{}'),
  ('pb_eje_default', 2, '{"after_days":2,"if":"no_reply"}', 'instagram_dm',
     'Cambio de canal: DM suave que nombra el correo anterior, sin repetir el pitch.', '{first_name}', null, '{}'),
  ('pb_eje_default', 3, '{"after_days":5,"if":"no_reply"}', 'email',
     'Segundo email corto: un solo ask, la llamada. Luego parar.', '{first_name}', 'stopped', '{"stop_after":true}')
on conflict (playbook_id, step_no) do nothing;

-- pb_001_channel_switch_reopen: the six-step sequence that turned a no into a request for a proposal.
insert into playbook_steps (playbook_id, step_no, trigger, channel, intent, required_fields, stop_if, next_state, meta) values
  ('pb_001_channel_switch_reopen', 1, '{"start":true}', 'email',
     'Primer contacto con un dato real de su empresa y la propuesta en una linea.',
     '{first_name,company,one_real_fact}', null, null, '{}'),
  ('pb_001_channel_switch_reopen', 2, '{"after_days":4,"if":"no_reply"}', 'instagram_dm',
     'Cambiar de canal. Nombrar el correo anterior. Ofrecer un resumen aqui, sin repetir el pitch.',
     '{first_name}', null, null,
     '{"example":"Hola! Te escribi un correo hace unos dias desde EJE. Quede esperando tu respuesta. Quieres que te haga un resumen por aqui?"}'),
  ('pb_001_channel_switch_reopen', 3, '{"after_days":3,"if":"no_reply"}', 'instagram_dm',
     'Tono humano. Reconocer que los mensajes se perdieron sin culpar. Decir por que ella (calza con el perfil de un cliente). Pitch en dos lineas. Terminar con una pregunta de capacidad, no de interes.',
     '{first_name,why_her_one_line}', null, null,
     '{"notes":"La pregunta de capacidad invita a responder aunque sea no. La de interes invita al silencio."}'),
  ('pb_001_channel_switch_reopen', 4, '{"on":"soft_no"}', 'voice_note',
     'No discutir el no. Preguntar como consiguen clientes hoy. Voz, no texto: una voz es una persona, un texto es un pitch.',
     '{}', 'hard_no', null,
     '{"example_prompt":"Y hoy como les llegan los clientes, mas que nada?"}'),
  ('pb_001_channel_switch_reopen', 5, '{"on":"answer_to_step_4"}', 'voice_note',
     'Reencuadre con lo que dijo. Si nombra referidos o anuncios: esa es una maquina, la otra es la que falta, las dos juntas es el ideal. Sin pedir nada todavia.',
     '{their_current_channel}', null, null, '{}'),
  ('pb_001_channel_switch_reopen', 6, '{"on":"reopened_or_asked_for_material"}', 'instagram_dm',
     'Celebrar el flujo que tienen, no minimizarlo. Posicionar el sistema para no depender de eso. Enviar material por el canal formal (email) y dejar la puerta abierta sin presion.',
     '{}', null, 'nurture',
     '{"nurture_rule":{"after_days":21,"channel":"email","intent":"Un dato nuevo, una linea, sin pedir reunion."}}')
on conflict (playbook_id, step_no) do nothing;

const script = document.currentScript;
const botId = script?.getAttribute('data-bot-id');
if (!botId) console.error('[FlowForge] Informe data-bot-id no script do widget.');
else {
  const api = new URL(script.src).origin;
  const parentDomain = window.location.origin;
  const frame = document.createElement('iframe');
  frame.title = 'Converse com nosso assistente';
  fetch(`${api}/api/widget/capability?bot_id=${encodeURIComponent(botId)}&origin=${encodeURIComponent(parentDomain)}`, {
    method: 'POST',
  })
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then(({ capability }) => {
      frame.src = `${api}/widget?bot_id=${encodeURIComponent(botId)}&capability=${encodeURIComponent(capability)}`;
    })
    .catch(() => {
      frame.src = `${api}/widget?bot_id=${encodeURIComponent(botId)}&denied=1`;
    });
  frame.style.cssText = 'position:fixed;right:20px;bottom:88px;width:360px;height:520px;max-height:calc(100vh - 110px);border:0;border-radius:16px;box-shadow:0 12px 45px #15132b30;z-index:2147483646;display:none;background:white';
  const button = document.createElement('button');
  button.type = 'button'; button.title = 'Abrir atendimento'; button.setAttribute('aria-label', 'Abrir atendimento');
  button.textContent = '✳';
  button.style.cssText = 'position:fixed;right:20px;bottom:20px;width:56px;height:56px;border:0;border-radius:50%;background:#6d5dfc;color:white;font-size:25px;box-shadow:0 5px 18px #241a563d;cursor:pointer;z-index:2147483647';
  button.onclick = () => { frame.style.display = frame.style.display === 'none' ? 'block' : 'none'; };
  document.body.append(frame, button);
}

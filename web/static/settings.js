const message=document.querySelector('#settings-message');
document.querySelector('#settings-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;
  try{const response=await fetch('/api/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))}),data=await response.json();message.textContent=data.message||data.detail;if(response.ok)document.querySelector('#refresh-codex').click();}
  catch(error){message.textContent='保存失败：'+error.message;}finally{button.disabled=false;}
});
const panel=document.querySelector('#login-panel'),state=document.querySelector('#login-state'),link=document.querySelector('#login-link'),loginButton=document.querySelector('#login-codex');
async function showLogin(data){
  panel.hidden=false;state.textContent=({idle:'尚未开始登录',starting:'正在准备官方登录…',waiting:'请在官方页面完成登录，然后返回此页。',completed:'登录成功。',cancelled:'登录已取消。',failed:'登录失败：'+(data.error||'请重试')})[data.status];
  link.hidden=!data.auth_url; if(data.auth_url){const url=new URL(data.auth_url);if(url.protocol==='https:'&&url.hostname==='auth.openai.com')link.href=data.auth_url;else{link.hidden=true;state.textContent='SDK 返回的登录地址无法识别。';}}
  const active=['starting','waiting'].includes(data.status);loginButton.disabled=active;document.querySelector('#cancel-login').hidden=!active;
  if(active)setTimeout(pollLogin,2000);if(data.status==='completed')document.querySelector('#refresh-codex').click();
}
async function pollLogin(){try{await showLogin(await (await fetch('/api/codex/login')).json());}catch(error){state.textContent='登录状态读取失败，请刷新页面。';loginButton.disabled=false;}}
loginButton.addEventListener('click',async()=>{loginButton.disabled=true;panel.hidden=false;state.textContent='正在准备官方登录…';try{const response=await fetch('/api/codex/login',{method:'POST'}),data=await response.json();if(!response.ok)throw new Error(data.detail||'启动失败');await showLogin(data);}catch(error){state.textContent=error.message;loginButton.disabled=false;}});
document.querySelector('#cancel-login').addEventListener('click',async()=>{await showLogin(await (await fetch('/api/codex/login/cancel',{method:'POST'})).json());});
pollLogin();

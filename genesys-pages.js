/* AEDATS: Genesys Ireland public queue snapshot (no credentials in browser). */
(() => {
  'use strict';
  const host = document.querySelector('.col-side') || document.querySelector('.wrap');
  if (!host) return;
  const panel = document.createElement('section');
  panel.className = 'card';
  const heading = document.createElement('h2');
  const status = document.createElement('div');
  const area = document.createElement('div');
  area.style.overflowX = 'auto';
  status.style.cssText = 'font-size:11px;color:var(--ink-soft);margin:5px 0 9px';
  panel.append(heading, status, area);
  host.append(panel);
  const lang = () => document.querySelector('#langSwitch button.on')?.dataset.lang === 'de' ? 'de' : 'zh';
  const words = {
    zh:['Genesys 队列监控 · 准实时','正在读取 Genesys 数据…','数据不可用','采集时间','数据过期','队列','排队','最长等待','接通率 / 30分钟','接听 / 30分钟','坐席工作量 / 30分钟','坐席','处理时间 / 分钟','个人工作量未公开','GitHub 每5分钟计划采集（可能延迟）'],
    de:['Genesys Queues · Zeitversetzt','Genesys-Daten werden geladen…','Daten nicht verfügbar','Erfasst am','Daten veraltet','Queue','Wartend','Längste Wartezeit','Annahmequote / 30 Min.','Angenommen / 30 Min.','Agentenleistung / 30 Min.','Agent','Bearbeitungszeit / Min.','Persönliche Leistungsdaten nicht veröffentlicht','GitHub-Abfrage geplant alle 5 Min. (Verzögerungen möglich)']
  };
  const t = i => words[lang()][i];
  const el = (tag,text) => {const x=document.createElement(tag); if(text!==undefined)x.textContent=String(text);return x;};
  const fmt = n => n==null || !Number.isFinite(Number(n))?'—':String(n);
  let data=null, error=null;
  function render(){
    heading.textContent=t(0);area.replaceChildren();
    if(!data){status.textContent=error?t(2)+': '+error:t(1);return;}
    const timestamp=Date.parse(data.generated_at_utc);
    const stale=!Number.isFinite(timestamp)||Date.now()-timestamp>15*60*1000||timestamp-Date.now()>60*1000;
    status.textContent=t(3)+' '+(Number.isFinite(timestamp)?new Date(timestamp).toLocaleString(lang()==='de'?'de-DE':'zh-CN'):'—')+(stale?' · '+t(4):'')+' · '+t(14);
    status.style.color=stale?'var(--danger-ink)':'var(--ink-soft)';
    const table=el('table');table.style.minWidth='390px';
    const tr=el('tr');
    for(const col of [t(5),t(6),t(7),t(8),t(9)])tr.append(el('th',col));
    const head=el('thead');head.append(tr);table.append(head);
    const body=el('tbody');
    for(const name of ['Ger-On-Site','GER_Installer']){
      const record=(data.queues||[]).find(x=>x.queue_name===name);
      const valid=record&&!stale;
      const values=[name,valid?fmt(record.live?.waiting):'—',valid?fmt(record.live?.longest_wait_seconds)+' s':'—',valid&&record.kpi?.answer_rate!=null?(record.kpi.answer_rate*100).toFixed(1)+'%':'—',valid?fmt(record.kpi?.answered):'—'];
      const row=el('tr');for(const value of values)row.append(el('td',value));body.append(row);
    }
    table.append(body);area.append(table);
    if(data.workload_published){
      const caption=el('h3',t(10));caption.style.margin='16px 0 6px';area.append(caption);
      const agents=el('table');const hrow=el('tr');
      for(const label of [t(11),t(5),t(9),t(12)])hrow.append(el('th',label));
      const ah=el('thead');ah.append(hrow);agents.append(ah);const ab=el('tbody');
      for(const item of data.workload||[]){
        const row=el('tr');
        for(const v of [item.agent_name,item.queue_name,stale?'—':fmt(item.answered),stale?'—':fmt((item.handle_seconds/60).toFixed(1))])row.append(el('td',v));
        ab.append(row);
      }
      agents.append(ab);area.append(agents);
    }else{
      const note=el('p',t(13));note.style.cssText='font-size:11px;color:var(--ink-soft)';area.append(note);
    }
  }
  async function load(){
    try{
      const response=await fetch('./data/genesys.json?_='+Date.now(),{cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const incoming=await response.json();
      if(incoming.schema_version!==1||!Array.isArray(incoming.queues))throw new Error('Invalid snapshot');
      data=incoming;error=null;
    }catch(e){data=null;error=e.message;}
    render();
  }
  document.querySelector('#langSwitch')?.addEventListener('click',()=>setTimeout(render,0));
  load();setInterval(load,60*1000);
})();

/* 回归：从「空」角色属性覆盖开始，三条添加路径都必须生成编辑框且不报错
   （此前 renderPC() 末尾 delete obj.PropertyChange 会让 handler 里 undefined.push 崩掉）
   覆盖两个事件：生成卡牌 PacketSpawn / 创建角色卡牌 PacketCreate */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(path.join(__dirname, 'gemmatch_builder.html'), 'utf8');
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true });
const win = dom.window, doc = win.document;
const errs = [];
win.addEventListener('error', e => errs.push('window.error: ' + (e.message || e)));

setTimeout(() => {
  const dbg = win.__builder_dbg;
  const fails = [];
  function ck(name, cond, extra) {
    if (!cond) fails.push(name + (extra ? '  [' + extra + ']' : ''));
    console.log((cond ? '[PASS] ' : '[FAIL] ') + name + (extra ? '  ' + extra : ''));
  }

  const lv = JSON.parse(JSON.stringify(dbg.getLV()));
  lv.Name = 'RegressPC';
  lv.Process = { Name: 'Wave', Data: {} };
  lv.Feature = [
    { Name: 'Map', Data: { MapName: 'Frontlawn' } },
    { Name: 'RainMode', Data: { Type: 'Default', Packet: [
      { Name: 'PlantPeashooter', Weight: 1, Override: {
        CharacterOverride: { DieEvent: [
          /* 关键：两个事件的覆盖都是「空对象」——即用户实际遇到的初始状态 */
          { EventName: 'PacketSpawn', Value: { CharacterOverride: {} } },
          { EventName: 'PacketCreate', Value: { Override: {} } }
        ] } } } ] } }
  ];
  dbg.setLV(lv);

  function cardOf(needle) {
    const ttl = Array.from(doc.querySelectorAll('.card > .hd .ttl'))
      .find(e => e.textContent.indexOf(needle) >= 0);
    return ttl ? ttl.closest('.card') : null;
  }
  function pcRow(card, needle) {
    return Array.from(card.querySelectorAll('.row')).find(r => {
      const l = r.querySelector(':scope > label');
      return l && l.textContent.indexOf(needle) >= 0;
    });
  }

  const pickedByEvent = {};
  ['生成卡牌 (PacketSpawn)', '创建角色卡牌 (PacketCreate)'].forEach(evName => {    console.log('\n--- ' + evName + ' ---');
    const card = cardOf(evName);
    ck(evName + ' 卡片存在', !!card);
    if (!card) return;

    const ovrCard = card.querySelector('.stack .card');
    ck(evName + ' 属性覆盖为 .stack 全宽块', !!card.querySelector('.stack'));

    /* 路径①：单选即出框 */
    const qRow = pcRow(card, '单选即出框');
    const qSel = qRow && qRow.querySelector('select');
    ck(evName + ' 有「单选即出框」下拉', !!qSel);
    if (qSel) {
      const before = doc.querySelectorAll('.card').length;
      const opt = Array.from(qSel.options).find(o => o.value);
      const picked = opt.value;
      qSel.value = picked;
      qSel.dispatchEvent(new win.Event('change'));
      const after = doc.querySelectorAll('.card').length;
      ck(evName + ' 单选后生成编辑框（卡片数增加）', after > before, picked + ' ' + before + '->' + after);
      const hasVal = !!cardOf(evName).querySelector('.stack .card .row input[type=number]');
      ck(evName + ' 新框内有「值」输入控件', hasVal);
      pickedByEvent[evName] = picked;
    }

    /* 路径②：勾选批量加入 */
    const cRow = pcRow(card, '勾选批量加入');
    ck(evName + ' 有「勾选批量加入」', !!cRow);
    if (cRow) {
      const boxes = cRow.querySelectorAll('input[type=checkbox]');
      ck(evName + ' 勾选框可渲染', boxes.length > 0, 'n=' + boxes.length);
      if (boxes.length) {
        const before = doc.querySelectorAll('.card').length;
        boxes[0].checked = true;
        const addBtn = cRow.querySelector('button');
        addBtn.dispatchEvent(new win.Event('click'));
        const after = doc.querySelectorAll('.card').length;
        ck(evName + ' 勾选批量加入生成编辑框', after > before, before + '->' + after);
      }
    }

    /* 路径③：自定义属性 */
    const aRow = pcRow(card, '自定义属性');
    ck(evName + ' 有「自定义属性」', !!aRow);
    if (aRow) {
      const nm = aRow.querySelector('input[type=text]');
      const before = doc.querySelectorAll('.card').length;
      nm.value = 'myCustomProp';
      aRow.querySelector('button').dispatchEvent(new win.Event('click'));
      const after = doc.querySelectorAll('.card').length;
      ck(evName + ' 自定义属性生成编辑框', after > before, before + '->' + after);
    }
  });

  /* 往返：写入的属性必须在导出 JSON 里 */
  const out = dbg.buildOut();
  const rm = out.Feature.find(f => f.Name === 'RainMode');
  const evs = rm.Data.Packet[0].Override.CharacterOverride.DieEvent;
  const spawnPC = evs.find(e => e.EventName === 'PacketSpawn').Value.CharacterOverride.PropertyChange;
  const createPC = evs.find(e => e.EventName === 'PacketCreate').Value.Override.PropertyChange;
  ck('生成卡牌：PropertyChange 写入且含所选属性',
     Array.isArray(spawnPC) && spawnPC.some(x => x.PropertyName === pickedByEvent['生成卡牌 (PacketSpawn)']),
     JSON.stringify(spawnPC));
  ck('创建角色卡牌：PropertyChange 写入且含所选属性',
     Array.isArray(createPC) && createPC.some(x => x.PropertyName === pickedByEvent['创建角色卡牌 (PacketCreate)']),
     JSON.stringify(createPC));
  ck('导出无 "PropertyChange":[] 空数组噪声',
     JSON.stringify(out).indexOf('"PropertyChange":[]') < 0);
  ck('运行期无 JS 错误（原先在此报 undefined.push）', errs.length === 0, errs.slice(0, 2).join(' | '));

  console.log('----------------------------------------');
  console.log(fails.length ? ('失败 ' + fails.length + ' 项：\n  ' + fails.join('\n  ')) : '全部通过');
  process.exit(fails.length ? 1 : 0);
}, 1000);

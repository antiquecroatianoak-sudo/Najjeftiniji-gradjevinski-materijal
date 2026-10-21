const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodes = new Map(), instances = [], saved = [];
function node(id) {
 if (!nodes.has(id)) nodes.set(id, {hidden:true,textContent:'',classList:{add(){},remove(){}},setAttribute(){},focus(){this.focused=true;}});
 return nodes.get(id);
}
// Mock: kontinuirano prepoznavanje skuplja rezultate kao preglednik (results raste, resultIndex = prvi novi).
class Speech {
 constructor(){instances.push(this);this.rezultati=[];}
 start(){this.started=true;}
 stop(){this.stopped=true;this.onend();}
 result(text, isFinal=true){const r=[{transcript:text}];r.isFinal=isFinal;this.rezultati.push(r);
  this.onresult({resultIndex:this.rezultati.length-1,results:this.rezultati});}
 repeat(){this.onresult({resultIndex:0,results:this.rezultati});}
}
let source = fs.readFileSync(require('node:path').join(__dirname,'../site/aplikacija.js'),'utf8');
source = source.slice(0,source.indexOf('// ---------- Prikaz ----------'));
const context = vm.createContext({Skupine:require('../site/skupine.js'),window:{SpeechRecognition:Speech},
 localStorage:{getItem:()=>null,setItem:(k,v)=>saved.push(JSON.parse(v))},document:{getElementById:node},
 setTimeout(){throw Error('voice input must not schedule automatic restarts');}});
vm.runInContext(source+'\nfunction prikazi() {}',context);
const run=s=>vm.runInContext(s,context);
const nazivi=()=>Array.from(run('stanje.popis.map(x=>x.naziv)'));
run('pokreniSlusanje()');
let current=instances.at(-1);
assert(current.started);assert.equal(current.lang,'hr-HR');assert.equal(current.continuous,true,'one press starts a multi-item session');
assert.equal(current.interimResults,false);assert.equal(node('mikrofon-tekst').textContent,'Gotovo');
current.result('20 m2 laminata, 2,5 kubika betona');
assert.deepEqual(nazivi(),['Laminata','Betona'],'saved immediately, decimal comma kept');
assert.deepEqual(JSON.parse(JSON.stringify(run('stanje.popis.map(x=>x.trazeno)'))),[{iznos:20,jedinica:'m2'},{iznos:2.5,jedinica:'m3'}]);
assert.equal(saved.at(-1).popis.length,2,'persisted before the session ends');
current.result('3 vreće cementa i stiropor');
assert.deepEqual(nazivi(),['Laminata','Betona','Cementa','Stiropor'],'keeps listening for more items');
assert.equal(run('stanje.popis[2].kom'),3);
current.repeat();assert.equal(run('stanje.popis.length'),4,'a result already processed is not added again');
current.result('cijev', false);assert.equal(run('stanje.popis.length'),4,'interim text is never added');
run('pokreniSlusanje()');assert(current.stopped,'second press (Gotovo) stops the session');
assert.equal(run('slusac'),null);assert.equal(instances.length,1,'finishing never restarts');
assert.equal(node('mikrofon-tekst').textContent,'Nastavi popis');assert.match(node('glasovni-nacrt').textContent,/Dodano 4 stavki/);
// Nastavak: zaboravljene stavke dodaju se bez brisanja postojećih.
run('pokreniSlusanje()');const second=instances.at(-1);current.result('zakašnjeli');
second.result('gips');second.onend();
assert.deepEqual(nazivi(),['Laminata','Betona','Cementa','Stiropor','Gips'],'resume appends; stale session is ignored');
// Preglednik sam završi (tišina): nema ponovnog pokretanja.
run('pokreniSlusanje()');current=instances.at(-1);current.onend();
assert.equal(run('slusac'),null);assert.match(node('glasovni-nacrt').textContent,/Nije prepoznata nijedna/);assert.equal(instances.length,3);
for(const error of ['not-allowed','audio-capture','network','no-speech']){
 run('pokreniSlusanje()');current=instances.at(-1);current.onerror({error});current.onend();
 assert.equal(run('slusac'),null);assert(!node('glasovni-nacrt').hidden);assert.equal(run('stanje.popis.length'),5);
}
Speech.prototype.start=function(){throw Error('unavailable');};
run('pokreniSlusanje()');assert.equal(run('slusac'),null);assert.match(node('glasovni-nacrt').textContent,/nije dostupan/);
const unsupported=vm.createContext({window:{},localStorage:{getItem:()=>null},document:{getElementById:node}});
vm.runInContext(source+'\nfunction prikazi() {}\npokreniSlusanje()',unsupported);
assert(node('unos').focused);assert.match(node('glasovni-nacrt').textContent,/ne podržava/);
console.log('VOICE PASS: multi-item session, Gotovo stops, resume appends, decimal comma, construction amounts, no duplicates, no interim, no restarts, errors, unsupported browser');

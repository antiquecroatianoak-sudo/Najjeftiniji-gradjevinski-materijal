const assert = require('node:assert/strict');
const Skupine = require('../site/skupine.js');
// Sintetički nazivi (nisu stvarni cjenici).
const names = [
 'Cement CEM II/B 25 kg', 'Marka Cement portland 25 kg', 'Ljepilo za pločice C2TE 25 kg', 'Ljepilo za stiropor 25 kg',
 'Ljepilo montažno 300 ml', 'Kanta za žbuku 12 l', 'Valjak za boju 25 cm', 'Boja za zidove bijela 15 l', 'Fasadna boja 15 l',
 'Stiropor EPS 100 10 cm', 'XPS ploča 5 cm', 'Kamena vuna 10 cm', 'PVC cijev 110 mm', 'Cijev bakrena 15 mm',
 'Mješalica za beton 140 l', 'Kolica za beton 80 l', 'Gotovi beton C25/30', 'Laminat hrast 8 mm', 'Vijak za drvo 4x40',
];
const input = names.map(n => [n, '', 1, 'kom', n.startsWith('Marka ') ? 1 : 0, [0, 2]]);
const g = Skupine.pripremi(input);
const ids = (q) => (g.pogoci(q) || []).map(i => input[i][0]);
assert.deepEqual(ids('cement'), ['Cement CEM II/B 25 kg', 'Marka Cement portland 25 kg'], 'brand words before the noun are allowed');
assert.deepEqual(ids('ljepilo za pločice'), ['Ljepilo za pločice C2TE 25 kg'], 'tile adhesive is its own group');
assert(!ids('ljepilo za pločice').includes('Ljepilo montažno 300 ml'), 'tile adhesive query does not include generic adhesive');
// Roditelj uključuje potomke: „ljepilo” prikazuje i ljepilo za pločice i za izolaciju (usporedba ostaje po specifikaciji).
assert.deepEqual(ids('ljepilo').sort(), ['Ljepilo montažno 300 ml', 'Ljepilo za pločice C2TE 25 kg', 'Ljepilo za stiropor 25 kg'].sort());
assert.deepEqual(ids('boja').sort(), ['Boja za zidove bijela 15 l', 'Fasadna boja 15 l'].sort(), 'paint includes wall and facade paint');
assert.equal(Skupine.definicije.find((d) => d.id === 'boja-zid').roditelj, 'boja');
assert(!ids('žbuka').includes('Kanta za žbuku 12 l'), 'a bucket for plaster is not plaster');
assert(!ids('boja').includes('Valjak za boju 25 cm'), 'a roller is not paint');
assert.deepEqual(ids('boja za zidove'), ['Boja za zidove bijela 15 l']);
assert.deepEqual(ids('fasadna boja'), ['Fasadna boja 15 l']);
assert.deepEqual(ids('stiropor'), ['Stiropor EPS 100 10 cm']);
assert.deepEqual(ids('pvc cijev'), ['PVC cijev 110 mm']);
assert.deepEqual(ids('cijev').sort(), ['Cijev bakrena 15 mm', 'PVC cijev 110 mm'], 'pipe includes its PVC subgroup');
assert.deepEqual(ids('mješalica'), ['Mješalica za beton 140 l']);
assert(!ids('beton').includes('Mješalica za beton 140 l'), 'a concrete mixer is not concrete');
assert(!ids('beton').includes('Kolica za beton 80 l'));
assert.deepEqual(ids('vijci'), ['Vijak za drvo 4x40'], 'plural query finds singular product');
// Stvarni nalaz revizije (run 29): upit „čavao” mora naći „Čavli…”, i velikim slovima i bez dijakritike.
const cavli = Skupine.pripremi([['Čavli građevinski 3,4x80 mm', '', 1, 'kom', 0, [0, 1]], ['ČAVLI 12 (42X120) 1/1 KG', '', 1, 'kg', 0, [0, 1]]]);
for (const q of ['čavao', 'ČAVAO', 'cavao', 'Čavli']) assert.deepEqual(cavli.pogoci(q), [0, 1], q);
assert.equal(g.pogoci('nepoznata stvar'), null, 'unknown words fall back to plain search');
// Spremljeni indeks mora odgovarati cjeniku.
const indeks = g.izvezi();
assert.deepEqual(Skupine.pripremi(input, indeks).pogoci('cement'), g.pogoci('cement'));
assert.throws(() => Skupine.pripremi(input.slice(1), indeks));
console.log('GROUP FIXTURES PASS');

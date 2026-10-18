import {first} from '../tests/first-fixture.mjs';
import {replay,facts} from './engine.mjs';
const second=document.querySelector('#second');
function update(){document.querySelector('#facts').textContent=JSON.stringify(facts(replay(first,Number(second.value))),null,2);}
second.addEventListener('input',update);update();

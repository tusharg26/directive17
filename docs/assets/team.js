/* Team page behaviour (round 46). Loaded only on /team.html. Without it the painting, names and full bios still show. */
(function(){
var $=function(s,r){return (r||document).querySelector(s)},$$=function(s,r){return [].slice.call((r||document).querySelectorAll(s))};
var root=$('.tgp');if(!root)return;document.documentElement.classList.add('tgjs');
var band=$('.gp-band',root),row=$('.gp-row',root),view=$('.gp-view',root),vfig=$('.gp-view-fig',view),vimg=$('.gv-art',vfig),vtx=$('.gp-view-tx',view),stack=$('.gv-stack',view),count=$('.gv-count',view),
    full=$('.gp-full',root),hits=$$('.gp-hit',root),names=$$('button.pk-n',root),solos=$$('.gp-solo',root),hero=$('.team-hero'),under=$('.gp-u-full',root),src=$$('.pf-src'),
    ids=[],items={},who={},art={},cur=-1,opener=null,y0=0,phone=window.matchMedia('(max-width:760px)'),calm=window.matchMedia('(prefers-reduced-motion:reduce)').matches,t1=null;
var two=function(v){return (v<10?'0':'')+v},of=function(b){return +b.getAttribute('data-p')};
/* the people with a bio, in the order of the painting: each one's text goes into the one cell of the profile, so it is as tall as the longest text whoever is showing */
src.forEach(function(a){var i=+a.id.replace('pf-',''),it=document.createElement('div');it.className='gv-item';it.tabIndex=-1;it.innerHTML=$('.pf-tx',a).innerHTML;stack.appendChild(it);ids.push(i);items[i]=it;who[i]=$('.nm',it).textContent;art[i]=$('.pf-ph img',a).getAttribute('src');});
var n=ids.length,at=function(i){return ids.indexOf(i)},step=function(i,d){return ids[(at(i)+d+n)%n]};
/* the single figures (pointing at a person; the profile) and the ring are fetched once the page has loaded, or at the first sign they are wanted */
var warmed=false,keep=[],warm=function(){if(warmed)return;warmed=true;solos.forEach(function(s){s.src=s.getAttribute('data-src');});
  ids.map(function(i){return art[i];}).concat([$('.gv-ring',view).getAttribute('src')]).forEach(function(u){var im=new Image();im.src=u;keep.push(im);});};
if(document.readyState==='complete')setTimeout(warm,400);else window.addEventListener('load',function(){setTimeout(warm,400);});
['pointerover','touchstart','focusin'].forEach(function(ev){root.addEventListener(ev,warm,{passive:true});});
var mark=function(i,on){solos.forEach(function(s){if(of(s)===i)s.classList.toggle('on',on);});names.forEach(function(b){if(of(b)===i)b.classList.toggle('hov',on);});full.classList.toggle('hovering',on);};
var hov=function(i,on){if(cur>=0)return;mark(i,on);};
var calmDown=function(){ids.forEach(function(i){mark(i,false);});};
/* the band changes height smoothly between the painting and a profile; then() runs once, with the page laid out as it will end up */
var resize=function(change,then){var h0=band.offsetHeight;change();band.style.height='';var h1=band.offsetHeight;if(then)then();if(calm||phone.matches||Math.abs(h1-h0)<2)return;
  band.style.height=h0+'px';void band.offsetHeight;band.style.transition='height .55s cubic-bezier(.2,.7,.2,1)';band.style.height=h1+'px';
  clearTimeout(t1);t1=setTimeout(function(){band.style.transition='';band.style.height='';},600);};
/* a profile takes the page: the heading fades and the whole block moves up to just under the bar (a negative top margin, eased by the style sheet) */
var lift=function(on){document.body.classList.toggle('team-open',on);if(!hero)return;root.style.marginTop=on?(-Math.max(0,Math.round(hero.getBoundingClientRect().bottom+window.pageYOffset-90)))+'px':'';};
/* where person i stands on the screen now: the box their figure was cut from, inside whichever picture is showing */
var place=function(i){var h=hits.filter(function(b){return of(b)===i&&b.offsetParent;})[0];if(!h)return null;var r=h.parentElement.getBoundingClientRect(),cs=getComputedStyle(h),v=function(k){return parseFloat(cs.getPropertyValue(k))/100;};
  return {left:r.left+v('--bx')*r.width,top:r.top+v('--by')*r.height,width:v('--bw')*r.width,height:v('--bh')*r.height};};
var fill=function(i){ids.forEach(function(j){items[j].classList.toggle('cur',j===i);});vimg.src=art[i];count.textContent=two(at(i)+1)+' / '+two(n);
  var pv=who[step(i,-1)],nx=who[step(i,1)];$('.gv-pn',view).textContent=pv;$('.gv-nn',view).textContent=nx;$('.gv-prev',view).setAttribute('aria-label','Previous: '+pv);$('.gv-next',view).setAttribute('aria-label','Next: '+nx);
  view.setAttribute('aria-label',who[i]);};
var open=function(i,from,byKey){
  if(at(i)<0)return;warm();var first=cur<0;if(from)opener=from;if(first)y0=window.pageYOffset;
  var a=first?place(i):null;                                                       /* where the chosen person is standing now */
  var held=stack.contains(document.activeElement);   /* keyboard focus was on the text being replaced: it moves to the new person's text */
  calmDown();cur=i;root.classList.remove('shown');
  resize(function(){fill(i);root.classList.add('open');if(first)lift(true);});
  if(window.pageYOffset>0)window.scrollTo(0,0);
  if(first&&a&&!calm){var b=vfig.getBoundingClientRect();                         /* the figure starts where the person stood in the painting and steps across to its place */
    vfig.style.transition='none';vfig.style.transform='translate('+(a.left-b.left)+'px,'+(a.top-b.top)+'px) scale('+(a.width/b.width)+')';void vfig.offsetWidth;vfig.style.transition='';vfig.style.transform='';}
  requestAnimationFrame(function(){requestAnimationFrame(function(){root.classList.add('shown');});});
  if(byKey||held)items[i].focus({preventScroll:true});
};
var close=function(){if(cur<0)return;cur=-1;
  var jump=y0>4;if(jump)root.style.transition='none';
  resize(function(){root.classList.remove('open');root.classList.remove('shown');lift(false);fitFirst();});if(jump){void root.offsetHeight;root.style.transition='';}vfig.style.transform='';
  if(Math.abs(window.pageYOffset-y0)>1)window.scrollTo(0,y0);   /* the page goes back to where it was before the first person was opened */
  if(opener&&document.activeElement&&view.contains(document.activeElement))opener.focus({preventScroll:true});opener=null;};
/* first screen (wide): trim the painting by exactly what the heading + painting + names overshoot the window */
var fitFirst=function(){if(cur>=0)return;root.style.removeProperty('--trim');root.style.removeProperty('--thero');if(phone.matches||!hero||!under)return;
  var top=hero.getBoundingClientRect().bottom+window.pageYOffset,t=0;root.style.setProperty('--thero',Math.ceil(top)+'px');   /* the real foot of the heading, in place of the style sheet's estimate */
  for(var k=0;k<3;k++){var w0=full.offsetWidth,over=top+full.offsetHeight+1+under.offsetHeight-window.innerHeight;if(over<=.5)break;t+=over;root.style.setProperty('--trim',t+'px');
    if(full.offsetWidth===w0)break;}};   /* trimming changed nothing: the painting is holding its size and the names go below the first screen */
hits.forEach(function(p){var i=of(p);
  p.addEventListener('click',function(e){open(i,p,e.detail===0);});
  p.addEventListener('pointerenter',function(e){if(e.pointerType==='mouse'&&!phone.matches)hov(i,true);});p.addEventListener('pointerleave',function(e){if(e.pointerType==='mouse')hov(i,false);});});
names.forEach(function(b){var i=of(b);b.addEventListener('click',function(e){open(i,b,e.detail===0);});
  b.addEventListener('pointerenter',function(e){if(e.pointerType==='mouse'&&!phone.matches)hov(i,true);});b.addEventListener('pointerleave',function(e){if(e.pointerType==='mouse')hov(i,false);});
  b.addEventListener('focus',function(){var kb=false;try{kb=b.matches(':focus-visible');}catch(e){}if(kb&&!phone.matches)hov(i,true);});b.addEventListener('blur',function(){hov(i,false);});});
$('.gv-close',view).addEventListener('click',close);
$('.gv-prev',view).addEventListener('click',function(){open(step(cur,-1));});$('.gv-next',view).addEventListener('click',function(){open(step(cur,1));});
document.addEventListener('keydown',function(e){if(cur<0)return;if(e.key==='Escape')close();else if(view.contains(document.activeElement)){if(e.key==='ArrowRight')open(step(cur,1));else if(e.key==='ArrowLeft')open(step(cur,-1));}});
var rz=0;window.addEventListener('resize',function(){if(rz)return;rz=requestAnimationFrame(function(){rz=0;fitFirst();});});
fitFirst();if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fitFirst);
})();

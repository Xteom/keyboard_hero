
const SR=22050,N=1024,HOP=256,HT=HOP/SR,OFS=N/2/SR;
const TARGET=[1.2,1.8,2.5,3.2,4.0],GAP=[0.25,0.2,0.15,0.12,0.1],MOODF={calm:0.6,groove:1,peak:1.35};
function fft(re,im){const n=re.length;for(let i=1,j=0;i<n;i++){let bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j){let t=re[i];re[i]=re[j];re[j]=t;t=im[i];im[i]=im[j];im[j]=t;}}
 for(let len=2;len<=n;len<<=1){const h=len>>1,a=-2*Math.PI/len,wr=Math.cos(a),wi=Math.sin(a);for(let i=0;i<n;i+=len){let cr=1,ci=0;for(let k=0;k<h;k++){const p=i+k,q=p+h;const vr=re[q]*cr-im[q]*ci,vi=re[q]*ci+im[q]*cr;re[q]=re[p]-vr;im[q]=im[p]-vi;re[p]+=vr;im[p]+=vi;const t=cr*wr-ci*wi;ci=cr*wi+ci*wr;cr=t;}}}}
function mean(a){let s=0;for(let i=0;i<a.length;i++)s+=a[i];return a.length?s/a.length:0;}
function rng(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function analyze(x,seed,prog){
 prog=prog||function(){};
 const dur=x.length/SR,F=Math.max(0,Math.floor((x.length-N)/HOP)+1);
 const empty=()=>({version:1,duration:dur,bpm:0,beats:[],sections:[{start:0,end:dur,mood:'groove'}],charts:[1,2,3,4,5].map(l=>({level:l,lanes:l+1,notes:[]}))});
 if(F<6*SR/HOP)return empty();
 const B=N/2,lowB=Math.round(200/(SR/N)),midB=Math.round(2000/(SR/N));
 const win=new Float64Array(N);for(let i=0;i<N;i++)win[i]=0.5-0.5*Math.cos(2*Math.PI*i/N);
 const fl=new Float32Array(F),fm=new Float32Array(F),fh=new Float32Array(F),cen=new Float32Array(F),rms=new Float32Array(F);
 let prev=new Float32Array(B),cur=new Float32Array(B);const re=new Float64Array(N),im=new Float64Array(N);
 for(let f=0;f<F;f++){const o=f*HOP;let e=0;for(let i=0;i<N;i++){const s=x[o+i];re[i]=s*win[i];im[i]=0;e+=s*s;}rms[f]=Math.sqrt(e/N);
  fft(re,im);let a=0,b=0,c=0,cs=0,ms=0;
  for(let k=1;k<B;k++){const m=Math.log(1+100*Math.sqrt(re[k]*re[k]+im[k]*im[k]));cur[k]=m;const d=m-prev[k];if(d>0){if(k<lowB)a+=d;else if(k<midB)b+=d;else c+=d;}cs+=k*m;ms+=m;}
  fl[f]=a;fm[f]=b;fh[f]=c;cen[f]=ms>0?cs/ms:0;const t=prev;prev=cur;cur=t;
  if((f&2047)===0)prog(0.7*f/F);}
 const mL=mean(fl)||1,mM=mean(fm)||1,mH=mean(fh)||1;
 const env=new Float32Array(F);for(let f=0;f<F;f++)env[f]=fl[f]/mL+fm[f]/mM+fh[f]/mH;
 // onsets
 const onsets=[];const W=8;
 for(let f=W;f<F-W;f++){let s=0;for(let j=f-W;j<=f+W;j++)s+=env[j];const thr=s/(2*W+1)*1.3+0.25;if(env[f]<=thr)continue;
  let mx=true;for(let j=f-3;j<=f+3;j++)if(env[j]>env[f]){mx=false;break;}
  if(mx&&(!onsets.length||f-onsets[onsets.length-1].f>=4))onsets.push({f,t:f*HT+OFS,s:env[f]});}
 if(analyze.__debug)analyze.__dbg={onsets:onsets.map(o=>o.t),env,fl,fm,fh,rms,F};
 if(onsets.length<8)return empty();
 {const cs=onsets.map(o=>cen[o.f]).sort((a,b)=>a-b);for(const o of onsets){let lo=0,hi=cs.length;const v=cen[o.f];while(lo<hi){const m=(lo+hi)>>1;if(cs[m]<v)lo=m+1;else hi=m;}o.b=Math.min(0.9999,lo/cs.length);}}
 prog(0.75);
 // tempo
 const od=new Float32Array(F);{const m=mean(env);let s2=0;for(let f=0;f<F;f++){od[f]=Math.max(0,env[f]-m);s2+=od[f]*od[f];}const sd=Math.sqrt(s2/F)||1;for(let f=0;f<F;f++)od[f]/=sd;}
 const ac=(L,a,b)=>{let s=0;const n=b-a-L;if(n<=0)return 0;for(let f=a;f<b-L;f++)s+=od[f]*od[f+L];return s/n;};
 function bestP(a,b,minL,maxL,cBpm,sig){let best=-1e9,bl=minL;const sc={};for(let L=minL;L<=maxL;L++){let v=ac(L,a,b)+0.5*ac(2*L,a,b);const bpm=60/(L*HT);v*=Math.exp(-0.5*Math.pow(Math.log2(bpm/cBpm)/sig,2));sc[L]=v;if(v>best){best=v;bl=L;}}
  const y0=sc[bl-1],y1=sc[bl],y2=sc[bl+1];let d=0;if(y0!==undefined&&y2!==undefined){const den=y0-2*y1+y2;if(den<0)d=0.5*(y0-y2)/den;}return bl+Math.max(-0.5,Math.min(0.5,d));}
 const minL=Math.round(60/200/HT),maxL=Math.round(60/60/HT);
 // global tempo: ACF + half-lag (subdivision) support, log-normal prior centred 140 BPM (sigma 0.8 oct).
 // The half-lag term rejects 2/3 metric levels (e.g. 87 vs 130), whose half period is not periodic.
 let P0=(()=>{const mx=Math.ceil(maxL)+2,A=new Float32Array(mx+1);for(let L=1;L<=mx;L++)A[L]=ac(L,0,F);
  const ax=Lf=>{const L=Math.floor(Lf),u=Lf-L;return A[L]*(1-u)+A[Math.min(mx,L+1)]*u;};
  let best=-1e9,bb=120;for(let b=60;b<=200;b+=0.25){const L=60/b/HT;let v=ax(L)+0.5*ax(L/2);v*=Math.exp(-0.5*Math.pow(Math.log2(b/140)/0.8,2));if(v>best){best=v;bb=b;}}
  return 60/bb/HT;})();
 // T vs 2T: a fast candidate (>140) needs real subdivision activity; sparse onsets (<2.2 per beat) mean half tempo.
 if(60/(P0*HT)>140&&onsets.length/dur/(60/(P0*HT)/60)<2.2&&60/(2*P0*HT)>=60)P0*=2;
 const bpm0=60/(P0*HT);
 const per=new Float32Array(F).fill(P0);
 {const wl=Math.round(12/HT),st=Math.round(6/HT);const cs=[],ps=[];
  for(let a=0;a+wl<=F;a+=st){cs.push(a+wl/2);ps.push(bestP(a,a+wl,Math.max(minL,Math.floor(P0*0.85)),Math.min(maxL*2,Math.ceil(P0*1.18)),bpm0,0.12));}
  if(ps.length>=3){const sm=ps.map((p,i)=>{const w=[ps[i-1]??p,p,ps[i+1]??p].sort((a,b)=>a-b);return w[1];});
   for(let f=0;f<F;f++){let i=0;while(i<cs.length-1&&cs[i+1]<f)i++;if(f<=cs[0])per[f]=sm[0];else if(f>=cs[cs.length-1])per[f]=sm[sm.length-1];else{const u=(f-cs[i])/(cs[i+1]-cs[i]);per[f]=sm[i]*(1-u)+sm[i+1]*u;}}}}
 prog(0.8);
 const sc=new Float32Array(F),bk=new Int32Array(F).fill(-1);const ALPHA=100;
 for(let f=0;f<F;f++){const P=per[f];const lo=Math.max(0,Math.floor(f-2*P)),hi=Math.floor(f-P/2);let best=-1e9,bi=-1;
  for(let j=lo;j<=hi;j++){const d=Math.log((f-j)/P);const v=sc[j]-ALPHA*d*d;if(v>best){best=v;bi=j;}}
  if(bi>=0&&best>0){sc[f]=od[f]+best;bk[f]=bi;}else sc[f]=od[f];}
 let f0=F-1,bs=-1e9;for(let f=Math.max(0,Math.floor(F-1-per[F-1]));f<F;f++)if(sc[f]>bs){bs=sc[f];f0=f;}
 const bf=[];for(let f=f0;f>=0;f=bk[f])bf.push(f);bf.reverse();
 let beats=bf.map(f=>f*HT+OFS);
 // average tempo over the tracked beats (handles rubato); trusted only when close to the global ACF tempo
 const bpmFit=beats.length>8?60*(beats.length-1)/(beats[beats.length-1]-beats[0]):bpm0;
 if(beats.length<4)return empty();
 {const P=60/bpm0;while(beats[0]-P>0.05)beats.unshift(beats[0]-P);while(beats[beats.length-1]+P<dur)beats.push(beats[beats.length-1]+P);}
 const bpm=Math.abs(bpmFit/bpm0-1)<0.03?bpmFit:bpm0;
 prog(0.85);
 // downbeat
 const fr=t=>Math.max(0,Math.min(F-1,Math.round((t-OFS)/HT)));
 let db=0,dbs=-1;for(let k=0;k<4;k++){let s=0;for(let i=k;i<beats.length;i+=4)s+=fl[fr(beats[i])];if(s>dbs){dbs=s;db=k;}}
 // bars
 const bars=[];for(let i=db;i+4<beats.length;i+=4)bars.push({start:beats[i],end:beats[i+4]});
 if(!bars.length)bars.push({start:0,end:dur});bars[0].start=0;bars[bars.length-1].end=dur;
 for(const br of bars){let e=0,n=0;for(let f=fr(br.start);f<=fr(br.end);f++){e+=rms[f];n++;}br.db=20*Math.log10((e/Math.max(1,n))+1e-6);let c=0;for(const o of onsets)if(o.t>=br.start&&o.t<br.end)c++;br.dens=c/Math.max(0.1,br.end-br.start);}
 // sections: blocks of 8 bars
 const blocks=[];for(let i=0;i<bars.length;i+=8){const g=bars.slice(i,i+8);if(g.length<4&&blocks.length){const L=blocks[blocks.length-1];L.end=g[g.length-1].end;L.n+=g.length;continue;}
  blocks.push({start:g[0].start,end:g[g.length-1].end,db:mean(g.map(x=>x.db)),dens:mean(g.map(x=>x.dens)),n:g.length});}
 const pct=(a,q)=>{const s=a.slice().sort((x,y)=>x-y);return s[Math.min(s.length-1,Math.max(0,Math.round(q*(s.length-1))))];};
 const bdb=blocks.map(b=>b.db),bdn=blocks.map(b=>b.dens);const dbMin=pct(bdb,0.1),dbMax=pct(bdb,0.9),dnMin=pct(bdn,0.1),dnMax=pct(bdn,0.9);
 if(analyze.__debug)analyze.__dbg.blocks=blocks;
 let sections;
 if(dbMax-dbMin<6||blocks.length<2)sections=[{start:0,end:dur,mood:'groove'}];
 else{sections=[];for(const b of blocks){const cl=u=>Math.max(0,Math.min(1,u));const v=0.9*cl((b.db-dbMin)/(dbMax-dbMin))+0.1*cl((b.dens-dnMin)/Math.max(1e-6,dnMax-dnMin));const mood=v<0.35?'calm':v>0.85?'peak':'groove';
   const L=sections[sections.length-1];if(L&&L.mood===mood)L.end=b.end;else sections.push({start:b.start,end:b.end,mood});}
  sections[0].start=0;sections[sections.length-1].end=dur;}
 for(const s of sections){s.start=Math.round(s.start*1e4)/1e4;s.end=Math.round(s.end*1e4)/1e4;}
 prog(0.9);
 // charts
 const bl=60/bpm;const strs=onsets.map(o=>o.s).sort((a,b)=>a-b);const thr85=strs[Math.floor(strs.length*0.85)];
 const idxOf=t=>{let lo=0,hi=beats.length-1;while(hi-lo>1){const m=(lo+hi)>>1;if(beats[m]<=t)lo=m;else hi=m;}return lo;};
 const snap=(t,sub)=>{if(t<=beats[0]||t>=beats[beats.length-1])return t;const i=idxOf(t),a=beats[i],b=beats[i+1],stp=(b-a)/sub;const g=a+Math.round((t-a)/stp)*stp;return Math.abs(g-t)<=0.03?g:t;};
 const nearBeat=t=>{const i=idxOf(t);return Math.min(Math.abs(t-beats[i]),Math.abs((beats[i+1]??1e9)-t))<0.04;};
 const charts=[];
 for(let L=1;L<=5;L++){const lanes=L+1,sub=L<=2?2:4,gap=GAP[L-1],slg=Math.max(0.1,bl/4);const rnd=rng((seed|0)+L*7919);
  let picked=[];
  const quotas=[],used=[];
  for(let si=0;si<sections.length;si++){const s=sections[si];quotas.push(0);used.push(0);const a=Math.max(s.start,2),b=Math.min(s.end,dur-0.3);if(b<=a)continue;const quota=quotas[si]=Math.floor(TARGET[L-1]*MOODF[s.mood]*(b-a));
   const c=onsets.filter(o=>o.t>=a&&o.t<b).sort((x,y)=>y.s-x.s);const ch=[];
   for(const o of c){if(ch.length>=quota)break;const t=Math.round(snap(o.t,sub)*1e4)/1e4;if(t<a||t>=b)continue;let ok=true;for(const q of ch)if(Math.abs(q.t-t)<gap){ok=false;break;}if(ok)ch.push({t,s:o.s,b:o.b,mood:s.mood,si});}
   picked=picked.concat(ch);}
  picked.sort((x,y)=>x.t-y.t);const seq=[];for(const p of picked){if(seq.length&&p.t-seq[seq.length-1].t<gap)continue;seq.push(p);}
  const notes=[];const last=new Array(lanes).fill(-9);let run=0,pl=-1;const rem=quotas.map(()=>0);for(const p of seq)rem[p.si]++;
  for(const p of seq){rem[p.si]--;let lane=Math.min(lanes-1,Math.floor(p.b*lanes));
   if(lane===pl&&run>=2&&rnd()<0.6)lane=Math.max(0,Math.min(lanes-1,lane+(rnd()<0.5?-1:1)));
   if(p.t-last[lane]<slg){let bst=-1;for(let d=1;d<lanes&&bst<0;d++)for(const c of [lane-d,lane+d])if(c>=0&&c<lanes&&p.t-last[c]>=slg){bst=c;break;}if(bst<0)continue;lane=bst;}
   run=lane===pl?run+1:0;pl=lane;last[lane]=p.t;notes.push({t:Math.round(p.t*1e4)/1e4,lane});used[p.si]++;
   if(L>=3&&p.mood==='peak'&&p.s>=thr85&&nearBeat(p.t)&&used[p.si]+rem[p.si]<quotas[p.si]&&rnd()<0.35){const l2=(lane+Math.max(1,Math.floor(lanes/2)))%lanes;if(p.t-last[l2]>=slg){last[l2]=p.t;used[p.si]++;notes.push({t:Math.round(p.t*1e4)/1e4,lane:l2});}}}
  charts.push({level:L,lanes,notes});}
 prog(1);
 return {version:1,duration:dur,bpm:Math.round(bpm*10)/10,beats:beats.map(b=>Math.round(b*1e4)/1e4),sections,charts};
}
if(typeof WorkerGlobalScope!=='undefined'&&self instanceof WorkerGlobalScope){self.onmessage=e=>{try{const r=analyze(e.data.samples,e.data.seed,p=>self.postMessage({type:'progress',p}));self.postMessage({type:'done',result:r});}catch(err){self.postMessage({type:'error',message:String(err&&err.message||err)});}};}

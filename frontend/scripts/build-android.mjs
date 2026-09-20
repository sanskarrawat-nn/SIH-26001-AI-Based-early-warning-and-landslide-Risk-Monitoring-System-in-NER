import {spawnSync} from 'node:child_process';
const url=process.env.VITE_API_URL;
if(!url||!/^https:\/\/.+\/api\/?$/.test(url)) {console.error('Set VITE_API_URL to your deployed HTTPS backend ending in /api before building Android.');process.exit(1);}
const npm=process.platform==='win32'?'npm.cmd':'npm';
for(const args of [['run','build'],['exec','--','cap','sync','android']]){const r=spawnSync(npm,args,{stdio:'inherit',env:process.env,shell:process.platform==='win32'});if(r.status!==0)process.exit(r.status||1);}

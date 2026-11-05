import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';
import {loadEnv} from 'vite';
import {fileURLToPath} from 'node:url';
import {readFileSync,readdirSync} from 'node:fs';
import type {Plugin} from 'vite';
const root=fileURLToPath(new URL('../',import.meta.url));
function fixtureAssets():Plugin {return {name:'connected-fixture-assets',configureServer(server){server.middlewares.use('/fixtures',(req,res,next)=>{const name=(req.url??'').split('?')[0].replace(/^\//,'');if(!/^[a-z_]+\.json$/.test(name))return next();try{res.setHeader('Content-Type','application/json');res.end(readFileSync(`${root}/demo/fixtures/${name}`));}catch{res.statusCode=404;res.end('Fixture not found');}});},generateBundle(){for(const file of readdirSync(`${root}/demo/fixtures`)){if(file.endsWith('.json'))this.emitFile({type:'asset',fileName:`fixtures/${file}`,source:readFileSync(`${root}/demo/fixtures/${file}`)});}}};}
// HTTP deployments must not resolve or publish the optional, gitignored demo tree.
function httpOnlyAdapter():Plugin {const id='\0aroundyou-http-only-mock';return {name:'http-only-adapter',enforce:'pre',resolveId(source){if(source.endsWith('/services/mock-adapter'))return id;},load(source){if(source===id)return "export async function createMockAdapter(){throw new Error('Demo adapter is excluded from this HTTP build.')}";}};}
export default defineConfig(({mode})=>{const env=loadEnv(mode,fileURLToPath(new URL('.',import.meta.url)),''),demo=mode==='test'||env.VITE_AROUNDYOU_MODE==='demo';return {plugins:[react(),...(demo?[fixtureAssets()]:[httpOnlyAdapter()])],define:{'import.meta.env.VITE_AROUNDYOU_MODE':JSON.stringify(demo?'demo':'http')},resolve:{alias:{'@demo':`${root}/demo/src/service.mjs`}},server:{fs:{allow:[root]}},test:{env:{VITE_AROUNDYOU_MODE:'demo',DEBUG_PRINT_LIMIT:'1200'},fileParallelism:false,testTimeout:20000,environment:'jsdom',setupFiles:['./tests/setup.ts'],include:['tests/**/*.test.ts','tests/**/*.test.tsx']}};});

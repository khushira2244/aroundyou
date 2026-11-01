import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import type {DemoState} from '../src/services/contracts';
let initial:Promise<DemoState>|null=null;
async function readSeed():Promise<DemoState>{const base=resolve(process.cwd(),'../demo/fixtures');const read=async(name:string):Promise<unknown>=>JSON.parse(await readFile(resolve(base,name),'utf8'));const manifest=await read('manifest.json') as {schema_version:number;notice:string;initial_runtime:Record<string,unknown>;files:{table:string;file:string}[]};const entries=await Promise.all(manifest.files.map(async f=>{const rows=await read(f.file) as ({id:string}&Record<string,unknown>)[];return [f.table,Object.fromEntries(rows.map(x=>[x.id,x]))] as const}));return {meta:{schema_version:manifest.schema_version,notice:manifest.notice},runtime:manifest.initial_runtime,tables:Object.fromEntries(entries)}}
export async function testSeed():Promise<DemoState>{initial??=readSeed();return structuredClone(await initial)}

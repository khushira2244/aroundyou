declare module '@demo' {
  import type {DemoState,Result} from '../services/contracts';
  export const ORGANIZER:string;
  export const SPONSOR:string;
  export class DemoService {
    constructor(seed:DemoState,options?:{accountId?:string});
    revision:number;accountId:string;
    snapshot():DemoState;
    switchDemoAccount(id:string):unknown;
    forkFlashback():DemoService;
    request<T=unknown>(operation:string,input?:Record<string,unknown>,options?:{expectedRevision?:number;onState?:(state:{status:string})=>void}):Promise<Result<T>>;
  }
  export function loadBrowserFixture(base:string):Promise<DemoState>;
}

import thumbnail from '../assets/canary-hill-dashboard.jpg';
import cover from '../assets/canary-hill-profile.jpg';
/** Bundled user-supplied images, shared by the seed and authored Canary Hill replay. */
export function eventImages(event:{id:string;title:string}){return event.id==='event-canary-hill-001'||/canary[\s_-]*hills?/i.test(event.title)?{thumbnail,cover}:null;}

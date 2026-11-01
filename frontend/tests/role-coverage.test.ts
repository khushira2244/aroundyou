import {it,expect} from 'vitest';
import {roleCoverage} from '../src/shared/roleCoverage';
const s=(start:number,end:number,day=1)=>({start_day:day,end_day:day,start_minute:start,end_minute:end,timezone:'Asia/Kolkata'});
it('merges parallel and adjacent work windows instead of summing team effort',()=>{const c=roleCoverage({commitment:{effort_person_hours:null,schedule_intervals:[s(540,660),s(540,660),s(660,720)]}});expect(c?.hours).toBe(3);expect(c?.windows).toEqual(['Day 1, 09:00–12:00 (Asia/Kolkata)'])});
it('keeps separate days and returns no invented hours for missing schedules',()=>{expect(roleCoverage({commitment:{effort_person_hours:null,schedule_intervals:[s(540,660),s(540,600,2)]}})?.hours).toBe(3);expect(roleCoverage({commitment:{effort_person_hours:null,schedule_intervals:[]}})).toBeNull()});

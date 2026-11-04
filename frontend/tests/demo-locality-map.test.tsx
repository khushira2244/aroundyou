import {it,expect,vi,afterEach} from 'vitest';
import {render,waitFor,fireEvent,cleanup} from '@testing-library/react';
import {GoogleEventMap} from '../src/shared/GoogleEventMap';

afterEach(()=>{cleanup();delete window.google;vi.restoreAllMocks()});
it('places all ten demo icons at independent supplied coordinates and clicks the correct event without offsets',async()=>{
 const markers:any[]=[];
 class FakeMap {addListener=vi.fn();fitBounds=vi.fn();setCenter=vi.fn();setZoom=vi.fn()}
 class Autocomplete {constructor(){return document.createElement('div')}}
 class Marker {map:any;constructor(public options:any){this.map=options.map;markers.push(this)}}
 const maps={importLibrary:async()=>({Map:FakeMap,PlaceAutocompleteElement:Autocomplete}),marker:{AdvancedMarkerElement:Marker},LatLngBounds:class {extend=vi.fn()}};
 window.google={maps};
 const events=Array.from({length:10},(_,i)=>({id:`event-${i}`,title:`Demo event ${i}`,category:'Education',location:{label:'Demo · Approximate location — venue unverified.',confidence:'demo_approximate_locality',coordinates:{lat:23.97+i*.0021,lng:85.3+i*.0037},source_id:'locality-reference',precise_meeting_point:null}}));
 const onSelect=vi.fn();render(<GoogleEventMap events={events} onSelect={onSelect}/>);
 await waitFor(()=>expect(markers).toHaveLength(10));
 markers.forEach((marker,i)=>{expect(marker.options.position).toEqual(events[i].location.coordinates);expect(marker.options.content.style.transform).toBe('');expect(marker.options.title).toContain('Demo · Approximate location — venue unverified.');fireEvent.click(marker.options.content);expect(onSelect).toHaveBeenLastCalledWith(events[i].id)});
});

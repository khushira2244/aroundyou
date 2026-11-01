import {RecoveryPanel} from '../recovery/RecoveryPanel';
import type {OrganizerDashboard} from '../../services/organizer-contracts';
import type {OrganizerActions} from './OrganizerShared';
export function OrganizerBlockers({d}:{d:OrganizerDashboard;act:OrganizerActions;busy:boolean}){return <RecoveryPanel eventId={d.event.id}/>;}

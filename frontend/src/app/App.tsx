import {Navigate,Route,Routes,useLocation} from 'react-router-dom';
import type {ReactNode} from 'react';
import {useApp} from './provider';
import {Signup} from '../features/auth/Signup';
import {Discovery} from '../features/discovery/Discovery';
import {Wizard} from '../features/event-creation/Wizard';
import {Success} from '../features/event-creation/Success';
import {Governance} from '../features/governance/Governance';
import {StagePlanning} from '../features/planning/StagePlanning';
import {WorkDesign} from '../features/planning/WorkDesign';
import {ActorRequirements} from '../features/planning/ActorRequirements';
import {EventSetup} from '../features/event-setup/EventSetup';
import {FinalizePublish} from '../features/event-setup/FinalizePublish';
import {EventProfile} from '../features/event-profile/EventProfile';
import {OrganizerManagement} from '../features/organizer/OrganizerManagement';
import {SponsorRegistration} from '../features/sponsor-registration/SponsorRegistration';
import {SponsorDashboard} from '../features/sponsor-dashboard/SponsorDashboard';
import {SponsorOpportunities,SponsorshipDetails} from '../features/sponsor-opportunities/SponsorOpportunities';
import {SponsorOfferForm,SponsorOffers} from '../features/sponsor-offers/SponsorOffers';
import {SponsorProfile,SponsorSettings} from '../features/sponsor-profile/SponsorProfile';
import {SponsorMapPage,SponsorImpact} from '../features/sponsor-impact/SponsorImpact';
import {JoinEvents} from '../features/participation/JoinEvents';
import {JoinApplication} from '../features/participation/JoinApplication';
import {MyEvents} from '../features/participation/MyEvents';
import {ParticipantWorkspace} from '../features/participation/ParticipantWorkspace';
function DemoOnly({children}:{children:ReactNode}){const {identity}=useApp(),location=useLocation();return identity?children:<Navigate to="/signup" state={{from:location.pathname}} replace/>}
function AccountEntry(){const {identity,service}=useApp();return service?.mode==='http'&&identity?<Navigate to="/discover" replace/>:<Signup/>}
export function App(){return <Routes><Route path="/sponsor/register/:step" element={<DemoOnly><SponsorRegistration/></DemoOnly>}/><Route path="/sponsor" element={<DemoOnly><SponsorDashboard/></DemoOnly>}/><Route path="/sponsor/profile" element={<DemoOnly><SponsorProfile/></DemoOnly>}/><Route path="/sponsor/settings" element={<DemoOnly><SponsorSettings/></DemoOnly>}/><Route path="/sponsor/opportunities" element={<DemoOnly><SponsorOpportunities/></DemoOnly>}/><Route path="/sponsor/opportunities/:eventId" element={<DemoOnly><SponsorshipDetails/></DemoOnly>}/><Route path="/sponsor/opportunities/:eventId/offer" element={<DemoOnly><SponsorOfferForm/></DemoOnly>}/><Route path="/sponsor/offers" element={<DemoOnly><SponsorOffers/></DemoOnly>}/><Route path="/sponsor/map" element={<DemoOnly><SponsorMapPage/></DemoOnly>}/><Route path="/sponsor/impact" element={<DemoOnly><SponsorImpact/></DemoOnly>}/><Route path="/signup" element={<AccountEntry/>}/><Route path="/discover" element={<DemoOnly><Discovery/></DemoOnly>}/><Route path="/events/:eventId" element={<DemoOnly><EventProfile/></DemoOnly>}/><Route path="/create/:step" element={<DemoOnly><Wizard/></DemoOnly>}/><Route path="/events/:eventId/created" element={<DemoOnly><Success/></DemoOnly>}/><Route path="/events/:eventId/planning" element={<DemoOnly><StagePlanning/></DemoOnly>}/><Route path="/events/:eventId/governance" element={<DemoOnly><Governance/></DemoOnly>}/><Route path="/events/:eventId/governance/ticket" element={<DemoOnly><Governance ticketView/></DemoOnly>}/><Route path="/events/:eventId/work/:stageId?" element={<DemoOnly><WorkDesign/></DemoOnly>}/><Route path="/events/:eventId/actors" element={<DemoOnly><ActorRequirements/></DemoOnly>}/><Route path="/events/:eventId/manage/:section?" element={<DemoOnly><OrganizerManagement/></DemoOnly>}/><Route path="/events/:eventId/setup" element={<DemoOnly><EventSetup/></DemoOnly>}/><Route path="/events/:eventId/finalize" element={<DemoOnly><FinalizePublish/></DemoOnly>}/><Route path="/join-events" element={<DemoOnly><JoinEvents/></DemoOnly>}/><Route path="/events/:eventId/join" element={<DemoOnly><JoinApplication/></DemoOnly>}/><Route path="/events/:eventId/participation/:section?" element={<DemoOnly><ParticipantWorkspace/></DemoOnly>}/><Route path="/my-events" element={<DemoOnly><MyEvents/></DemoOnly>}/><Route path="/my-events/:section" element={<DemoOnly><MyEvents/></DemoOnly>}/><Route path="*" element={<Navigate to="/signup" replace/>}/></Routes>}

declare module '*.jpg' {const source:string;export default source;}

declare module '*recovery-replay.mjs' { export function buildRecoveryReplay(seed: import('../services/contracts').DemoState): Promise<import('../services/contracts').DemoState>; }

declare module '*ten-participants.mjs' { export function buildTenParticipantScenario(seed: import('../services/contracts').DemoState): Promise<import('../services/contracts').DemoState>; }

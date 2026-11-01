/** Secure backend integration boundary. No browser key or live provider configured. */
export interface RecoveryReasoningInput {blocker_id:string;active_plan_id:string;investigation_version:number;confirmed_facts:unknown[];unknown_facts:string[];deterministic_impact:unknown;execution_snapshot:unknown;permitted_scope:string[]}
export interface RecoveryReasoningResult {provider:string;model:string;timestamp:string;blocker_id:string;active_plan_id:string;investigation_version:number;observations:string[];recommendations:{action:string;preconditions:string[];uncertainties:string[]}[];limitations:string[];source:'secure_backend_provider'}
export interface RecoveryReasoningAdapter {configured:boolean;reason(input:RecoveryReasoningInput):Promise<RecoveryReasoningResult>}
export const unavailableRecoveryReasoning:RecoveryReasoningAdapter={configured:false,async reason(){throw new Error('Live AI recovery reasoning is unavailable. Deterministic investigation remains available.')}};

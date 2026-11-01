import type {CreationForm} from '../../services/contracts';
export interface StepProps {form:CreationForm;update:<K extends keyof CreationForm>(key:K,value:CreationForm[K])=>void;errors:Record<string,string>}

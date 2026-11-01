import type {ReactNode} from 'react';
export function Field({label,required,error,hint,children,className=''}:{label:string;required?:boolean;error?:string;hint?:string;children:ReactNode;className?:string}){return <div className={`field ${className}`}><label><span>{label}{required&&<em> *</em>}</span>{children}</label>{hint&&<small>{hint}</small>}{error&&<small className="field-error" role="alert">{error}</small>}</div>}
export function Banner({children}:{children:ReactNode}){return <div className="notice">{children}</div>}

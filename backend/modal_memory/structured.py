"""Pure offline-testable schema, exact-quote validation and content-free diagnostics."""
import hashlib,json
TITLE='Reviewed operational source excerpt'
def source_digest(sources):
    return hashlib.sha256(json.dumps(sources,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def choices(sources):
    selected={}
    for source in sources:
        if set(source)!={'source_id','text'} or not isinstance(source['source_id'],str) or not 1<=len(source['source_id'])<=36 or not isinstance(source['text'],str):raise ValueError('Invalid source contract')
        record=json.loads(source['text']);quotes=[]
        for key in ('interventions','blocker_categories','actions_attempted','outcome'):
            if key in record:
                quote=json.dumps(key)+': '+json.dumps(record[key],sort_keys=True)
                if 8<=len(quote)<=500 and quote in source['text']:quotes.append(quote)
        if not quotes:raise ValueError('No bounded exact operational excerpt')
        if source['source_id'] in selected:raise ValueError('Duplicate source')
        selected[source['source_id']]=quotes
    return selected
def schema_for(sources):
    available=choices(sources)
    return {'type':'object','additionalProperties':False,'required':['lessons'],'properties':{'lessons':{'type':'array','minItems':1,'maxItems':1,'items':{'type':'object','additionalProperties':False,'required':['source_id','title','excerpt'],'properties':{'source_id':{'type':'string','enum':list(available)},'title':{'type':'string','enum':[TITLE]},'excerpt':{'type':'string','enum':sorted({q for values in available.values() for q in values})}}}}}}
def constrained_parser(sources):
    from lmformatenforcer import StringParser,UnionParser
    # Finite JSON language: bind each ID to its own exact evidence excerpts.
    # Avoid JsonSchemaParser's escaped-quote enum incompatibility found offline.
    return UnionParser([StringParser(json.dumps({'lessons':[{'source_id':sid,'title':TITLE,'excerpt':quote}]},separators=(',',':'))) for sid,quotes in choices(sources).items() for quote in quotes])
def validate_output(text,sources):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate output key')
            result[key]=value
        return result
    output=json.loads(text,object_pairs_hook=unique)
    if not isinstance(output,dict) or set(output)!={'lessons'} or not isinstance(output['lessons'],list) or len(output['lessons'])!=1:raise ValueError('Output schema mismatch')
    allowed=choices(sources)
    for lesson in output['lessons']:
        if not isinstance(lesson,dict) or set(lesson)!={'source_id','title','excerpt'}:raise ValueError('Lesson schema mismatch')
        if lesson['title']!=TITLE or lesson['source_id'] not in allowed or lesson['excerpt'] not in allowed[lesson['source_id']]:raise ValueError('Unsupported source or factual excerpt')
    return output
def diagnostic(text,*,model,revision,sources,generated_tokens,max_tokens,eos_reached,error):
    # Redact every content character; retain JSON punctuation/whitespace only.
    excerpt=''.join(c if c in '{}[],:"\\` \n\r\t' else 'x' for c in text[:320])
    return {'model':model,'revision':revision,'source_digest':source_digest(sources),'generated_characters':len(text),'generated_tokens':generated_tokens,'finish_reason':'eos' if eos_reached else 'length' if generated_tokens>=max_tokens else 'unknown','possibly_truncated':not eos_reached and generated_tokens>=max_tokens,'error_type':type(error).__name__,'json_error':error.msg if isinstance(error,json.JSONDecodeError) else 'Strict schema/provenance validation failed','json_error_position':error.pos if isinstance(error,json.JSONDecodeError) else None,'redacted_excerpt':excerpt}

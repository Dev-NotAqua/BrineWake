import json
MT='editor_toolset.toolsets.material.MaterialTools.'
OT='editor_toolset.toolsets.object.ObjectTools.'
AS='editor_toolset.toolsets.asset.AssetTools.'
P='/Game/Brinewake/Ocean/M_BW_Water'
CODE=r'''// shore foam: a solid line at the waterline, lace left by the swash, bands rolling in over the shallows
float wob = sin(P.x*0.0031 + P.y*0.0017)*0.35 + sin(P.x*0.0013 - P.y*0.0027)*0.30;
float ph = T*0.9 + wob;
float rise = 0.5 + 0.5*sin(ph);
float shallow = 1.0 - smoothstep(0.0, 520.0, D);
float band = frac(D/210.0 + T*0.30 + wob*0.45);
float crest = smoothstep(0.55, 0.88, band) * (1.0 - smoothstep(0.88, 1.0, band));
float bands = crest * shallow * smoothstep(6.0, 70.0, D);
float edge = 1.0 - smoothstep(0.0, 22.0 + 30.0*rise, SD);
float lace = (1.0 - smoothstep(0.0, 170.0, SD)) * (0.35 + 0.65*rise);
// object foam: a bright collar and ripples running outward round anything that stands in the water.
// DF = distance to the nearest mesh (global distance field), DG = which way that mesh lies: the sea bed below is ignored.
float3 g = normalize(DG + float3(0.0, 0.0, 1e-4));
float beside = 1.0 - smoothstep(0.50, 0.88, g.z);
float w = max(OW, 1.0);
float collar = 1.0 - smoothstep(0.0, w*(0.30 + 0.18*rise), DF);
float ring = frac(DF/(w*0.5) - T*ORS + wob*0.6);
float ripples = smoothstep(0.52, 0.84, ring) * (1.0 - smoothstep(0.84, 1.0, ring)) * (1.0 - smoothstep(w*0.25, w*1.7, DF));
float objectFoam = (collar*1.6 + ripples*1.05) * beside * OS;
float f = edge*1.4 + bands*1.25 + lace*0.55 + objectFoam;
return saturate(smoothstep(0.38, 0.78, f * (0.40 + N*1.25)));'''
def call(n_,a): return execute_tool(n_,json.dumps(a))
def run():
    out={}
    mr={'refPath':P+'.M_BW_Water'}
    cu={'refPath':P+'.M_BW_Water:MaterialExpressionCustom_0'}
    p=json.loads(call(OT+'get_properties',{'instance':cu,'properties':['inputs']})['returnValue'])
    names=[i['inputName'] for i in p['inputs']]
    out['before']=names
    def add(cls,x,y,props=None):
        e=call(MT+'add_expression',{'material_or_function':mr,'expression_class':{'refPath':'/Script/Engine.MaterialExpression'+cls},'x':x,'y':y})['returnValue']
        if props: call(OT+'set_properties',{'instance':e,'values':json.dumps(props)})
        return e
    if 'DF' not in names:
        new=['DF','DG','OW','OS','ORS']
        grown=p['inputs']+[dict(p['inputs'][-1]) for _ in new]
        call(OT+'set_properties',{'instance':cu,'values':json.dumps({'inputs':grown})})
        p2=json.loads(call(OT+'get_properties',{'instance':cu,'properties':['inputs']})['returnValue'])
        for k,n in enumerate(new):
            p2['inputs'][len(names)+k]['inputName']=n
        call(OT+'set_properties',{'instance':cu,'values':json.dumps({'inputs':p2['inputs']})})
        dts=add('DistanceToNearestSurface',-3400,2600)
        dfg=add('DistanceFieldGradient',-3400,2750)
        ow=add('ScalarParameter',-3400,2900,{'parameterName':'Object Foam Width','defaultValue':240.0,'group':'Brinewake Object Foam'})
        os_=add('ScalarParameter',-3400,3000,{'parameterName':'Object Foam Strength','defaultValue':1.1,'group':'Brinewake Object Foam'})
        ors=add('ScalarParameter',-3400,3100,{'parameterName':'Object Ripple Speed','defaultValue':0.45,'group':'Brinewake Object Foam'})
        for e,n in ((dts,'DF'),(dfg,'DG'),(ow,'OW'),(os_,'OS'),(ors,'ORS')):
            o=call(MT+'get_expression_output_names',{'expression':e})['returnValue']
            call(MT+'connect_expressions',{'from_expression':e,'from_output_name':o[0] if o else '','to_expression':cu,'to_input_name':n})
    call(OT+'set_properties',{'instance':cu,'values':json.dumps({'code':CODE})})
    out['after']=call(MT+'get_expression_input_names',{'expression':cu})['returnValue']
    out['wiring']=str(call(MT+'get_expression_inputs',{'material_or_function':mr,'expression':cu})['returnValue'])[-900:]
    out['recompile']=str(call(MT+'recompile',{'material_or_function':mr}))[:300]
    call(AS+'save_assets',{'asset_paths':[P]})
    return out

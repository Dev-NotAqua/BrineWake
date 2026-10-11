import json
ST='editor_toolset.toolsets.scene.SceneTools.'
AT='editor_toolset.toolsets.actor.ActorTools.'
def call(n_,a): return execute_tool(n_,json.dumps(a))
def run():
    out={}
    for nm in ('BW_PlayerBody','BP_FirstPersonCharacter','BW_WaterFX'):
        try:
            acts=call(ST+'find_actors',{'root':None,'name':nm,'actor_type':None,'tag':'','bounds':None,'collision_channels':[]})['returnValue']
            out[nm]=[(a['refPath'].split(':')[0][-28:],call(AT+'get_actor_transform',{'actor':a})['returnValue']['location']) for a in acts[:3]]
        except Exception as e: out[nm]=str(e)[:150]
    try:
        n=call(ST+'find_actors',{'root':None,'name':'','actor_type':{'refPath':'/Script/Niagara.NiagaraActor'},'tag':'','bounds':None,'collision_channels':[]})['returnValue']
        out['niagara_actors']=len(n)
    except Exception as e: out['niagara_actors']=str(e)[:100]
    return out
